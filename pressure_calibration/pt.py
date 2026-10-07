import time
import statistics

import board
import busio
import RPi.GPIO as GPIO

import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.ads1x15 import Pin
from adafruit_ads1x15.analog_in import AnalogIn


# ============================================================
# GPIO 설정
# ============================================================

S0 = 22
S1 = 23
S2 = 24
S3 = 25

# 실제 하드웨어 기준
# A1 → 현재 왼발에 연결된 MUX
# A0 → 현재 오른발에 연결된 MUX
EN_LEFT_HW = 27
EN_RIGHT_HW = 17

MUX_PINS = [S0, S1, S2, S3]


GPIO.setmode(GPIO.BCM)

for pin in MUX_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

GPIO.setup(EN_LEFT_HW, GPIO.OUT)
GPIO.setup(EN_RIGHT_HW, GPIO.OUT)


# ============================================================
# ADS1115 설정
# ============================================================

i2c = busio.I2C(board.SCL, board.SDA)

ads = ADS.ADS1115(
    i2c,
    address=0x48
)

ads.gain = 1

# 실제 하드웨어 연결
# A1 = 왼발 MUX
# A0 = 오른발 MUX

adc_left_hw = AnalogIn(ads, Pin.A1)
adc_right_hw = AnalogIn(ads, Pin.A0)


# ============================================================
# Zero Offset
#
# 기존 보정값이 있다면 여기에 입력
# 현재는 0으로 설정
# ============================================================

LEFT_HW_OFFSETS = [
    0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0
]

RIGHT_HW_OFFSETS = [
    0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0
]


# ============================================================
# 측정 설정
# ============================================================

SAMPLES_PER_CHANNEL = 10

CHANNEL_SETTLE_TIME = 0.005

READ_INTERVAL = 0.002


# ============================================================
# MUX 채널 선택
# ============================================================

def select_channel(channel):

    GPIO.output(S0, (channel >> 0) & 1)
    GPIO.output(S1, (channel >> 1) & 1)
    GPIO.output(S2, (channel >> 2) & 1)
    GPIO.output(S3, (channel >> 3) & 1)

    time.sleep(CHANNEL_SETTLE_TIME)


# ============================================================
# MUX 제어
# ============================================================

def left_hw_mux_on():

    # 현재 하드웨어 왼발 = EN GPIO27
    GPIO.output(EN_LEFT_HW, GPIO.LOW)
    GPIO.output(EN_RIGHT_HW, GPIO.HIGH)


def right_hw_mux_on():

    # 현재 하드웨어 오른발 = EN GPIO17
    GPIO.output(EN_LEFT_HW, GPIO.HIGH)
    GPIO.output(EN_RIGHT_HW, GPIO.LOW)


def mux_off():

    GPIO.output(EN_LEFT_HW, GPIO.HIGH)
    GPIO.output(EN_RIGHT_HW, GPIO.HIGH)


# ============================================================
# ADC 채널 측정
# ============================================================

def read_adc_channel(adc, channel):

    select_channel(channel)

    # 채널 변경 직후 첫 값 버림
    _ = adc.value

    time.sleep(READ_INTERVAL)

    values = []

    for _ in range(SAMPLES_PER_CHANNEL):

        values.append(adc.value)

        time.sleep(READ_INTERVAL)

    return values


# ============================================================
# 한쪽 발 전체 측정
# ============================================================

def measure_foot(adc, offsets):

    raw_average = []
    corrected_average = []
    corrected_min = []
    corrected_max = []

    for channel in range(12):

        values = read_adc_channel(
            adc,
            channel
        )

        # RAW 평균
        raw_avg = statistics.mean(values)

        # Zero Offset 보정
        corrected_values = [
            max(
                0.0,
                value - offsets[channel]
            )
            for value in values
        ]

        # 보정 평균
        corrected_avg = statistics.mean(
            corrected_values
        )

        # 보정 최소
        corrected_min_value = min(
            corrected_values
        )

        # 보정 최대
        corrected_max_value = max(
            corrected_values
        )

        raw_average.append(raw_avg)
        corrected_average.append(corrected_avg)
        corrected_min.append(corrected_min_value)
        corrected_max.append(corrected_max_value)

    return (
        raw_average,
        corrected_average,
        corrected_min,
        corrected_max
    )


# ============================================================
# Relative 계산
#
# 양발 전체 Corrected Avg 중 최대값 = 100%
# ============================================================

def calculate_relative(
    left_corrected,
    right_corrected
):

    all_values = (
        left_corrected +
        right_corrected
    )

    max_value = max(all_values)

    if max_value <= 0:

        left_relative = [
            0.0
        ] * 12

        right_relative = [
            0.0
        ] * 12

    else:

        left_relative = [
            (value / max_value) * 100.0
            for value in left_corrected
        ]

        right_relative = [
            (value / max_value) * 100.0
            for value in right_corrected
        ]

    return (
        left_relative,
        right_relative
    )


