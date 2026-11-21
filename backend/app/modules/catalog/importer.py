"""Import of catalog data from CSV / Excel (supplier exports, own tables).

File format — one row = one physical key, first row = headers:

    kind    | name               | Silca  | JMA    | Keyline | frequency_mhz | chip_type
    blank   | VW / Audi HU66     | HU66   | HU-66  | HU66P   |               |
    car_key | Ford Focus 3 btn   |        | FO-21D |         | 433,92        | ID63

* Reserved columns (any case): kind, name, description, frequency_mhz, chip_type, fcc_id.
* Every other column is a brand; the cell holds that brand's code(s).
  Several codes in one cell are separated by ';' or '|' or a new line.
* `kind` may be empty if a default kind is given for the whole file.
* CSV: delimiter ',' ';' or tab is detected; UTF-8 or Windows-1251; decimal comma OK.

Row logic:
* no code known yet         -> new item with all codes
* codes known, one item     -> missing codes are added to that item
* codes point to 2+ items   -> conflict, row skipped (merge those items first)

Dry run executes everything inside a transaction and rolls it back, so the
preview shows exactly what a real run would do.
"""

import csv
import io
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.modules.catalog import service
from app.modules.catalog.models import CatalogImport, ItemKind, SourceType
from app.modules.catalog.normalize import normalize_code
from app.modules.users.models import User

RESERVED = {"kind", "name", "description", "frequency_mhz", "chip_type", "fcc_id"}
MAX_ROWS = 20_000


def _split_codes(cell: str) -> list[str]:
    for sep in ("|", "\n", "\r"):
        cell = cell.replace(sep, ";")
    return [c.strip() for c in cell.split(";") if c.strip()]


def read_table(filename: str, content: bytes) -> list[dict[str, str]]:
    name = filename.lower()
    if name.endswith((".xlsx", ".xlsm")):
        rows = _read_xlsx(content)
    elif name.endswith((".csv", ".txt")):
        rows = _read_csv(content)
    else:
        raise AppError("catalog.import_bad_format", message="Use .xlsx or .csv")
    if not rows:
        raise AppError("catalog.import_empty", message="File has no data rows")
    if len(rows) > MAX_ROWS:
        raise AppError("catalog.import_too_big", message=f"Max {MAX_ROWS} rows per file")
    return rows


ROW_KEY = "__row__"  # original row number in the file, for error messages


def _rows_from_matrix(matrix: list[list[Any]]) -> list[dict[str, str]]:
    def blank(r: list[Any]) -> bool:
        return not any(str(c or "").strip() for c in r)

    header_at = next((i for i, r in enumerate(matrix) if not blank(r)), None)
    if header_at is None:
        return []
    headers = [str(h or "").strip() for h in matrix[header_at]]
    out = []
    for offset, raw in enumerate(matrix[header_at + 1 :], start=header_at + 2):
        if blank(raw):
            continue
        row = {ROW_KEY: offset}
        for h, v in zip(headers, raw, strict=False):
            if h:
                row[h] = "" if v is None else str(v).strip()
        out.append(row)
    return out


def _read_xlsx(content: bytes) -> list[dict[str, str]]:
    from openpyxl import load_workbook

    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:
        raise AppError("catalog.import_bad_format", message="Cannot read Excel file") from exc
    sheet = wb.worksheets[0]
    return _rows_from_matrix([list(r) for r in sheet.iter_rows(values_only=True)])


def _read_csv(content: bytes) -> list[dict[str, str]]:
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            text = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise AppError("catalog.import_bad_format", message="Unknown text encoding")
    # The header line decides: Excel in Ukraine/EU saves CSV with ";", and rows often have
    # fewer cells than the header, which confuses csv.Sniffer.
    header = next((line for line in text.splitlines() if line.strip()), "")
    counts = {d: header.count(d) for d in (";", "\t", ",")}
    delimiter = max(counts, key=counts.get)
    if counts[delimiter]:
        return _rows_from_matrix(list(csv.reader(io.StringIO(text), delimiter=delimiter)))
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    return _rows_from_matrix(list(csv.reader(io.StringIO(text), dialect)))


def _decimal(value: str) -> Decimal | None:
    if not value:
        return None
    try:
        return Decimal(value.replace(",", ".").replace(" ", ""))
    except InvalidOperation as exc:
        raise ValueError(f"not a number: {value}") from exc


