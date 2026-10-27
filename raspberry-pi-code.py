import time
import serial
import RPi.GPIO as GPIO
from RPLCD.i2c import CharLCD

# ---------- CONFIGURATION ----------

SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600

RELAY_PIN = 17       # BCM GPIO 17, physical pin 11
BUZZER_PIN = 23      # BCM GPIO 23, physical pin 16
BUTTON_PIN = 24      # BCM GPIO 24, physical pin 18

POWER_LIMIT = 1500   # Overload threshold in watts

# ---------- GPIO SETUP ----------

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(
    BUTTON_PIN,
    GPIO.IN,
    pull_up_down=GPIO.PUD_UP
)

# Active-low relay:
# LOW = relay energized; HIGH = relay de-energized.
# Verify the actual relay module behavior before connecting a load.
GPIO.output(RELAY_PIN, GPIO.LOW)
GPIO.output(BUZZER_PIN, GPIO.LOW)

# ---------- LCD SETUP ----------

lcd = CharLCD(
    "PCF8574",
    address=0x27,
    port=1,
    cols=16,
    rows=2
)

lcd.clear()
lcd.write_string("Power Monitor")
lcd.cursor_pos = (1, 0)
lcd.write_string("Starting...")
time.sleep(2)
lcd.clear()

# ---------- SERIAL SETUP ----------

ser = None
system_locked = False

try:
    ser = serial.Serial(
        SERIAL_PORT,
        BAUD_RATE,
        timeout=1
    )

    time.sleep(2)
    print("SYSTEM STARTED")

    # ---------- MAIN LOOP ----------

    while True:
        try:
            # Read: current,power
            line = ser.readline().decode(
                "utf-8",
                errors="ignore"
            ).strip()

            if line:
                print("RAW:", line)

                parts = line.split(",")

                if len(parts) != 2:
                    continue

                try:
                    current = float(parts[0])
                    power = float(parts[1])
                except ValueError:
                    continue

                # ---------- BUTTON RESET ----------

                if GPIO.input(BUTTON_PIN) == GPIO.LOW:
                    print("RESET PRESSED")
                    system_locked = False
                    time.sleep(0.3)

                # ---------- OVERLOAD LOGIC ----------

                if system_locked:
                    status = "LOCKED"

                    GPIO.output(RELAY_PIN, GPIO.HIGH)
                    GPIO.output(BUZZER_PIN, GPIO.HIGH)

                elif power > POWER_LIMIT:
                    status = "OVERLOAD"
                    system_locked = True

                    GPIO.output(RELAY_PIN, GPIO.HIGH)
                    GPIO.output(BUZZER_PIN, GPIO.HIGH)

                else:
                    status = "NORMAL"

                    GPIO.output(RELAY_PIN, GPIO.LOW)
                    GPIO.output(BUZZER_PIN, GPIO.LOW)

                # ---------- LCD DISPLAY ----------

                lcd.clear()
                lcd.write_string(
                    f"I={current:.2f}A"
                )

                lcd.cursor_pos = (1, 0)
                lcd.write_string(
                    f"P={power:.0f}W {status}"[:16]
                )

                print(
                    f"I={current:.2f} A | "
                    f"P={power:.0f} W | {status}"
                )

                time.sleep(0.5)

        except Exception as error:
            print("Reading error:", error)
            time.sleep(0.5)

except KeyboardInterrupt:
    print("Program stopped by user.")

except Exception as error:
    print("System error:", error)

finally:
    if ser is not None and ser.is_open:
        ser.close()

    try:
        lcd.clear()
    except Exception:
        pass

    GPIO.cleanup()
    print("GPIO cleaned up.")
