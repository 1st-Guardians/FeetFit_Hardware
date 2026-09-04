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

# 다시 확인할 오른발 채널
TEST_CHANNELS = [0, 2, 4, 8, 9, 10]


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in SELECT_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

GPIO.setup(EN_LEFT, GPIO.OUT)
GPIO.setup(EN_RIGHT, GPIO.OUT)


# =========================================================
# RIGHT MUX ON
# LEFT  = GPIO27
# RIGHT = GPIO17
# Active LOW
# =========================================================

GPIO.output(EN_LEFT, GPIO.HIGH)    # LEFT OFF
GPIO.output(EN_RIGHT, GPIO.LOW)    # RIGHT ON


# =========================================================
# ADS1115
# RIGHT = A0
# =========================================================

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)

right_adc = AnalogIn(ads, Pin.A0)


# =========================================================
# MUX channel select
# =========================================================

def select_channel(channel):

    for bit, pin in enumerate(SELECT_PINS):
        GPIO.output(pin, (channel >> bit) & 1)

    # MUX switching settling time
    time.sleep(0.05)


# =========================================================
# 측정
# 2초 동안 계속 RAW 측정
# =========================================================

def measure(duration=2.0):

    # MUX 전환 직후 값 버림
    for _ in range(5):
        _ = right_adc.value
        time.sleep(0.01)

    values = []

    start = time.time()

    while time.time() - start < duration:

        values.append(right_adc.value)
        time.sleep(0.02)

    return {
        "median": statistics.median(values),
        "average": sum(values) / len(values),
        "min": min(values),
        "max": max(values)
    }


# =========================================================
# MAIN
# =========================================================

try:

    print()
    print("=" * 70)
    print("RIGHT FOOT FAILED CHANNEL RETEST")
    print("RIGHT EN  = GPIO17")
    print("RIGHT ADC = A0")
    print()
    print("Channels:", TEST_CHANNELS)
    print("=" * 70)


    for channel in TEST_CHANNELS:

        print()
        print("-" * 70)
        print(f"RIGHT C{channel:02d} RETEST")
        print("-" * 70)

        select_channel(channel)


        # -------------------------------------------------
        # BASELINE
        # -------------------------------------------------

        input(
            f"Release C{channel:02d}, then press Enter: "
        )

        print("Measuring baseline for 2 seconds...")

        baseline = measure(2.0)


        print()
        print(
            f"BASELINE | "
            f"Median={baseline['median']:.1f} | "
            f"Max={baseline['max']}"
        )


        # -------------------------------------------------
        # PRESSED
        # -------------------------------------------------

        input(
            f"\nPress and HOLD C{channel:02d}, then press Enter: "
        )

        print("KEEP HOLDING for 2 seconds...")

        pressed = measure(2.0)


        median_change = (
            pressed["median"]
            - baseline["median"]
        )

        max_change = (
            pressed["max"]
            - baseline["max"]
        )


        print()
        print(
            f"PRESSED  | "
            f"Median={pressed['median']:.1f} | "
            f"Max={pressed['max']}"
        )

        print(
            f"CHANGE   | "
            f"Median={median_change:+.1f} | "
            f"Max={max_change:+.1f}"
        )


        # -------------------------------------------------
        # 판정
        # -------------------------------------------------

        if median_change >= 3000:

            print(">>> STRONG RESPONSE")

        elif median_change >= 1000:

            print(">>> RESPONSE OK")

        elif median_change >= 300:

            print(">>> WEAK RESPONSE")

        else:

            print(">>> VERY SMALL / NO RESPONSE")


        input(
            "\nRelease sensor and press Enter for next channel."
        )


    print()
    print("=" * 70)
    print("RETEST COMPLETE")
    print("=" * 70)


except KeyboardInterrupt:

    print("\nTEST STOPPED")


finally:

    GPIO.output(EN_LEFT, GPIO.HIGH)
    GPIO.output(EN_RIGHT, GPIO.HIGH)

    GPIO.cleanup()

    print("GPIO cleanup complete")
