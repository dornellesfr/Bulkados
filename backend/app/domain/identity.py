import re

ADMIN_LEVEL = 0
USER_LEVEL = 1
ADMIN_NICK = "bulkados"

NICK_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_nick(value: str) -> str:
    if NICK_PATTERN.fullmatch(value) is None:
        message = "nick must be 3 to 20 characters: letters, digits, underscore"
        raise ValueError(message)
    return value


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if EMAIL_PATTERN.fullmatch(email) is None or len(email) > 320:
        message = "invalid email"
        raise ValueError(message)
    return email
