import time
import smbus2
import bme280

# =========================
# BME280 설정
# =========================
I2C_PORT = 1
BME280_ADDRESS = 0x76

bus = smbus2.SMBus(I2C_PORT)

# 센서 보정값 로드
calibration_params = bme280.load_calibration_params(
    bus,
    BME280_ADDRESS
)

print("====================================")
print(" FeetFit BME280 온·습도 테스트")
print(" 종료: Ctrl + C")
print("====================================")

try:
    while True:
        data = bme280.sample(
            bus,
            BME280_ADDRESS,
            calibration_params
        )

        temperature = data.temperature
        humidity = data.humidity

        print(
            f"온도: {temperature:.2f} °C | "
            f"습도: {humidity:.2f} %"
        )

        time.sleep(1)

except KeyboardInterrupt:
    print("\n측정을 종료합니다.")

finally:
    bus.close()
