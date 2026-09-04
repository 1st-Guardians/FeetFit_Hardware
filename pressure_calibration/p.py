import time
import board
import busio
import RPi.GPIO as GPIO

from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1x15 import Pin


# =========================
# GPIO
# =========================
EN_LEFT = 27
EN_RIGHT = 17

S0 = 22
S1 = 23
S2 = 24
S3 = 25

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in [S0, S1, S2, S3]:
    GPIO.setup(pin, GPIO.OUT)

GPIO.setup(EN_LEFT, GPIO.OUT)
GPIO.setup(EN_RIGHT, GPIO.OUT)


# =========================
# ?? MUX ON / ??? OFF
# =========================
GPIO.output(EN_LEFT, GPIO.LOW)
GPIO.output(EN_RIGHT, GPIO.HIGH)


# =========================
# C1 ??
# S3 S2 S1 S0 = 0001
# =========================
GPIO.output(S0, GPIO.HIGH)
GPIO.output(S1, GPIO.LOW)
GPIO.output(S2, GPIO.LOW)
GPIO.output(S3, GPIO.LOW)


# =========================
# ADS1115
# =========================
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS1115(i2c)

a0 = AnalogIn(ads, Pin.A0)
a1 = AnalogIn(ads, Pin.A1)


print("=" * 55)
print("LEFT C1 -> ADS A0/A1 MAPPING TEST")
print("?? C1? ??? ??? ?????.")
print("Ctrl+C to stop")
print("=" * 55)


try:
    while True:

        v0 = a0.voltage
        v1 = a1.voltage

        print(
            f"A0 = {v0:.4f} V   |   "
            f"A1 = {v1:.4f} V"
        )

        time.sleep(0.2)

except KeyboardInterrupt:
    print("\nSTOP")

finally:
    GPIO.output(EN_LEFT, GPIO.HIGH)
    GPIO.output(EN_RIGHT, GPIO.HIGH)
    GPIO.cleanup()
