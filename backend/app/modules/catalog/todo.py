"""Admin "what to do today": the catalog work as a short to-do list instead of tools.

1. new codes from workshops wait for a decision (proposals);
2. keys that workshops have in stock but that are not on the public site yet
   (no description and no car/lock fits — the site does not publish empty pages);
3. keys on the site without a photo;
4. cards that look like the same key (same name, or codes differing by one end letter).
"""

import re
import uuid
from collections import defaultdict
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import distinct, exists, func, or_, select

from app.core.deps import SessionDep, require_admin_perm
from app.core.errors import AppError
from app.modules.admin.permissions import AdminPerm
from app.modules.catalog import service
from app.modules.catalog.models import (
    CatalogImage,
    CatalogItem,
    CatalogProposal,
    DuplicateDismissal,
    ItemCode,
    ItemLockFit,
    ItemStatus,
    ItemVehicleFit,
    ProposalStatus,
)
from app.modules.inventory.models import InventoryItem
from app.modules.users.models import User

router = APIRouter(prefix="/admin/todo", tags=["admin: catalog"])

Reader = Annotated[
    User,
    Depends(
        require_admin_perm(
            AdminPerm.CATALOG_VIEW,
            AdminPerm.CATALOG_EDIT,
            AdminPerm.CATALOG_MODERATE,
            AdminPerm.CATALOG_IMPORT,
        )
    ),
]
Editor = Annotated[User, Depends(require_admin_perm(AdminPerm.CATALOG_EDIT))]


class TodoItem(BaseModel):
    id: uuid.UUID
    name: str
    codes: list[str]
    workshops: int  # how many workshops have it in stock


class TodoList(BaseModel):
    total: int
    items: list[TodoItem]


class DuplicatePair(BaseModel):
    a: TodoItem
    b: TodoItem
    reason: Literal["name", "code"]


class DuplicateList(BaseModel):
    total: int
    items: list[DuplicatePair]


class TodoOut(BaseModel):
    pending_proposals: int
    not_on_site: TodoList
    no_photo: TodoList
    duplicates: DuplicateList


class DismissIn(BaseModel):
    item_ids: list[uuid.UUID] = Field(min_length=2, max_length=2)


def has_content():
    """Same rule as the public site: a description or at least one car/lock fit."""
    return or_(
        func.length(func.coalesce(CatalogItem.description, "")) > 0,
        exists().where(ItemVehicleFit.item_id == CatalogItem.id),
        exists().where(ItemLockFit.item_id == CatalogItem.id),
    )


def _stock_counts():
    return (
        select(
            InventoryItem.catalog_item_id.label("item_id"),
            func.count(distinct(InventoryItem.workshop_id)).label("n"),
        )
        .where(InventoryItem.catalog_item_id.is_not(None), InventoryItem.is_archived.is_(False))
        .group_by(InventoryItem.catalog_item_id)
        .subquery()
    )


def _out(item: CatalogItem, n: int) -> TodoItem:
    return TodoItem(
        id=item.id,
        name=item.name,
        codes=[f"{c.brand.name} {c.code}" for c in item.codes],
        workshops=n or 0,
    )


async def _list(session, where, limit: int, *, stock_only: bool) -> TodoList:
    counts = _stock_counts()
    n = func.coalesce(counts.c.n, 0)
    base = select(CatalogItem, n).where(CatalogItem.status == ItemStatus.ACTIVE, where)
    base = (
        base.join(counts, counts.c.item_id == CatalogItem.id)
        if stock_only
        else base.outerjoin(counts, counts.c.item_id == CatalogItem.id)
    )
    total = await session.scalar(select(func.count()).select_from(base.subquery()))
    rows = (await session.execute(base.order_by(n.desc(), CatalogItem.name).limit(limit))).all()
    return TodoList(total=total or 0, items=[_out(i, c) for i, c in rows])


_NAME_SPACES = re.compile(r"\s+")


async def _duplicates(session, limit: int) -> DuplicateList:
    rows = (
        await session.execute(
            select(CatalogItem.id, CatalogItem.name, ItemCode.code_normalized)
            .join(ItemCode, ItemCode.item_id == CatalogItem.id)
            .where(CatalogItem.status == ItemStatus.ACTIVE)
        )
    ).all()
    names: dict[str, set[uuid.UUID]] = defaultdict(set)
    code_owner: dict[str, set[uuid.UUID]] = defaultdict(set)
    for item_id, name, code in rows:
        names[_NAME_SPACES.sub(" ", name.strip().lower())].add(item_id)
        code_owner[code].add(item_id)

    pairs: dict[tuple[uuid.UUID, uuid.UUID], str] = {}

    def add(a: uuid.UUID, b: uuid.UUID, reason: str) -> None:
        if a != b:
            pairs.setdefault((min(a, b), max(a, b)), reason)

    for ids in names.values():
        ids = sorted(ids)
        for i, a in enumerate(ids):
            for b in ids[i + 1 :]:
                add(a, b, "name")
    # HU66 vs HU66P: the same profile, a maker's one-letter suffix.
    for code, owners in code_owner.items():
        if len(code) > 2 and code[-1].isalpha() and code[:-1] in code_owner:
            for a in owners:
                for b in code_owner[code[:-1]]:
                    add(a, b, "code")

    if pairs:
        dismissed = set(
            (
                await session.execute(
                    select(DuplicateDismissal.item_a_id, DuplicateDismissal.item_b_id)
                )
            ).all()
        )
        pairs = {k: v for k, v in pairs.items() if k not in dismissed}
    chosen = list(pairs.items())[:limit]
    ids = {i for (a, b), _ in chosen for i in (a, b)}
    counts = _stock_counts()
    loaded = {
        item.id: (item, n)
        for item, n in (
            await session.execute(
                select(CatalogItem, func.coalesce(counts.c.n, 0))
                .outerjoin(counts, counts.c.item_id == CatalogItem.id)
                .where(CatalogItem.id.in_(ids))
            )
        ).all()
    }
    return DuplicateList(
        total=len(pairs),
        items=[
            DuplicatePair(a=_out(*loaded[a]), b=_out(*loaded[b]), reason=reason)
            for (a, b), reason in chosen
        ],
    )


@router.get("", response_model=TodoOut)
async def todo(
    _: Reader,
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 5,
):
    has_photo = exists().where(CatalogImage.item_id == CatalogItem.id)
    return TodoOut(
        pending_proposals=await session.scalar(
            select(func.count()).where(CatalogProposal.status == ProposalStatus.PENDING)
        )
        or 0,
        not_on_site=await _list(session, ~has_content(), limit, stock_only=True),
        no_photo=await _list(session, has_content() & ~has_photo, limit, stock_only=False),
        duplicates=await _duplicates(session, limit),
    )


@router.post("/duplicates/dismiss", status_code=status.HTTP_204_NO_CONTENT)
async def dismiss_duplicate(data: DismissIn, actor: Editor, session: SessionDep):
    """ "These are different keys" — the pair is not suggested again."""
    a, b = sorted(data.item_ids)
    if a == b:
        raise AppError("catalog.same_item", message="Two different items are needed")
    await service.get_item(session, a)
    await service.get_item(session, b)
    if not await session.get(DuplicateDismissal, (a, b)):
        session.add(DuplicateDismissal(item_a_id=a, item_b_id=b, created_by_id=actor.id))
        service.audit(session, actor, "duplicate.dismiss", "item", a, other_item_id=str(b))
        await session.commit()
