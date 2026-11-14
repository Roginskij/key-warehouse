"""Moderation queue: how the catalog grows from workshops' real stock.

A workshop proposes something; if other workshops propose the same thing it
becomes one proposal with more votes. A moderator accepts or rejects. Workshops
refer to keys by (brand, code) because that's what they see on their shelves.
"""

import uuid
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, Conflict
from app.core.security import utcnow
from app.modules.catalog import service
from app.modules.catalog.models import (
    CatalogItem,
    CatalogProposal,
    ItemKind,
    ItemStatus,
    ProposalStatus,
    ProposalType,
    ProposalVote,
    SourceType,
)
from app.modules.catalog.normalize import normalize_brand, normalize_code
from app.modules.users.models import User


class CodeRef(BaseModel):
    brand: str = Field(min_length=1, max_length=80)
    code: str = Field(min_length=1, max_length=64)

    def key(self) -> str:
        return f"{normalize_brand(self.brand)}/{normalize_code(self.code)}"


class NewItemProposal(BaseModel):
    type: Literal["new_item"]
    kind: ItemKind
    name: str = Field(min_length=1, max_length=200)
    codes: list[CodeRef] = Field(min_length=1, max_length=20)
    frequency_mhz: Decimal | None = Field(default=None, ge=0, le=9999)
    chip_type: str | None = Field(default=None, max_length=64)
    fcc_id: str | None = Field(default=None, max_length=32)

    def dedup_key(self) -> str:
        return "new_item:" + "|".join(sorted({c.key() for c in self.codes}))


class EquivalentProposal(BaseModel):
    """`a` and `b` are the same key under different numbers."""

    type: Literal["equivalent"]
    a: CodeRef
    b: CodeRef
    # Used only if neither code is in the catalog yet.
    kind: ItemKind | None = None
    name: str | None = Field(default=None, max_length=200)

    def dedup_key(self) -> str:
        return "equivalent:" + "|".join(sorted([self.a.key(), self.b.key()]))


class SubstituteProposal(BaseModel):
    """`substitute` can be used instead of `item` (one way)."""

    type: Literal["substitute"]
    item: CodeRef
    substitute: CodeRef
    note: str | None = Field(default=None, max_length=300)

    def dedup_key(self) -> str:
        return f"substitute:{self.item.key()}>{self.substitute.key()}"


class AddCodeProposal(BaseModel):
    type: Literal["add_code"]
    item_id: uuid.UUID
    code: CodeRef

    def dedup_key(self) -> str:
        return f"add_code:{self.item_id}:{self.code.key()}"


ProposalBody = Annotated[
    NewItemProposal | EquivalentProposal | SubstituteProposal | AddCodeProposal,
    Field(discriminator="type"),
]
_MODELS = {
    ProposalType.NEW_ITEM: NewItemProposal,
    ProposalType.EQUIVALENT: EquivalentProposal,
    ProposalType.SUBSTITUTE: SubstituteProposal,
    ProposalType.ADD_CODE: AddCodeProposal,
}


def parse_payload(proposal: CatalogProposal):
    return _MODELS[ProposalType(proposal.type)].model_validate(
        {"type": proposal.type, **proposal.payload}
    )


# --- submit (workshop side) ------------------------------------------------------------


async def submit(
    session: AsyncSession, user: User, workshop_id: uuid.UUID, body: ProposalBody
) -> CatalogProposal:
    if isinstance(body, EquivalentProposal) and body.a.key() == body.b.key():
        raise AppError("catalog.bad_proposal", message="Codes are identical")
    if isinstance(body, SubstituteProposal) and body.item.key() == body.substitute.key():
        raise AppError("catalog.bad_proposal", message="Codes are identical")
    if isinstance(body, AddCodeProposal):
        item = await service.resolve_item(session, body.item_id)
        body.item_id = item.id

    key = body.dedup_key()
    proposal = await session.scalar(
        select(CatalogProposal).where(
            CatalogProposal.dedup_key == key, CatalogProposal.status == ProposalStatus.PENDING
        )
    )
    if proposal is None:
        proposal = CatalogProposal(
            type=body.type,
            payload=body.model_dump(mode="json", exclude={"type"}),
            dedup_key=key,
            first_proposed_by_id=user.id,
            votes_count=0,
        )
        session.add(proposal)
        try:
            async with session.begin_nested():
                await session.flush()
        except IntegrityError:  # someone created the same one in parallel
            proposal = await session.scalar(
                select(CatalogProposal).where(
                    CatalogProposal.dedup_key == key,
                    CatalogProposal.status == ProposalStatus.PENDING,
                )
            )

    voted = await session.get(ProposalVote, (proposal.id, workshop_id))
    if voted is None:
        session.add(ProposalVote(proposal_id=proposal.id, workshop_id=workshop_id, user_id=user.id))
        proposal.votes_count += 1
    await session.flush()
    return proposal


