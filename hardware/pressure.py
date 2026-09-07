import time
import statistics

from threading import Lock

import RPi.GPIO as GPIO
import board
import busio

import adafruit_ads1x15.ads1115 as ADS
import adafruit_ads1x15.ads1x15 as ADS1X15

from adafruit_ads1x15.analog_in import AnalogIn

from config import (
    PRESSURE_FIXED_INPUT,
    PRESSURE_FIXED_SCAN_COUNT
)

from errors import HardwareMeasurementError


# =========================================================
# GPIO Configuration
# =========================================================

S0 = 22
S1 = 23
S2 = 24
S3 = 25

EN_LEFT = 17
EN_RIGHT = 27


# =========================================================
# Baseline
#
# 최종 조립 상태에서 측정한 채널별 무하중 기준값
# =========================================================

LEFT_BASELINE = [
    12.3,
    174.3,
    50.6,
    23.1,
    23.4,
    15.3,
    17.2,
    24.2,
    27.0,
    33.4,
    14.2,
    10.0
]


RIGHT_BASELINE = [
    25.1,
    26.4,
    25.2,
    20.1,
    20.6,
    26.3,
    29.5,
    23.0,
    12.4,
    16.6,
    29.7,
    153.6
]


# =========================================================
# Temporary Fixed Pressure Input
#
# 압력센서 점검 중 사용할 보정 후 값
#
# PRESSURE_FIXED_INPUT=false 로 변경하면
# 아래 값은 사용되지 않고 실제 ADS1115 측정 수행
# =========================================================

FIXED_LEFT_CORRECTED = [
    51.8,
    20.8,
    58.8,
    56.0,
    50.2,
    11099.0,
    629.3,
    45.2,
    43.8,
    587.7,
    8840.7,
    12134.9
]


FIXED_RIGHT_CORRECTED = [
    9939.8,
    7652.4,
    814.9,
    27.5,
    0.0,
    1684.3,
    8571.8,
    10.2,
    3379.6,
    4.9,
    4.4,
    0.0
]


# =========================================================
# Measurement Configuration
# =========================================================

MEASUREMENT_SECONDS = 10.0

MUX_DISCHARGE_TIME = 0.010
MUX_SETTLE_TIME = 0.010
ADC_SETTLE_TIME = 0.003

DISCARD_READS = 3
VALID_READS = 3


# =========================================================
# Pressure Lock
# =========================================================

pressure_lock = Lock()


# =========================================================
# GPIO Setup
# =========================================================

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)


for pin in [
    S0,
    S1,
    S2,
    S3
]:

    GPIO.setup(
        pin,
        GPIO.OUT,
        initial=GPIO.LOW
    )


GPIO.setup(
    EN_LEFT,
    GPIO.OUT,
    initial=GPIO.HIGH
)


GPIO.setup(
    EN_RIGHT,
    GPIO.OUT,
    initial=GPIO.HIGH
)


# =========================================================
# ADS1115 Setup
# =========================================================

i2c = busio.I2C(
    board.SCL,
    board.SDA
)


ads = ADS.ADS1115(
    i2c,
    address=0x48
)


ads.gain = 1
ads.data_rate = 860


# Left MUX SIG -> ADS1115 A0
left_adc = AnalogIn(
    ads,
    ADS1X15.Pin.A0
)


# Right MUX SIG -> ADS1115 A1
right_adc = AnalogIn(
    ads,
    ADS1X15.Pin.A1
)


# =========================================================
# MUX Address
# =========================================================

def set_mux_address(
    channel: int
):

    GPIO.output(
        S0,
        (channel >> 0) & 1
    )

    GPIO.output(
        S1,
        (channel >> 1) & 1
    )

    GPIO.output(
        S2,
        (channel >> 2) & 1
    )

    GPIO.output(
        S3,
        (channel >> 3) & 1
    )


# =========================================================
# Read One Channel
#
# 채널 전환
# -> 초기 ADC 3개 제거
# -> 유효 ADC 3개 수집
# -> Median
# =========================================================

