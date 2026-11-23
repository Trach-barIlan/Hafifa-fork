"""Compatibility package exposing ORM components.

The test suite does ``from database import Base, get_db``.  By providing a
real package named ``database`` we avoid reliance on the current working
directory being on ``sys.path``.
"""

from rolling_exercise.database import Base, get_db, init_db, settings, engine, SessionLocal  # noqa: F401
