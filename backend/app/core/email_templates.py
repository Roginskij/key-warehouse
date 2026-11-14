"""Plain-text e-mail templates in all launch languages.

Machine-translated; main ones should be checked by native speakers (see plan).
Placeholders: {name}, {link}, {workshop}, {hours}, {minutes}, {days}.
"""

from app.core.email import OutgoingEmail
from app.core.i18n import normalize_locale

TEMPLATES: dict[str, dict[str, tuple[str, str]]] = {
    "verify_email": {
        "en": (
            "Confirm your e-mail",
            "Hello {name},\n\nPlease confirm your e-mail address by opening this link:\n{link}\n\n"
            "The link is valid for {hours} hours. If you did not register, ignore this e-mail.",
        ),
        "uk": (
            "Підтвердіть свою електронну пошту",
            "Вітаємо, {name}!\n\nПідтвердіть адресу електронної пошти за посиланням:\n{link}\n\n"
            "Посилання дійсне {hours} год. Якщо ви не реєструвалися, проігноруйте цей лист.",
        ),
        "pl": (
            "Potwierdź swój adres e-mail",
            "Dzień dobry, {name}!\n\nPotwierdź swój adres e-mail, otwierając ten link:\n{link}\n\n"
            "Link jest ważny przez {hours} godz. Jeśli to nie Ty się rejestrowałeś, zignoruj tę wiadomość.",
        ),
        "de": (
            "Bestätigen Sie Ihre E-Mail-Adresse",
            "Hallo {name},\n\nbitte bestätigen Sie Ihre E-Mail-Adresse über diesen Link:\n{link}\n\n"
            "Der Link ist {hours} Stunden gültig. Wenn Sie sich nicht registriert haben, ignorieren Sie diese E-Mail.",
        ),
        "fr": (
            "Confirmez votre adresse e-mail",
            "Bonjour {name},\n\nVeuillez confirmer votre adresse e-mail en ouvrant ce lien :\n{link}\n\n"
            "Le lien est valable {hours} heures. Si vous ne vous êtes pas inscrit, ignorez cet e-mail.",
        ),
        "es": (
            "Confirma tu correo electrónico",
            "Hola, {name}:\n\nConfirma tu dirección de correo abriendo este enlace:\n{link}\n\n"
            "El enlace es válido durante {hours} horas. Si no te has registrado, ignora este correo.",
        ),
        "it": (
            "Conferma il tuo indirizzo e-mail",
            "Ciao {name},\n\nconferma il tuo indirizzo e-mail aprendo questo link:\n{link}\n\n"
            "Il link è valido per {hours} ore. Se non ti sei registrato, ignora questa e-mail.",
        ),
    },
    "reset_password": {
        "en": (
            "Reset your password",
            "Hello {name},\n\nTo set a new password, open this link:\n{link}\n\n"
            "The link is valid for {minutes} minutes. If you did not request this, ignore this e-mail.",
        ),
        "uk": (
            "Відновлення пароля",
            "Вітаємо, {name}!\n\nЩоб встановити новий пароль, відкрийте посилання:\n{link}\n\n"
            "Посилання дійсне {minutes} хв. Якщо ви цього не запитували, проігноруйте лист.",
        ),
        "pl": (
            "Resetowanie hasła",
            "Dzień dobry, {name}!\n\nAby ustawić nowe hasło, otwórz ten link:\n{link}\n\n"
            "Link jest ważny przez {minutes} min. Jeśli nie prosiłeś o zmianę hasła, zignoruj tę wiadomość.",
        ),
        "de": (
            "Passwort zurücksetzen",
            "Hallo {name},\n\num ein neues Passwort festzulegen, öffnen Sie diesen Link:\n{link}\n\n"
            "Der Link ist {minutes} Minuten gültig. Wenn Sie dies nicht angefordert haben, ignorieren Sie diese E-Mail.",
        ),
        "fr": (
            "Réinitialisation du mot de passe",
            "Bonjour {name},\n\nPour définir un nouveau mot de passe, ouvrez ce lien :\n{link}\n\n"
            "Le lien est valable {minutes} minutes. Si vous n'avez rien demandé, ignorez cet e-mail.",
        ),
        "es": (
            "Restablecer la contraseña",
            "Hola, {name}:\n\nPara establecer una nueva contraseña, abre este enlace:\n{link}\n\n"
            "El enlace es válido durante {minutes} minutos. Si no lo has solicitado, ignora este correo.",
        ),
        "it": (
            "Reimposta la password",
            "Ciao {name},\n\nper impostare una nuova password apri questo link:\n{link}\n\n"
            "Il link è valido per {minutes} minuti. Se non l'hai richiesto, ignora questa e-mail.",
        ),
    },
    "invitation": {
        "en": (
            "Invitation to {workshop}",
            'Hello,\n\n{name} invites you to join the workshop "{workshop}".\n'
            "Open this link to accept:\n{link}\n\nThe invitation is valid for {days} days.",
        ),
        "uk": (
            "Запрошення до {workshop}",
            "Вітаємо!\n\n{name} запрошує вас до майстерні «{workshop}».\n"
            "Щоб прийняти запрошення, відкрийте посилання:\n{link}\n\nЗапрошення дійсне {days} дн.",
        ),
        "pl": (
            "Zaproszenie do {workshop}",
            "Dzień dobry!\n\n{name} zaprasza Cię do warsztatu „{workshop}”.\n"
            "Aby przyjąć zaproszenie, otwórz ten link:\n{link}\n\nZaproszenie jest ważne przez {days} dni.",
        ),
        "de": (
            "Einladung zu {workshop}",
            "Hallo,\n\n{name} lädt Sie in die Werkstatt „{workshop}“ ein.\n"
            "Öffnen Sie diesen Link, um die Einladung anzunehmen:\n{link}\n\nDie Einladung ist {days} Tage gültig.",
        ),
        "fr": (
            "Invitation à {workshop}",
            "Bonjour,\n\n{name} vous invite à rejoindre l'atelier « {workshop} ».\n"
            "Ouvrez ce lien pour accepter :\n{link}\n\nL'invitation est valable {days} jours.",
        ),
        "es": (
            "Invitación a {workshop}",
            "Hola:\n\n{name} te invita a unirte al taller «{workshop}».\n"
            "Abre este enlace para aceptar:\n{link}\n\nLa invitación es válida durante {days} días.",
        ),
        "it": (
            "Invito a {workshop}",
            "Ciao,\n\n{name} ti invita a unirti all'officina «{workshop}».\n"
            "Apri questo link per accettare:\n{link}\n\nL'invito è valido per {days} giorni.",
        ),
    },
}


def render(kind: str, locale: str | None, to: str, **params: object) -> OutgoingEmail:
    variants = TEMPLATES[kind]
    subject, body = variants.get(normalize_locale(locale), variants["en"])
    return OutgoingEmail(to=to, subject=subject.format(**params), text=body.format(**params))
