from collections.abc import Iterable

WUBRG = "WUBRG"

_NAMES: dict[str, str] = {
    "": "Incolor",
    "W": "Mono-branco",
    "U": "Mono-azul",
    "B": "Mono-preto",
    "R": "Mono-vermelho",
    "G": "Mono-verde",
    "WU": "Azorius",
    "UB": "Dimir",
    "BR": "Rakdos",
    "RG": "Gruul",
    "WG": "Selesnya",
    "WB": "Orzhov",
    "UR": "Izzet",
    "BG": "Golgari",
    "WR": "Boros",
    "UG": "Simic",
    "WUG": "Bant",
    "WUB": "Esper",
    "UBR": "Grixis",
    "BRG": "Jund",
    "WRG": "Naya",
    "WBG": "Abzan",
    "WUR": "Jeskai",
    "UBG": "Sultai",
    "WBR": "Mardu",
    "URG": "Temur",
    "WUBR": "Yore-Tiller",
    "UBRG": "Glint-Eye",
    "WBRG": "Dune-Brood",
    "WURG": "Ink-Treader",
    "WUBG": "Witch-Maw",
    "WUBRG": "Cinco cores",
}


def canonical_colors(colors: Iterable[str]) -> list[str]:
    """As cores na ordem branco, azul, preto, vermelho, verde."""
    wanted = {color.upper() for color in colors}
    return [color for color in WUBRG if color in wanted]


def identity_name(colors: Iterable[str]) -> str:
    return _NAMES["".join(canonical_colors(colors))]
