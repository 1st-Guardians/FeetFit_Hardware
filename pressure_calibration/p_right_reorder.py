import time
import statistics

import RPi.GPIO as GPIO
import board
import busio

import adafruit_ads1x15.ads1115 as ADS
import adafruit_ads1x15.ads1x15 as ADS1X15
from adafruit_ads1x15.analog_in import AnalogIn


# =========================================================
# GPIO Configuration
# =========================================================

S0 = 22
S1 = 23
S2 = 24
S3 = 25

EN_LEFT = 17
EN_RIGHT = 27


# =========================================================
# Right Foot Baseline
# =========================================================

RIGHT_BASELINE = [
    25.1, 26.4, 25.2, 20.1,
    20.6, 26.3, 29.5, 23.0,
    12.4, 16.6, 29.7, 153.6
]

RIGHT_NOISE_STD = [
    76.4, 80.2, 68.3, 74.4,
    77.9, 75.8, 73.6, 77.3,
    73.0, 70.5, 76.7, 83.4
]


# =========================================================
# Measurement Configuration
# =========================================================

TEST_SECONDS = 10.0

MUX_DISCHARGE_TIME = 0.010
MUX_SETTLE_TIME = 0.010
ADC_SETTLE_TIME = 0.003

DISCARD_READS = 3
VALID_READS = 3


# =========================================================
# GPIO Setup
# =========================================================

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

for pin in [S0, S1, S2, S3]:
    GPIO.setup(
        pin,
        GPIO.OUT,
        initial=GPIO.LOW
    )

GPIO.setup(
    EN_LEFT,
    GPIO.OUT,
    initial=GPIO.HIGH
)

GPIO.setup(
    EN_RIGHT,
    GPIO.OUT,
    initial=GPIO.HIGH
)


# =========================================================
# ADS1115 Setup
# =========================================================

i2c = busio.I2C(
    board.SCL,
    board.SDA
)

ads = ADS.ADS1115(
    i2c,
    address=0x48
)

ads.gain = 1
ads.data_rate = 860

right_adc = AnalogIn(
    ads,
    ADS1X15.Pin.A1
)

# =========================================================
# Set MUX Address
# =========================================================

def set_mux_address(channel):

    GPIO.output(
        S0,
        (channel >> 0) & 1
    )

    GPIO.output(
        S1,
        (channel >> 1) & 1
    )

    GPIO.output(
        S2,
        (channel >> 2) & 1
    )

    GPIO.output(
        S3,
        (channel >> 3) & 1
    )


# =========================================================
# Read One Right Channel
# =========================================================

def read_right_channel(channel):

    # Keep left MUX disabled
    GPIO.output(
        EN_LEFT,
        GPIO.HIGH
    )

    # Disable right MUX before switching
    GPIO.output(
        EN_RIGHT,
        GPIO.HIGH
    )

    time.sleep(
        MUX_DISCHARGE_TIME
    )

    set_mux_address(
        channel
    )

    # Enable right MUX
    GPIO.output(
        EN_RIGHT,
        GPIO.LOW
    )

    time.sleep(
        MUX_SETTLE_TIME
    )

    # Discard initial ADC readings
    for _ in range(DISCARD_READS):

        _ = right_adc.value

        time.sleep(
            ADC_SETTLE_TIME
        )

    # Collect stable readings
    samples = []

    for _ in range(VALID_READS):

        samples.append(
            right_adc.value
        )

        time.sleep(
            ADC_SETTLE_TIME
        )

    GPIO.output(
        EN_RIGHT,
        GPIO.HIGH
    )

    return float(
        statistics.median(samples)
    )


# =========================================================
# Baseline Correction
# =========================================================

def correct_value(channel, raw):

    corrected = (
        raw
        - RIGHT_BASELINE[channel]
    )

    if corrected < 0:
        corrected = 0.0

    return corrected


# =========================================================
# Reordered Scan
# =========================================================

def scan_reordered():

    # C11 -> C1 occurs between scans
    # C1 -> C0 occurs inside the scan
    order = [
        1, 0, 2, 3, 4, 5,
        6, 7, 8, 9, 10, 11
    ]

    result = {}

    for channel in order:

        raw = read_right_channel(
            channel
        )

        corrected = correct_value(
            channel,
            raw
        )

        result[channel] = (
            raw,
            corrected
        )

    return result
# =========================================================
# Main
# =========================================================

try:

    print("=" * 72)
    print("FeetFit Right Foot Reordered Carryover Test")
    print("=" * 72)

    print()
    print("Scan order:")
    print("C1 -> C0 -> C2 -> C3 -> ... -> C11")
    print()
    print("Between scans:")
    print("C11 -> C1 -> C0")
    print()

    print(
        "The purpose of this test is to check "
        "whether C11 leaks into C1."
    )

    print()

    input(
        "Press and hold RIGHT C11 strongly, then press Enter: "
    )

    print()
    print(
        f"Measuring for {TEST_SECONDS:.0f} seconds..."
    )

    print()

    c0_values = []
    c1_values = []
    c11_values = []

    scan_count = 0

    start_time = time.time()

    while (
        time.time() - start_time
        < TEST_SECONDS
    ):

        result = scan_reordered()

        scan_count += 1

        c0 = result[0][1]
        c1 = result[1][1]
        c11 = result[11][1]

        print(
            f"Scan {scan_count:02d} | "
            f"C00 {c0:8.1f} | "
            f"C01 {c1:8.1f} | "
            f"C11 {c11:8.1f}"
        )

        # Ignore the first scan
        if scan_count > 1:

            c0_values.append(
                c0
            )

            c1_values.append(
                c1
            )

            c11_values.append(
                c11
            )


    print()
    print("=" * 72)
    print("RESULT")
    print("=" * 72)

    print()

    if c0_values:

        print(
            f"C00 Average: "
            f"{statistics.mean(c0_values):.1f}"
        )

        print(
            f"C00 Median: "
            f"{statistics.median(c0_values):.1f}"
        )

        print(
            f"C00 Max: "
            f"{max(c0_values):.1f}"
        )

    print()

    if c1_values:

        print(
            f"C01 Average: "
            f"{statistics.mean(c1_values):.1f}"
        )

        print(
            f"C01 Median: "
            f"{statistics.median(c1_values):.1f}"
        )

        print(
            f"C01 Max: "
            f"{max(c1_values):.1f}"
        )

    print()

    if c11_values:

        print(
            f"C11 Average: "
            f"{statistics.mean(c11_values):.1f}"
        )

        print(
            f"C11 Median: "
            f"{statistics.median(c11_values):.1f}"
        )

        print(
            f"C11 Max: "
            f"{max(c11_values):.1f}"
        )

    print()
    print("-" * 72)

    print(
        f"C00 3-sigma reference: "
        f"{RIGHT_NOISE_STD[0] * 3:.1f}"
    )

    print(
        f"C01 3-sigma reference: "
        f"{RIGHT_NOISE_STD[1] * 3:.1f}"
    )

    print()

    print(
        "Keep C11 pressed until the measurement is completely finished."
    )


except KeyboardInterrupt:

    print()
    print(
        "Test stopped by user."
    )


finally:

    GPIO.output(
        EN_LEFT,
        GPIO.HIGH
    )

    GPIO.output(
        EN_RIGHT,
        GPIO.HIGH
    )

    GPIO.cleanup()
