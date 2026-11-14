"""Moving a workshop's stock from its own Excel / CSV table, and export back to Excel.

Import is two steps (the file is sent each time, nothing is stored in between):
1. `analyze` — headers, first rows and a suggested mapping "our field -> your column".
   Headers are recognized in uk / ru / en / pl / de / fr / es / it.
2. `import` with the mapping the master confirmed (dry_run first for the preview).

Real tables are messy: decimal commas, "12 грн", "5 шт", empty rows — all handled.
"""

import io
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.core.security import utcnow
from app.modules.catalog.importer import ROW_KEY, read_table
from app.modules.catalog.models import ItemKind
from app.modules.inventory import service
from app.modules.inventory.models import InventoryItem, MovementType
from app.modules.users.models import User
from app.modules.workshops.models import Workshop

FIELDS = [
    "name",
    "code",
    "brand",
    "kind",
    "quantity",
    "purchase_price",
    "sale_price",
    "min_quantity",
    "vehicles",
    "location",
    "notes",
    "stale",
]

# Order matters: more specific words first. Compared with lowercased header.
SYNONYMS: dict[str, list[str]] = {
    "vehicles": [
        "марка авто",
        "марка автомобіля",
        "марка автомобиля",
        "автомобіль",
        "автомобиль",
        "авто",
        "машина",
        "модель",
        "car",
        "vehicle",
        "vehicles",
        "samochód",
        "auto",
        "fahrzeug",
        "voiture",
        "véhicule",
        "coche",
        "vehículo",
        "veicolo",
    ],
    "purchase_price": [
        "закупівельна ціна",
        "закупочная цена",
        "ціна закупівлі",
        "цена закупки",
        "закупка",
        "закупівля",
        "собівартість",
        "себестоимость",
        "вхід",
        "вход",
        "purchase price",
        "purchase",
        "cost",
        "cena zakupu",
        "zakup",
        "einkaufspreis",
        "einkauf",
        "ek",
        "prix d'achat",
        "achat",
        "precio de compra",
        "compra",
        "prezzo d'acquisto",
        "acquisto",
    ],
    "sale_price": [
        "ціна продажу",
        "цена продажи",
        "роздріб",
        "розница",
        "продаж",
        "продажа",
        "ціна",
        "цена",
        "sale price",
        "price",
        "sale",
        "retail",
        "cena sprzedaży",
        "cena",
        "verkaufspreis",
        "verkauf",
        "vk",
        "preis",
        "prix de vente",
        "prix",
        "precio de venta",
        "precio",
        "prezzo di vendita",
        "prezzo",
    ],
    "min_quantity": [
        "мінімальний залишок",
        "минимальный остаток",
        "мінімум",
        "минимум",
        "мін",
        "мин",
        "min stock",
        "minimum",
        "min",
        "stan minimalny",
        "mindestbestand",
        "stock minimum",
        "stock mínimo",
        "scorta minima",
    ],
    "quantity": [
        "кількість",
        "количество",
        "кол-во",
        "к-сть",
        "залишок",
        "остаток",
        "наявність",
        "наличие",
        "шт",
        "qty",
        "quantity",
        "stock",
        "amount",
        "ilość",
        "stan",
        "menge",
        "anzahl",
        "bestand",
        "quantité",
        "cantidad",
        "existencias",
        "quantità",
        "giacenza",
    ],
    "brand": [
        "виробник",
        "производитель",
        "бренд",
        "brand",
        "manufacturer",
        "make",
        "producent",
        "marka",
        "hersteller",
        "marke",
        "marque",
        "fabricant",
        "fabricante",
        "marca",
        "produttore",
    ],
    "code": [
        "номер заготовки",
        "артикул",
        "номер",
        "код",
        "code",
        "number",
        "part number",
        "ref",
        "reference",
        "numer",
        "kod",
        "nummer",
        "artikelnummer",
        "référence",
        "código",
        "codice",
        "sku",
    ],
    "kind": [
        "вид",
        "тип",
        "категорія",
        "категория",
        "kind",
        "type",
        "category",
        "typ",
        "kategoria",
        "kategorie",
        "catégorie",
        "tipo",
        "categoría",
        "categoria",
    ],
    "location": [
        "місце зберігання",
        "место хранения",
        "місце",
        "место",
        "ящик",
        "полиця",
        "полка",
        "location",
        "place",
        "shelf",
        "box",
        "lokalizacja",
        "miejsce",
        "półka",
        "lagerort",
        "ort",
        "regal",
        "emplacement",
        "ubicación",
        "posizione",
        "scaffale",
    ],
    "notes": [
        "примітка",
        "примечание",
        "коментар",
        "комментарий",
        "notes",
        "note",
        "comment",
        "uwagi",
        "notiz",
        "bemerkung",
        "remarque",
        "nota",
        "note",
        "commento",
    ],
    "stale": [
        "залежалось",
        "лежить давно",
        "лежит давно",
        "неліквід",
        "неликвид",
        "stale",
        "old stock",
        "dead stock",
        "zalegający",
        "ladenhüter",
    ],
    "name": [
        "найменування",
        "наименование",
        "назва",
        "название",
        "опис",
        "описание",
        "товар",
        "name",
        "description",
        "item",
        "product",
        "nazwa",
        "bezeichnung",
        "artikel",
        "name",
        "désignation",
        "nom",
        "nombre",
        "descripción",
        "nome",
        "descrizione",
    ],
}

