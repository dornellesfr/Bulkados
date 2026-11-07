from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

# O teste roda cada caso em um event loop novo; sem pool, uma conexão não vaza
# de um loop fechado para o próximo.
if settings.environment == "test":
    engine: AsyncEngine = create_async_engine(
        settings.effective_database_url,
        echo=settings.debug,
        pool_pre_ping=True,
        poolclass=NullPool,
    )
else:
    engine = create_async_engine(
        settings.effective_database_url,
        echo=settings.debug,
        # Evita um round-trip de ping em cada request. O recycle cobre conexões
        # antigas sem pagar esse custo em toda leitura.
        pool_pre_ping=False,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_use_lifo=True,
    )

SessionFactory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Abre uma sessão por request e confirma a transação quando não há erro."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
