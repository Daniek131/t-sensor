import struct

import pytest

from tsensor.codec import SensorLayout, crc16, decode_response, request_frame


def synthetic_frame(registers=(500, 250, 1200, 650, 45, 20, 80), address=1):
    body = bytes([address, 3, 14]) + struct.pack(">7H", *registers)
    return body + struct.pack("<H", crc16(body))


def test_request_known_crc_vector_and_measurement_scaling():
    assert request_frame().hex() == "0103000000070408"
    result = decode_response(synthetic_frame())
    assert result == {
        "moisture": 50.0,
        "temperature": 25.0,
        "ec": 1200,
        "ph": 6.5,
        "nitrogen": 45,
        "phosphorus": 20,
        "potassium": 80,
    }


def test_signed_temperature_and_configurable_ph_scale():
    result = decode_response(
        synthetic_frame((500, 65511, 1200, 65, 45, 20, 80)), layout=SensorLayout(ph_divisor=10)
    )
    assert result["temperature"] == -2.5
    assert result["ph"] == 6.5


@pytest.mark.parametrize("case", ["truncated", "crc", "address", "function", "byte_count"])
def test_invalid_frames_are_rejected(case):
    frame = bytearray(synthetic_frame())
    if case == "truncated":
        frame = frame[:4]
    elif case == "crc":
        frame[4] ^= 1
    else:
        frame[{"address": 0, "function": 1, "byte_count": 2}[case]] = 9
        frame[-2:] = struct.pack("<H", crc16(frame[:-2]))
    with pytest.raises(ValueError):
        decode_response(bytes(frame))


def test_exception_response_is_reported():
    body = bytes([1, 0x83, 2])
    with pytest.raises(ValueError, match="Sensor exception code 2"):
        decode_response(body + struct.pack("<H", crc16(body)))


@pytest.mark.parametrize("args", [(0, 0), (248, 0), (1, -1), (1, 65530)])
def test_invalid_request_address(args):
    with pytest.raises(ValueError):
        request_frame(*args)
