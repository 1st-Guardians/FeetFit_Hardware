import time
import statistics
import board
import busio
import RPi.GPIO as GPIO

from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1x15 import Pin


# =========================================================
# GPIO 설정
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
# ADS1115 설정
# =========================================================
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)

# 왼발 = A0
adc_left = AnalogIn(ads, Pin.A0)

# 오른발 = A1
adc_right = AnalogIn(ads, Pin.A1)


# =========================================================
# MUX 채널 선택
# =========================================================
def select_channel(channel):
    for bit, pin in enumerate(SELECT_PINS):
        GPIO.output(pin, (channel >> bit) & 1)

    time.sleep(0.02)


# =========================================================
# ADC 읽기
# =========================================================
def read_adc(adc, samples=15):

    # MUX 전환 후 초기값 버리기
    for _ in range(3):
        _ = adc.value
        time.sleep(0.005)

    values = []

    for _ in range(samples):
        values.append(adc.value)
        time.sleep(0.01)

    return statistics.median(values)


# =========================================================
# 발 선택
# =========================================================
foot = input("측정할 발 선택 [L/R]: ").strip().upper()

if foot == "L":

    print("\n왼발 측정")
    print("ADS1115 = A0")

    # 왼발 ON / 오른발 OFF
    GPIO.output(EN_LEFT, GPIO.LOW)
    GPIO.output(EN_RIGHT, GPIO.HIGH)

    adc = adc_left
    foot_name = "LEFT"

elif foot == "R":

    print("\n오른발 측정")
    print("ADS1115 = A1")

    # 왼발 OFF / 오른발 ON
    GPIO.output(EN_LEFT, GPIO.HIGH)
    GPIO.output(EN_RIGHT, GPIO.LOW)

    adc = adc_right
    foot_name = "RIGHT"

else:
    print("L 또는 R만 입력해주세요.")
    GPIO.cleanup()
    exit()


# =========================================================
# C0 ~ C11 하나씩 테스트
# =========================================================
try:

    print("\n" + "=" * 65)
    print(f"FeetFit {foot_name} C0 ~ C11 개별 센서 테스트")
    print("=" * 65)

    for channel in range(12):

        print("\n" + "-" * 65)
        print(f"C{channel:02d} 테스트")
        print("-" * 65)

        select_channel(channel)

        # -------------------------------------------------
        # 1. 누르지 않은 상태
        # -------------------------------------------------
        input(
            f"C{channel:02d} 센서에서 손을 떼고 "
            "Enter를 누르세요: "
        )

        time.sleep(0.5)

        baseline = read_adc(adc)

        print(f"누르기 전 RAW : {baseline:.1f}")

        # -------------------------------------------------
        # 2. 누른 상태
        # -------------------------------------------------
        input(
            f"\n이제 C{channel:02d} 센서를 강하게 누른 상태에서 "
            "Enter를 누르세요: "
        )

        time.sleep(0.3)

        pressed = read_adc(adc)

        difference = pressed - baseline

        print()
        print(f"누르기 전 : {baseline:8.1f}")
        print(f"누른 후   : {pressed:8.1f}")
        print(f"변화량    : {difference:+8.1f}")

        # -------------------------------------------------
        # 간단 판정
        # -------------------------------------------------
        if difference >= 3000:
            print(">>> 반응 매우 큼")

        elif difference >= 1000:
            print(">>> 반응 확인됨")

        elif difference >= 300:
            print(">>> 반응은 있으나 작음")

        else:
            print(">>> 반응이 매우 작음 → 배선/센서 확인 필요")

        input("\n손을 떼고 Enter를 누르면 다음 센서로 넘어갑니다.")


    print("\n" + "=" * 65)
    print("C0 ~ C11 테스트 완료")
    print("=" * 65)


except KeyboardInterrupt:
    print("\n\n측정을 중단합니다.")


finally:

    # 양쪽 MUX OFF
    GPIO.output(EN_LEFT, GPIO.HIGH)
    GPIO.output(EN_RIGHT, GPIO.HIGH)

    GPIO.cleanup()

    print("GPIO cleanup 완료")

