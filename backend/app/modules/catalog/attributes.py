"""Characteristics of a catalog card: per kind, a list of fields the admin manages
(tables catalog_attribute_defs / catalog_attribute_options).

Card values live in CatalogItem.attributes as {field key: value}; select values are
option keys. Only visible fields of the item's kind are accepted; values of fields the
admin has hidden stay in the card untouched.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.catalog.models import AttributeDef, AttributeType

LANGS = ("uk", "en", "pl", "de", "fr", "es", "it")
REQUIRED_LANGS = ("uk", "en")


async def defs_for(
    session: AsyncSession, kind: str | None = None, *, with_hidden: bool = False
) -> list[AttributeDef]:
    stmt = select(AttributeDef).order_by(AttributeDef.kind, AttributeDef.sort_order)
    if kind is not None:
        stmt = stmt.where(AttributeDef.kind == kind)
    if not with_hidden:
        stmt = stmt.where(AttributeDef.is_hidden.is_(False))
    return list((await session.scalars(stmt)).all())


def _bad(key: str) -> AppError:
    return AppError("catalog.bad_attribute", message=f"Bad value for {key}").with_params(field=key)


async def clean(
    session: AsyncSession,
    kind: str | None,
    values: dict[str, Any] | None,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Valid values for the visible fields of `kind`; empty values are dropped. Hidden
    fields keep what `existing` had. A wrong value: catalog.bad_attribute (params.field)."""
    if not kind:
        return {}
    out: dict[str, Any] = {}
    for d in await defs_for(session, kind, with_hidden=True):
        if d.is_hidden:
            if existing and d.key in existing:
                out[d.key] = existing[d.key]
            continue
        v = (values or {}).get(d.key)
        if v is None or v == "":
            continue
        if d.type == AttributeType.SELECT:
            allowed = {o.key for o in d.options if not o.is_hidden}
            old = (existing or {}).get(d.key)
            # A hidden option may stay where it already was, but is not chosen anew.
            if str(v) not in allowed and str(v) != old:
                raise _bad(d.key)
            out[d.key] = str(v)
        elif d.type == AttributeType.NUMBER:
            try:
                n = int(v)
            except (TypeError, ValueError):
                raise _bad(d.key) from None
            if (d.min_value is not None and n < d.min_value) or (
                d.max_value is not None and n > d.max_value
            ):
                raise _bad(d.key)
            out[d.key] = n
        elif d.type == AttributeType.BOOL:
            if not isinstance(v, bool):
                raise _bad(d.key)
            out[d.key] = v
    return out


def label(labels: dict[str, str] | None, lang: str) -> str:
    labels = labels or {}
    return labels.get(lang) or labels.get("en") or labels.get("uk") or ""


async def readable(
    session: AsyncSession, kind: str, values: dict[str, Any] | None
) -> list[dict[str, Any]]:
    """For display (site): visible fields that have a value, in the admin's order, with
    labels in all languages. Select values come with their option's labels."""
    out = []
    for d in await defs_for(session, kind):
        if not values or d.key not in values:
            continue
        v = values[d.key]
        value_labels = None
        if d.type == AttributeType.SELECT:
            opt = next((o for o in d.options if o.key == str(v)), None)
            value_labels = opt.labels if opt else None
        out.append(
            {
                "key": d.key,
                "type": d.type,
                "labels": d.labels,
                "value": v,
                "value_labels": value_labels,
            }
        )
    return out
