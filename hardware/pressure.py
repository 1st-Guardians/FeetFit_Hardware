import time
from threading import Lock

import board
import busio
import RPi.GPIO as GPIO

from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1x15 import Pin

from errors import HardwareMeasurementError


# =========================================================
# FeetFit Pressure Sensor
#
# ★ 사용자 기준 실제 배선 ★
#
# 사용자 LEFT
#   MUX EN -> GPIO17
#   SIG    -> ADS1115 A0
#
# 사용자 RIGHT
#   MUX EN -> GPIO27
#   SIG    -> ADS1115 A1
#
# CD74HC4067
#   EN LOW  = 활성화
#   EN HIGH = 비활성화
# =========================================================

EN_LEFT = 17
EN_RIGHT = 27

S0 = 22
S1 = 23
S2 = 24
S3 = 25

SELECT_PINS = [
    S0,
    S1,
    S2,
    S3,
]

CHANNEL_COUNT = 12


# =========================================================
# Baseline
#
# IMPORTANT
#
# 기존 baseline은 잘못된 MUX/ADC 조합에서 측정했기 때문에
# 사용하지 않음.
#
# RAW 정상 확인 후 무하중 상태에서 다시 측정하여
# 아래 값을 교체해야 함.
# =========================================================

LEFT_BASELINE = [
    26.6,
    185.8,
    138.6,
    27.0,
    29.3,
    28.4,
    30.9,
    29.1,
    27.9,
    28.7,
    25.8,
    30.5,
]

RIGHT_BASELINE = [
    26.2,
    25.6,
    26.9,
    26.9,
    23.6,
    25.9,
    34.6,
    28.0,
    28.8,
    31.4,
    28.5,
    26.5,
]


# =========================================================
# Measurement Configuration
#
# pt.py 방식
#
# 채널 변경
# ↓
# 안정화
# ↓
# ADC 초기값 3개 버림
# ↓
# 실제 값 10회 측정
# ↓
# 평균
# =========================================================

MEASUREMENT_SECONDS = 10.0

MUX_SETTLE_TIME = 0.010

DISCARD_READS = 3
DISCARD_INTERVAL = 0.005

VALID_READS = 10
SAMPLE_INTERVAL = 0.010

NOISE_THRESHOLD = 15.0
# =========================================================
# Lock
#
# API에서 압력 측정이 동시에 실행되는 것 방지
# =========================================================

pressure_lock = Lock()


# =========================================================
# GPIO Setup
# =========================================================

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)


for pin in SELECT_PINS:

    GPIO.setup(
        pin,
        GPIO.OUT,
    )

    GPIO.output(
        pin,
        GPIO.LOW,
    )


GPIO.setup(
    EN_LEFT,
    GPIO.OUT,
)

GPIO.setup(
    EN_RIGHT,
    GPIO.OUT,
)


# 처음에는 양쪽 MUX 모두 OFF
GPIO.output(
    EN_LEFT,
    GPIO.HIGH,
)

GPIO.output(
    EN_RIGHT,
    GPIO.HIGH,
)


# =========================================================
# ADS1115 Setup
#
# 사용자 LEFT  -> A0
# 사용자 RIGHT -> A1
# =========================================================

i2c = busio.I2C(
    board.SCL,
    board.SDA,
)


ads = ADS1115(
    i2c,
    address=0x48,
)


left_adc = AnalogIn(
    ads,
    Pin.A0,
)


right_adc = AnalogIn(
    ads,
    Pin.A1,
)


# =========================================================
# Disable Both MUXes
# =========================================================

def disable_muxes():

    GPIO.output(
        EN_LEFT,
        GPIO.HIGH,
    )

    GPIO.output(
        EN_RIGHT,
        GPIO.HIGH,
    )


# =========================================================
# Select MUX Channel
#
# CD74HC4067
#
# C0 ~ C15
#
# S0 = LSB
# =========================================================

def select_channel(
    channel: int,
):

    if channel < 0 or channel > 15:

        raise ValueError(
            "channel은 0~15 사이여야 합니다."
        )


    for bit, pin in enumerate(
        SELECT_PINS
    ):

        GPIO.output(
            pin,
            (channel >> bit) & 1,
        )


    # 채널 전환 후 안정화
    time.sleep(
        MUX_SETTLE_TIME
    )


# =========================================================
# Read ADC
#
# 채널 변경 직후 값 3회 버림
# ↓
# 10회 읽기
# ↓
# 평균값 반환
# =========================================================

