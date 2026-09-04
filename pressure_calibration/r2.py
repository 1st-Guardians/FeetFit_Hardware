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

# 다시 확인할 채널
TEST_CHANNELS = [2, 4, 8, 9, 10]


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in SELECT_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

GPIO.setup(EN_LEFT, GPIO.OUT)
GPIO.setup(EN_RIGHT, GPIO.OUT)


# =========================================================
# RIGHT MUX ON
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
# MUX 채널 선택
# =========================================================
def select_channel(channel):

    for bit, pin in enumerate(SELECT_PINS):
        GPIO.output(pin, (channel >> bit) & 1)

    time.sleep(0.05)


# =========================================================
# ADC 측정
# =========================================================
def read_adc(samples=20):

    # 전환 직후 값 버림
    for _ in range(5):
        _ = right_adc.value
        time.sleep(0.01)

    values = []

    for _ in range(samples):
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

    print("=" * 70)
    print("RIGHT FOOT CHANNEL DIAGNOSTIC")
    print("RIGHT EN  = GPIO17")
    print("RIGHT ADC = A0")
    print("CHANNELS  =", TEST_CHANNELS)
    print("=" * 70)

    for channel in TEST_CHANNELS:

        print()
        print("=" * 70)
        print(f"RIGHT C{channel:02d}")
        print("=" * 70)

        select_channel(channel)

        print()
        print(f"현재 MUX는 C{channel:02d}에 고정되어 있습니다.")
        print()
        print("멀티미터로 확인하려면:")
        print("  검은 프로브 -> MUX GND")
        print(f"  빨간 프로브 -> RIGHT MUX C{channel}")
        print()
        print("센서를 눌렀다 떼면서 전압 변화를 먼저 확인하세요.")

        input(
            f"\nC{channel:02d}를 누르지 않은 상태에서 Enter: "
        )

        baseline = read_adc()

        print()
        print(
            f"BASELINE | "
            f"Median={baseline['median']:.1f} | "
            f"Max={baseline['max']}"
        )

        input(
            f"\nC{channel:02d}를 강하게 누른 상태에서 Enter: "
        )

        pressed = read_adc()

        change = (
            pressed["median"]
            - baseline["median"]
        )

        print()
        print(
            f"PRESSED  | "
            f"Median={pressed['median']:.1f} | "
            f"Max={pressed['max']}"
        )

        print(
            f"CHANGE   | "
            f"{change:+.1f}"
        )

        print()
        print("----- 판단 -----")

        if change >= 3000:
            print("정상적으로 큰 반응")

        elif change >= 1000:
            print("반응 확인됨")

        elif change >= 300:
            print("반응은 있으나 약함")

        else:
            print("반응 매우 작음")

        print()
        input(
            "센서에서 손을 떼고 Enter를 누르면 다음 채널로 이동합니다."
        )


except KeyboardInterrupt:
    print("\nTEST STOPPED")


finally:

    GPIO.output(EN_LEFT, GPIO.HIGH)
    GPIO.output(EN_RIGHT, GPIO.HIGH)

    GPIO.cleanup()

    print("GPIO cleanup complete")
