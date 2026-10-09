# Implementation evidence

## Initial audit

The inputs described a breadboard prototype, UART communication, a seven-in-one probe, nineteen-byte responses, voltage measurements, and intended cloud/analytics work. No original firmware, exact probe datasheet, schematic, PCB design, enclosure, real measurements, or prototype photograph was supplied. Original implementation quality and historical hardware results cannot be independently rated from these inputs.

The local Git repository was initialized before the new source was written. This is a reference implementation prepared with coding assistance in October 2026. It is not presented as the original March 2026 firmware or proof of its earlier bench results.

## Evidence by claim

| Resume or LinkedIn claim | Current source supports | Remaining evidence |
| --- | --- | --- |
| ESP32 Modbus communication and parsing | UART sketch and tested Python/C++ protocol code | Exact original firmware, target compile, upload, and real response log |
| Seven structured soil measurements | A configurable seven-register decoder | Probe register map, signed temperature format, scales, units, and calibration |
| Validated breadboard and end-to-end telemetry | Owner-reported hardware work plus new software tests | Photos, raw frames, wiring, measured output, and on-device confirmation |
| Device/time/organization-indexed storage | Composite keys, foreign keys, unique time index, and query scoping | Live PostgreSQL integration and deployment |
| Agronomic or fungal/leaching alerts | Exploratory rolling rules and returned inspection flags | Field validation and agronomic basis for calibrated thresholds |
| PCB and enclosure transition | Documented future work | Actual design files and fabrication evidence |
| ESP-NOW, Raspberry Pi manager, two caching tiers | Owner-described intended topology | Gateway firmware, Pi service, cache behavior, and network tests |
| JobProgress-inspired cloud logic and state machines | Owner-described design background; small new relational schema | Original implementation, transitions, routing, and deployment evidence |
| Flux-to-KiCad design pipeline | Export handoff documented | Actual `.flx`, BOM, netlist, reviewed schematic, and routed PCB |
| Golf-tee enclosure, revised LiPo, sealed charging port | Owner-described mechanical concept | CAD, fit checks, charging design, environmental and battery tests |
| Cloud deployment transition | REST API and a local serial bridge | Hosted backend, device credentials, offline buffering, and remote operations |
| Sub-$50 BOM or voltage stabilization | Prior owner-reported observations in hardware notes | Current parts list, receipts/specifications, and recorded measurements |

NPK fields are probe-reported values, not independently verified nutrient assays. The monitoring rules cannot substantiate a scientifically validated nutrient, leaching, or fungal-risk model. No PyTorch model is implemented in this repository.

The added project-status narrative gives useful hardware and design context, but it does not provide the referenced JPGs, source files, CAD, or PCB exports. The prototype can be described as bench-validated according to the owner; this repository cannot independently verify that milestone. The 30-minute telemetry interval belongs to the intended product design, while this reference firmware uses a five-second bench polling interval.

## Checks actually performed

The Python suite checks a known Modbus request CRC vector, response scaling, negative temperatures under the assumed encoding, malformed/truncated/exception frames, API deduplication, organization/device integrity, invalid ranges, scoped queries, and illustrative rolling flags. The C++ protocol library is compiled and exercised with the host compiler. Synthetic inputs are labeled as such.

The serial bridge's retry behavior is tested with an in-process fake HTTP transport; it is not a hardware/USB test. The API tests are in-process and use SQLite. See `verification.json` for the final results and build limitations. No physical sensor, PCB, enclosure, live cloud, or real data is represented as tested by these checks.
