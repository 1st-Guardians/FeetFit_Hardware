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

GPIO.setmode(GPIO.BCM)

for pin in [S0, S1, S2, S3]:
    GPIO.setup(pin, GPIO.OUT)

GPIO.setup(EN_LEFT, GPIO.OUT)


# =========================
# ?? MUX ???
# EN = LOW ? ON
# =========================

GPIO.output(EN_LEFT, GPIO.LOW)


# =========================
# ADS1115 ??
# =========================

i2c = busio.I2C(board.SCL, board.SDA)

ads = ADS.ADS1115(
    i2c,
    address=0x48
)

ads.gain = 1

# ?? MUX SIG ? ADS1115 A1
adc = AnalogIn(ads, Pin.A1)


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

    # ?? ?? ?? ? ??
    for _ in range(3):
        _ = adc.value
        time.sleep(0.005)

    values = []

    for _ in range(5):
        values.append(adc.value)
        time.sleep(0.005)

    return int(statistics.median(values))


# =========================
# ?? ??
# =========================

print("=" * 65)
print("LEFT FOOT FSR TEST")
print("ADS1115 : A1")
print("MUX EN  : GPIO27")
print("CHANNEL : C0 ~ C11")
print("??    : Ctrl + C")
print("=" * 65)


try:

    while True:

        results = []

        for ch in range(12):

            value = read_channel(ch)

            results.append(value)

        print()
        print("-" * 65)

        for ch, value in enumerate(results):

            print(
                f"C{ch:02d} : {value:6d}"
            )

        print("-" * 65)

        time.sleep(0.5)


except KeyboardInterrupt:

    print("\n?? ??")


finally:

    GPIO.output(EN_LEFT, GPIO.HIGH)

    GPIO.cleanup()
