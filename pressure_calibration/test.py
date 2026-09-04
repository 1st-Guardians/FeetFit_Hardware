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

EN_GPIO27 = 27
EN_GPIO17 = 17

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

GPIO.setup(EN_GPIO27, GPIO.OUT)
GPIO.setup(EN_GPIO17, GPIO.OUT)


# ???? ? ? OFF
# CD74HC4067 EN = Active LOW
GPIO.output(EN_GPIO27, GPIO.HIGH)
GPIO.output(EN_GPIO17, GPIO.HIGH)


# =========================================================
# C1 ??
#
# C1 = S3 S2 S1 S0 = 0001
# =========================================================

GPIO.output(S0, GPIO.HIGH)
GPIO.output(S1, GPIO.LOW)
GPIO.output(S2, GPIO.LOW)
GPIO.output(S3, GPIO.LOW)


# =========================================================
# ADS1115
# =========================================================

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)

a0 = AnalogIn(ads, Pin.A0)
a1 = AnalogIn(ads, Pin.A1)


# =========================================================
# ADC ??
# =========================================================

def read_voltage(adc, samples=15):

    # ??? ???
    for _ in range(3):
        _ = adc.voltage
        time.sleep(0.01)

    values = []

    for _ in range(samples):
        values.append(adc.voltage)
        time.sleep(0.02)

    return statistics.median(values)


def read_both():

    v0 = read_voltage(a0)
    v1 = read_voltage(a1)

    return v0, v1


# =========================================================
# MUX ??
# =========================================================

def enable_gpio27():

    GPIO.output(EN_GPIO27, GPIO.LOW)
    GPIO.output(EN_GPIO17, GPIO.HIGH)

    time.sleep(0.1)


def enable_gpio17():

    GPIO.output(EN_GPIO27, GPIO.HIGH)
    GPIO.output(EN_GPIO17, GPIO.LOW)

    time.sleep(0.1)


def disable_all():

    GPIO.output(EN_GPIO27, GPIO.HIGH)
    GPIO.output(EN_GPIO17, GPIO.HIGH)

# =========================================================
# ??? ??
# =========================================================

def test_sensor(sensor_name, enable_function, en_name):

    print()
    print("=" * 70)
    print(f"{sensor_name} / {en_name} ACTIVE")
    print("=" * 70)

    enable_function()

    input(
        f"Release physical {sensor_name} C1, then press Enter: "
    )

    time.sleep(0.5)

    before_a0, before_a1 = read_both()

    print()
    print(
        f"BEFORE | "
        f"A0 = {before_a0:.4f} V | "
        f"A1 = {before_a1:.4f} V"
    )

    input(
        f"Press and HOLD physical {sensor_name} C1, then press Enter: "
    )

    time.sleep(0.3)

    pressed_a0, pressed_a1 = read_both()

    diff_a0 = pressed_a0 - before_a0
    diff_a1 = pressed_a1 - before_a1

    print()
    print(
        f"PRESSED | "
        f"A0 = {pressed_a0:.4f} V | "
        f"A1 = {pressed_a1:.4f} V"
    )

    print(
        f"CHANGE  | "
        f"A0 = {diff_a0:+.4f} V | "
        f"A1 = {diff_a1:+.4f} V"
    )

    print()

    if abs(diff_a0) > abs(diff_a1):

        print(">>> Larger response: A0")

    elif abs(diff_a1) > abs(diff_a0):

        print(">>> Larger response: A1")

    else:

        print(">>> No clear difference")

    input("Release sensor and press Enter to continue.")

    disable_all()

# =========================================================
# MAIN
# =========================================================

try:

    print()
    print("=" * 70)
    print("FeetFit PHYSICAL LEFT/RIGHT MAPPING TEST")
    print("CHANNEL = C1")
    print("=" * 70)

    print()
    print("IMPORTANT:")
    print("- LEFT means the actual physical LEFT foot sensor plate.")
    print("- RIGHT means the actual physical RIGHT foot sensor plate.")
    print("- Ignore old software variable names.")
    print()


    # -----------------------------------------------------
    # ?? ?? C1
    # -----------------------------------------------------

    test_sensor(
        "LEFT",
        enable_gpio27,
        "GPIO27 MUX"
    )

    test_sensor(
        "LEFT",
        enable_gpio17,
        "GPIO17 MUX"
    )


    # -----------------------------------------------------
    # ?? ??? C1
    # -----------------------------------------------------

    test_sensor(
        "RIGHT",
        enable_gpio27,
        "GPIO27 MUX"
    )

    test_sensor(
        "RIGHT",
        enable_gpio17,
        "GPIO17 MUX"
    )


    print()
    print("=" * 70)
    print("MAPPING TEST COMPLETE")
    print("=" * 70)


except KeyboardInterrupt:

    print("\nSTOP")


finally:

    disable_all()
    GPIO.cleanup()

    print("GPIO cleanup complete")
