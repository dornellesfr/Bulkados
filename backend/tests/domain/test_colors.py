from itertools import combinations

import pytest

from app.domain.colors import WUBRG, canonical_colors, identity_name


def test_every_combination_has_its_own_name() -> None:
    names = {identity_name(subset) for size in range(6) for subset in combinations(WUBRG, size)}

    assert len(names) == 32
    assert all(names)


@pytest.mark.parametrize(
    ("colors", "name"),
    [
        ([], "Incolor"),
        (["R"], "Mono-vermelho"),
        (["G", "W"], "Selesnya"),
        (["R", "B"], "Rakdos"),
        (["U", "G"], "Simic"),
        (["G", "U", "W"], "Bant"),
        (["R", "U", "B"], "Grixis"),
        (["W", "B", "G"], "Abzan"),
        (["W", "U", "B", "R"], "Yore-Tiller"),
        (["U", "B", "R", "G"], "Glint-Eye"),
        (["W", "U", "B", "R", "G"], "Cinco cores"),
    ],
)
def test_names_ignore_the_order_and_case_of_the_colors(colors: list[str], name: str) -> None:
    assert identity_name(colors) == name
    assert identity_name([color.lower() for color in colors]) == name


def test_colors_come_out_in_wubrg_order() -> None:
    assert canonical_colors(["G", "r", "W", "G"]) == ["W", "R", "G"]
