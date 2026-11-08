import pytest

from app.domain.search import normalize_search_text


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("Abdução", "abducao"),
        ("Jötun Grunt", "jotun grunt"),
        ("Urza, Lord High Artificer", "urza lord high artificer"),
        ("Abu Ja'far", "abu ja far"),
        ("  Fire // Ice ", "fire ice"),
    ],
)
def test_normalizes_accents_case_and_punctuation(value: str, expected: str) -> None:
    assert normalize_search_text(value) == expected
