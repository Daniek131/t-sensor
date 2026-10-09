from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from tsensor.api import create_app
from tsensor.codec import crc16

BASE = "/organizations/demo/devices/probe-1"


def payload(now=None):
    return {
        "observed_at": (now or datetime.now(timezone.utc)).isoformat(),
        "source": "synthetic",
        "moisture": 50,
        "temperature": 25,
        "ec": 1200,
        "ph": 6.5,
        "nitrogen": 45,
        "phosphorus": 20,
        "potassium": 80,
    }


def test_reading_retry_is_idempotent_and_changed_value_is_conflict(client):
    value = payload()
    assert client.post(BASE + "/readings", json=value).json()["duplicate"] is False
    assert client.post(BASE + "/readings", json=value).json()["duplicate"] is True
    value["ec"] = 1000
    assert client.post(BASE + "/readings", json=value).status_code == 409
    assert len(client.get(BASE + "/readings").json()) == 1


def test_device_org_reference_is_enforced_and_queries_are_scoped(client):
    value = payload()
    unknown = "/organizations/other/devices/probe-1/readings"
    assert client.post(unknown, json=value).status_code == 404
    client.post("/organizations", json={"id": "other", "name": "Other test site"})
    client.post("/organizations/other/devices", json={"id": "probe-1"})
    client.post(unknown, json=value)
    assert client.get(BASE + "/readings").json() == []
    assert len(client.get(unknown).json()) == 1


@pytest.mark.parametrize(
    "change",
    [
        {"moisture": 101},
        {"ph": 15},
        {"nitrogen": -1},
        {"ec": 1.5},
        {"observed_at": "2026-01-01T00:00:00"},
        {"source": "fake"},
        {"temperature": "NaN"},
    ],
)
def test_invalid_measurement_rejected(client, change):
    value = payload()
    value.update(change)
    assert client.post(BASE + "/readings", json=value).status_code == 422


def test_frame_endpoint_validates_and_retains_raw_bytes(client):
    body = bytes.fromhex("01030e01f400fa04b0028a002d00140050")
    frame = body + crc16(body).to_bytes(2, "little")
    response = client.post(
        BASE + "/frames",
        json={
            "frame_hex": frame.hex(),
            "observed_at": payload()["observed_at"],
            "source": "synthetic",
        },
    )
    assert response.status_code == 200
    stored = client.get(BASE + "/readings").json()[0]
    assert stored["ph"] == 6.5
    assert stored["raw_frame_hex"] == frame.hex()
    invalid = frame[:-1] + bytes([frame[-1] ^ 1])
    assert (
        client.post(
            BASE + "/frames",
            json={"frame_hex": invalid.hex(), "observed_at": payload()["observed_at"]},
        ).status_code
        == 422
    )


def test_monitoring_flags_are_exploratory_and_require_sustained_conditions(client):
    now = datetime.now(timezone.utc)
    for minutes, moisture, ec in [(60, 60, 1500), (30, 75, 1300), (15, 78, 1100), (0, 80, 1000)]:
        value = payload(now - timedelta(minutes=minutes))
        value.update(moisture=moisture, ec=ec)
        assert client.post(BASE + "/readings", json=value).status_code == 200
    report = client.get(BASE + "/monitoring").json()
    assert report["sample_count"] == 4
    assert {flag["rule"] for flag in report["flags"]} == {
        "warm_wet_watch",
        "dilution_leaching_watch",
    }
    assert "field validation" in report["notice"]


def test_one_warm_wet_reading_does_not_trigger_a_sustained_flag(client):
    value = payload()
    value["moisture"] = 80
    client.post(BASE + "/readings", json=value)
    assert client.get(BASE + "/monitoring").json()["flags"] == []


def test_token_protects_ingestion():
    with TestClient(create_app("sqlite:///:memory:", api_token="test-only-token")) as client:
        assert client.post("/organizations", json={"id": "x", "name": "x"}).status_code == 401
