import time
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
# MUX 활성화
# CD74HC4067 EN = Active LOW
# =========================================================

# 왼발 비활성화
GPIO.output(EN_LEFT, GPIO.HIGH)

# 오른발 활성화
GPIO.output(EN_RIGHT, GPIO.LOW)


# =========================================================
# ADS1115 설정
# =========================================================
i2c = busio.I2C(board.SCL, board.SDA)

ads = ADS1115(i2c)

# 오른발 MUX 출력이 ADS1115 A1에 연결되어 있다고 가정
adc = AnalogIn(ads, Pin.A1)


# =========================================================
# MUX 채널 선택
# =========================================================
def select_channel(channel):
    if channel < 0 or channel > 15:
        raise ValueError("channel은 0~15 사이여야 합니다.")

    for bit, pin in enumerate(SELECT_PINS):
        GPIO.output(pin, (channel >> bit) & 1)

    time.sleep(0.01)


# =========================================================
# ADC 측정
# =========================================================
def read_channel(channel, samples=10):
    select_channel(channel)

    # MUX 변경 직후 값 버리기
    for _ in range(3):
        _ = adc.value
        time.sleep(0.005)

    values = []

    for _ in range(samples):
        values.append(adc.value)
        time.sleep(0.01)

    avg = sum(values) / len(values)

    return avg


# =========================================================
# 오른발 C0 ~ C11 측정
# =========================================================
try:
    print("=" * 60)
    print("FeetFit RIGHT FOOT C0 ~ C11 Test")
    print("=" * 60)

    while True:

        print("\n---------------- RIGHT FOOT ----------------")

        for channel in range(12):
            value = read_channel(channel)

            print(
                f"C{channel:02d} | "
                f"RAW: {value:8.1f}"
            )

        print("--------------------------------------------")
        print("다음 측정까지 1초...\n")

        time.sleep(1)


except KeyboardInterrupt:
    print("\n측정을 종료합니다.")


finally:
    GPIO.output(EN_LEFT, GPIO.HIGH)
    GPIO.output(EN_RIGHT, GPIO.HIGH)

    GPIO.cleanup()

    print("GPIO cleanup 완료")
