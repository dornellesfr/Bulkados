import asyncio
import logging

from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionFactory, engine
from app.domain.identity import normalize_email
from app.integrations.supabase import SupabaseAuthProvider
from app.models.user import User
from app.services.admin_bootstrap import admin_password, ensure_admin

logger = logging.getLogger(__name__)


async def seed_admin() -> bool:
    """Grava o admin se o e-mail ainda não existe. E-mail que já está em users fica como está."""
    settings = get_settings()
    if settings.environment == "test":
        return True
    required = bool(settings.admin_email.strip()) and admin_password(settings) is not None
    async with SessionFactory() as session:
        await ensure_admin(session, SupabaseAuthProvider(settings), settings)
        await session.commit()
        if not required:
            return True
        try:
            email = normalize_email(settings.admin_email)
        except ValueError:
            return False
        user = await session.scalar(select(User).where(User.email == email))
        return user is not None


async def _run() -> bool:
    try:
        return await seed_admin()
    finally:
        await engine.dispose()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    try:
        created = asyncio.run(_run())
    except Exception:
        logger.exception("admin: falha ao gravar o usuário admin")
        raise SystemExit(1) from None
    if not created:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
