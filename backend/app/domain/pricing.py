from typing import Protocol


class PriceProvider(Protocol):
    async def lowest_brl_cents(self, name_en: str) -> int | None:
        """Menor preço em centavos de real, ou vazio quando a fonte não responde."""


class NullPriceProvider:
    """Sem adaptador da LigaMagic o preço fica vazio e o deck avisa `missing_price`."""

    async def lowest_brl_cents(self, name_en: str) -> int | None:
        return None
