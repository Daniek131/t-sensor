"""Forward ESP32 serial measurements to the telemetry API."""

import argparse
import json
import os
import time
from datetime import datetime, timezone

import httpx
import serial

from tsensor.schemas import ReadingInput


def forward(client, url, payload):
    # I reuse the payload and timestamp on retries to avoid duplicate readings.
    for attempt in range(3):
        try:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError:
            if attempt == 2:
                raise
            time.sleep(0.5 * (attempt + 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True, help="ESP32 USB serial port")
    parser.add_argument("--api-url", default="http://127.0.0.1:8001")
    parser.add_argument("--org-id", required=True)
    parser.add_argument("--device-id", required=True)
    args = parser.parse_args()
    url = (
        f"{args.api_url.rstrip('/')}/organizations/{args.org_id}/devices/{args.device_id}/readings"
    )
    headers = {"X-API-Key": os.getenv("API_TOKEN", "")}
    with serial.Serial(args.port, baudrate=115200, timeout=2) as port:
        with httpx.Client(headers=headers, timeout=10) as client:
            while True:
                line = port.readline()
                if not line:
                    continue
                try:
                    values = json.loads(line)
                    payload = ReadingInput(
                        **values, observed_at=datetime.now(timezone.utc), source="hardware"
                    ).model_dump(mode="json")
                    result = forward(client, url, payload)
                    print(f"Stored reading {result['reading_id']}")
                except (ValueError, httpx.HTTPError) as error:
                    print(f"Skipped reading: {type(error).__name__}")


if __name__ == "__main__":
    main()
