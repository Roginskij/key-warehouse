"""Demo account for local testing: a regular workshop owner (NOT an admin) with stock.

    uv run python -m app.seed_demo            # create (skips if it exists)
    uv run python -m app.seed_demo --reset    # delete and create again
    uv run python -m app.seed_demo --shop     # also show the demo workshop on the public site

The e-mail and a freshly generated password are written to `dev-accounts.local.md`
(git-ignored). Never run against production.
"""

import argparse
import asyncio
import secrets
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

import app.models  # noqa: F401
from app.core.config import settings
from app.core.db import SessionLocal
from app.core.security import hash_password, utcnow
from app.modules.inventory import service as inv
from app.modules.inventory.models import CurrencyRate, InventoryItem, MovementType, StorageLocation
from app.modules.users.models import User
from app.modules.users.service import purge_user
from app.modules.workshops.service import create_workshop

EMAIL = "demo@example.com"
OUT = Path(__file__).resolve().parents[1] / "dev-accounts.local.md"

# name, kind, brand, code, qty, min, purchase (price, cur), sale UAH, vehicles, place
ITEMS = [
    (
        "Заготовка VW / Audi",
        "blank",
        "Silca",
        "HU66",
        14,
        5,
        ("1.50", "USD"),
        "120",
        "VW Golf 4, Passat B5, Audi A4",
        "box1",
    ),
    (
        "Заготовка Fiat",
        "blank",
        "Silca",
        "SIP22",
        7,
        3,
        ("1.20", "USD"),
        "110",
        "Fiat Doblo, Punto",
        "box1",
    ),
    (
        "Заготовка Renault",
        "blank",
        "Silca",
        "VA2",
        2,
        4,
        ("1.30", "USD"),
        "110",
        "Renault Kangoo, Megane",
        "box1",
    ),
    (
        "Заготовка Toyota",
        "blank",
        "Silca",
        "TOY43",
        9,
        3,
        ("1.40", "USD"),
        "120",
        "Toyota Corolla, Camry",
        "box2",
    ),
    (
        "Заготовка Ford",
        "blank",
        "JMA",
        "FO-21D",
        6,
        3,
        ("38", "UAH"),
        "110",
        "Ford Focus, Transit",
        "box2",
    ),
    (
        "Заготовка Opel",
        "blank",
        "Silca",
        "HU100",
        0,
        3,
        ("1.50", "USD"),
        "120",
        "Opel Astra H, Zafira B",
        "box2",
    ),
    (
        "Брелок Ford 3 кнопки",
        "remote",
        None,
        "FO21-R",
        2,
        3,
        ("250", "UAH"),
        "800",
        "Ford Focus 2",
        "car",
    ),
    (
        "Автоключ VW 3 кнопки 434 МГц",
        "car_key",
        None,
        "1J0959753",
        3,
        2,
        ("14", "USD"),
        "1500",
        "VW Golf 4, Passat B5",
        "car",
    ),
    ("Чип ID46", "transponder", None, "ID46", 1, 5, ("90", "UAH"), "350", None, "shelf"),
    (
        "Чип ID48",
        "transponder",
        None,
        "ID48",
        6,
        3,
        ("110", "UAH"),
        "400",
        "VW, Audi, Skoda",
        "shelf",
    ),
    (
        "Корпус Toyota 2 кнопки",
        "key_shell",
        None,
        "TOY43-2B",
        4,
        0,
        ("70", "UAH"),
        "280",
        "Toyota",
        "shelf",
    ),
    ("Батарейка CR2032", "battery", None, "CR2032", 25, 10, ("8", "UAH"), "40", None, "shelf"),
]


