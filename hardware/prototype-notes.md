# Hardware prototype and design direction

## Bench configuration

| Component | Configuration |
| --- | --- |
| Controller | ESP32 development board; UART2 RX=16, TX=17 |
| Probe | Seven-in-one Modbus RS485 soil sensor |
| Serial interface | TTL-to-RS485 converter, 9600 baud |
| Bench supply | MB102 supply with MT3608 boost converter |
| Logic interface | Passive 1 kΩ / 2.2 kΩ divider at RX2 |
| Recorded rails | 4.99 V supply; 4.88 V transceiver output; approximately 3.35 V after divider |

These values are project bench records. Automated repository checks cover protocol and backend software. Confirm the probe specifications, direction control, wiring, and signal levels before using the reference firmware on hardware.

## Design exports

`dank131-t-sensor.flx` is a draft Flux project with circuit/net and layout data. Inspection found no saved routes. `t-sensor.step` is a Flux electronic-assembly export containing component geometry. These are earlier design-iteration exports, including TPS63001-related geometry; they are not a fabrication release or a complete representation of the current MT3608 breadboard.

The next PCB milestone is schematic/net review followed by routing and fabrication checks in KiCad. Actual BOM, netlist, Gerbers, and a reviewed manufacturing release will accompany that stage.

## Mechanical direction

The enclosure concept evolved from a PETG cylinder with a low-mounted 18650 cell, internal shelf, and solar-glass separation to a compact golf-tee form. The current concept places an EEMB 803465 flat LiPo below the PCB in a double-decker arrangement.

The intended design uses a sealed four-wire passage, cable gland or silicone plug, and recessed USB charging access. Battery/charging behavior, fit, thermal conditions, and weatherproofing require validation. The STEP asset represents electronics; final enclosure CAD remains a separate deliverable.

## Network direction

The intended edge network uses ESP-NOW nodes, a Raspberry Pi manager, and two caching tiers. The current repository path uses USB serial and a Python HTTP bridge. Gateway firmware, manager services, durable caching, and cloud operations remain subsequent implementation milestones.
