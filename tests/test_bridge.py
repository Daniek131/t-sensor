import json

import httpx

from tsensor.bridge import forward


def test_retry_preserves_the_exact_telemetry_payload(monkeypatch):
    requests = []

    def handler(request):
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            return httpx.Response(503, request=request)
        return httpx.Response(200, json={"reading_id": 1, "duplicate": True}, request=request)

    monkeypatch.setattr("tsensor.bridge.time.sleep", lambda _: None)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        payload = {"observed_at": "2026-10-01T12:00:00Z", "source": "synthetic"}
        result = forward(client, "http://test/readings", payload)
    assert result["reading_id"] == 1
    assert requests == [payload, payload]
