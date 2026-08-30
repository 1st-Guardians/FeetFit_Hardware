import csv
import time
import statistics
from datetime import datetime

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
# Test Configuration
# =========================================================

TARGET_CHANNEL = 5

TRIALS = 5

LOAD_SETTLE_SECONDS = 2.0
MEASUREMENT_SECONDS = 3.0
RECOVERY_SECONDS = 5.0


# =========================================================
# Left Foot Baseline
# =========================================================

LEFT_BASELINE = [
    12.3, 174.3, 50.6, 23.1,
    23.4, 15.3, 17.2, 24.2,
    27.0, 33.4, 14.2, 10.0
]

LEFT_NOISE_STD = [
    66.5, 70.2, 67.6, 71.4,
    69.2, 69.1, 70.0, 68.6,
    65.9, 66.5, 68.2, 73.5
]


# =========================================================
# ADC / MUX Configuration
# =========================================================

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

left_adc = AnalogIn(
    ads,
    ADS1X15.Pin.A0
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
# Read C5
# =========================================================

def read_left_channel(channel):

    # Keep right MUX disabled
    GPIO.output(
        EN_RIGHT,
        GPIO.HIGH
    )

    # Disable left MUX
    GPIO.output(
        EN_LEFT,
        GPIO.HIGH
    )

    time.sleep(
        MUX_DISCHARGE_TIME
    )

    set_mux_address(
        channel
    )

    # Enable left MUX
    GPIO.output(
        EN_LEFT,
        GPIO.LOW
    )

    time.sleep(
        MUX_SETTLE_TIME
    )

    # Discard initial readings
    for _ in range(DISCARD_READS):

        _ = left_adc.value

        time.sleep(
            ADC_SETTLE_TIME
        )

    samples = []

    # Collect valid readings
    for _ in range(VALID_READS):

        samples.append(
            left_adc.value
        )

        time.sleep(
            ADC_SETTLE_TIME
        )

    GPIO.output(
        EN_LEFT,
        GPIO.HIGH
    )

    return float(
        statistics.median(samples)
    )


# =========================================================
# Baseline Correction
# =========================================================

def correct_value(raw):

    corrected = (
        raw
        - LEFT_BASELINE[TARGET_CHANNEL]
    )

    if corrected < 0:
        corrected = 0.0

    return corrected


# =========================================================
# Measure One Trial
# =========================================================

def measure_trial():

    raw_values = []
    corrected_values = []

    start_time = time.time()

    while (
        time.time() - start_time
        < MEASUREMENT_SECONDS
    ):

        raw = read_left_channel(
            TARGET_CHANNEL
        )

        corrected = correct_value(
            raw
        )

        raw_values.append(
            raw
        )

        corrected_values.append(
            corrected
        )

        print(
            f"C05 | "
            f"RAW {raw:8.1f} | "
            f"Corrected {corrected:8.1f}"
        )

    raw_average = statistics.mean(
        raw_values
    )

    corrected_average = statistics.mean(
        corrected_values
    )

    return (
        raw_average,
        corrected_average,
        len(corrected_values)
    )


# =========================================================
# Main
# =========================================================

try:

    print("=" * 72)
    print("FeetFit Left C05 2 kg Reposition Test")
    print("=" * 72)

    print()
    print(
        "Use the same 2 kg load and the same loading cap."
    )

    print(
        "Completely remove and reposition the load for every trial."
    )

    print(
        "Keep the loading cap centered over the C05 pressure post."
    )

    print()

    trial_results = []

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"c05_2kg_reposition_{timestamp}.csv"
    )


    with open(
        filename,
        "w",
        newline=""
    ) as csv_file:

        writer = csv.writer(
            csv_file
        )

        writer.writerow(
            [
                "trial",
                "raw_average",
                "corrected_average",
                "sample_count"
            ]
        )


        for trial in range(
            1,
            TRIALS + 1
        ):

            print()
            print("=" * 72)

            print(
                f"Trial {trial}/{TRIALS}"
            )

            print("=" * 72)

            print()

            input(
                "Place the 2 kg load on C05, then press Enter: "
            )

            print(
                f"Waiting {LOAD_SETTLE_SECONDS:.0f} seconds "
                "for load settling..."
            )

            time.sleep(
                LOAD_SETTLE_SECONDS
            )

            print(
                f"Measuring for {MEASUREMENT_SECONDS:.0f} seconds..."
            )

            print()

            (
                raw_average,
                corrected_average,
                sample_count
            ) = measure_trial()

            trial_results.append(
                corrected_average
            )

            print()

            print(
                f"Trial {trial} RAW Average: "
                f"{raw_average:.1f}"
            )

            print(
                f"Trial {trial} Corrected Average: "
                f"{corrected_average:.1f}"
            )

            print(
                f"Sample count: "
                f"{sample_count}"
            )

            writer.writerow(
                [
                    trial,
                    raw_average,
                    corrected_average,
                    sample_count
                ]
            )

            print()

            input(
                "Remove the load completely, then press Enter: "
            )

            print(
                f"Waiting {RECOVERY_SECONDS:.0f} seconds "
                "for sensor recovery..."
            )

            time.sleep(
                RECOVERY_SECONDS
            )


    # =====================================================
    # Final Statistics
    # =====================================================

    mean_response = statistics.mean(
        trial_results
    )

    median_response = statistics.median(
        trial_results
    )

    std_response = statistics.stdev(
        trial_results
    )

    if mean_response > 0:

        cv_percent = (
            std_response
            / mean_response
            * 100.0
        )

    else:

        cv_percent = 0.0


    three_sigma = (
        LEFT_NOISE_STD[TARGET_CHANNEL]
        * 3.0
    )

    if three_sigma > 0:

        signal_ratio = (
            mean_response
            / three_sigma
        )

    else:

        signal_ratio = 0.0


    print()
    print("=" * 72)
    print("FINAL RESULT")
    print("=" * 72)

    print()

    print(
        "Trial responses: "
        + ", ".join(
            f"{value:.1f}"
            for value in trial_results
        )
    )

    print()

    print(
        f"Mean: "
        f"{mean_response:.1f}"
    )

    print(
        f"Median: "
        f"{median_response:.1f}"
    )

    print(
        f"Standard deviation: "
        f"{std_response:.1f}"
    )

    print(
        f"CV: "
        f"{cv_percent:.1f}%"
    )

    print()

    print(
        f"C05 3-sigma reference: "
        f"{three_sigma:.1f}"
    )

    print(
        f"Signal / 3-sigma: "
        f"{signal_ratio:.2f}"
    )

    print()

    print(
        f"CSV saved: "
        f"{filename}"
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
