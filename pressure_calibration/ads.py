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
a2 = AnalogIn(ads, Pin.A2)
a3 = AnalogIn(ads, Pin.A3)

print("ADS1115 A0~A3 TEST")
print("Ctrl+C to stop")

try:
    while True:
        v0 = a0.voltage
        v1 = a1.voltage
        v2 = a2.voltage
        v3 = a3.voltage

        print(
            f"A0: {v0:.4f} V | "
            f"A1: {v1:.4f} V | "
            f"A2: {v2:.4f} V | "
            f"A3: {v3:.4f} V"
        )

        time.sleep(0.5)

except KeyboardInterrupt:
    print("\nStop")
