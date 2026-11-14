"""Catalog admin panel. Access only by admin permissions (see AdminPerm)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy import func, select

from app.core.deps import SessionDep, require_admin_perm
from app.core.errors import AppError, Conflict, NotFound
from app.core.security import utcnow
from app.modules.admin.permissions import AdminPerm
from app.modules.catalog import fits, images, importer, proposals, service
from app.modules.catalog.models import (
    Brand,
    CatalogAudit,
    CatalogImage,
    CatalogImport,
    CatalogItem,
    CatalogProposal,
    ImageSource,
    ItemCode,
    ItemKind,
    ItemLockFit,
    ItemStatus,
    ItemSubstitute,
    ItemVehicleFit,
    ProposalStatus,
    ProposalType,
)
from app.modules.catalog.normalize import normalize_brand
from app.modules.catalog.router import run_search, search_stmt
from app.modules.catalog.schemas import (
    AuditOut,
    BrandIn,
    BrandOut,
    BrandUpdateIn,
    CodeIn,
    ImportOut,
    ItemAdminDetailOut,
    ItemAdminPage,
    ItemCreateIn,
    ItemUpdateIn,
    LockFitIn,
    MergeIn,
    ProposalAcceptIn,
    ProposalOut,
    ProposalPage,
    ProposalRejectIn,
    SplitIn,
    SubstituteIn,
    VehicleFitIn,
    brief_out,
    item_admin_out,
)
from app.modules.users.models import User

router = APIRouter(prefix="/admin/catalog", tags=["admin: catalog"])

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
Moderator = Annotated[User, Depends(require_admin_perm(AdminPerm.CATALOG_MODERATE))]
Importer = Annotated[User, Depends(require_admin_perm(AdminPerm.CATALOG_IMPORT))]

MAX_UPLOAD_BYTES = 10 * 1024 * 1024


async def _detail(session, item: CatalogItem) -> ItemAdminDetailOut:
    replaced_by, replaces = await service.substitutes_of(session, item.id)
    return ItemAdminDetailOut(
        **item_admin_out(item).model_dump(),
        slug=item.slug,
        can_be_replaced_by=[brief_out(i) for i in replaced_by],
        can_replace=[brief_out(i) for i in replaces],
        vehicle_fits=await fits.vehicle_fits(session, item.id),
        lock_fits=await fits.lock_fits(session, item.id),
        images=await fits.images(session, item.id),
    )


async def _brands_for(session, codes: list[CodeIn]):
    return [(await service.get_brand(session, c.brand, create=False), c.code) for c in codes]


# --- brands ----------------------------------------------------------------------------


@router.get("/brands", response_model=list[BrandOut])
async def list_brands(_: Reader, session: SessionDep):
    return (await session.scalars(select(Brand).order_by(Brand.name))).all()


@router.post("/brands", response_model=BrandOut, status_code=status.HTTP_201_CREATED)
async def create_brand(data: BrandIn, actor: Editor, session: SessionDep):
    if await service.find_brand(session, data.name):
        raise Conflict("catalog.brand_exists", "Brand already exists")
    brand = await service.get_brand(session, data.name, create=True, actor=actor)
    brand.website = data.website
    await session.commit()
    return brand


@router.patch("/brands/{brand_id}", response_model=BrandOut)
async def update_brand(
    brand_id: uuid.UUID, data: BrandUpdateIn, actor: Editor, session: SessionDep
):
    brand = await session.get(Brand, brand_id)
    if brand is None:
        raise NotFound("catalog.brand_not_found", "Brand not found")
    if data.name is not None:
        other = await service.find_brand(session, data.name)
        if other and other.id != brand.id:
            raise Conflict("catalog.brand_exists", "Brand already exists")
        brand.name = data.name.strip()
        brand.name_normalized = normalize_brand(data.name)
    if data.website is not None:
        brand.website = data.website
    if data.is_active is not None:
        brand.is_active = data.is_active
    service.audit(
        session, actor, "brand.update", "brand", brand.id, **data.model_dump(exclude_unset=True)
    )
    await session.commit()
    return brand


# --- items -----------------------------------------------------------------------------


@router.get("/items", response_model=ItemAdminPage)
async def list_items(
    _: Reader,
    session: SessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    kind: ItemKind | None = None,
    item_status: Annotated[list[ItemStatus] | None, Query(alias="status")] = None,
    import_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    stmt, order = search_stmt(q, kind, item_status)
    if import_id:
        stmt = stmt.where(CatalogItem.import_id == import_id)
    items, total = await run_search(session, stmt, order, limit, offset)
    return ItemAdminPage(items=[item_admin_out(i) for i in items], total=total)


@router.get("/items/{item_id}", response_model=ItemAdminDetailOut)
async def get_item(item_id: uuid.UUID, _: Reader, session: SessionDep):
    return await _detail(session, await service.get_item(session, item_id))


@router.post("/items", response_model=ItemAdminDetailOut, status_code=status.HTTP_201_CREATED)
async def create_item(data: ItemCreateIn, actor: Editor, session: SessionDep):
    item = await service.create_item(
        session,
        actor,
        kind=data.kind,
        name=data.name,
        codes=await _brands_for(session, data.codes),
        description=data.description,
        frequency_mhz=data.frequency_mhz,
        chip_type=data.chip_type,
        fcc_id=data.fcc_id,
        attributes=data.attributes,
    )
    await session.commit()
    return await _detail(session, item)


@router.patch("/items/{item_id}", response_model=ItemAdminDetailOut)
async def update_item(item_id: uuid.UUID, data: ItemUpdateIn, actor: Editor, session: SessionDep):
    item = await service.get_item(session, item_id)
    changes = data.model_dump(exclude_unset=True)
    if "status" in changes:
        if item.status == ItemStatus.MERGED or changes["status"] == ItemStatus.MERGED:
            raise AppError("catalog.bad_status", message="Use merge to merge items")
    for field, value in changes.items():
        if field in ("name",) and value is None:
            continue
        setattr(item, field, value.strip() if field == "name" else value)
    service.audit(session, actor, "item.update", "item", item.id, **changes)
    await session.commit()
    await session.refresh(item)
    return await _detail(session, item)


@router.post("/items/{item_id}/codes", response_model=ItemAdminDetailOut)
async def add_code(item_id: uuid.UUID, data: CodeIn, actor: Editor, session: SessionDep):
    item = await service.get_item(session, item_id)
    if item.status != ItemStatus.ACTIVE:
        raise AppError("catalog.item_not_active", message="Item is not active")
    brand = await service.get_brand(session, data.brand, create=False)
    await service.add_code(session, actor, item, brand, data.code)
    await session.commit()
    await session.refresh(item, ["codes"])
    return await _detail(session, item)


@router.delete("/items/{item_id}/codes/{code_id}", response_model=ItemAdminDetailOut)
async def remove_code(item_id: uuid.UUID, code_id: uuid.UUID, actor: Editor, session: SessionDep):
    item = await service.get_item(session, item_id)
    await service.remove_code(session, actor, item, code_id)
    await session.commit()
    await session.refresh(item, ["codes"])
    return await _detail(session, item)


@router.post("/items/{item_id}/merge", response_model=ItemAdminDetailOut)
async def merge_items(item_id: uuid.UUID, data: MergeIn, actor: Editor, session: SessionDep):
    """These items are duplicates of `item_id`: their codes, substitutes and
    vehicle fits move to it, they become 'merged' and their ids redirect to it."""
    target = await service.get_item(session, item_id)
    sources = [await service.get_item(session, i) for i in dict.fromkeys(data.source_item_ids)]
    await service.merge_items(session, actor, target, sources)
    await session.commit()
    return await _detail(session, target)


@router.post(
    "/items/{item_id}/split", response_model=ItemAdminDetailOut, status_code=status.HTTP_201_CREATED
)
async def split_item(item_id: uuid.UUID, data: SplitIn, actor: Editor, session: SessionDep):
    """Moves the given codes to a NEW item (returned). Fixes a wrong merge."""
    item = await service.get_item(session, item_id)
    new = await service.split_item(session, actor, item, data.code_ids, data.kind, data.name)
    await session.commit()
    return await _detail(session, new)


# --- substitutes -----------------------------------------------------------------------


@router.post("/substitutes", response_model=ItemAdminDetailOut, status_code=status.HTTP_201_CREATED)
async def add_substitute(data: SubstituteIn, actor: Editor, session: SessionDep):
    item = await service.get_item(session, data.item_id)
    sub = await service.get_item(session, data.substitute_item_id)
    await service.add_substitute(session, actor, item, sub, data.note)
    await session.commit()
    return await _detail(session, item)


@router.delete(
    "/substitutes/{item_id}/{substitute_item_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_substitute(
    item_id: uuid.UUID, substitute_item_id: uuid.UUID, actor: Editor, session: SessionDep
):
    link = await session.scalar(
        select(ItemSubstitute).where(
            ItemSubstitute.item_id == item_id,
            ItemSubstitute.substitute_item_id == substitute_item_id,
        )
    )
    if link is None:
        raise NotFound("catalog.substitute_not_found", "Substitute link not found")
    await session.delete(link)
    service.audit(
        session, actor, "substitute.remove", "item", item_id, substitute_item_id=substitute_item_id
    )
    await session.commit()


# --- moderation queue ------------------------------------------------------------------


@router.get("/proposals", response_model=ProposalPage)
async def list_proposals(
    _: Reader,
    session: SessionDep,
    proposal_status: Annotated[ProposalStatus, Query(alias="status")] = ProposalStatus.PENDING,
    type: ProposalType | None = None,  # noqa: A002
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """Most-voted first: what many workshops agree on is checked first."""
    stmt = select(CatalogProposal).where(CatalogProposal.status == proposal_status)
    if type:
        stmt = stmt.where(CatalogProposal.type == type)
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = await session.scalars(
        stmt.order_by(CatalogProposal.votes_count.desc(), CatalogProposal.created_at)
        .limit(limit)
        .offset(offset)
    )
    return ProposalPage(items=rows.all(), total=total)


async def _proposal(session, proposal_id: uuid.UUID) -> CatalogProposal:
    p = await session.get(CatalogProposal, proposal_id, with_for_update=True)
    if p is None:
        raise NotFound("catalog.proposal_not_found", "Proposal not found")
    return p


@router.post("/proposals/{proposal_id}/accept", response_model=ItemAdminDetailOut)
async def accept_proposal(
    proposal_id: uuid.UUID,
    actor: Moderator,
    session: SessionDep,
    data: ProposalAcceptIn | None = None,
):
    """Applies the proposal and returns the resulting catalog item."""
    p = await _proposal(session, proposal_id)
    data = data or ProposalAcceptIn()
    item = await proposals.accept(session, actor, p, data.kind, data.name)
    await session.commit()
    await session.refresh(item)
    return await _detail(session, item)


@router.post("/proposals/{proposal_id}/reject", response_model=ProposalOut)
async def reject_proposal(
    proposal_id: uuid.UUID, data: ProposalRejectIn, actor: Moderator, session: SessionDep
):
    p = await _proposal(session, proposal_id)
    await proposals.reject(session, actor, p, data.note)
    await session.commit()
    await session.refresh(p)
    return p


# --- import ----------------------------------------------------------------------------


@router.post("/import")
async def import_file(
    actor: Importer,
    session: SessionDep,
    file: Annotated[UploadFile, File(description=".xlsx or .csv, format in importer.py")],
    source_label: Annotated[str, Form(min_length=1, max_length=160)],
    default_kind: Annotated[ItemKind | None, Form()] = None,
    dry_run: Annotated[bool, Form()] = True,
):
    """Upload with dry_run=true (default) to preview, then again with dry_run=false."""
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise AppError("catalog.import_too_big", 413, "File is larger than 10 MB")
    rows = importer.read_table(file.filename or "upload", content)
    report = await importer.run_import(
        session,
        actor,
        filename=file.filename or "upload",
        rows=rows,
        source_label=source_label,
        default_kind=default_kind,
        dry_run=dry_run,
    )
    if dry_run:
        await session.rollback()
    else:
        await session.commit()
    return report


@router.get("/imports", response_model=list[ImportOut])
async def list_imports(_: Reader, session: SessionDep):
    rows = await session.scalars(select(CatalogImport).order_by(CatalogImport.created_at.desc()))
    return rows.all()


@router.delete("/imports/{import_id}", response_model=ImportOut)
async def revert_import(import_id: uuid.UUID, actor: Importer, session: SessionDep):
    """Removes everything this import added: its codes and substitute links.
    Items it created that are left without codes are archived."""
    imp = await session.get(CatalogImport, import_id)
    if imp is None:
        raise NotFound("catalog.import_not_found", "Import not found")
    if imp.reverted_at:
        raise Conflict("catalog.import_reverted", "Import is already reverted")

    codes = (await session.scalars(select(ItemCode).where(ItemCode.import_id == import_id))).all()
    for c in codes:
        await session.delete(c)
    links = (
        await session.scalars(select(ItemSubstitute).where(ItemSubstitute.import_id == import_id))
    ).all()
    for link in links:
        await session.delete(link)
    await session.flush()

    archived = 0
    items = (
        await session.scalars(
            select(CatalogItem).where(
                CatalogItem.import_id == import_id, CatalogItem.status == ItemStatus.ACTIVE
            )
        )
    ).all()
    for item in items:
        await session.refresh(item, ["codes"])
        if not item.codes:
            item.status = ItemStatus.ARCHIVED
            archived += 1

    imp.reverted_at = utcnow()
    service.audit(
        session,
        actor,
        "import.revert",
        "import",
        imp.id,
        codes_removed=len(codes),
        substitutes_removed=len(links),
        items_archived=archived,
    )
    await session.commit()
    await session.refresh(imp)
    return imp


# --- history ---------------------------------------------------------------------------


@router.get("/audit", response_model=list[AuditOut])
async def audit_log(
    _: Reader,
    session: SessionDep,
    entity_id: uuid.UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    stmt = select(CatalogAudit)
    if entity_id:
        stmt = stmt.where(CatalogAudit.entity_id == entity_id)
    rows = await session.scalars(
        stmt.order_by(CatalogAudit.created_at.desc()).limit(limit).offset(offset)
    )
    return rows.all()


# --- fits: cars and locks --------------------------------------------------------------


@router.post("/items/{item_id}/fits/vehicle", response_model=ItemAdminDetailOut)
async def add_vehicle_fit(
    item_id: uuid.UUID, data: VehicleFitIn, actor: Editor, session: SessionDep
):
    item = await service.get_item(session, item_id)
    if data.year_from and data.year_to and data.year_from > data.year_to:
        raise AppError("catalog.bad_years", message="year_from is after year_to")
    model = await fits.vehicle_model(session, data.make, data.model)
    session.add(
        ItemVehicleFit(
            item_id=item.id,
            model_id=model.id,
            year_from=data.year_from,
            year_to=data.year_to,
            note=data.note,
            created_by_id=actor.id,
        )
    )
    service.audit(session, actor, "fit.add", "item", item.id, make=data.make, model=data.model)
    await session.commit()
    return await _detail(session, item)


@router.post("/items/{item_id}/fits/lock", response_model=ItemAdminDetailOut)
async def add_lock_fit(item_id: uuid.UUID, data: LockFitIn, actor: Editor, session: SessionDep):
    item = await service.get_item(session, item_id)
    model = await fits.lock_model(session, data.make, data.model, data.profile)
    session.add(
        ItemLockFit(item_id=item.id, model_id=model.id, note=data.note, created_by_id=actor.id)
    )
    service.audit(session, actor, "fit.add", "item", item.id, make=data.make, model=data.model)
    await session.commit()
    return await _detail(session, item)


@router.delete("/fits/{kind}/{fit_id}", response_model=ItemAdminDetailOut)
async def remove_fit(kind: str, fit_id: uuid.UUID, actor: Editor, session: SessionDep):
    model = {"vehicle": ItemVehicleFit, "lock": ItemLockFit}.get(kind)
    fit = await session.get(model, fit_id) if model else None
    if fit is None:
        raise NotFound("catalog.fit_not_found", "Fit not found")
    item = await service.get_item(session, fit.item_id)
    await session.delete(fit)
    service.audit(session, actor, "fit.remove", "item", item.id, kind=kind)
    await session.commit()
    return await _detail(session, item)


# --- photos ----------------------------------------------------------------------------


@router.post("/items/{item_id}/images", response_model=ItemAdminDetailOut)
async def upload_image(
    item_id: uuid.UUID,
    actor: Editor,
    session: SessionDep,
    file: Annotated[UploadFile, File()],
    source_type: Annotated[ImageSource, Form()],
    source_note: Annotated[str | None, Form(max_length=300)] = None,
):
    """Only own photos, workshop photos (licensed via terms) or supplier photos with
    written permission. Never photos copied from manufacturers' sites."""
    item = await service.get_item(session, item_id)
    content = await file.read(images.MAX_BYTES + 1)
    image = await images.save_image(session, actor, item, content, source_type, source_note)
    has_primary = await session.scalar(
        select(func.count()).where(
            CatalogImage.item_id == item.id, CatalogImage.is_primary.is_(True)
        )
    )
    if not has_primary:
        image.is_primary = True
    service.audit(session, actor, "image.add", "item", item.id, source=source_type)
    await session.commit()
    return await _detail(session, item)


