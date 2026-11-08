import re

ADMIN_LEVEL = 0
USER_LEVEL = 1

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if EMAIL_PATTERN.fullmatch(email) is None or len(email) > 320:
        message = "Informe um e-mail válido."
        raise ValueError(message)
    return email


def normalize_person_name(value: str, *, missing: str) -> str:
    name = " ".join(value.split())
    if not name:
        raise ValueError(missing)
    if len(name) > 80:
        message = "Use no máximo 80 caracteres."
        raise ValueError(message)
    return name
