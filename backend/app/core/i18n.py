"""Languages supported at launch. The UI itself is translated on the frontend;
the backend only needs the locale for e-mails."""

SUPPORTED_LOCALES: dict[str, str] = {
    "uk": "Українська",
    "en": "English",
    "pl": "Polski",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "it": "Italiano",
}
DEFAULT_LOCALE = "en"


def normalize_locale(locale: str | None) -> str:
    if not locale:
        return DEFAULT_LOCALE
    short = locale.split("-")[0].split("_")[0].lower()
    return short if short in SUPPORTED_LOCALES else DEFAULT_LOCALE
