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
# Final Baselines
# =========================================================

LEFT_BASELINE = [
    12.3, 174.3, 50.6, 23.1,
    23.4, 15.3, 17.2, 24.2,
    27.0, 33.4, 14.2, 10.0
]

RIGHT_BASELINE = [
    25.1, 26.4, 25.2, 20.1,
    20.6, 26.3, 29.5, 23.0,
    12.4, 16.6, 29.7, 153.6
]


# =========================================================
# Baseline Noise
# =========================================================

LEFT_NOISE_STD = [
    66.5, 70.2, 67.6, 71.4,
    69.2, 69.1, 70.0, 68.6,
    65.9, 66.5, 68.2, 73.5
]

RIGHT_NOISE_STD = [
    76.4, 80.2, 68.3, 74.4,
    77.9, 75.8, 73.6, 77.3,
    73.0, 70.5, 76.7, 83.4
]


# =========================================================
# Diagnostic Configuration
# =========================================================

LEFT_TEST_CHANNELS = [
    4, 5, 6, 9, 10, 11
]

RIGHT_TEST_CHANNELS = [
    4, 5, 6, 9, 10, 11
]

NO_LOAD_SECONDS = 3.0
FINGER_SECONDS = 3.0
LOAD_SECONDS = 3.0


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
# Read One Channel
# =========================================================

def read_channel(
    channel,
    enable_pin,
    other_enable_pin,
    adc
):

    # Keep opposite MUX disabled
    GPIO.output(
        other_enable_pin,
        GPIO.HIGH
    )

    # Disable target MUX before switching
    GPIO.output(
        enable_pin,
        GPIO.HIGH
    )

    time.sleep(
        MUX_DISCHARGE_TIME
    )

    set_mux_address(
        channel
    )

    # Enable target MUX
    GPIO.output(
        enable_pin,
        GPIO.LOW
    )

    time.sleep(
        MUX_SETTLE_TIME
    )

    # Discard initial ADC readings
    for _ in range(DISCARD_READS):

        _ = adc.value

        time.sleep(
            ADC_SETTLE_TIME
        )

    samples = []

    # Collect stable ADC readings
    for _ in range(VALID_READS):

        samples.append(
            adc.value
        )

        time.sleep(
            ADC_SETTLE_TIME
        )

    GPIO.output(
        enable_pin,
        GPIO.HIGH
    )

    return float(
        statistics.median(samples)
    )


# =========================================================
# Baseline Correction
# =========================================================

def correct_value(
    raw,
    baseline
):

    corrected = (
        raw - baseline
    )

    if corrected < 0:
        corrected = 0.0

    return corrected


# =========================================================
# Measure One Channel
# =========================================================

def measure_channel(
    channel,
    seconds,
    enable_pin,
    other_enable_pin,
    adc,
    baseline
):

    raw_values = []
    corrected_values = []

    start_time = time.time()

    while (
        time.time() - start_time
        < seconds
    ):

        raw = read_channel(
            channel,
            enable_pin,
            other_enable_pin,
            adc
        )

        corrected = correct_value(
            raw,
            baseline[channel]
        )

        raw_values.append(
            raw
        )

        corrected_values.append(
            corrected
        )

        print(
            f"C{channel:02d} | "
            f"RAW {raw:8.1f} | "
            f"Corrected {corrected:8.1f}"
        )

    return (
        raw_values,
        corrected_values
    )


# =========================================================
# Statistics
# =========================================================

def calculate_stats(values):

    if not values:

        return {
            "mean": 0.0,
            "median": 0.0,
            "min": 0.0,
            "max": 0.0,
            "std": 0.0
        }

    if len(values) > 1:

        std_value = statistics.stdev(
            values
        )

    else:

        std_value = 0.0

    return {
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "min": min(values),
        "max": max(values),
        "std": std_value
    }


# =========================================================
# Print Statistics
# =========================================================

def print_stats(
    title,
    stats
):

    print(
        f"{title:<15} | "
        f"Mean {stats['mean']:8.1f} | "
        f"Median {stats['median']:8.1f} | "
        f"Max {stats['max']:8.1f} | "
        f"Std {stats['std']:8.1f}"
    )


# =========================================================
# Diagnose One Channel
# =========================================================

