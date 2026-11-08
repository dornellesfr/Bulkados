import pytest
from sqlalchemy import text

from app.core.database import SessionFactory


@pytest.mark.integration
async def test_database_accepts_queries() -> None:
    async with SessionFactory() as session:
        result = await session.execute(text("SELECT 1"))

    assert result.scalar_one() == 1
