import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

GPIO27 = 27
GPIO17 = 17

GPIO.setup(GPIO27, GPIO.OUT)
GPIO.setup(GPIO17, GPIO.OUT)

try:
    while True:

        print("\nSTATE 1")
        print("GPIO27 = LOW")
        print("GPIO17 = HIGH")

        GPIO.output(GPIO27, GPIO.LOW)
        GPIO.output(GPIO17, GPIO.HIGH)

        time.sleep(5)


        print("\nSTATE 2")
        print("GPIO27 = HIGH")
        print("GPIO17 = LOW")

        GPIO.output(GPIO27, GPIO.HIGH)
        GPIO.output(GPIO17, GPIO.LOW)

        time.sleep(5)

except KeyboardInterrupt:
    pass

finally:
    GPIO.cleanup()
