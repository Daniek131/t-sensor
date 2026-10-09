# T-Sensor

An ESP32 soil-telemetry project with Modbus frame parsing, Python ingestion, and an indexed time-series database.

The goal is to make root-zone conditions easier to inspect over time. The intended device reads a seven-variable RS485 probe and passes structured measurements to a backend. Telemetry complements calibration and soil testing; this source does not establish laboratory-grade nutrient accuracy.

**Current source:** a newly written reference implementation prepared in October 2026 with coding assistance. The project owner reports a previously validated breadboard prototype. Original firmware, the exact probe manual, photos, and raw bench logs have not been supplied here. The new parser and API are software-tested; this firmware has not been verified on that physical device.

## Implementation status

| Component | Status |
| --- | --- |
| Modbus request and 19-byte parser | Implemented in Python and C++; synthetic protocol tests pass |
| CRC, address, function, byte-count checks | Implemented; malformed frames are rejected |
| ESP32 UART polling sketch | Written for an ESP32 development board; target build and on-device test pending |
| Serial-to-REST bridge | Implemented; repeated HTTP submissions retain their timestamp |
| Telemetry API and schema | Implemented; ingestion, query scoping, duplicates, and ranges tested on SQLite |
| PostgreSQL integration | Schema and Docker configuration provided; live database test pending |
| Rolling monitoring | Implemented as exploratory warm/wet and dilution trend rules |
| Physical prototype and voltage measurements | Owner-reported prior work; original evidence still needed |
| ESP-NOW, Raspberry Pi manager, two caching tiers | Intended topology described by the owner; implementation not supplied |
| PCB, golf-tee enclosure, cloud deployment | Design transition documented; finished assets and deployment not supplied |

See [implementation evidence](docs/implementation-status.md) for the resume/LinkedIn comparison.

## Local API demo

Python 3.11+ is required; verification used Python 3.12.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn tsensor.api:app --host 127.0.0.1 --port 8001
# In another shell with the environment activated:
python -m tsensor.demo
```

Open [the API explorer](http://127.0.0.1:8001/docs). The demo sends four clearly labeled synthetic readings, prints the monitoring report, and does not claim a probe was attached. By default, SQLite stores them in `tsensor.db`.

### Raw-frame example

Create an organization and device, then submit the supplied synthetic fixture through the API. Replace the timestamp with a current or past UTC timestamp when trying a new reading.

```bash
curl -X POST http://127.0.0.1:8001/organizations \
  -H 'Content-Type: application/json' -d '{"id":"example","name":"Synthetic example"}'
curl -X POST http://127.0.0.1:8001/organizations/example/devices \
  -H 'Content-Type: application/json' -d '{"id":"probe-1"}'
```

`sample_data/synthetic_frame.json` contains a constructed response. Its expected decoded values are explained below. Submit it to:

```bash
curl -X POST http://127.0.0.1:8001/organizations/example/devices/probe-1/frames \
  -H 'Content-Type: application/json' -d @sample_data/synthetic_frame.json