@router.post("/images/{image_id}/primary", response_model=ItemAdminDetailOut)
async def make_primary(image_id: uuid.UUID, actor: Editor, session: SessionDep):
    image = await session.get(CatalogImage, image_id)
    if image is None:
        raise NotFound("catalog.image_not_found", "Image not found")
    others = await session.scalars(
        select(CatalogImage).where(CatalogImage.item_id == image.item_id)
    )
    for other in others.all():
        other.is_primary = other.id == image.id
    await session.commit()
    return await _detail(session, await service.get_item(session, image.item_id))


@router.delete("/images/{image_id}", response_model=ItemAdminDetailOut)
async def delete_image(image_id: uuid.UUID, actor: Editor, session: SessionDep):
    image = await session.get(CatalogImage, image_id)
    if image is None:
        raise NotFound("catalog.image_not_found", "Image not found")
    item = await service.get_item(session, image.item_id)
    was_primary = image.is_primary
    images.delete_files(image)
    await session.delete(image)
    await session.flush()
    if was_primary:
        nxt = await session.scalar(select(CatalogImage).where(CatalogImage.item_id == item.id))
        if nxt:
            nxt.is_primary = True
    service.audit(session, actor, "image.remove", "item", item.id)
    await session.commit()
    return await _detail(session, item)
