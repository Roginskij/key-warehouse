"""Stable, language-independent addresses for public key pages: /uk/keys/<slug>."""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import CatalogItem

_TRANSLIT = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "h",
    "ґ": "g",
    "д": "d",
    "е": "e",
    "є": "ie",
    "ж": "zh",
    "з": "z",
    "и": "y",
    "і": "i",
    "ї": "i",
    "й": "i",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ь": "",
    "ю": "iu",
    "я": "ia",
    "ё": "e",
    "ы": "y",
    "э": "e",
    "ъ": "",
    "ä": "a",
    "ö": "o",
    "ü": "u",
    "ß": "ss",
    "ą": "a",
    "ć": "c",
    "ę": "e",
    "ł": "l",
    "ń": "n",
    "ó": "o",
    "ś": "s",
    "ź": "z",
    "ż": "z",
    "é": "e",
    "è": "e",
    "à": "a",
    "ç": "c",
    "ñ": "n",
    "í": "i",
    "ú": "u",
    "ò": "o",
    "ì": "i",
}


def slugify(text: str) -> str:
    out = "".join(_TRANSLIT.get(ch, ch) for ch in text.lower())
    out = re.sub(r"[^a-z0-9]+", "-", out).strip("-")
    return out[:120] or "key"


async def ensure_slug(session: AsyncSession, item: CatalogItem) -> str:
    """Gives the item a unique slug once; it never changes afterwards (links stay valid)."""
    if item.slug:
        return item.slug
    first = item.codes[0] if item.codes else None
    base = slugify(f"{first.brand.name} {first.code} {item.name}" if first else item.name)
    slug, n = base, 2
    while await session.scalar(select(CatalogItem.id).where(CatalogItem.slug == slug)):
        slug = f"{base}-{n}"
        n += 1
    item.slug = slug
    await session.flush()
    # The UPDATE bumped updated_at on the server; load it now (no lazy IO later).
    await session.refresh(item, ["updated_at"])
    return slug
