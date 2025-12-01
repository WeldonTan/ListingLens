import pytest
from httpx import AsyncClient
from app.main import app
from app.db.base import Base # Import Base for user creation
from app.models.user import User # Import User model
from app.core import security
from sqlalchemy.ext.asyncio import AsyncSession

# Fixture for the test client from conftest.py is automatically available
# Fixture for db_session from conftest.py is automatically available

@pytest.mark.asyncio
async def test_api_health_check(client: AsyncClient):
    """
    Test the main API health check endpoint.
    """
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

@pytest.mark.asyncio
async def test_authentication_invalid_credentials(client: AsyncClient):
    """
    Test login with invalid credentials.
    """
    response = await client.post(
        "/api/v1/login/access-token",
        data={"username": "nonexistent@example.com", "password": "wrongpassword"}
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Incorrect email or password"}

@pytest.mark.asyncio
async def test_authentication_successful_login(client: AsyncClient, db_session: AsyncSession):
    """
    Test successful user login and access token retrieval.
    """
    # Create a test user directly in the database
    hashed_password = security.get_password_hash("testpassword")
    test_user = User(email="test@example.com", hashed_password=hashed_password, is_active=True)
    db_session.add(test_user)
    await db_session.commit()

    response = await client.post(
        "/api/v1/login/access-token",
        data={"username": "test@example.com", "password": "testpassword"}
    )
    assert response.status_code == 200
    token_data = response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_listings_no_listings_returns_empty_list(client: AsyncClient):
    """
    Test retrieving listings when none exist returns an empty list.
    """
    response = await client.get("/api/v1/listings/")
    assert response.status_code == 200
    assert response.json() == []

@pytest.mark.asyncio
async def test_scrape_listings_endpoint_success(client: AsyncClient):
    """
    Test the /scrape endpoint successfully triggers scraping tasks.
    """
    test_urls = ["http://example.com/listing1", "http://example.com/listing2"]
    response = await client.post("/api/v1/listings/scrape", json={"urls": test_urls})
    assert response.status_code == 202
    response_data = response.json()
    assert response_data["message"] == "Scraping started"
    assert len(response_data["task_ids"]) == len(test_urls)

@pytest.mark.asyncio
async def test_scrape_status_endpoint_success(client: AsyncClient):
    """
    Test the /scrape/status endpoint to check task statuses.
    """
    # Assuming the mock Arq pool always returns "complete"
    task_ids = ["mock_task_id_1", "mock_task_id_2"]
    response = await client.post("/api/v1/listings/scrape/status", json=task_ids)
    assert response.status_code == 200
    response_data = response.json()
    assert all(task_id in response_data for task_id in task_ids)
    assert all(data["status"] == "complete" for data in response_data.values())

@pytest.mark.asyncio
async def test_purge_queue_endpoint_success(client: AsyncClient):
    """
    Test the /scrape/purge endpoint successfully purges the queue.
    """
    response = await client.post("/api/v1/listings/scrape/purge")
    assert response.status_code == 200
    assert response.json() == {"message": "Queue purged"}

# Additional tests could be added for:
# - User registration (if implemented)
# - Listing creation, update, deletion (requires authenticated user)
# - Generate copy endpoint
# - Edge cases for all endpoints (e.g., invalid input, permissions)
