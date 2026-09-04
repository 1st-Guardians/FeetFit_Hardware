import time
import statistics

from threading import Lock

import RPi.GPIO as GPIO
import board
import busio

import adafruit_ads1x15.ads1115 as ADS
import adafruit_ads1x15.ads1x15 as ADS1X15

from adafruit_ads1x15.analog_in import AnalogIn

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
# 무하중 상태에서 측정한 채널별 영점값
# =========================================================

LEFT_BASELINE = [
    12.3, 174.3, 50.6, 23.1,
    23.4, 15.3, 17.2, 24.2,
    27.0, 33.4, 14.2, 10.0
]

RIGHT_BASELINE = [
    25.1, 26.4, 25.2, 20.1,
    20.6, 26.3, 29.5, 23.0,
    12.4, 16.6, 29.7, 153.6
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
#
# 동시에 여러 압력 측정 요청이 들어오는 것을 방지
# =========================================================

pressure_lock = Lock()


# =========================================================
# GPIO Setup
# =========================================================

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

for pin in [S0, S1, S2, S3]:

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
# =========================================================

def read_channel(
    channel: int,
    enable_pin: int,
    other_enable_pin: int,
    adc: AnalogIn
) -> float:

    # -----------------------------------------------------
    # 1. 양쪽 MUX 비활성화
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # 2. 읽을 채널 선택
    # -----------------------------------------------------

    set_mux_address(
        channel
    )


    # -----------------------------------------------------
    # 3. 해당 발 MUX만 활성화
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # 4. 채널 전환 직후 ADC 값 버리기
    # -----------------------------------------------------

    for _ in range(
        DISCARD_READS
    ):

        _ = adc.value

        time.sleep(
            ADC_SETTLE_TIME
        )


    # -----------------------------------------------------
    # 5. 실제 사용할 ADC 값 수집
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # 6. MUX 비활성화
    # -----------------------------------------------------

    GPIO.output(
        enable_pin,
        GPIO.HIGH
    )


    # -----------------------------------------------------
    # 7. 중앙값 사용
    # -----------------------------------------------------

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

        # 왼발
        left_value = read_channel(
            channel,
            EN_LEFT,
            EN_RIGHT,
            left_adc
        )


        # 오른발
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
# 0보다 작으면 0으로 처리
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
# AI에는 보내지 않음.
# 디버깅/확인용으로만 계산.
# =========================================================

def calculate_relative(
    corrected_values: list
) -> list:

    max_value = max(
        corrected_values
    )


    if max_value <= 0:

        return [0.0] * 12


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
# Router에서 호출하는 실제 함수
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
            print("=" * 72)


            # -------------------------------------------------
            # 각 채널 RAW 누적값
            # -------------------------------------------------

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


            # -------------------------------------------------
            # 지정 시간 동안 반복 측정
            # -------------------------------------------------

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


            # -------------------------------------------------
            # 측정 실패 방어
            # -------------------------------------------------

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
            # ★ 영점 보정
            # =================================================

            left_corrected = (
                apply_baseline(
                    left_raw_average,
                    LEFT_BASELINE
                )
            )


            right_corrected = (
                apply_baseline(
                    right_raw_average,
                    RIGHT_BASELINE
                )
            )


            # =================================================
            # Relative
            #
            # 디버깅 확인용이며
            # AI에는 전달하지 않음
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
            # 소수점 한 자리 정리
            # =================================================

            left_raw_average = [
                round(value, 1)
                for value
                in left_raw_average
            ]

            right_raw_average = [
                round(value, 1)
                for value
                in right_raw_average
            ]

            left_corrected = [
                round(value, 1)
                for value
                in left_corrected
            ]

            right_corrected = [
                round(value, 1)
                for value
                in right_corrected
            ]

            left_relative = [
                round(value, 1)
                for value
                in left_relative
            ]

            right_relative = [
                round(value, 1)
                for value
                in right_relative
            ]


            # =================================================
            # 결과 로그
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

            print("=" * 72)


            # =================================================
            # ★ AI에 전달할 값
            #
            # CORRECTED 값을 left/right로 반환
            # =================================================

            return {

                "left":
                    left_corrected,

                "right":
                    right_corrected
            }


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

        # -------------------------------------------------
        # FastAPI는 다음 측정 세션에서도 GPIO를 사용해야 하므로
        # GPIO.cleanup()은 여기서 호출하지 않음.
        #
        # MUX만 안전하게 비활성화.
        # -------------------------------------------------

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
