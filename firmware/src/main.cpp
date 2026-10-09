#include <Arduino.h>
#include "config.h"
#include "soil_protocol.h"

HardwareSerial sensor(2);
uint32_t last_poll = 0;

void setup() {
    Serial.begin(115200);
    sensor.begin(SENSOR_BAUD, SERIAL_8N1, SENSOR_RX_PIN, SENSOR_TX_PIN);
    sensor.setTimeout(RESPONSE_TIMEOUT_MS);
    if (RS485_DE_PIN >= 0) {
        pinMode(RS485_DE_PIN, OUTPUT);
        digitalWrite(RS485_DE_PIN, LOW);
    }
}

void loop() {
    // I subtract unsigned timestamps so polling still works after millis() wraps.
    if (millis() - last_poll < POLL_INTERVAL_MS) return;
    last_poll = millis();
    while (sensor.available()) sensor.read();
    uint8_t request[8];
    if (!soil::make_request(SENSOR_ADDRESS, START_REGISTER, request)) {
        Serial.println("Invalid sensor address or starting register");
        return;
    }
    if (RS485_DE_PIN >= 0) digitalWrite(RS485_DE_PIN, HIGH);
    sensor.write(request, sizeof(request));
    sensor.flush();
    if (RS485_DE_PIN >= 0) digitalWrite(RS485_DE_PIN, LOW);
    uint8_t response[19];
    const size_t length = sensor.readBytes(response, sizeof(response));
    soil::Values values{};
    const soil::Status status = soil::parse(response, length, SENSOR_ADDRESS, values);
    if (status != soil::Status::Ok) {
        Serial.printf("Frame rejected: status=%d length=%u\n", static_cast<int>(status),
                      static_cast<unsigned>(length));
        return;
    }
    Serial.printf("{\"moisture\":%.3f,\"temperature\":%.3f,\"ec\":%u,\"ph\":%.3f,"
                  "\"nitrogen\":%u,\"phosphorus\":%u,\"potassium\":%u,\"raw_frame_hex\":\"",
                  values.moisture, values.temperature, static_cast<unsigned>(values.ec), values.ph,
                  static_cast<unsigned>(values.nitrogen), static_cast<unsigned>(values.phosphorus),
                  static_cast<unsigned>(values.potassium));
    for (size_t i = 0; i < length; ++i) Serial.printf("%02x", static_cast<unsigned>(response[i]));
    Serial.println("\"}");
}
