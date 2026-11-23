"""Pytest fixtures for mocking the database and providing a FastAPI test client.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from database import Base, get_db  # Base is still needed for any metadata ops (no‑op here)
from main import app
from models import AirQualityRecord, Alert
from sqlalchemy.exc import IntegrityError

# ---------------------------------------------------------------------------
# Mock Session helpers
# ---------------------------------------------------------------------------

class MockResult:
    """Simple iterator wrapper mimicking SQLAlchemy Result.

    The real code often does ``session.scalars(select(...)).all()``.
    Our mock returns a list via ``all()``.
    """

    def __init__(self, data):
        self._data = data

    def all(self):
        return list(self._data)

    def __iter__(self):
        return iter(self._data)


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Create a ``MagicMock`` that behaves like a minimal SQLAlchemy Session.

    It stores ``AirQualityRecord`` and ``Alert`` objects in in‑memory lists.
    ``add`` appends to the appropriate list, ``commit`` is a no‑op (but can
    raise ``IntegrityError`` for duplicate alerts), and ``scalars`` returns a
    ``MockResult`` over the stored records.
    """
    session = MagicMock()
    # In‑memory “tables”
    session._records = []
    session._alerts = []

    def add(obj):
        if isinstance(obj, AirQualityRecord):
            session._records.append(obj)
        elif isinstance(obj, Alert):
            # Enforce the unique ``record_id`` constraint used in the real DB.
            if any(a.record_id == obj.record_id for a in session._alerts):
                raise IntegrityError("duplicate key value violates unique constraint \"alerts_record_id_key\"", None, None)
            session._alerts.append(obj)
        else:
            # For any other ORM object we just store it in a generic list.
            if not hasattr(session, "_generic"):
                session._generic = []
            session._generic.append(obj)

    def commit():
        # No‑op for the mock; real constraints are handled in ``add``.
        return None

    def rollback():
        # Reset the in‑memory tables – used if a test expects a clean state
        # after an exception.
        session._records.clear()
        session._alerts.clear()
        if hasattr(session, "_generic"):
            session._generic.clear()

    def scalars(*args, **kwargs):
        """Return all AirQualityRecord objects regardless of the query.

        The test suite only uses ``scalars`` to fetch records for calculations;
        a simple ``MockResult`` over the full list is sufficient.
        """
        return MockResult(session._records)

    # Bind the behaviours to the mock
    session.add.side_effect = add
    session.commit.side_effect = commit
    session.rollback.side_effect = rollback
    session.scalars.side_effect = scalars

    # ``query`` is sometimes used directly; we make it return ``self`` so that
    # chained calls (e.g. ``session.query(Model).filter(...).all()``) still work.
    session.query.return_value = session
    session.filter = lambda *a, **kw: session
    session.all = lambda: list(session._records)

    return session


# ---------------------------------------------------------------------------
# FastAPI TestClient with DB dependency overridden
# ---------------------------------------------------------------------------

@pytest.fixture
def client(mock_db_session: MagicMock) -> TestClient:
    """Provide a FastAPI ``TestClient`` that uses the mocked DB session.

    The application’s ``get_db`` dependency is replaced with a generator that
    yields the ``mock_db_session`` created above.
    """

    def override_get_db():
        try:
            yield mock_db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# CSV fixtures used by the existing tests
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_valid_csv() -> str:
    return (
        "date,city,PM2.5,NO2,CO2\n"
        "2024-11-20,Haifa,10.0,20.0,3.0\n"
        "2024-11-20,Tel Aviv,25.0,40.0,10.0\n"
        "2024-11-20,Jerusalem,80.0,120.0,70.0\n"
    )


@pytest.fixture
def sample_corrupted_csv() -> str:
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