def read_channel(
    channel: int,
    enable_pin: int,
    other_enable_pin: int,
    adc: AnalogIn
) -> float:

    # 양쪽 MUX 비활성화
    GPIO.output(
        EN_LEFT,
        GPIO.HIGH
    )

    GPIO.output(
        EN_RIGHT,
        GPIO.HIGH
    )

    time.sleep(
        MUX_DISCHARGE_TIME
    )


    # 채널 선택
    set_mux_address(
        channel
    )


    # 해당 발 MUX 활성화
    GPIO.output(
        enable_pin,
        GPIO.LOW
    )

    GPIO.output(
        other_enable_pin,
        GPIO.HIGH
    )

    time.sleep(
        MUX_SETTLE_TIME
    )


    # 초기 ADC 값 3개 버림
    for _ in range(
        DISCARD_READS
    ):

        _ = adc.value

        time.sleep(
            ADC_SETTLE_TIME
        )


    # 유효 ADC 값 3개 수집
    samples = []

    for _ in range(
        VALID_READS
    ):

        samples.append(
            adc.value
        )

        time.sleep(
            ADC_SETTLE_TIME
        )


    # MUX 비활성화
    GPIO.output(
        enable_pin,
        GPIO.HIGH
    )


    # 중앙값
    return float(
        statistics.median(
            samples
        )
    )


# =========================================================
# Read Both Feet
# =========================================================

def read_both_feet():

    left_values = []
    right_values = []


    for channel in range(12):

        left_value = read_channel(
            channel,
            EN_LEFT,
            EN_RIGHT,
            left_adc
        )


        right_value = read_channel(
            channel,
            EN_RIGHT,
            EN_LEFT,
            right_adc
        )


        left_values.append(
            left_value
        )


        right_values.append(
            right_value
        )


    return (
        left_values,
        right_values
    )


# =========================================================
# Baseline Correction
#
# corrected = raw - baseline
#
# 음수 -> 0
# =========================================================

def apply_baseline(
    raw_values: list,
    baseline: list
) -> list:

    corrected = []


    for channel in range(12):

        value = (
            raw_values[channel]
            - baseline[channel]
        )


        if value < 0:

            value = 0.0


        corrected.append(
            value
        )


    return corrected


# =========================================================
# Relative Value
#
# 디버깅 및 하중 분포 확인용
#
# AI에는 corrected 값을 전달
# =========================================================

def calculate_relative(
    corrected_values: list
) -> list:

    max_value = max(
        corrected_values
    )


    if max_value <= 0:

        return [
            0.0
        ] * 12


    return [

        value
        / max_value
        * 100.0

        for value
        in corrected_values
    ]


# =========================================================
# Fixed Input Scan
#
# 최종 9회 평균이 목표 corrected 값과 동일하도록
# 각 스캔에 작은 변동을 부여
# =========================================================

def read_fixed_pressure_scan(
    scan_index: int
):

    # 9개의 평균 = 1.0
    factors = [
        0.96,
        0.97,
        0.98,
        0.99,
        1.00,
        1.01,
        1.02,
        1.03,
        1.04
    ]


    # 기본은 9회
    if (
        PRESSURE_FIXED_SCAN_COUNT
        == 9
    ):

        factor = factors[
            scan_index
        ]

    else:

        # scan 수를 변경한 경우
        # 최종값을 그대로 사용
        factor = 1.0


    # -----------------------------------------------------
    # corrected 값에 스캔별 변동 적용
    # -----------------------------------------------------

    left_corrected_scan = [

        value * factor

        for value
        in FIXED_LEFT_CORRECTED
    ]


    right_corrected_scan = [

        value * factor

        for value
        in FIXED_RIGHT_CORRECTED
    ]


    # -----------------------------------------------------
    # 기존 측정 알고리즘과 동일하게
    # RAW -> Baseline Correction 경로를 거치도록
    #
    # RAW = Corrected + Baseline
    # -----------------------------------------------------

    left_raw_scan = [

        LEFT_BASELINE[channel]
        + left_corrected_scan[channel]

        for channel in range(12)
    ]


    right_raw_scan = [

        RIGHT_BASELINE[channel]
        + right_corrected_scan[channel]

        for channel in range(12)
    ]


    return (
        left_raw_scan,
        right_raw_scan
    )


# =========================================================
# Pressure Measurement
# =========================================================

