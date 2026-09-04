import time
import statistics
import board
import busio
import RPi.GPIO as GPIO

from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1x15 import Pin


# =========================================================
# GPIO
# =========================================================

EN_LEFT = 27
EN_RIGHT = 17

S0 = 22
S1 = 23
S2 = 24
S3 = 25

SELECT_PINS = [S0, S1, S2, S3]


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in SELECT_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

GPIO.setup(EN_LEFT, GPIO.OUT)
GPIO.setup(EN_RIGHT, GPIO.OUT)


# =========================================================
# RIGHT MUX ON
#
# LEFT  EN = GPIO27
# RIGHT EN = GPIO17
#
# CD74HC4067 EN = Active LOW
# =========================================================

GPIO.output(EN_LEFT, GPIO.HIGH)    # LEFT OFF
GPIO.output(EN_RIGHT, GPIO.LOW)    # RIGHT ON


# =========================================================
# ADS1115
#
# RIGHT = A0
# LEFT  = A1
# =========================================================

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)

right_adc = AnalogIn(ads, Pin.A0)


# =========================================================
# MUX channel select
# =========================================================

def select_channel(channel):

    if not 0 <= channel <= 15:
        raise ValueError("Channel must be 0~15")

    for bit, pin in enumerate(SELECT_PINS):
        GPIO.output(pin, (channel >> bit) & 1)

    # wait for MUX settling
    time.sleep(0.03)


# =========================================================
# ADC read
# =========================================================

def read_raw(samples=15):

    # discard first samples after switching
    for _ in range(3):
        _ = right_adc.value
        time.sleep(0.01)

    values = []

    for _ in range(samples):
        values.append(right_adc.value)
        time.sleep(0.02)

    return statistics.median(values)


def read_voltage(samples=10):

    values = []

    for _ in range(samples):
        values.append(right_adc.voltage)
        time.sleep(0.02)

    return statistics.median(values)


# =========================================================
# C0 ~ C11 individual test
# =========================================================

try:

    print()
    print("=" * 65)
    print("FeetFit RIGHT FOOT SENSOR TEST")
    print("RIGHT EN  = GPIO17")
    print("RIGHT ADC = A0")
    print("=" * 65)

    for channel in range(12):

        print()
        print("-" * 65)
        print(f"RIGHT C{channel:02d} TEST")
        print("-" * 65)

        select_channel(channel)


        # -------------------------------------------------
        # BEFORE
        # -------------------------------------------------

        input(
            f"Release RIGHT C{channel:02d}, then press Enter: "
        )

        time.sleep(0.5)

        before_raw = read_raw()
        before_voltage = read_voltage()

        print()
        print(
            f"BEFORE  | RAW = {before_raw:8.1f} | "
            f"Voltage = {before_voltage:.4f} V"
        )


        # -------------------------------------------------
        # PRESSED
        # -------------------------------------------------

        input(
            f"Press and HOLD RIGHT C{channel:02d}, "
            f"then press Enter: "
        )

        time.sleep(0.3)

        pressed_raw = read_raw()
        pressed_voltage = read_voltage()

        raw_change = pressed_raw - before_raw
        voltage_change = pressed_voltage - before_voltage


        print()
        print(
            f"BEFORE   | RAW = {before_raw:8.1f} | "
            f"{before_voltage:.4f} V"
        )

        print(
            f"PRESSED  | RAW = {pressed_raw:8.1f} | "
            f"{pressed_voltage:.4f} V"
        )

        print(
            f"CHANGE   | RAW = {raw_change:+8.1f} | "
            f"{voltage_change:+.4f} V"
        )


        # -------------------------------------------------
        # simple response check
        # -------------------------------------------------

        if raw_change >= 3000:
            print(">>> STRONG RESPONSE")

        elif raw_change >= 1000:
            print(">>> RESPONSE OK")

        elif raw_change >= 300:
            print(">>> WEAK RESPONSE")

        else:
            print(">>> VERY SMALL RESPONSE")


        input(
            "\nRelease sensor and press Enter for next channel."
        )


    print()
    print("=" * 65)
    print("RIGHT C0 ~ C11 TEST COMPLETE")
    print("=" * 65)


except KeyboardInterrupt:

    print("\nTEST STOPPED")


finally:

    # both MUX OFF
    GPIO.output(EN_LEFT, GPIO.HIGH)
    GPIO.output(EN_RIGHT, GPIO.HIGH)

    GPIO.cleanup()

    print("GPIO cleanup complete")