KIND_WORDS: dict[str, list[str]] = {
    ItemKind.CAR_KEY: [
        "автоключ",
        "авто ключ",
        "ключ авто",
        "car key",
        "carkey",
        "autoschlüssel",
        "kluczyk",
    ],
    ItemKind.REMOTE: [
        "брелок",
        "пульт",
        "remote",
        "fob",
        "pilot",
        "fernbedienung",
        "télécommande",
        "mando",
        "telecomando",
    ],
    ItemKind.TRANSPONDER: ["транспондер", "чип", "chip", "transponder"],
    ItemKind.CYLINDER: [
        "циліндр",
        "цилиндр",
        "личинка",
        "сердцевина",
        "cylinder",
        "wkładka",
        "zylinder",
        "cylindre",
        "cilindro",
        "bombín",
    ],
    ItemKind.KEY_SHELL: [
        "корпус",
        "shell",
        "case",
        "obudowa",
        "gehäuse",
        "coque",
        "carcasa",
        "guscio",
    ],
    ItemKind.BATTERY: [
        "батарейка",
        "батарея",
        "battery",
        "bateria",
        "batterie",
        "pile",
        "batería",
        "batteria",
    ],
    ItemKind.MACHINE: [
        "верстат",
        "станок",
        "machine",
        "maszyna",
        "maschine",
        "máquina",
        "macchina",
    ],
    ItemKind.PROGRAMMER: [
        "програматор",
        "программатор",
        "programmer",
        "programator",
        "programmiergerät",
        "programmateur",
        "programador",
        "programmatore",
    ],
    ItemKind.BLANK: [
        "заготовка",
        "заготовки",
        "blank",
        "półfabrykat",
        "rohling",
        "ébauche",
        "llave en bruto",
        "grezzo",
    ],
}

TRUTHY = {
    "1",
    "+",
    "так",
    "да",
    "yes",
    "y",
    "x",
    "true",
    "tak",
    "ja",
    "oui",
    "sí",
    "si",
    "v",
    "✓",
    "✔",
}


def suggest_mapping(headers: list[str]) -> dict[str, str]:
    """our field -> header. Exact synonym match first, then 'header contains synonym'."""
    lowered = {h: h.strip().lower() for h in headers if h and h.strip()}
    mapping: dict[str, str] = {}
    used: set[str] = set()
    for exact in (True, False):
        for field, words in SYNONYMS.items():
            if field in mapping:
                continue
            for word in words:
                hit = next(
                    (
                        h
                        for h, low in lowered.items()
                        if h not in used and (low == word if exact else word in low)
                    ),
                    None,
                )
                if hit:
                    mapping[field] = hit
                    used.add(hit)
                    break
    return {f: mapping[f] for f in FIELDS if f in mapping}


def analyze(filename: str, content: bytes) -> dict[str, Any]:
    rows = read_table(filename, content)
    headers = list(dict.fromkeys(h for r in rows for h in r if h != ROW_KEY))
    return {
        "headers": headers,
        "rows_total": len(rows),
        "sample": [{k: v for k, v in r.items() if k != ROW_KEY} for r in rows[:5]],
        "suggested_mapping": suggest_mapping(headers),
        "fields": FIELDS,
    }


_NUM = re.compile(r"[^\d,.\-]")


def parse_decimal(value: str | None) -> Decimal | None:
    if value is None:
        return None
    raw = str(value).strip()
    if raw in {"", "-", "—", "–"}:
        return None
    s = _NUM.sub("", raw)
    if not s or s in {"-", ".", ","}:
        raise ValueError(f"not a number: {value}")
    if "," in s and "." in s:  # 1.234,50 or 1,234.50 — the last one is the decimal mark
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
    else:
        s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"not a number: {value}") from None


def parse_int(value: str | None) -> int:
    d = parse_decimal(value)
    if d is None:
        return 0
    if d < 0:
        raise ValueError(f"negative quantity: {value}")
    return int(d.to_integral_value())


def parse_kind(value: str | None, default: ItemKind) -> ItemKind:
    if not value or not value.strip():
        return default
    low = value.strip().lower()
    try:
        return ItemKind(low)
    except ValueError:
        pass
    for kind, words in KIND_WORDS.items():
        if any(w in low for w in words):
            return ItemKind(kind)
    return default