async def run_import(
    session: AsyncSession,
    actor: User,
    *,
    filename: str,
    rows: list[dict[str, str]],
    source_label: str,
    default_kind: ItemKind | None,
    dry_run: bool,
) -> dict[str, Any]:
    imp = CatalogImport(filename=filename, source_label=source_label, created_by_id=actor.id)
    session.add(imp)
    await session.flush()
    source = service.Source(SourceType.IMPORT, ref=source_label, import_id=imp.id)

    headers = {h for r in rows for h in r if h != ROW_KEY}
    reserved = {h: h.lower() for h in headers if h.lower() in RESERVED}
    brand_columns = sorted(h for h in headers if h not in reserved)
    if not brand_columns:
        raise AppError("catalog.import_no_brands", message="No brand columns found")

    report: dict[str, Any] = {
        "rows_total": len(rows),
        "created_items": 0,
        "updated_items": 0,
        "codes_added": 0,
        "unchanged": 0,
        "skipped_empty": 0,
        "new_brands": [],
        "conflicts": [],
        "errors": [],
    }
    brands = {}
    for col in brand_columns:
        existing = await service.find_brand(session, col)
        brands[col] = existing or await service.get_brand(session, col, create=True, actor=actor)
        if existing is None:
            report["new_brands"].append(col)

    for raw in rows:
        index = raw.get(ROW_KEY)
        row = {reserved.get(k, k): v for k, v in raw.items() if k != ROW_KEY}
        codes = [
            (brands[col], code) for col in brand_columns for code in _split_codes(row.get(col, ""))
        ]
        codes = [(b, c) for b, c in codes if normalize_code(c)]
        if not codes:
            report["skipped_empty"] += 1
            continue
        try:
            async with session.begin_nested():
                outcome = await _import_row(session, actor, row, codes, default_kind, source)
        except ValueError as exc:
            report["errors"].append({"row": index, "reason": str(exc)})
            continue
        except _RowConflict as exc:
            report["conflicts"].append({"row": index, "item_ids": exc.item_ids})
            continue
        except AppError as exc:
            report["errors"].append({"row": index, "reason": exc.code, "params": exc.params})
            continue
        kind, added = outcome
        report[kind] += 1
        report["codes_added"] += added

    imp.stats = {k: v for k, v in report.items() if isinstance(v, int)}
    service.audit(
        session,
        actor,
        "import.run",
        "import",
        imp.id,
        filename=filename,
        source=source_label,
        stats=imp.stats,
    )
    report["import_id"] = None if dry_run else str(imp.id)
    report["dry_run"] = dry_run
    return report


class _RowConflict(Exception):
    def __init__(self, item_ids: list[str]) -> None:
        self.item_ids = item_ids


async def _import_row(session, actor, row, codes, default_kind, source) -> tuple[str, int]:
    found = {}
    for brand, code in codes:
        existing = await service.find_code(session, brand, code)
        if existing:
            item = await service.resolve_item(session, existing.item_id)
            found[item.id] = item
    if len(found) > 1:
        raise _RowConflict(sorted(str(i) for i in found))

    if found:
        item = next(iter(found.values()))
        before = len(item.codes)
        for brand, code in codes:
            await service.add_code(session, actor, item, brand, code, source)
        await session.refresh(item, ["codes"])
        added = len(item.codes) - before
        return ("updated_items" if added else "unchanged"), added

    kind_raw = (row.get("kind") or "").strip().lower() or (default_kind or "")
    try:
        kind = ItemKind(kind_raw)
    except ValueError as exc:
        raise ValueError(f"unknown kind '{kind_raw}'") from exc
    item = await service.create_item(
        session,
        actor,
        kind=kind,
        name=row.get("name") or codes[0][1],
        codes=_unique(codes),
        source=source,
        description=row.get("description") or None,
        frequency_mhz=_decimal(row.get("frequency_mhz", "")),
        chip_type=row.get("chip_type") or None,
        fcc_id=row.get("fcc_id") or None,
    )
    return "created_items", len(item.codes)


def _unique(codes):
    seen, out = set(), []
    for brand, code in codes:
        key = (brand.id, normalize_code(code))
        if key not in seen:
            seen.add(key)
            out.append((brand, code))
    return out
