import pytest
import pytest_asyncio
import os
# Set an in-memory SQLite DB for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
import app.models.domain # Import models so Base.metadata has tables
from app.main import app
from httpx import AsyncClient, ASGITransport



@pytest_asyncio.fixture(scope="session", autouse=True)
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL, 
        echo=False, 
        poolclass=StaticPool, 
        connect_args={"check_same_thread": False}
    )
    # Override the global engine in database module
    import app.core.database as database
    import app.agent as agent
    database.engine = engine
    database.async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    agent.async_session = database.async_session
    
    # Also patch anything in services that might have imported it
    import app.services.supervisor_service as sup_service
    if hasattr(sup_service, "async_session"):
        sup_service.async_session = database.async_session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture()
async def db_session(test_engine):
    async_session = async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session

@pytest_asyncio.fixture()
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    # Override get_current_user to bypass Supabase auth during tests
    from app.api.auth import get_current_user
    async def override_get_current_user():
        return {"sub": "test-user", "role": "authenticated"}
    
    app.dependency_overrides[get_current_user] = override_get_current_user

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test",
                           headers={"Authorization": "Bearer dummy_token"}) as ac:
        yield ac
    app.dependency_overrides.clear()