async def run_import(
    session: AsyncSession,
    user: User,
    workshop: Workshop,
    *,
    rows: list[dict[str, str]],
    mapping: dict[str, str],
    default_kind: ItemKind,
    currency: str,
    location_id,
) -> dict[str, Any]:
    unknown = set(mapping) - set(FIELDS)
    if unknown:
        raise AppError("inventory.import_bad_mapping", message=f"Unknown fields {sorted(unknown)}")
    if "name" not in mapping and "code" not in mapping:
        raise AppError(
            "inventory.import_bad_mapping", message="Map at least a name or a code column"
        )

    def cell(row: dict[str, str], field: str) -> str | None:
        header = mapping.get(field)
        value = row.get(header) if header else None
        return value.strip() if value and value.strip() else None

    report: dict[str, Any] = {
        "rows_total": len(rows),
        "created": 0,
        "skipped_empty": 0,
        "duplicates": [],
        "errors": [],
        "linked_to_catalog": 0,
        "proposed_to_catalog": 0,
        "total_quantity": 0,
    }
    default_loc = location_id or (await service.default_location(session, workshop.id)).id
    now = utcnow()

    for row in rows:
        index = row.get(ROW_KEY)
        name, code, brand = cell(row, "name"), cell(row, "code"), cell(row, "brand")
        if not name and not code:
            report["skipped_empty"] += 1
            continue
        try:
            async with session.begin_nested():
                if await service.find_duplicate(session, workshop.id, brand, code):
                    report["duplicates"].append({"row": index, "code": code})
                    continue
                qty = parse_int(cell(row, "quantity"))
                purchase = parse_decimal(cell(row, "purchase_price"))
                sale = parse_decimal(cell(row, "sale_price"))
                loc_name = cell(row, "location")
                loc_id = (
                    (await service.find_or_create_location(session, workshop.id, loc_name)).id
                    if loc_name
                    else default_loc
                )
                item = InventoryItem(
                    workshop_id=workshop.id,
                    kind=parse_kind(cell(row, "kind") or name, default_kind),
                    name=(name or code)[:200],
                    vehicles=(cell(row, "vehicles") or None),
                    purchase_price=purchase,
                    purchase_currency=currency if purchase is not None else None,
                    sale_price=sale,
                    sale_currency=currency if sale is not None else None,
                    min_quantity=parse_int(cell(row, "min_quantity")),
                    notes=cell(row, "notes"),
                    marked_stale_at=now if (cell(row, "stale") or "").lower() in TRUTHY else None,
                    created_by_id=user.id,
                    quantity=0,
                )
                service.apply_code(item, brand, code)
                session.add(item)
                await session.flush()
                if qty > 0:
                    await service.move(
                        session,
                        user,
                        item,
                        MovementType.INITIAL,
                        qty,
                        location_id=loc_id,
                        note="import",
                    )
                link = await service.auto_link(session, user, item)
        except ValueError as exc:
            report["errors"].append({"row": index, "reason": str(exc)})
            continue
        except AppError as exc:
            report["errors"].append({"row": index, "reason": exc.code})
            continue
        report["created"] += 1
        report["total_quantity"] += qty
        report["linked_to_catalog"] += link == "linked"
        report["proposed_to_catalog"] += link == "proposed"

    service.audit(
        session,
        workshop.id,
        user,
        "import",
        None,
        **{k: v for k, v in report.items() if isinstance(v, int)},
    )
    return report


# --- export ----------------------------------------------------------------------------


def export_xlsx(
    items: list[InventoryItem], locations: dict, show_purchase: bool, base_currency: str
) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font

    wb = Workbook()
    ws = wb.active
    ws.title = "Stock"
    headers = [
        "Name",
        "Kind",
        "Brand",
        "Code",
        "Catalog codes",
        "Vehicles",
        "Quantity",
        "Min",
        "Locations",
        "Sale price",
        "Sale currency",
    ]
    if show_purchase:
        headers += ["Purchase price", "Purchase currency", "Value"]
    headers += ["Notes", "Last movement"]
    ws.append(headers)
    for c in ws[1]:
        c.font = Font(bold=True)

    for it in items:
        catalog_codes = (
            "; ".join(f"{c.brand.name} {c.code}" for c in it.catalog_item.codes)
            if it.catalog_item
            else ""
        )
        locs = "; ".join(f"{locations.get(lv.location_id, '?')}: {lv.quantity}" for lv in it.levels)
        row: list[Any] = [
            it.name,
            it.kind,
            it.brand,
            it.code,
            catalog_codes,
            it.vehicles,
            it.quantity,
            it.min_quantity,
            locs,
            it.sale_price,
            it.sale_currency,
        ]
        if show_purchase:
            value = it.purchase_price * it.quantity if it.purchase_price is not None else None
            row += [it.purchase_price, it.purchase_currency, value]
        row += [it.notes, _naive(it.last_movement_at)]
        ws.append(row)

    ws.freeze_panes = "A2"
    for col in ws.columns:
        width = max(len(str(c.value or "")) for c in col)
        ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 8), 50)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _naive(dt: datetime | None):
    return dt.replace(tzinfo=None) if dt else None
