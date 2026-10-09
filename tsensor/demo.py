"""Send synthetic measurements to a running local telemetry API."""

import argparse
import os
from datetime import datetime, timedelta, timezone

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", default="http://127.0.0.1:8001")
    args = parser.parse_args()
    with httpx.Client(
        base_url=args.api_url, headers={"X-API-Key": os.getenv("API_TOKEN", "")}, timeout=10
    ) as client:
        for path, value in [
            ("/organizations", {"id": "synthetic-demo", "name": "Synthetic demonstration"}),
            ("/organizations/synthetic-demo/devices", {"id": "probe-demo"}),
        ]:
            response = client.post(path, json=value)
            if response.status_code != 409:
                response.raise_for_status()
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
        base = "/organizations/synthetic-demo/devices/probe-demo"
        for minutes, moisture, ec in [
            (60, 60, 1500),
            (30, 75, 1300),
            (15, 78, 1100),
            (0, 80, 1000),
        ]:
            response = client.post(
                base + "/readings",
                json={
                    "observed_at": (now - timedelta(minutes=minutes)).isoformat(),
                    "source": "synthetic",
                    "moisture": moisture,
                    "temperature": 25,
                    "ec": ec,
                    "ph": 6.5,
                    "nitrogen": 45,
                    "phosphorus": 20,
                    "potassium": 80,
                },
            )
            response.raise_for_status()
        response = client.get(base + "/monitoring")
        response.raise_for_status()
        print("Synthetic demonstration; no physical probe readings:")
        print(response.text)


if __name__ == "__main__":
    main()
