import math
import time

import bme280
import smbus2

from config import (
    BME280_I2C_BUS,
    BME280_I2C_ADDRESS,
    BME280_SAMPLE_COUNT,
    BME280_SAMPLE_INTERVAL_SECONDS,
)

from errors import HardwareMeasurementError


# =========================================================
# 온습도 데이터 검증
# =========================================================

def validate_environment_measurement(
    temperature: float,
    humidity: float
):
    # -----------------------------------------------------
    # 숫자 여부
    # -----------------------------------------------------

    try:
        temperature = float(
            temperature
        )

        humidity = float(
            humidity
        )

    except (TypeError, ValueError):

        raise HardwareMeasurementError(
            reason="ENVIRONMENT_SENSOR_ERROR",

            message=(
                "온습도 측정에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                "BME280에서 읽은 온습도 값이 "
                "숫자가 아닙니다."
            )
        )


    # -----------------------------------------------------
    # NaN / Infinity 검사
    # -----------------------------------------------------

    if not math.isfinite(
        temperature
    ):

        raise HardwareMeasurementError(
            reason="ENVIRONMENT_SENSOR_ERROR",

            message=(
                "온습도 측정에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                "BME280 온도값이 "
                "유효하지 않습니다."
            )
        )


    if not math.isfinite(
        humidity
    ):

        raise HardwareMeasurementError(
            reason="ENVIRONMENT_SENSOR_ERROR",

            message=(
                "온습도 측정에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                "BME280 습도값이 "
                "유효하지 않습니다."
            )
        )


    # -----------------------------------------------------
    # 습도 범위 검증
    # -----------------------------------------------------

    if not (
        0.0
        <= humidity
        <= 100.0
    ):

        raise HardwareMeasurementError(
            reason="ENVIRONMENT_SENSOR_ERROR",

            message=(
                "온습도 측정에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                "BME280 습도값이 "
                "0~100% 범위를 벗어났습니다. "
                f"humidity={humidity}"
            )
        )


    # -----------------------------------------------------
    # 온도 범위 검증
    #
    # FeetFit 실내 장비이므로 비정상적인 값만 차단
    # -----------------------------------------------------

    if not (
        -20.0
        <= temperature
        <= 80.0
    ):

        raise HardwareMeasurementError(
            reason="ENVIRONMENT_SENSOR_ERROR",

            message=(
                "온습도 측정에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                "BME280 온도값이 "
                "정상 측정 범위를 벗어났습니다. "
                f"temperature={temperature}"
            )
        )


# =========================================================
# 실제 BME280 온습도 측정
#
# PDF 기준
#
# I2C BUS     : 1
# I2C ADDRESS : 0x76
# SDA         : GPIO2 / Physical Pin 3
# SCL         : GPIO3 / Physical Pin 5
# =========================================================

def measure_environment() -> dict:

    print()
    print(
        "========================================"
    )

    print(
        "[ENVIRONMENT] BME280 측정 시작"
    )

    print(
        f"[I2C BUS] {BME280_I2C_BUS}"
    )

    print(
        f"[I2C ADDRESS] "
        f"0x{BME280_I2C_ADDRESS:02X}"
    )

    print(
        "========================================"
    )


    bus = None


    try:

        # -------------------------------------------------
        # I2C BUS OPEN
        # -------------------------------------------------

        bus = smbus2.SMBus(
            BME280_I2C_BUS
        )


        # -------------------------------------------------
        # BME280 calibration data
        # -------------------------------------------------

        calibration_params = (
            bme280.load_calibration_params(
                bus,
                BME280_I2C_ADDRESS
            )
        )


        temperatures = []
        humidities = []


        # -------------------------------------------------
        # 여러 번 측정 후 평균
        #
        # 순간 노이즈를 줄이기 위해
        # 기본 5회 측정
        # -------------------------------------------------

        for index in range(
            BME280_SAMPLE_COUNT
        ):

            data = bme280.sample(
                bus,
                BME280_I2C_ADDRESS,
                calibration_params
            )


            temperature = float(
                data.temperature
            )

            humidity = float(
                data.humidity
            )


            validate_environment_measurement(
                temperature,
                humidity
            )


            temperatures.append(
                temperature
            )

            humidities.append(
                humidity
            )


            print(
                f"[BME280 SAMPLE "
                f"{index + 1}/"
                f"{BME280_SAMPLE_COUNT}] "
                f"Temperature="
                f"{temperature:.2f}°C, "
                f"Humidity="
                f"{humidity:.2f}%"
            )


            if (
                index
                < BME280_SAMPLE_COUNT - 1
            ):

                time.sleep(
                    BME280_SAMPLE_INTERVAL_SECONDS
                )


        # -------------------------------------------------
        # 평균
        # -------------------------------------------------

        average_temperature = (
            sum(
                temperatures
            )
            / len(
                temperatures
            )
        )


        average_humidity = (
            sum(
                humidities
            )
            / len(
                humidities
            )
        )


        # -------------------------------------------------
        # 최종 검증
        # -------------------------------------------------

        validate_environment_measurement(
            average_temperature,
            average_humidity
        )


        # -------------------------------------------------
        # 소수점 한 자리
        #
        # AI API 형식:
        # 28.1
        # 52.0
        # -------------------------------------------------

        average_temperature = round(
            average_temperature,
            1
        )

        average_humidity = round(
            average_humidity,
            1
        )


        print()
        print(
            "========================================"
        )

        print(
            "[ENVIRONMENT RESULT]"
        )

        print(
            f"Temperature : "
            f"{average_temperature} °C"
        )

        print(
            f"Humidity    : "
            f"{average_humidity} %"
        )

        print(
            "========================================"
        )


        return {
            "temperature":
                average_temperature,

            "humidity":
                average_humidity
        }


    # =====================================================
    # 우리가 직접 발생시킨 센서 오류
    # =====================================================

    except HardwareMeasurementError:

        raise


    # =====================================================
    # I2C / BME280 실제 오류
    # =====================================================

    except OSError as e:

        raise HardwareMeasurementError(
            reason="ENVIRONMENT_SENSOR_ERROR",

            message=(
                "온습도 측정에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                "BME280 I2C 통신에 "
                "실패했습니다. "
                f"bus={BME280_I2C_BUS}, "
                f"address="
                f"0x{BME280_I2C_ADDRESS:02X}, "
                f"error={e}"
            )
        )


    except Exception as e:

        raise HardwareMeasurementError(
            reason="ENVIRONMENT_SENSOR_ERROR",

            message=(
                "온습도 측정에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                "BME280 온습도 측정 중 "
                f"오류가 발생했습니다: {e}"
            )
        )


    # =====================================================
    # I2C BUS CLOSE
    # =====================================================

    finally:

        if bus is not None:

            try:

                bus.close()

            except Exception:

                pass
