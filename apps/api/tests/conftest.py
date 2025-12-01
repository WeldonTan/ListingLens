import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.base import Base
from app.main import app
from app.core.config import settings
from app.db.session import get_db

# Setup for testing database
# Use an in-memory SQLite database for tests
DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

@pytest_asyncio.fixture(name="db_session")
async def db_session_fixture():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with TestingSessionLocal() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture(name="client")
async def client_fixture(db_session: AsyncSession):
    # Override get_db dependency for tests
    app.dependency_overrides[get_db] = lambda: db_session
    
    # Mock Arq pool for tests
    class MockArqPool:
        async def enqueue_job(self, *args, **kwargs):
            return MockJob("mock_task_id")
        
        async def execute_command(self, *args, **kwargs):
            pass # Mock flushing database
    
    class MockJob:
        def __init__(self, job_id):
            self.job_id = job_id
        
        async def status(self):
            return "complete" # Always complete for mock
            
        async def result(self):
            return {"mock_result": True}

        async def abort(self, timeout):
            pass

    app.state.arq_pool = MockArqPool()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    
    # Clean up overrides
    app.dependency_overrides = {}