def read_adc(
    adc: AnalogIn,
) -> float:

    # -----------------------------------------
    # 초기값 버리기
    # -----------------------------------------

    for _ in range(
        DISCARD_READS
    ):

        _ = adc.value

        time.sleep(
            DISCARD_INTERVAL
        )


    # -----------------------------------------
    # 실제 측정값
    # -----------------------------------------

    values = []


    for _ in range(
        VALID_READS
    ):

        values.append(
            adc.value
        )

        time.sleep(
            SAMPLE_INTERVAL
        )


    # -----------------------------------------
    # 평균
    # -----------------------------------------

    return float(
        sum(values)
        / len(values)
    )


# =========================================================
# Read One Foot
#
# pt.py 방식
#
# 해당 발 MUX를 한 번 켠 뒤
# C0 ~ C11 전체 측정
#
# 전체 측정이 끝난 뒤 MUX OFF
# =========================================================

def read_foot(
    adc: AnalogIn,
    enable_pin: int,
    other_enable_pin: int,
) -> list:

    values = []


    # -----------------------------------------
    # 두 MUX 모두 OFF
    # -----------------------------------------

    disable_muxes()


    # -----------------------------------------
    # 반대쪽 MUX는 OFF 상태 유지
    # -----------------------------------------

    GPIO.output(
        other_enable_pin,
        GPIO.HIGH,
    )


    # -----------------------------------------
    # 측정할 MUX ON
    #
    # CD74HC4067 EN = Active LOW
    # -----------------------------------------

    GPIO.output(
        enable_pin,
        GPIO.LOW,
    )


    # MUX 활성화 안정화
    time.sleep(
        0.020
    )


    try:

        # -------------------------------------
        # MUX를 켠 상태로
        # C0 ~ C11 연속 측정
        # -------------------------------------

        for channel in range(
            CHANNEL_COUNT
        ):

            select_channel(
                channel
            )


            value = read_adc(
                adc
            )


            values.append(
                value
            )


        return values


    finally:

        # -------------------------------------
        # 한 발 전체 측정 완료 후 MUX OFF
        # -------------------------------------

        GPIO.output(
            enable_pin,
            GPIO.HIGH,
        )


# =========================================================
# Read Both Feet
#
# ★ 사용자 기준 ★
#
# LEFT
# GPIO17 + ADS1115 A0
#
# RIGHT
# GPIO27 + ADS1115 A1
# =========================================================

def read_both_feet():

    # -----------------------------------------
    # 사용자 LEFT
    #
    # GPIO17
    # ADS1115 A0
    # -----------------------------------------

    left_values = read_foot(
        adc=left_adc,
        enable_pin=EN_LEFT,
        other_enable_pin=EN_RIGHT,
    )


    # -----------------------------------------
    # 사용자 RIGHT
    #
    # GPIO27
    # ADS1115 A1
    # -----------------------------------------

    right_values = read_foot(
        adc=right_adc,
        enable_pin=EN_RIGHT,
        other_enable_pin=EN_LEFT,
    )


    return (
        left_values,
        right_values,
    )


# =========================================================
# Baseline Correction
#
# corrected = raw - baseline
#
# 음수는 0
#
# 현재는 baseline이 0이므로
# RAW 정상 여부 확인용.
#
# baseline 재측정 후 실제 보정값이 적용됨.
# =========================================================

def apply_baseline(
    raw_values: list,
    baseline: list,
) -> list:

    corrected = []

    for channel in range(CHANNEL_COUNT):

        value = raw_values[channel] - baseline[channel]

        if value <= NOISE_THRESHOLD:
            value = 0.0

        corrected.append(value)

    return corrected


# =========================================================
# Relative Pressure
#
# 한 발에서 가장 높은 센서를 100으로 환산
#
# 히트맵 / 디버깅용
# =========================================================

def calculate_relative(
    corrected_values: list,
) -> list:

    max_value = max(
        corrected_values
    )


    if max_value <= 0:

        return [
            0.0
        ] * CHANNEL_COUNT


    return [

        value
        / max_value
        * 100.0

        for value
        in corrected_values
    ]


# =========================================================
# Pressure Measurement
#
# 10초 동안 반복 측정
#
# Scan:
#
# LEFT C0 ~ C11
# ↓
# RIGHT C0 ~ C11
#
# 각 Scan 결과를 누적한 뒤
# 채널별 평균 계산
# =========================================================

