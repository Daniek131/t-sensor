import pytest
from fastapi.testclient import TestClient

from tsensor.api import create_app


@pytest.fixture
def client():
    with TestClient(create_app("sqlite:///:memory:", api_token="")) as connection:
        connection.post("/organizations", json={"id": "demo", "name": "Synthetic test site"})
        connection.post("/organizations/demo/devices", json={"id": "probe-1"})
        yield connection
