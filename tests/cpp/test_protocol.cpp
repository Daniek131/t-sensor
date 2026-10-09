#include <cassert>
#include <cmath>
#include <cstring>
#include "soil_protocol.h"

int main() {
    uint8_t request[8];
    const uint8_t expected[] = {1, 3, 0, 0, 0, 7, 4, 8};
    assert(soil::make_request(1, 0, request));
    assert(std::memcmp(request, expected, 8) == 0);
    assert(!soil::make_request(0, 0, request));
    uint8_t frame[19] = {1, 3, 14, 1, 244, 0, 250, 4, 176, 2, 138, 0, 45, 0, 20, 0, 80, 0, 0};
    const uint16_t crc = soil::crc16(frame, 17);
    frame[17] = crc & 0xFF; frame[18] = crc >> 8;
    soil::Values values{};
    assert(soil::parse(frame, 19, 1, values) == soil::Status::Ok);
    assert(std::fabs(values.moisture-50) < 0.001);
    assert(std::fabs(values.temperature-25) < 0.001);
    assert(std::fabs(values.ph-6.5) < 0.001);
    assert(values.ec == 1200 && values.nitrogen == 45 && values.phosphorus == 20);
    assert(values.potassium == 80);
    assert(soil::parse(frame, 4, 1, values) == soil::Status::Truncated);
    assert(soil::parse(frame, 19, 2, values) == soil::Status::Address);
    frame[5] ^= 1;
    assert(soil::parse(frame, 19, 1, values) == soil::Status::CrcMismatch);
    frame[5] ^= 1;
    soil::Layout invalid;
    invalid.ec = invalid.moisture;
    assert(soil::parse(frame, 19, 1, values, invalid) == soil::Status::Configuration);
    return 0;
}