async def run(reset: bool) -> None:
    if settings.environment == "prod":
        raise SystemExit("Refusing to create a demo account in production")
    async with SessionLocal() as session:
        existing = await session.scalar(select(User).where(User.email == EMAIL))
        if existing and not reset:
            print(f"{EMAIL} already exists — see {OUT.name}, or run with --reset")
            return
        if existing:
            await purge_user(session, existing)
            await session.commit()

        password = "demo-" + secrets.token_urlsafe(9)
        user = User(
            email=EMAIL,
            full_name="Демо Майстер",
            password_hash=hash_password(password),
            email_verified_at=utcnow(),
            locale="uk",
            terms_version=settings.terms_version,
            terms_accepted_at=utcnow(),
        )
        session.add(user)
        await session.flush()
        workshop, _ = await create_workshop(session, user, "Демо Ключі Київ", "UA")

        main = await inv.default_location(session, workshop.id)
        rack = StorageLocation(workshop_id=workshop.id, name="Стелаж", kind="rack")
        car = StorageLocation(workshop_id=workshop.id, name="Ford Transit", kind="vehicle")
        session.add_all([rack, car])
        await session.flush()
        box1 = StorageLocation(
            workshop_id=workshop.id, name="Ящик 1", kind="box", parent_id=rack.id
        )
        box2 = StorageLocation(
            workshop_id=workshop.id, name="Ящик 2", kind="box", parent_id=rack.id
        )
        shelf = StorageLocation(
            workshop_id=workshop.id, name="Полиця", kind="shelf", parent_id=rack.id
        )
        car_box = StorageLocation(
            workshop_id=workshop.id, name="Бокс 1", kind="box", parent_id=car.id
        )
        session.add_all([box1, box2, shelf, car_box])
        await session.flush()
        places = {"box1": box1, "box2": box2, "shelf": shelf, "car": car_box, "main": main}
        session.add(CurrencyRate(workshop_id=workshop.id, currency="USD", rate=Decimal("41.5")))

        created = []
        for name, kind, brand, code, qty, min_q, (pp, pcur), sale, cars, place in ITEMS:
            item = InventoryItem(
                workshop_id=workshop.id,
                kind=kind,
                name=name,
                vehicles=cars,
                purchase_price=Decimal(pp),
                purchase_currency=pcur,
                sale_price=Decimal(sale),
                sale_currency="UAH",
                min_quantity=min_q,
                quantity=0,
                created_by_id=user.id,
            )
            inv.apply_code(item, brand, code)
            session.add(item)
            await session.flush()
            if qty:
                await inv.move(
                    session, user, item, MovementType.INITIAL, qty, location_id=places[place].id
                )
            match = await inv.find_catalog_match(session, item.brand, item.code)
            if match:
                item.catalog_item_id = match.id
            created.append(item)

        # A little history: a few sales and a delivery.
        hu66, fiat, chip48 = created[0], created[1], created[9]
        for it, n, client in [(hu66, 2, "Олег, Golf 4"), (fiat, 1, None), (chip48, 1, "Ірина")]:
            await inv.move(session, user, it, MovementType.SALE, n, client_name=client)
        await inv.move(session, user, hu66, MovementType.RECEIPT, 5, location_id=box1.id)
        # Something that has been lying for a long time (stage 2 "stale stock").
        created[3].marked_stale_at = utcnow() - timedelta(days=200)
        await session.commit()

    OUT.write_text(
        "# Local dev accounts (git-ignored, never commit)\n\n"
        "Regular workshop owner, not an admin, with demo stock:\n\n"
        f"- e-mail: `{EMAIL}`\n- password: `{password}`\n- workshop: Демо Ключі Київ (UA)\n\n"
        "Recreate with `uv run python -m app.seed_demo --reset` (new password).\n",
        encoding="utf-8",
    )
    print(f"Demo account created. Credentials: {OUT}")


DEMO_TEXT = "Демо-опис для локальної перевірки сайту. {name}: заготовка під код {code}."


async def run_shop() -> None:
    """Local only: public profile for the demo workshop, its stock shown on the site,
    and catalog items (with a demo description and car fits) for stock that has none."""
    from app.modules.catalog import fits
    from app.modules.catalog import service as cat
    from app.modules.catalog.models import ItemVehicleFit
    from app.modules.catalog.service import Source
    from app.modules.workshops.models import Membership, Workshop

    if settings.environment == "prod":
        raise SystemExit("Refusing to touch production")
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == EMAIL))
        if user is None:
            raise SystemExit("Run `python -m app.seed_demo` first")
        workshop = await session.scalar(
            select(Workshop).join(Membership).where(Membership.user_id == user.id)
        )
        workshop.public_listed = True
        workshop.public_city = "Київ"
        workshop.public_address = "вул. Демонстраційна, 1"
        workshop.public_phone = "+380000000000"
        workshop.public_telegram = "@demo_keys"
        workshop.public_hours = "Пн–Пт 9–18, Сб 10–15"
        workshop.public_about = "Демо-майстерня для локальної перевірки."
        workshop.price_display = "from"
        items = (
            await session.scalars(
                select(InventoryItem).where(InventoryItem.workshop_id == workshop.id)
            )
        ).all()
        source = Source(type="admin", ref="demo seed")
        for it in items:
            if not it.brand or not it.code:
                continue
            if it.catalog_item_id is None:
                brand = await cat.get_brand(session, it.brand, create=True)
                found = await cat.find_code(session, brand, it.code)
                if found:
                    item = await cat.resolve_item(session, found.item_id)
                else:
                    item = await cat.create_item(
                        session,
                        None,
                        kind=it.kind,
                        name=it.name,
                        codes=[(brand, it.code)],
                        source=source,
                    )
                it.catalog_item_id = item.id
            item = await cat.get_item(session, it.catalog_item_id)
            if not item.description:
                item.description = DEMO_TEXT.format(name=item.name, code=it.code)
            for car in (it.vehicles or "").split(","):
                make, _, model = car.strip().partition(" ")
                if make and model:
                    vm = await fits.vehicle_model(session, make, model)
                    exists = await session.scalar(
                        select(ItemVehicleFit.id).where(
                            ItemVehicleFit.item_id == item.id, ItemVehicleFit.model_id == vm.id
                        )
                    )
                    if not exists:
                        session.add(ItemVehicleFit(item_id=item.id, model_id=vm.id))
            it.public_visible = True
            await session.flush()
        await session.commit()
    print("Demo workshop is now on the public site (city: Київ).")


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.seed_demo")
    parser.add_argument(
        "--reset", action="store_true", help="delete the demo account and recreate it"
    )
    parser.add_argument(
        "--shop", action="store_true", help="show the demo workshop on the public site"
    )
    args = parser.parse_args()
    if args.shop:
        asyncio.run(run_shop())
    else:
        asyncio.run(run(args.reset))


if __name__ == "__main__":
    main()