curl http://127.0.0.1:8001/organizations/example/devices/probe-1/readings
```

It decodes to moisture 50.0, temperature 25.0, EC 1200, pH 6.5, nitrogen 45, phosphorus 20, and potassium 80 under the configured layout. This is a protocol fixture, not recorded hardware output. A repeated identical device/timestamp is returned as a duplicate; a different measurement at that timestamp returns HTTP 409.

## Protocol and sensor assumptions

A seven-register holding-register response contains one address byte, one function byte, one byte-count field, fourteen data bytes, and two CRC bytes: `1 + 1 + 1 + 14 + 2 = 19`. The request is eight bytes. Registers are big-endian; the RTU CRC is sent low byte first. Function `0x83` with a valid five-byte frame reports an exception rather than measurements.

The current profile assumes the following order. This is **sensor-specific and awaiting confirmation**, not a universal Modbus mapping.

| Register offset | Field | Interpretation |
| --- | --- | --- |
| 0 | Moisture | Raw / 10; assumed percent |
| 1 | Temperature | Signed two's-complement raw / 10; assumed Celsius |
| 2 | Electrical conductivity | Raw integer; confirm the probe's unit |
| 3 | pH | Raw / 100; confirm whether this probe instead uses / 10 |
| 4 | Nitrogen | Raw integer in the probe's reported unit |
| 5 | Phosphorus | Raw integer in the probe's reported unit |
| 6 | Potassium | Raw integer in the probe's reported unit |

The default address is 1 and the starting register is 0. The firmware uses 9600 baud and 8N1 to match the owner's stated prototype setting. Confirm those settings with the exact probe; they are not a claim of generic Modbus serial conformance.

Change Python's `SensorLayout` and the C++ `soil::Layout` together if the probe uses a different register order. Python scaling can also be set through `TS_PH_DIVISOR`, `TS_MOISTURE_DIVISOR`, and `TS_TEMPERATURE_DIVISOR`. The firmware layout defaults live in `firmware/include/soil_protocol.h`; its wiring and polling settings live in `config.h`.

## Firmware and physical data flow

1. The ESP32 sends a seven-register request over UART through the RS485 converter.
2. The C++ protocol parser checks framing and CRC, then applies the configured scaling.
3. The sketch emits a JSON line on USB serial, including the raw frame.
4. A Python bridge stamps the receipt time in UTC and posts the measurements to the API.
5. The database stores organization, device, time, measurements, source, and optional raw bytes.
6. A scoped query supplies rolling averages and inspection flags.

This foundation uses a computer as the serial bridge. The owner's intended topology uses ESP-NOW, a Raspberry Pi manager, and two caching tiers. Gateway code, durable buffering, cloud hosting, and a dashboard are separate next steps. The sketch polls every five seconds for bench inspection; the proposed 30-minute product telemetry interval is not implemented.

With [PlatformIO](https://docs.platformio.org/en/latest/), the normal local build commands are:

```bash
cd firmware
pio run
pio run --target upload
pio device monitor
```

Check the exact device, pins, supply requirements, and level shifting before uploading. The current sketch defaults to UART2 RX=16 and TX=17; these are reference settings. `RS485_DE_PIN=-1` assumes an auto-direction module. For a manually controlled transceiver, set the correct DE/RE pin and verify direction timing. See [hardware notes](hardware/prototype-notes.md).

Register the organization and device in the API before starting the bridge:

```bash
python -m tsensor.bridge --port /dev/ttyUSB0 --org-id example --device-id probe-1
```

Use the actual serial port on your computer. The API key, when configured, comes from the bridge computer's `API_TOKEN`; it is not embedded in the firmware.

## Database and monitoring

The schema has three tables: organizations, devices, and readings. A composite device foreign key prevents a reading from referencing a device in the wrong organization. A unique `(org_id, device_id, observed_at)` key prevents duplicate samples and provides the index for scoped time queries. This groups data; it is not tenant authorization.

`GET /organizations/{org}/devices/{device}/monitoring` returns recent values, one-hour rolling averages, nutrient changes, and exploratory flags. It reads at most the latest 2,000 rows in the requested window and reports when that sample limit is reached.

The warm/wet rule needs at least three readings spanning roughly 30 minutes, all with moisture at least 70 and temperature between 18 and 30. The dilution rule looks for a moisture increase of at least 10 and an EC decrease of at least 20% over a sampled period of at least 30 minutes. These illustrative thresholds are not calibrated for a turf species, soil, probe, or disease. They prompt inspection; they do not diagnose fungal disease, measure leaching, or prescribe fertilizer.

## PostgreSQL option

```bash
export POSTGRES_PASSWORD="$(python -c 'import secrets; print(secrets.token_hex(16))')"
export API_TOKEN="$(python -c 'import secrets; print(secrets.token_hex(16))')"
docker compose up --build
```

Compose binds the API to localhost and requires a shared API token. Add `X-API-Key` to HTTP calls, or export the same token before using the demo and bridge. PostgreSQL's port is not exposed. `.env.example` documents available settings; local shell commands use exported variables. The cloud deployment is not complete, and Docker was not available for verification here.

## Code map and tests

| Location | Purpose |
| --- | --- |
| `firmware/include/soil_protocol.h` | Small Arduino-independent C++ parser used by the sketch and native tests |
| `firmware/include/config.h` | UART pins, sensor address, and polling settings |
| `firmware/src/main.cpp` | UART polling and JSON serial output |
| `tsensor/codec.py` | Python request/response validation and configurable scaling |
| `tsensor/schemas.py` | Ranges, timestamps, identifiers, and provenance labels |
| `tsensor/db.py` | Organization/device relationships and indexed time storage |
| `tsensor/api.py` | Registration, ingestion, deduplication, and queries |
| `tsensor/analytics.py` | Rolling summaries and exploratory inspection rules |
| `tsensor/bridge.py` | Serial forwarding with bounded retry |
| `sql/reports.sql` | Scoped PostgreSQL time-series reports |
| `tests/` | Malformed-frame, API, monitoring, and native C++ tests |

```bash
pytest -q
ruff check tsensor tests
ruff format --check tsensor tests
```

Install `g++` to run the native C++ check; otherwise that test is explicitly skipped. Native compilation verifies the shared protocol code, not the ESP32 UART or physical hardware. See `docs/verification.json` for measured results and [the interview guide](docs/interview-guide.md) for explanations tied to the files.

## Next work

The most valuable next evidence is the original firmware and probe manual, followed by a short captured frame log and a prototype photo. Confirm mapping, signed temperature representation, units, CRC checks, and serial settings with those inputs. Then build/upload the sketch, compare decoded values with the sensor's reference output, and validate the complete serial/API/database path. Custom PCB, enclosure, field calibration, cloud access control, and a calibrated monitoring model remain separate milestones.

The current source demonstrates binary parsing, checksums, serial integration design, API validation, database keys, idempotent telemetry, and rolling data analysis. It does not claim completed hardware redesign, laboratory accuracy, a trained model, or an active deployment.

## Technical reference

[Modbus serial-line specification](https://www.modbus.org/file/secure/modbusoverserial.pdf) describes the protocol and CRC. A probe's own manual is still required for register meanings and scales.
