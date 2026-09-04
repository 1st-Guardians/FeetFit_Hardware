import time
import RPi.GPIO as GPIO

EN_LEFT = 27
EN_RIGHT = 17

S0 = 22
S1 = 23
S2 = 24
S3 = 25

SELECT_PINS = [S0, S1, S2, S3]

GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

for pin in SELECT_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)

GPIO.setup(EN_LEFT, GPIO.OUT)
GPIO.setup(EN_RIGHT, GPIO.OUT)

# LEFT OFF / RIGHT ON
GPIO.output(EN_LEFT, GPIO.HIGH)
GPIO.output(EN_RIGHT, GPIO.LOW)


def select_channel(channel):
    for bit, pin in enumerate(SELECT_PINS):
        GPIO.output(pin, (channel >> bit) & 1)

    time.sleep(0.1)


try:
    while True:

        print("\n==============================")
        print("RIGHT C2 SELECTED")
        print("==============================")

        select_channel(2)

        input("Measure C2 and SIG. Press Enter for C3...")


        print("\n==============================")
        print("RIGHT C3 SELECTED")
        print("==============================")

        select_channel(3)

        input("Measure C3 and SIG. Press Enter for C2...")


except KeyboardInterrupt:
    print("\nSTOP")


finally:
    GPIO.output(EN_LEFT, GPIO.HIGH)
    GPIO.output(EN_RIGHT, GPIO.HIGH)
    GPIO.cleanup()