# ============================================================
# 결과 출력
# ============================================================

def print_results(
    name,
    raw_average,
    corrected_average,
    corrected_min,
    corrected_max,
    relative
):

    print()
    print("=" * 100)
    print(name)
    print("=" * 100)

    for channel in range(12):

        print(
            f"C{channel:02d}: "
            f"RAW Avg {raw_average[channel]:8.1f} | "
            f"Corrected Avg {corrected_average[channel]:8.1f} | "
            f"Corrected Min {corrected_min[channel]:8.1f} | "
            f"Corrected Max {corrected_max[channel]:8.1f} | "
            f"Relative {relative[channel]:6.1f}%"
        )


# ============================================================
# 배열 출력
# ============================================================

def print_array(
    name,
    values
):

    print()
    print(
        f"{name} = ["
    )

    print(
        ", ".join(
            f"{value:.1f}"
            for value in values
        )
    )

    print("]")


# ============================================================
# 메인
# ============================================================

print("=" * 100)
print("FeetFit 양발 압력 센서 측정")
print("=" * 100)

print()
print("실제 하드웨어 연결")
print("A1 / GPIO27 → 현재 왼발 MUX")
print("A0 / GPIO17 → 현재 오른발 MUX")

print()
print("최종 출력")
print("LEFT  ← 현재 오른발 하드웨어")
print("RIGHT ← 현재 왼발 하드웨어")

print()
print("C0 ~ C11 전체 측정")
print("종료 : Ctrl + C")
print("=" * 100)


try:

    while True:

        # ====================================================
        # 1. 현재 하드웨어 왼발 측정
        #
        # A1 / GPIO27
        # ====================================================

        left_hw_mux_on()

        (
            left_hw_raw,
            left_hw_corrected,
            left_hw_min,
            left_hw_max
        ) = measure_foot(
            adc_left_hw,
            LEFT_HW_OFFSETS
        )


        # ====================================================
        # 2. 현재 하드웨어 오른발 측정
        #
        # A0 / GPIO17
        # ====================================================

        right_hw_mux_on()

        (
            right_hw_raw,
            right_hw_corrected,
            right_hw_min,
            right_hw_max
        ) = measure_foot(
            adc_right_hw,
            RIGHT_HW_OFFSETS
        )


        # ====================================================
        # ⭐ LEFT / RIGHT 최종 출력 교체
        #
        # 현재 하드웨어:
        #   A1 → 왼발
        #   A0 → 오른발
        #
        # 최종 출력:
        #   LEFT  ← A0 데이터
        #   RIGHT ← A1 데이터
        # ====================================================

        LEFT_RAW_AVERAGE = right_hw_raw
        LEFT_CORRECTED = right_hw_corrected
        LEFT_CORRECTED_MIN = right_hw_min
        LEFT_CORRECTED_MAX = right_hw_max

        RIGHT_RAW_AVERAGE = left_hw_raw
        RIGHT_CORRECTED = left_hw_corrected
        RIGHT_CORRECTED_MIN = left_hw_min
        RIGHT_CORRECTED_MAX = left_hw_max


        # ====================================================
        # Relative
        # ====================================================

        (
            LEFT_RELATIVE,
            RIGHT_RELATIVE
        ) = calculate_relative(
            LEFT_CORRECTED,
            RIGHT_CORRECTED
        )


        # ====================================================
        # LEFT 출력
        # ====================================================

        print_results(
            "LEFT FOOT",
            LEFT_RAW_AVERAGE,
            LEFT_CORRECTED,
            LEFT_CORRECTED_MIN,
            LEFT_CORRECTED_MAX,
            LEFT_RELATIVE
        )


        # ====================================================
        # RIGHT 출력
        # ====================================================

        print_results(
            "RIGHT FOOT",
            RIGHT_RAW_AVERAGE,
            RIGHT_CORRECTED,
            RIGHT_CORRECTED_MIN,
            RIGHT_CORRECTED_MAX,
            RIGHT_RELATIVE
        )


        # ====================================================
        # 배열 출력
        # ====================================================

        print_array(
            "LEFT_RAW_AVERAGE",
            LEFT_RAW_AVERAGE
        )

        print_array(
            "LEFT_CORRECTED",
            LEFT_CORRECTED
        )

        print_array(
            "LEFT_RELATIVE",
            LEFT_RELATIVE
        )

        print_array(
            "RIGHT_RAW_AVERAGE",
            RIGHT_RAW_AVERAGE
        )

        print_array(
            "RIGHT_CORRECTED",
            RIGHT_CORRECTED
        )

        print_array(
            "RIGHT_RELATIVE",
            RIGHT_RELATIVE
        )


        print()
        print("=" * 100)
        print("다음 측정까지 1초...")
        print("=" * 100)

        time.sleep(1)


except KeyboardInterrupt:

    print()
    print("측정을 종료합니다.")


finally:

    mux_off()

    GPIO.cleanup()
