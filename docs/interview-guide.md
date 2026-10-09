# Interview guide

Start with the byte layout: the probe response has fourteen measurement bytes inside a nineteen-byte Modbus RTU frame. The parser checks the frame before interpreting any measurement.

| Question | Code that prompts it | What to understand |
| --- | --- | --- |
| 1. Why is the response nineteen bytes? | `codec.py`, C++ `parse` | Address + function + byte count + seven 16-bit registers + CRC. Compare with the eight-byte request. |
| 2. Why are there two different byte orders? | `struct.unpack`, `crc16`, `make_request` | Registers use big-endian bytes; the RTU CRC's low byte is transmitted first. |
| 3. What prevents corrupt readings from reaching the database? | Both parsers, `/frames`, request schemas | Length, CRC, address, function, byte count, then measurement ranges. Direct structured ingestion trusts its authenticated sender. |
| 4. How do you handle a negative temperature? | Signed conversion in both parsers | The assumed two's-complement value needs conversion before scaling. Confirm that representation in the real manual. |
| 5. Is the pH divisor always one hundred? | `SensorLayout`, `soil::Layout` | No; register mapping and scaling are probe-specific. Explain the unconfirmed defaults and keep both languages consistent. |
| 6. What does the UART sketch do on a timeout? | `main.cpp`, `config.h` | Bounded read, rejected partial frame, next polling cycle, UART pins, converter direction, and unsigned timer subtraction. |
| 7. What happens when an HTTP post is retried? | `bridge.forward`, `save_reading` | Preserve the timestamp, use a device/time unique key, return an identical reading as duplicate, and reject conflicting values. |
| 8. Why include organization in the device key? | Composite `Device` key and reading foreign key | Device names can repeat across organizations; data must keep its full scope. A key is not a user-authorization policy. |
| 9. What do the monitoring flags prove? | `monitoring_report` | Rolling observations and chosen thresholds; no diagnosis, field-validation result, or verified causal inference. |
| 10. What is actually bench-validated? | Status document and hardware notes | The owner reports earlier prototype work. Native parser tests and an API demo do not verify hardware or this new sketch on a probe. |

## Byte walkthrough

Under the reference layout, `01 f4` is raw 500 and becomes moisture 50.0 after dividing by ten. `00 fa` is temperature 250 and becomes 25.0. `02 8a` is raw pH 650 and becomes 6.5 after dividing by one hundred. Explain why a valid CRC can accompany incorrectly interpreted measurements if the register layout is wrong.

Read both parsers side by side. They deliberately use simple loops and explicit conversions. Be able to calculate a 16-bit value from two bytes, explain the CRC accumulator, identify exception responses, and show why malformed data is rejected before decoding.

The bridge has bounded retry but no durable offline queue. A lost network connection after the retries can lose that reading. The backend has one shared token for a local demo, no per-device secret provisioning, and no real cloud deployment. Those are practical next steps, not features hidden in the current implementation.

If asked about the intended ESP-NOW/Raspberry Pi topology, describe why a local manager could aggregate readings and cache them during an internet outage. Then identify the current USB/HTTP path in this repository and explain that the gateway and caching tiers still need implementation evidence. Be equally precise about the Flux/KiCad handoff and golf-tee enclosure: the owner supplied design history, while the actual exports and CAD are absent.
