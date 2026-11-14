"""GDPR right of access: everything we store about the person, as one JSON file.

Workshop stock belongs to the workshop, not to the person — the owner downloads it
with the Excel export. Here: profile, memberships, sessions, invitations sent,
stock changes the person made, catalog proposals they supported.
"""

import json
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy import select

from app.core import ratelimit as rl
from app.core.deps import CurrentUser, SessionDep
from app.modules.auth.models import RefreshToken
from app.modules.catalog.models import CatalogProposal, ProposalVote
from app.modules.inventory.models import InventoryItem, StockMovement
from app.modules.workshops.models import Invitation, Workshop
from app.modules.workshops.service import list_user_memberships

router = APIRouter(prefix="/users", tags=["users"])


def _dt(v: datetime | None) -> str | None:
    return v.isoformat() if v else None


@router.get("/me/export")
async def export_my_data(user: CurrentUser, session: SessionDep) -> Response:
    rl.check(f"export:{user.id}", rl.Limit(10, 3600))
    memberships = await list_user_memberships(session, user.id)
    tokens = (
        await session.scalars(
            select(RefreshToken)
            .where(RefreshToken.user_id == user.id)
            .order_by(RefreshToken.created_at)
        )
    ).all()
    invitations = (
        await session.execute(
            select(Invitation, Workshop.name)
            .join(Workshop, Workshop.id == Invitation.workshop_id)
            .where(Invitation.invited_by_id == user.id)
            .order_by(Invitation.created_at)
        )
    ).all()
    movements = (
        await session.execute(
            select(StockMovement, InventoryItem.name, Workshop.name)
            .join(InventoryItem, InventoryItem.id == StockMovement.item_id)
            .join(Workshop, Workshop.id == StockMovement.workshop_id)
            .where(StockMovement.user_id == user.id)
            .order_by(StockMovement.created_at)
        )
    ).all()
    votes = (
        await session.execute(
            select(ProposalVote, CatalogProposal)
            .join(CatalogProposal, CatalogProposal.id == ProposalVote.proposal_id)
            .where(ProposalVote.user_id == user.id)
            .order_by(ProposalVote.created_at)
        )
    ).all()

    data: dict[str, Any] = {
        "exported_at": datetime.now(UTC).isoformat(),
        "profile": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "locale": user.locale,
            "email_verified_at": _dt(user.email_verified_at),
            "created_at": _dt(user.created_at),
            "last_login_at": _dt(user.last_login_at),
            "terms_version": user.terms_version,
            "terms_accepted_at": _dt(user.terms_accepted_at),
            "is_active": user.is_active,
            "admin_permissions": sorted(user.permissions),
        },
        "workshops": [
            {
                "workshop": m.workshop.name,
                "country": m.workshop.country_code,
                "role": m.role,
                "sees_purchase_prices": m.sees_purchase_prices,
                "joined_at": _dt(m.created_at),
            }
            for m in memberships
        ],
        "sessions": [
            {
                "created_at": _dt(t.created_at),
                "expires_at": _dt(t.expires_at),
                "revoked_at": _dt(t.revoked_at),
                "device": t.user_agent,
            }
            for t in tokens
        ],
        "invitations_sent": [
            {
                "workshop": ws,
                "email": i.email,
                "role": i.role,
                "sent_at": _dt(i.created_at),
                "accepted_at": _dt(i.accepted_at),
            }
            for i, ws in invitations
        ],
        "stock_changes": [
            {
                "at": _dt(m.created_at),
                "workshop": ws,
                "item": item,
                "type": m.type,
                "quantity": m.quantity,
                "unit_price": str(m.unit_price) if m.unit_price is not None else None,
                "currency": m.currency,
                "client_name": m.client_name,
                "client_phone": m.client_phone,
                "note": m.note,
            }
            for m, item, ws in movements
        ],
        "catalog_proposals_supported": [
            {"at": _dt(v.created_at), "type": p.type, "proposal": p.payload, "status": p.status}
            for v, p in votes
        ],
    }
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    return Response(
        json.dumps(data, ensure_ascii=False, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="keyverhaus-my-data-{stamp}.json"'},
    )
