import time
import serial
import RPi.GPIO as GPIO

from RPLCD.i2c import CharLCD


# ==============================
# CONFIGURATION
# ==============================

SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600

VOLTAGE = 230.0
POWER_LIMIT = 1500.0

# Raspberry Pi BCM GPIO pin numbers
RELAY_PIN = 17
BUZZER_PIN = 23
RESET_BUTTON_PIN = 24

# Assumption: relay is active LOW.
# LOW  = load powered
# HIGH = load disconnected
RELAY_ON = GPIO.LOW
RELAY_OFF = GPIO.HIGH

# LCD configuration
LCD_ADDRESS = 0x27
LCD_COLUMNS = 16
LCD_ROWS = 2


# ==============================
# GPIO AND LCD INITIALIZATION
# ==============================

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(RELAY_PIN, GPIO.OUT)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(
    RESET_BUTTON_PIN,
    GPIO.IN,
    pull_up_down=GPIO.PUD_UP
)

# Start with the load enabled and buzzer off.
GPIO.output(RELAY_PIN, RELAY_ON)
GPIO.output(BUZZER_PIN, GPIO.LOW)

lcd = None
ser = None


# ==============================
# HELPER FUNCTIONS
# ==============================

def display_message(line1, line2=""):
    """Display two lines on the 16x2 LCD."""
    lcd.clear()
    lcd.cursor_pos = (0, 0)
    lcd.write_string(line1[:LCD_COLUMNS])

    lcd.cursor_pos = (1, 0)
    lcd.write_string(line2[:LCD_COLUMNS])


def disconnect_load():
    """Disconnect the load and activate the buzzer."""
    GPIO.output(RELAY_PIN, RELAY_OFF)
    GPIO.output(BUZZER_PIN, GPIO.HIGH)


def reconnect_load():
    """Reconnect the load and turn off the buzzer."""
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    GPIO.output(RELAY_PIN, RELAY_ON)


# ==============================
# MAIN PROGRAM
# ==============================

try:
    # Initialize serial communication with Arduino Nano.
    ser = serial.Serial(
        SERIAL_PORT,
        BAUD_RATE,
        timeout=2
    )

    # Allow the serial connection to stabilize.
    time.sleep(2)

    lcd = CharLCD(
        i2c_expander="PCF8574",
        address=LCD_ADDRESS,
        port=1,
        cols=LCD_COLUMNS,
        rows=LCD_ROWS,
        charmap="A00",
        auto_linebreaks=False
    )

    display_message("Power Monitoring", "System Starting")
    time.sleep(2)

    overload = False

    while True:

        # ------------------------------
        # RESET BUTTON
        # ------------------------------
        # Button is assumed to connect GPIO24 to GND
        # when pressed.
        if GPIO.input(RESET_BUTTON_PIN) == GPIO.LOW:

            if overload:
                reconnect_load()
                overload = False

                display_message(
                    "System Reset",
                    "Load Restored"
                )

                time.sleep(1)

            # Debounce the button.
            while GPIO.input(RESET_BUTTON_PIN) == GPIO.LOW:
                time.sleep(0.05)

        # ------------------------------
        # READ CURRENT FROM ARDUINO
        # ------------------------------
        line = ser.readline().decode(
            "utf-8",
            errors="ignore"
        ).strip()

        if not line or line.startswith("#"):
            continue

        try:
            current = float(line)

        except ValueError:
            # Ignore invalid or non-numeric serial data.
            continue

        # ------------------------------
        # ESTIMATE POWER
        # ------------------------------
        # This assumes a fixed 230 V supply.
        # It is an estimate, not a true AC real-power
        # measurement.
        power = current * VOLTAGE

        # ------------------------------
        # OVERLOAD DETECTION
        # ------------------------------
        if power > POWER_LIMIT and not overload:

            overload = True
            disconnect_load()

            display_message(
                "!! OVERLOAD !!",
                "Power: {:.0f} W".format(power)
            )

            print(
                "OVERLOAD! Current: {:.2f} A, "
                "Estimated Power: {:.2f} W".format(
                    current, power
                )
            )

            continue

        # ------------------------------
        # DISPLAY NORMAL READINGS
        # ------------------------------
        if not overload:

            display_message(
                "I:{:.2f} A".format(current),
                "P:{:.0f} W".format(power)
            )

            print(
                "Current: {:.2f} A | "
                "Estimated Power: {:.2f} W".format(
                    current, power
                )
            )

        else:
            # Keep the load disconnected until reset.
            disconnect_load()

            display_message(
                "!! OVERLOAD !!",
                "Press Reset Btn"
            )

        time.sleep(0.1)


except KeyboardInterrupt:
    print("\nProgram stopped by user.")

except Exception as error:
    print("Error:", error)

finally:
    # Turn off the buzzer and release GPIO resources.
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    GPIO.cleanup()

    if ser is not None and ser.is_open:
        ser.close()

    if lcd is not None:
        try:
            lcd.close(clear=True)
        except Exception:
            pass

    print("GPIO cleanup completed.")
