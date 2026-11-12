"""Pytest fixtures for database isolation and FastAPI test client."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from database import Base, get_db
from main import app

# In-memory SQLite engine for test isolation
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(autouse=True)
def setup_test_db():
    """Create all tables before each test and drop them after."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Session:
    """Provide a clean in-memory database session."""
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """Provide a FastAPI TestClient with database dependency overridden."""

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_valid_csv() -> str:
    """Provide valid CSV content for testing."""
    return (
        "date,city,PM2.5,NO2,CO2\n"
        "2024-11-20,Haifa,10.0,20.0,3.0\n"
        "2024-11-20,Tel Aviv,25.0,40.0,10.0\n"
        "2024-11-20,Jerusalem,80.0,120.0,70.0\n"
    )


@pytest.fixture
def sample_corrupted_csv() -> str:
    """Provide CSV content with both valid and corrupted rows."""
    return (
        "date,city,PM2.5,NO2,CO2\n"
        "2024-11-21,Haifa,10.0,20.0,3.0\n"  # Valid
        "2024-11-21,Eilat,NaN,20.0,3.0\n"   # Missing PM2.5
        "2024-11-21,Acre,15.0,,4.0\n"       # Empty NO2
        "2024-11-21,Tiberias,15.0,20.0,-5\n" # Negative CO2
        "2024-11-21,,12.0,25.0,4.0\n"       # Missing city
        "invalid_date,Holon,12.0,25.0,4.0\n" # Invalid date
        "2024-11-21,Netanya,280.0,700.0,150.0\n" # Valid, High AQI (Alert)
    )