# --- decide (moderator side) -----------------------------------------------------------


async def _item_by_ref(session: AsyncSession, ref: CodeRef) -> CatalogItem | None:
    brand = await service.find_brand(session, ref.brand)
    if brand is None:
        return None
    code = await service.find_code(session, brand, ref.code)
    return await service.resolve_item(session, code.item_id) if code else None


async def accept(
    session: AsyncSession,
    actor: User,
    proposal: CatalogProposal,
    kind: ItemKind | None = None,
    name: str | None = None,
) -> CatalogItem:
    """Applies the proposal. Unknown brands are created. `kind` / `name` let the
    moderator correct a new item before it appears in the catalog."""
    if proposal.status != ProposalStatus.PENDING:
        raise Conflict("catalog.proposal_decided", "Proposal is already decided")
    body = parse_payload(proposal)
    source = service.Source(SourceType.WORKSHOP, ref=f"proposal:{proposal.id}")
    votes = proposal.votes_count

    async def brand(ref: CodeRef):
        return await service.get_brand(session, ref.brand, create=True, actor=actor)

    match body:
        case NewItemProposal():
            existing = {i.id: i for c in body.codes if (i := await _item_by_ref(session, c))}
            if len(existing) > 1:
                raise Conflict(
                    "catalog.proposal_conflict",
                    "Codes belong to different items — merge them first",
                ).with_params(item_ids=[str(i) for i in existing])
            if existing:
                result = next(iter(existing.values()))
                for c in body.codes:
                    await service.add_code(
                        session, actor, result, await brand(c), c.code, source, votes
                    )
            else:
                result = await service.create_item(
                    session,
                    actor,
                    kind=kind or body.kind,
                    name=name or body.name,
                    codes=[(await brand(c), c.code) for c in body.codes],
                    source=source,
                    confirmations=votes,
                    frequency_mhz=body.frequency_mhz,
                    chip_type=body.chip_type,
                    fcc_id=body.fcc_id,
                )

        case EquivalentProposal():
            ia, ib = await _item_by_ref(session, body.a), await _item_by_ref(session, body.b)
            if ia and ib and ia.id != ib.id:
                result = await service.merge_items(session, actor, ia, [ib])
            elif ia or ib:
                result = ia or ib
                for ref in (body.a, body.b):
                    await service.add_code(
                        session, actor, result, await brand(ref), ref.code, source, votes
                    )
            else:
                final_kind = kind or body.kind
                if final_kind is None:
                    raise AppError(
                        "catalog.kind_required", message="Neither code is known: specify kind"
                    )
                result = await service.create_item(
                    session,
                    actor,
                    kind=final_kind,
                    name=name or body.name or body.a.code,
                    codes=[(await brand(body.a), body.a.code), (await brand(body.b), body.b.code)],
                    source=source,
                    confirmations=votes,
                )

        case SubstituteProposal():
            item = await _item_by_ref(session, body.item)
            sub = await _item_by_ref(session, body.substitute)
            if item is None or sub is None:
                raise AppError(
                    "catalog.proposal_unresolved",
                    message="Both codes must exist in the catalog first",
                )
            await service.add_substitute(session, actor, item, sub, body.note, source, votes)
            result = item

        case AddCodeProposal():
            result = await service.resolve_item(session, body.item_id)
            if result.status != ItemStatus.ACTIVE:
                raise AppError("catalog.item_not_active", message="Item is not active")
            await service.add_code(
                session, actor, result, await brand(body.code), body.code.code, source, votes
            )

    proposal.status = ProposalStatus.ACCEPTED
    proposal.decided_by_id = actor.id
    proposal.decided_at = utcnow()
    proposal.result_item_id = result.id
    service.audit(session, actor, "proposal.accept", "proposal", proposal.id, item_id=result.id)
    await session.flush()
    return result


async def reject(
    session: AsyncSession, actor: User, proposal: CatalogProposal, note: str | None
) -> None:
    if proposal.status != ProposalStatus.PENDING:
        raise Conflict("catalog.proposal_decided", "Proposal is already decided")
    proposal.status = ProposalStatus.REJECTED
    proposal.decided_by_id = actor.id
    proposal.decided_at = utcnow()
    proposal.decision_note = note
    service.audit(session, actor, "proposal.reject", "proposal", proposal.id, note=note)
    await session.flush()