def diagnose_channel(
    foot_name,
    channel,
    enable_pin,
    other_enable_pin,
    adc,
    baseline,
    noise_std,
    writer
):

    print()
    print("=" * 72)
    print(
        f"{foot_name} C{channel:02d} Diagnostic Test"
    )
    print("=" * 72)


    # =====================================================
    # Test 1: No Load
    # =====================================================

    print()
    print("TEST 1 - NO LOAD")
    print()

    input(
        "Remove all pressure and press Enter: "
    )

    print(
        f"Measuring for {NO_LOAD_SECONDS:.0f} seconds..."
    )

    _, no_load_values = measure_channel(
        channel,
        NO_LOAD_SECONDS,
        enable_pin,
        other_enable_pin,
        adc,
        baseline
    )

    no_load_stats = calculate_stats(
        no_load_values
    )


    # =====================================================
    # Test 2: Finger Press
    # =====================================================

    print()
    print("TEST 2 - FINGER PRESS")
    print()

    print(
        "Press the target pressure post strongly "
        "through the final assembled structure."
    )

    input(
        "Start pressing, then press Enter while holding pressure: "
    )

    print(
        f"Measuring for {FINGER_SECONDS:.0f} seconds..."
    )

    _, finger_values = measure_channel(
        channel,
        FINGER_SECONDS,
        enable_pin,
        other_enable_pin,
        adc,
        baseline
    )

    finger_stats = calculate_stats(
        finger_values
    )

    input(
        "Release the pressure, then press Enter: "
    )

    time.sleep(
        3.0
    )


    # =====================================================
    # Test 3: 2 kg Load
    # =====================================================

    print()
    print("TEST 3 - 2 KG LOAD")
    print()

    input(
        f"Place the 2 kg load at the center of C{channel:02d}, "
        "then press Enter: "
    )

    print(
        "Waiting 2 seconds for load settling..."
    )

    time.sleep(
        2.0
    )

    print(
        f"Measuring for {LOAD_SECONDS:.0f} seconds..."
    )

    _, load_values = measure_channel(
        channel,
        LOAD_SECONDS,
        enable_pin,
        other_enable_pin,
        adc,
        baseline
    )

    load_stats = calculate_stats(
        load_values
    )

    input(
        "Remove the load, then press Enter: "
    )

    time.sleep(
        5.0
    )


    # =====================================================
    # Diagnostic Summary
    # =====================================================

    three_sigma = (
        noise_std[channel]
        * 3.0
    )

    print()
    print("-" * 72)

    print(
        f"C{channel:02d} DIAGNOSTIC SUMMARY"
    )

    print("-" * 72)

    print_stats(
        "NO LOAD",
        no_load_stats
    )

    print_stats(
        "FINGER",
        finger_stats
    )

    print_stats(
        "2 KG",
        load_stats
    )

    print()

    print(
        f"3-sigma reference: "
        f"{three_sigma:.1f}"
    )

    print()

    finger_ratio = (
        finger_stats["mean"]
        / three_sigma
        if three_sigma > 0
        else 0.0
    )

    load_ratio = (
        load_stats["mean"]
        / three_sigma
        if three_sigma > 0
        else 0.0
    )

    print(
        f"Finger / 3-sigma: "
        f"{finger_ratio:.2f}"
    )

    print(
        f"2 kg / 3-sigma: "
        f"{load_ratio:.2f}"
    )


    # =====================================================
    # Simple Diagnostic Classification
    # =====================================================

    if (
        finger_ratio >= 3.0
        and load_ratio >= 3.0
    ):

        diagnosis = "SENSOR_RESPONDS_TO_BOTH"

    elif (
        finger_ratio >= 3.0
        and load_ratio < 3.0
    ):

        diagnosis = "LOAD_TRANSFER_OR_PLACEMENT_ISSUE"

    elif (
        finger_ratio < 3.0
        and load_ratio < 3.0
    ):

        diagnosis = "SENSOR_OR_CHANNEL_CHECK_REQUIRED"

    else:

        diagnosis = "INCONSISTENT_RESPONSE"


    print()

    print(
        f"Diagnostic flag: "
        f"{diagnosis}"
    )


    # =====================================================
    # Save CSV
    # =====================================================

    writer.writerow(
        [
            foot_name,
            channel,
            baseline[channel],
            three_sigma,

            no_load_stats["mean"],
            no_load_stats["median"],
            no_load_stats["max"],
            no_load_stats["std"],

            finger_stats["mean"],
            finger_stats["median"],
            finger_stats["max"],
            finger_stats["std"],

            load_stats["mean"],
            load_stats["median"],
            load_stats["max"],
            load_stats["std"],

            finger_ratio,
            load_ratio,

            diagnosis
        ]
    )


# =========================================================
# Main
# =========================================================

try:

    print("=" * 72)
    print("FeetFit FSR Channel Diagnostic")
    print("=" * 72)

    print()
    print("L = Left foot")
    print("R = Right foot")
    print()

    selection = input(
        "Select foot [L/R]: "
    ).strip().upper()


    if selection == "L":

        foot_name = "Left"

        enable_pin = EN_LEFT
        other_enable_pin = EN_RIGHT

        adc = left_adc

        baseline = LEFT_BASELINE
        noise_std = LEFT_NOISE_STD

        test_channels = LEFT_TEST_CHANNELS


    elif selection == "R":

        foot_name = "Right"

        enable_pin = EN_RIGHT
        other_enable_pin = EN_LEFT

        adc = right_adc

        baseline = RIGHT_BASELINE
        noise_std = RIGHT_NOISE_STD

        test_channels = RIGHT_TEST_CHANNELS


    else:

        raise ValueError(
            "Invalid foot selection."
        )


    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"fsr_channel_diagnostic_{selection}_{timestamp}.csv"
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
                "foot",
                "channel",
                "baseline",
                "noise_3sigma",

                "no_load_mean",
                "no_load_median",
                "no_load_max",
                "no_load_std",

                "finger_mean",
                "finger_median",
                "finger_max",
                "finger_std",

                "load_2kg_mean",
                "load_2kg_median",
                "load_2kg_max",
                "load_2kg_std",

                "finger_signal_to_3sigma",
                "load_signal_to_3sigma",

                "diagnostic_flag"
            ]
        )


        print()
        print(
            "Channels to test:"
        )

        print(
            ", ".join(
                f"C{channel:02d}"
                for channel in test_channels
            )
        )

        print()


        for channel in test_channels:

            diagnose_channel(
                foot_name,
                channel,
                enable_pin,
                other_enable_pin,
                adc,
                baseline,
                noise_std,
                writer
            )


    print()
    print("=" * 72)
    print("Diagnostic Test Completed")
    print("=" * 72)

    print()

    print(
        f"CSV saved: {filename}"
    )


except KeyboardInterrupt:

    print()
    print(
        "Diagnostic test stopped by user."
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