def measure_pressure() -> dict:

    try:

        with pressure_lock:

            print()
            print("=" * 72)
            print("[PRESSURE] 측정 시작")
            print(
                f"[PRESSURE] 측정 시간: "
                f"{MEASUREMENT_SECONDS:.0f}초"
            )

           # print(
           #     "[PRESSURE] Input mode:",
           #     (
           #         "FIXED"
           #         if PRESSURE_FIXED_INPUT
           #         else "SENSOR"
           #     )
           # )

            print("=" * 72)


            # =================================================
            # RAW 누적값
            # =================================================

            left_sums = [
                0.0
            ] * 12


            right_sums = [
                0.0
            ] * 12


            scan_count = 0

            start_time = (
                time.time()
            )


            # =================================================
            # FIXED INPUT
            # =================================================

            if PRESSURE_FIXED_INPUT:

                if (
                    PRESSURE_FIXED_SCAN_COUNT
                    <= 0
                ):

                    raise ValueError(
                        "PRESSURE_FIXED_SCAN_COUNT는 "
                        "1 이상이어야 합니다."
                    )


                scan_interval = (
                    MEASUREMENT_SECONDS
                    / PRESSURE_FIXED_SCAN_COUNT
                )


                for scan_index in range(
                    PRESSURE_FIXED_SCAN_COUNT
                ):

                    (
                        left_values,
                        right_values
                    ) = read_fixed_pressure_scan(
                        scan_index
                    )


                    # -----------------------------------------
                    # RAW 누적
                    # -----------------------------------------

                    for channel in range(12):

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


                    # -----------------------------------------
                    # 전체 10초 측정 시간 유지
                    # -----------------------------------------

                    target_time = (
                        start_time
                        + (
                            scan_count
                            * scan_interval
                        )
                    )


                    remaining = (
                        target_time
                        - time.time()
                    )


                    if remaining > 0:

                        time.sleep(
                            remaining
                        )


            # =================================================
            # REAL SENSOR
            # =================================================

            else:

                while (
                    time.time()
                    - start_time
                    < MEASUREMENT_SECONDS
                ):

                    (
                        left_values,
                        right_values
                    ) = read_both_feet()


                    for channel in range(12):

                        left_sums[channel] += (
                            left_values[channel]
                        )


                        right_sums[channel] += (
                            right_values[channel]
                        )


                    scan_count += 1


                    print(
                        f"[PRESSURE] "
                        f"Scan {scan_count:02d} | "
                        f"L Max "
                        f"{max(left_values):8.1f} | "
                        f"R Max "
                        f"{max(right_values):8.1f}"
                    )


            # =================================================
            # Measurement Validation
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

            left_corrected = apply_baseline(
                left_raw_average,
                LEFT_BASELINE
            )


            right_corrected = apply_baseline(
                right_raw_average,
                RIGHT_BASELINE
            )


            # =================================================
            # Relative
            # =================================================

            left_relative = calculate_relative(
                left_corrected
            )


            right_relative = calculate_relative(
                right_corrected
            )


            # =================================================
            # Round
            # =================================================

            left_raw_average = [

                round(
                    value,
                    1
                )

                for value
                in left_raw_average
            ]


            right_raw_average = [

                round(
                    value,
                    1
                )

                for value
                in right_raw_average
            ]


            left_corrected = [

                round(
                    value,
                    1
                )

                for value
                in left_corrected
            ]


            right_corrected = [

                round(
                    value,
                    1
                )

                for value
                in right_corrected
            ]


            left_relative = [

                round(
                    value,
                    1
                )

                for value
                in left_relative
            ]


            right_relative = [

                round(
                    value,
                    1
                )

                for value
                in right_relative
            ]


            # =================================================
            # Result Log
            # =================================================

            print()
            print("=" * 72)
            print("[PRESSURE RESULT]")
            print("=" * 72)


            print(
                "LEFT RAW       =",
                left_raw_average
            )


            print(
                "LEFT CORRECTED =",
                left_corrected
            )


            print(
                "LEFT RELATIVE  =",
                left_relative
            )


            print()


            print(
                "RIGHT RAW       =",
                right_raw_average
            )


            print(
                "RIGHT CORRECTED =",
                right_corrected
            )


            print(
                "RIGHT RELATIVE  =",
                right_relative
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
                f"{time.time() - start_time:.1f}s"
            )


            print("=" * 72)


            # =================================================
            # AI 전달값
            #
            # Relative가 아니라
            # Baseline 보정 후 Corrected 값 전달
            # =================================================

            return {

                "left":
                    left_corrected,

                "right":
                    right_corrected
            }


    except HardwareMeasurementError:

        raise


    except Exception as e:

        raise HardwareMeasurementError(
            reason="PRESSURE_SENSOR_ERROR",
            message=(
                "압력 측정에 실패했습니다. "
                "다시 시도해주세요."
            ),
            detail=str(e)
        )


    finally:

        # FastAPI에서 다음 세션에서도
        # GPIO를 사용해야 하므로 cleanup() 하지 않음.

        try:

            GPIO.output(
                EN_LEFT,
                GPIO.HIGH
            )

            GPIO.output(
                EN_RIGHT,
                GPIO.HIGH
            )

        except Exception:

            pass
