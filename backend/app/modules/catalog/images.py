"""Catalog photos: resized to WebP in three sizes (media/catalog/<id>_<size>.webp);
the original upload is not kept."""

import io
import uuid
from pathlib import Path

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError
from app.modules.catalog.models import CatalogImage, CatalogItem
from app.modules.users.models import User

SIZES = (1600, 800, 400)  # 1600: Google image results need ≥1200 px
MAX_BYTES = 15 * 1024 * 1024
MIN_SIDE = 600


def image_path(image_id: uuid.UUID, size: int) -> Path:
    """By image id only, so files stay put when items are merged or split."""
    return Path(settings.media_dir).resolve() / "catalog" / f"{image_id}_{size}.webp"


async def save_image(
    session: AsyncSession,
    actor: User,
    item: CatalogItem,
    content: bytes,
    source_type: str,
    source_note: str | None,
) -> CatalogImage:
    if len(content) > MAX_BYTES:
        raise AppError("catalog.image_too_big", 413, "Image is larger than 15 MB")
    try:
        img = Image.open(io.BytesIO(content))
        img = ImageOps.exif_transpose(img).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise AppError("catalog.image_bad_format", message="Use a JPEG, PNG or WebP photo") from exc
    if min(img.size) < MIN_SIDE:
        raise AppError(
            "catalog.image_too_small", message=f"At least {MIN_SIDE} px on the short side"
        )

    image = CatalogImage(
        id=uuid.uuid4(),
        item_id=item.id,
        source_type=source_type,
        source_note=source_note,
        width=img.width,
        height=img.height,
        created_by_id=actor.id,
        is_primary=False,
    )
    for size in SIZES:
        copy = img.copy()
        copy.thumbnail((size, size), Image.Resampling.LANCZOS)
        path = image_path(image.id, size)
        path.parent.mkdir(parents=True, exist_ok=True)
        copy.save(path, "WEBP", quality=82, method=6)
    session.add(image)
    await session.flush()
    return image


def delete_files(image: CatalogImage) -> None:
    for size in SIZES:
        image_path(image.id, size).unlink(missing_ok=True)
