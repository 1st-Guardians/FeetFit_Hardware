import time
import board
import busio

from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1x15 import Pin


i2c = busio.I2C(board.SCL, board.SDA)

ads = ADS1115(i2c)

a0 = AnalogIn(ads, Pin.A0)
a1 = AnalogIn(ads, Pin.A1)

print("ADS1115 A0 / A1 ???")
print("??: Ctrl + C")

try:
    while True:

        print(
            f"A0 RAW: {a0.value:6d} | "
            f"A0 Voltage: {a0.voltage:.3f} V || "
            f"A1 RAW: {a1.value:6d} | "
            f"A1 Voltage: {a1.voltage:.3f} V"
        )

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\n??")
