"""Catalog API for workshops (any signed-in user): search, item card, proposals."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status
from sqlalchemy import case, func, or_, select

from app.core.deps import CurrentUser, SessionDep
from app.core.errors import NotFound
from app.modules.catalog import proposals, service
from app.modules.catalog.models import (
    Brand,
    CatalogItem,
    CatalogProposal,
    ItemCode,
    ItemKind,
    ItemStatus,
    ProposalVote,
)
from app.modules.catalog.normalize import normalize_code
from app.modules.catalog.schemas import (
    BrandOut,
    ItemDetailOut,
    ItemPage,
    ProposalOut,
    ProposalSubmitIn,
    brief_out,
    item_out,
)
from app.modules.workshops.service import get_membership

router = APIRouter(prefix="/catalog", tags=["catalog"])


def search_stmt(q: str | None, kind: ItemKind | None, statuses: list[str] | None):
    stmt = select(CatalogItem)
    if statuses:
        stmt = stmt.where(CatalogItem.status.in_(statuses))
    if kind:
        stmt = stmt.where(CatalogItem.kind == kind)
    order = [CatalogItem.name]
    if q and q.strip():
        qn = normalize_code(q)
        conditions = [CatalogItem.name.ilike(f"%{q.strip()}%")]
        if qn:
            conditions.append(
                CatalogItem.id.in_(
                    select(ItemCode.item_id).where(ItemCode.code_normalized.contains(qn))
                )
            )
            exact = select(ItemCode.item_id).where(ItemCode.code_normalized == qn)
            order.insert(0, case((CatalogItem.id.in_(exact), 0), else_=1))
        stmt = stmt.where(or_(*conditions))
    return stmt, order


async def run_search(session, stmt, order, limit: int, offset: int):
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = await session.scalars(stmt.order_by(*order).limit(limit).offset(offset))
    return rows.all(), total


@router.get("/brands", response_model=list[BrandOut])
async def list_brands(_: CurrentUser, session: SessionDep):
    rows = await session.scalars(
        select(Brand).where(Brand.is_active.is_(True)).order_by(Brand.name)
    )
    return rows.all()


@router.get("/items", response_model=ItemPage)
async def search_items(
    _: CurrentUser,
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100, description="Code (any brand) or name")] = None,
    kind: ItemKind | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Search finds an item by ANY of its codes: 'hu-66', 'HU66', 'hu 66' are the same."""
    stmt, order = search_stmt(q, kind, [ItemStatus.ACTIVE])
    items, total = await run_search(session, stmt, order, limit, offset)
    return ItemPage(items=[item_out(i) for i in items], total=total)


@router.get("/items/{item_id}", response_model=ItemDetailOut)
async def get_item(item_id: uuid.UUID, _: CurrentUser, session: SessionDep):
    """Old ids of merged items lead to the surviving item."""
    item = await service.resolve_item(session, item_id)
    if item.status != ItemStatus.ACTIVE:
        raise NotFound("catalog.item_not_found", "Catalog item not found")
    replaced_by, replaces = await service.substitutes_of(session, item.id)
    return ItemDetailOut(
        **item_out(item).model_dump(),
        can_be_replaced_by=[brief_out(i) for i in replaced_by],
        can_replace=[brief_out(i) for i in replaces],
    )


@router.post("/proposals", response_model=ProposalOut, status_code=status.HTTP_201_CREATED)
async def submit_proposal(data: ProposalSubmitIn, user: CurrentUser, session: SessionDep):
    """A workshop suggests a catalog change. Same suggestion from several workshops
    = one proposal with several votes."""
    await get_membership(session, data.workshop_id, user)
    proposal = await proposals.submit(session, user, data.workshop_id, data.proposal)
    await session.commit()
    await session.refresh(proposal)
    return proposal


@router.get("/proposals", response_model=list[ProposalOut])
async def my_workshop_proposals(workshop_id: uuid.UUID, user: CurrentUser, session: SessionDep):
    """Proposals this workshop made or supported, with their status."""
    await get_membership(session, workshop_id, user)
    rows = await session.scalars(
        select(CatalogProposal)
        .join(ProposalVote, ProposalVote.proposal_id == CatalogProposal.id)
        .where(ProposalVote.workshop_id == workshop_id)
        .order_by(CatalogProposal.created_at.desc())
        .limit(200)
    )
    return rows.all()
