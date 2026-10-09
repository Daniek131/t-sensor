#pragma once
#include <stdint.h>

// UART and probe settings for the bench node; confirm the register profile before flashing.
constexpr int SENSOR_RX_PIN = 16;
constexpr int SENSOR_TX_PIN = 17;
constexpr int RS485_DE_PIN = -1;  // -1 for an auto-direction module; otherwise wire DE and /RE.
constexpr uint8_t SENSOR_ADDRESS = 1;
constexpr uint16_t START_REGISTER = 0;
constexpr uint32_t SENSOR_BAUD = 9600;
constexpr uint32_t POLL_INTERVAL_MS = 5000;
constexpr uint32_t RESPONSE_TIMEOUT_MS = 300;
