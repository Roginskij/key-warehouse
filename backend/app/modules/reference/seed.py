"""Reference data. New countries / zones (UK, North America) are added here
plus a migration — no code changes needed elsewhere."""

CURRENCIES = [
    {"code": "EUR", "name": "Euro", "minor_units": 2},
    {"code": "UAH", "name": "Ukrainian hryvnia", "minor_units": 2},
    {"code": "USD", "name": "US dollar", "minor_units": 2},
    {"code": "PLN", "name": "Polish złoty", "minor_units": 2},
    {"code": "CZK", "name": "Czech koruna", "minor_units": 2},
    {"code": "HUF", "name": "Hungarian forint", "minor_units": 2},
    {"code": "RON", "name": "Romanian leu", "minor_units": 2},
    {"code": "SEK", "name": "Swedish krona", "minor_units": 2},
    {"code": "DKK", "name": "Danish krone", "minor_units": 2},
]

TRADE_ZONES = [
    {"code": "EU", "name": "European Union"},
    {"code": "UA", "name": "Ukraine"},
]

_EU = [
    ("AT", "Austria", "EUR"),
    ("BE", "Belgium", "EUR"),
    ("BG", "Bulgaria", "EUR"),  # euro since 2026-01-01
    ("HR", "Croatia", "EUR"),
    ("CY", "Cyprus", "EUR"),
    ("CZ", "Czechia", "CZK"),
    ("DK", "Denmark", "DKK"),
    ("EE", "Estonia", "EUR"),
    ("FI", "Finland", "EUR"),
    ("FR", "France", "EUR"),
    ("DE", "Germany", "EUR"),
    ("GR", "Greece", "EUR"),
    ("HU", "Hungary", "HUF"),
    ("IE", "Ireland", "EUR"),
    ("IT", "Italy", "EUR"),
    ("LV", "Latvia", "EUR"),
    ("LT", "Lithuania", "EUR"),
    ("LU", "Luxembourg", "EUR"),
    ("MT", "Malta", "EUR"),
    ("NL", "Netherlands", "EUR"),
    ("PL", "Poland", "PLN"),
    ("PT", "Portugal", "EUR"),
    ("RO", "Romania", "RON"),
    ("SK", "Slovakia", "EUR"),
    ("SI", "Slovenia", "EUR"),
    ("ES", "Spain", "EUR"),
    ("SE", "Sweden", "SEK"),
]

COUNTRIES = [
    {"code": c, "name": n, "default_currency": cur, "trade_zone": "EU", "is_enabled": True}
    for c, n, cur in _EU
] + [
    {
        "code": "UA",
        "name": "Ukraine",
        "default_currency": "UAH",
        "trade_zone": "UA",
        "is_enabled": True,
    }
]
