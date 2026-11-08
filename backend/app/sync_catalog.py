import asyncio
import logging

from app.core.database import SessionFactory, engine
from app.integrations.scryfall import scryfall_client
from app.services import catalog_control

logger = logging.getLogger(__name__)


async def _run() -> bool:
    try:
        await catalog_control.run_claimed_sync(scryfall_client())
        async with SessionFactory() as session:
            status = await catalog_control.get_status(session)
    finally:
        await engine.dispose()
    if status.last_error is not None:
        logger.error("catálogo: %s", status.last_error)
        return False
    return True


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    if not asyncio.run(_run()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
