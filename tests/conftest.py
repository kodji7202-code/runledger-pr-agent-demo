import pytest

from app import create_app
from app.db import apply_migrations, connect

API_KEY = "test-key"


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test.db"
    conn = connect(db_path)
    apply_migrations(conn)
    conn.close()
    return create_app({"DATABASE": str(db_path), "API_KEY": API_KEY, "TESTING": True})


@pytest.fixture
def client(app):
    client = app.test_client()
    client.environ_base["HTTP_X_API_KEY"] = API_KEY
    return client


@pytest.fixture
def user(client):
    return client.post("/users", json={"email": "ada@example.com", "name": "Ada"}).get_json()
