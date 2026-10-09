"""Protocol validation is separate from sensor-specific register assumptions."""

import os
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class SensorLayout:
    # Confirm this register order and these units with the exact probe manual.
    registers: tuple[str, ...] = (
        "moisture",
        "temperature",
        "ec",
        "ph",
        "nitrogen",
        "phosphorus",
        "potassium",
    )
    moisture_divisor: float = 10
    temperature_divisor: float = 10
    ph_divisor: float = 100

    def __post_init__(self):
        expected = {"moisture", "temperature", "ec", "ph", "nitrogen", "phosphorus", "potassium"}
        if len(self.registers) != 7 or set(self.registers) != expected:
            raise ValueError("The layout must contain each of the seven fields once")
        if min(self.moisture_divisor, self.temperature_divisor, self.ph_divisor) <= 0:
            raise ValueError("Scaling divisors must be positive")


def configured_layout():
    return SensorLayout(
        moisture_divisor=float(os.getenv("TS_MOISTURE_DIVISOR", "10")),
        temperature_divisor=float(os.getenv("TS_TEMPERATURE_DIVISOR", "10")),
        ph_divisor=float(os.getenv("TS_PH_DIVISOR", "100")),
    )


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def request_frame(address=1, start_register=0) -> bytes:
    if not 1 <= address <= 247 or not 0 <= start_register <= 65529:
        raise ValueError("Invalid address or seven-register start address")
    body = struct.pack(">BBHH", address, 3, start_register, 7)
    return body + struct.pack("<H", crc16(body))


def decode_response(frame: bytes, address=1, layout: SensorLayout | None = None) -> dict:
    layout = layout or configured_layout()
    if len(frame) < 5:
        raise ValueError("Truncated response")
    if crc16(frame[:-2]) != int.from_bytes(frame[-2:], "little"):
        raise ValueError("CRC mismatch")
    if frame[0] != address:
        raise ValueError("Unexpected sensor address")
    if frame[1] == 0x83 and len(frame) == 5:
        raise ValueError(f"Sensor exception code {frame[2]}")
    if len(frame) != 19 or frame[1] != 3 or frame[2] != 14:
        raise ValueError("Expected function 03, 14 payload bytes, and a 19-byte frame")
    raw = dict(zip(layout.registers, struct.unpack(">7H", frame[3:17]), strict=True))
    # Assumes the probe uses signed two's-complement temperature registers.
    temperature = raw["temperature"]
    if temperature & 0x8000:
        temperature -= 65536
    return {
        "moisture": raw["moisture"] / layout.moisture_divisor,
        "temperature": temperature / layout.temperature_divisor,
        "ec": raw["ec"],
        "ph": raw["ph"] / layout.ph_divisor,
        "nitrogen": raw["nitrogen"],
        "phosphorus": raw["phosphorus"],
        "potassium": raw["potassium"],
    }
