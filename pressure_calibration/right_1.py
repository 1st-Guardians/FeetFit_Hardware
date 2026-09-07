import time
import statistics

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

EN_LEFT = 27
EN_RIGHT = 17

S_PINS = [S0, S1, S2, S3]

GPIO.setmode(GPIO.BCM)

for pin in S_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

GPIO.setup(EN_LEFT, GPIO.OUT)
GPIO.setup(EN_RIGHT, GPIO.OUT)


# =========================
# ??? MUX ???
# EN Active LOW
# =========================

GPIO.output(EN_LEFT, GPIO.HIGH)     # ?? OFF
GPIO.output(EN_RIGHT, GPIO.LOW)     # ??? ON


# =========================
# ADS1115
# =========================

i2c = busio.I2C(board.SCL, board.SDA)

ads = ADS.ADS1115(
    i2c,
    address=0x48
)

ads.gain = 1

adc = AnalogIn(ads, Pin.A0)


# =========================
# MUX ?? ??
# =========================

def select_channel(channel):

    GPIO.output(S0, (channel >> 0) & 1)
    GPIO.output(S1, (channel >> 1) & 1)
    GPIO.output(S2, (channel >> 2) & 1)
    GPIO.output(S3, (channel >> 3) & 1)

    time.sleep(0.01)



# =========================
# ?? ??
# =========================

def read_channel(channel):

    select_channel(channel)

    # ? ? ??
    for _ in range(3):
        _ = adc.value
        time.sleep(0.005)

    values = []

    for _ in range(5):
        values.append(adc.value)
        time.sleep(0.005)

    return int(statistics.median(values))


# =========================
# ???? ??
# =========================

channels = [1, 2, 4, 6, 8, 9, 10]


print("="*60)
print("RIGHT FOOT SENSOR TEST")
print("CHANNEL : C2 C4 C6 C8 C9 C10")
print("?? : Ctrl + C")
print("="*60)


try:

    while True:

        print()

        for ch in channels:

            value = read_channel(ch)

            print(f"C{ch:02d} : {value}")

        print("-"*60)

        time.sleep(0.5)


except KeyboardInterrupt:

    print("??")


finally:

    GPIO.output(EN_RIGHT, GPIO.HIGH)
    GPIO.output(EN_LEFT, GPIO.HIGH)

    GPIO.cleanup()
