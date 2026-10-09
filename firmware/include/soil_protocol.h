#pragma once
#include <stddef.h>
#include <stdint.h>

namespace soil {
struct Layout {
    uint8_t moisture = 0, temperature = 1, ec = 2, ph = 3;
    uint8_t nitrogen = 4, phosphorus = 5, potassium = 6;
    float moisture_divisor = 10, temperature_divisor = 10, ph_divisor = 100;
};

struct Values {
    float moisture, temperature, ph;
    uint16_t ec, nitrogen, phosphorus, potassium;
};

enum class Status { Ok, Truncated, CrcMismatch, Address, Exception, Format, Configuration };

inline uint16_t crc16(const uint8_t* data, size_t length) {
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < length; ++i) {
        crc ^= data[i];
        for (uint8_t bit = 0; bit < 8; ++bit)
            crc = (crc & 1) ? (crc >> 1) ^ 0xA001 : crc >> 1;
    }
    return crc;
}

inline bool make_request(uint8_t address, uint16_t start, uint8_t* out) {
    if (address < 1 || address > 247 || start > 65529) return false;
    out[0] = address; out[1] = 3;
    out[2] = start >> 8; out[3] = start & 0xFF;
    out[4] = 0; out[5] = 7;
    const uint16_t crc = crc16(out, 6);
    out[6] = crc & 0xFF; out[7] = crc >> 8;
    return true;
}

inline Status parse(const uint8_t* frame, size_t length, uint8_t address,
                    Values& values, const Layout& layout = Layout{}) {
    if (length < 5) return Status::Truncated;
    const uint16_t expected = frame[length-2] | (frame[length-1] << 8);
    if (crc16(frame, length-2) != expected) return Status::CrcMismatch;
    if (frame[0] != address) return Status::Address;
    if (frame[1] == 0x83 && length == 5) return Status::Exception;
    if (length != 19 || frame[1] != 3 || frame[2] != 14) return Status::Format;
    const uint8_t indexes[] = {layout.moisture, layout.temperature, layout.ec, layout.ph,
                               layout.nitrogen, layout.phosphorus, layout.potassium};
    uint8_t used = 0;
    for (uint8_t index : indexes) {
        if (index >= 7 || (used & (1 << index))) return Status::Configuration;
        used |= 1 << index;
    }
    if (layout.moisture_divisor <= 0 || layout.temperature_divisor <= 0 ||
        layout.ph_divisor <= 0) return Status::Configuration;
    uint16_t raw[7];
    for (size_t i = 0; i < 7; ++i) raw[i] = (frame[3+2*i] << 8) | frame[4+2*i];
    int32_t temperature = raw[layout.temperature];
    if (temperature & 0x8000) temperature -= 65536;
    values.moisture = raw[layout.moisture] / layout.moisture_divisor;
    values.temperature = temperature / layout.temperature_divisor;
    values.ph = raw[layout.ph] / layout.ph_divisor;
    values.ec = raw[layout.ec];
    values.nitrogen = raw[layout.nitrogen];
    values.phosphorus = raw[layout.phosphorus];
    values.potassium = raw[layout.potassium];
    return Status::Ok;
}
}  // namespace soil
