import time
import RPi.GPIO as GPIO

EN_LEFT = 27
EN_RIGHT = 17

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO.setup(EN_LEFT, GPIO.OUT)
GPIO.setup(EN_RIGHT, GPIO.OUT)

# ? ? OFF
# CD74HC4067 EN = HIGH ? disabled
GPIO.output(EN_LEFT, GPIO.HIGH)
GPIO.output(EN_RIGHT, GPIO.HIGH)

print("Both MUX disabled")
print("Measure RIGHT MUX C2 with multimeter.")
print("Press and release C2.")
print("Ctrl+C to stop")

try:
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()
