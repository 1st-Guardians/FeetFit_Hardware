import time

import board
import busio
import RPi.GPIO as GPIO

import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.ads1x15 import Pin
from adafruit_ads1x15.analog_in import AnalogIn


# =========================
# GPIO ??
# =========================

S0 = 22
S1 = 23
S2 = 24
S3 = 25

EN = 17       # ?? ????? MUX? EN
              # ??? MUX ??
              # ???? 27? ??

MUX_GND = None


GPIO.setmode(GPIO.BCM)

GPIO.setup(S0, GPIO.OUT)
GPIO.setup(S1, GPIO.OUT)
GPIO.setup(S2, GPIO.OUT)
GPIO.setup(S3, GPIO.OUT)

GPIO.setup(EN, GPIO.OUT)


# =========================
# MUX ???
# EN = LOW ? ???
# =========================

GPIO.output(EN, GPIO.LOW)


# =========================
# C11 ??
#
# C11 = binary 1011
#
# S3 S2 S1 S0
#  1  0  1  1
# =========================

GPIO.output(S0, GPIO.HIGH)
GPIO.output(S1, GPIO.HIGH)
GPIO.output(S2, GPIO.LOW)
GPIO.output(S3, GPIO.HIGH)


print("MUX C11 ?? ??")
print("S0 = HIGH")
print("S1 = HIGH")
print("S2 = LOW")
print("S3 = HIGH")
print("EN = LOW")


# =========================
# ADS1115
# =========================

i2c = busio.I2C(board.SCL, board.SDA)

ads = ADS.ADS1115(
    i2c,
    address=0x48
)

ads.gain = 1

# C11 ? MUX SIG ? ADS1115 A0
adc = AnalogIn(ads, Pin.A0)


# =========================
# ??
# =========================

try:

    while True:

        raw = adc.value
        voltage = adc.voltage

        print(
            f"A0 RAW: {raw:6d} | "
            f"Voltage: {voltage:.4f} V"
        )

        time.sleep(0.2)


except KeyboardInterrupt:

    print("\n?? ??")


finally:

    # MUX OFF
    GPIO.output(EN, GPIO.HIGH)

    GPIO.cleanup()

