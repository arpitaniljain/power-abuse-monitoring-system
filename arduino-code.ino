/*
  Power Abuse Monitoring System
  Arduino Nano + ACS712 + Raspberry Pi

  Function:
  - Read current from ACS712 on analog pin A0.
  - Send current in amperes to Raspberry Pi over serial.
  - Raspberry Pi calculates power using fixed 230 V.

  IMPORTANT:
  This is reconstructed example code.
  Calibrate it for your actual ACS712 module before use.
*/

const int CURRENT_SENSOR_PIN = A0;

const unsigned long SERIAL_BAUD_RATE = 9600;
const unsigned long SAMPLE_INTERVAL_MS = 500;

// Typical ACS712 20 A module sensitivity.
// Verify this against your actual sensor variant.
const float SENSOR_SENSITIVITY = 0.100; // V/A

const float ADC_REFERENCE_VOLTAGE = 5.0;
const int ADC_MAX_VALUE = 1023;

float zeroCurrentVoltage = 2.5;

float readSensorVoltage() {
  long total = 0;
  const int samples = 100;

  for (int i = 0; i < samples; i++) {
    total += analogRead(CURRENT_SENSOR_PIN);
    delay(2);
  }

  float averageADC = total / (float)samples;

  return averageADC * ADC_REFERENCE_VOLTAGE
         / ADC_MAX_VALUE;
}

void calibrateZeroCurrent() {
  // Perform calibration with no load current flowing.
  zeroCurrentVoltage = readSensorVoltage();

  Serial.print("# Zero-current voltage: ");
  Serial.println(zeroCurrentVoltage, 4);
}

float readCurrentAmps() {
  float sensorVoltage = readSensorVoltage();

  float current = (sensorVoltage - zeroCurrentVoltage)
                  / SENSOR_SENSITIVITY;

  // The sensor measures an AC waveform.
  // This simple averaging method is only a starting point,
  // not an accurate AC RMS current measurement.
  return abs(current);
}

void setup() {
  Serial.begin(SERIAL_BAUD_RATE);

  pinMode(CURRENT_SENSOR_PIN, INPUT);

  delay(1000);

  calibrateZeroCurrent();

  // Raspberry Pi should ignore lines beginning with '#'.
  Serial.println("# Power monitoring system started");
}

void loop() {
  float currentAmps = readCurrentAmps();

  // Send only current, as in the described architecture.
  // Example: 1.25
  Serial.println(currentAmps, 3);

  delay(SAMPLE_INTERVAL_MS);
}
