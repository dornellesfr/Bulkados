from enum import StrEnum

from sqlalchemy import Enum


def _enum_values(enum_cls: type[StrEnum]) -> list[str]:
    return [item.value for item in enum_cls]


def str_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    return Enum(
        enum_cls,
        name=name,
        native_enum=False,
        length=32,
        create_constraint=True,
        values_callable=_enum_values,
    )