def measure_pressure() -> dict:

    try:

        with pressure_lock:

            print()

            print(
                "=" * 72
            )

            print(
                "[PRESSURE] 실제 센서 측정 시작"
            )

            print(
                f"[PRESSURE] 측정 시간: "
                f"{MEASUREMENT_SECONDS:.0f}초"
            )

            print(
                "[PRESSURE] USER LEFT  = GPIO17 / ADS1115 A0"
            )

            print(
                "[PRESSURE] USER RIGHT = GPIO27 / ADS1115 A1"
            )

            print(
                "[PRESSURE] MUX 방식 = 한 발 C0~C11 연속 측정"
            )

            print(
                "=" * 72
            )


            # =================================================
            # RAW 누적
            # =================================================

            left_sums = [
                0.0
            ] * CHANNEL_COUNT


            right_sums = [
                0.0
            ] * CHANNEL_COUNT


            scan_count = 0


            start_time = (
                time.monotonic()
            )


            # =================================================
            # 실제 측정
            # =================================================

            while (
                time.monotonic()
                - start_time
                < MEASUREMENT_SECONDS
            ):

                (
                    left_values,
                    right_values,
                ) = read_both_feet()


                # -----------------------------------------
                # 이번 Scan RAW 누적
                # -----------------------------------------

                for channel in range(
                    CHANNEL_COUNT
                ):

                    left_sums[channel] += (
                        left_values[channel]
                    )

                    right_sums[channel] += (
                        right_values[channel]
                    )


                scan_count += 1


                # -----------------------------------------
                # Scan Log
                # -----------------------------------------

                print(
                    f"[PRESSURE] "
                    f"Scan {scan_count:02d} | "
                    f"L Max "
                    f"{max(left_values):8.1f} | "
                    f"R Max "
                    f"{max(right_values):8.1f}"
                )


            # =================================================
            # Validation
            # =================================================

            if scan_count <= 0:

                raise ValueError(
                    "압력 센서 측정값이 없습니다."
                )


            # =================================================
            # RAW Average
            # =================================================

            left_raw_average = [

                value / scan_count

                for value
                in left_sums
            ]


            right_raw_average = [

                value / scan_count

                for value
                in right_sums
            ]


            # =================================================
            # Baseline Correction
            # =================================================

            left_corrected = (
                apply_baseline(
                    left_raw_average,
                    LEFT_BASELINE,
                )
            )


            right_corrected = (
                apply_baseline(
                    right_raw_average,
                    RIGHT_BASELINE,
                )
            )


            # =================================================
            # Relative Pressure
            # =================================================

            left_relative = (
                calculate_relative(
                    left_corrected
                )
            )


            right_relative = (
                calculate_relative(
                    right_corrected
                )
            )


            # =================================================
            # Round
            # =================================================

            left_raw_average = [

                round(
                    value,
                    1,
                )

                for value
                in left_raw_average
            ]


            right_raw_average = [

                round(
                    value,
                    1,
                )

                for value
                in right_raw_average
            ]


            left_corrected = [

                round(
                    value,
                    1,
                )

                for value
                in left_corrected
            ]


            right_corrected = [

                round(
                    value,
                    1,
                )

                for value
                in right_corrected
            ]


            left_relative = [

                round(
                    value,
                    1,
                )

                for value
                in left_relative
            ]


            right_relative = [

                round(
                    value,
                    1,
                )

                for value
                in right_relative
            ]


            # =================================================
            # Result
            # =================================================

            print()

            print(
                "=" * 72
            )

            print(
                "[PRESSURE RESULT]"
            )

            print(
                "=" * 72
            )


            print(
                "LEFT RAW =",
                left_raw_average,
            )


            print(
                "LEFT CORRECTED =",
                left_corrected,
            )


            print(
                "LEFT RELATIVE =",
                left_relative,
            )


            print()


            print(
                "RIGHT RAW =",
                right_raw_average,
            )


            print(
                "RIGHT CORRECTED =",
                right_corrected,
            )


            print(
                "RIGHT RELATIVE =",
                right_relative,
            )


            print()


            print(
                f"[PRESSURE] "
                f"Total Scan Count = "
                f"{scan_count}"
            )


            print(
                f"[PRESSURE] "
                f"Elapsed = "
                f"{time.monotonic() - start_time:.1f}s"
            )


            print(
                "=" * 72
            )


            # =================================================
            # API / AI 전달
            #
            # 기존 인터페이스 유지
            #
            # {
            #     "left":  [C0 ... C11],
            #     "right": [C0 ... C11]
            # }
            #
            # 사용자 기준 LEFT / RIGHT
            # =================================================

            return {

                "left":
                    left_corrected,

                "right":
                    right_corrected,
            }


    except HardwareMeasurementError:

        raise


    except Exception as e:

        raise HardwareMeasurementError(

            reason=
                "PRESSURE_SENSOR_ERROR",

            message=(
                "압력 측정에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=
                str(e),
        )


    finally:

        # FastAPI 서버에서 다음 측정에도
        # GPIO를 사용해야 하므로 GPIO.cleanup() 하지 않음.

        try:

            disable_muxes()

        except Exception:

            pass
