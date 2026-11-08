import re
import unicodedata

_NOT_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


def normalize_search_text(value: str) -> str:
    """Minúsculas, sem acento nem pontuação, para a busca por prefixo do catálogo."""
    decomposed = unicodedata.normalize("NFKD", value)
    unaccented = "".join(char for char in decomposed if not unicodedata.combining(char))
    return _NOT_ALPHANUMERIC.sub(" ", unaccented.lower()).strip()
