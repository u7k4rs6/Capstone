import os
import tempfile

# Point the app at a throwaway SQLite file before it is imported. Never touches Postgres.
_db_file = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file}"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def item(client):
    payload = {"name": "Oat Milk 1L", "sku": "MLK-OAT-1L", "category": "Dairy", "quantity": 10, "reorder_level": 4, "unit_price": 2.5}
    return client.post("/api/items", json=payload).json()
