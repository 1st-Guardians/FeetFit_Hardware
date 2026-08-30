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
# Screening Configuration
# =========================================================

# Change this value if the actual measured mass is different
CALIBRATION_MASS_G = 2000.0

# Channels that showed weak or unstable response at 1 kg
SCREENING_CHANNELS = [
    3, 4, 5, 6,
    8, 9, 10, 11
]

PRECONDITION_CYCLES = 3
TRIALS_PER_CHANNEL = 3

LOAD_SETTLE_SECONDS = 2.0
MEASUREMENT_SECONDS = 3.0
RECOVERY_SECONDS = 5.0


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

    # Enable selected MUX
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

    # Collect stable readings
    samples = []

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
# Read Full Foot Scan
# =========================================================

def read_full_scan(
    enable_pin,
    other_enable_pin,
    adc
):

    values = []

    for channel in range(12):

        values.append(
            read_channel(
                channel,
                enable_pin,
                other_enable_pin,
                adc
            )
        )

    return values


# =========================================================
# Measure Average
# =========================================================

def measure_average(
    seconds,
    enable_pin,
    other_enable_pin,
    adc
):

    sums = [0.0] * 12
    scan_count = 0

    start_time = time.time()

    while (
        time.time() - start_time
        < seconds
    ):

        values = read_full_scan(
            enable_pin,
            other_enable_pin,
            adc
        )

        for channel in range(12):
            sums[channel] += values[channel]

        scan_count += 1

    averages = [
        value / scan_count
        for value in sums
    ]

    return averages, scan_count


# =========================================================
# Baseline Correction
# =========================================================

def apply_baseline(
    raw_values,
    baseline
):

    corrected = []

    for channel in range(12):

        value = (
            raw_values[channel]
            - baseline[channel]
        )

        corrected.append(
            max(value, 0.0)
        )

    return corrected


# =========================================================
# Find Strongest Other Channel
# =========================================================

def find_strongest_other(
    corrected,
    target_channel
):

    candidates = [
        (corrected[channel], channel)
        for channel in range(12)
        if channel != target_channel
    ]

    value, channel = max(
        candidates
    )

    return channel, value


# =========================================================
# Preconditioning
# =========================================================

def precondition(
    target_channel
):

    print()
    print(
        f"Preconditioning C{target_channel:02d}"
    )

    for cycle in range(
        1,
        PRECONDITION_CYCLES + 1
    ):

        print()
        print(
            f"Preconditioning "
            f"{cycle}/{PRECONDITION_CYCLES}"
        )

        input(
            f"Place the 2 kg load on C{target_channel:02d}, "
            "then press Enter: "
        )

        time.sleep(
            LOAD_SETTLE_SECONDS
        )

        input(
            "Remove the load, then press Enter: "
        )

        print(
            f"Waiting {RECOVERY_SECONDS:.0f} seconds "
            "for recovery..."
        )

        time.sleep(
            RECOVERY_SECONDS
        )


# =========================================================
# Screening One Foot
# =========================================================

def run_screening(
    foot_name,
    enable_pin,
    other_enable_pin,
    adc,
    baseline,
    noise_std,
    writer
):

    all_results = []

    print()
    print("=" * 72)
    print(
        f"{foot_name} Foot 2 kg Screening"
    )
    print("=" * 72)

    for target_channel in SCREENING_CHANNELS:

        print()
        print("=" * 72)
        print(
            f"{foot_name} C{target_channel:02d}"
        )
        print("=" * 72)

        precondition(
            target_channel
        )

        trial_values = []


        # =================================================
        # Recorded Trials
        # =================================================

        for trial in range(
            1,
            TRIALS_PER_CHANNEL + 1
        ):

            print()
            print(
                f"Trial {trial}/{TRIALS_PER_CHANNEL}"
            )

            input(
                f"Place the 2 kg load at the center of "
                f"C{target_channel:02d}, then press Enter: "
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

            raw_average, scan_count = measure_average(
                MEASUREMENT_SECONDS,
                enable_pin,
                other_enable_pin,
                adc
            )

            corrected = apply_baseline(
                raw_average,
                baseline
            )

            target_raw = (
                raw_average[target_channel]
            )

            target_corrected = (
                corrected[target_channel]
            )

            trial_values.append(
                target_corrected
            )

            (
                strongest_other_channel,
                strongest_other_value
            ) = find_strongest_other(
                corrected,
                target_channel
            )

            print()
            print(
                f"C{target_channel:02d} RAW Average: "
                f"{target_raw:.1f}"
            )

            print(
                f"C{target_channel:02d} Corrected: "
                f"{target_corrected:.1f}"
            )

            print(
                f"Scan count: {scan_count}"
            )

            print(
                f"Strongest other channel: "
                f"C{strongest_other_channel:02d} "
                f"({strongest_other_value:.1f})"
            )

            input(
                "Remove the load, then press Enter: "
            )

            print(
                f"Waiting {RECOVERY_SECONDS:.0f} seconds "
                "for recovery..."
            )

            time.sleep(
                RECOVERY_SECONDS
            )


        # =================================================
        # Statistics
        # =================================================

        mean_response = statistics.mean(
            trial_values
        )

        median_response = statistics.median(
            trial_values
        )

        std_response = statistics.stdev(
            trial_values
        )

        if mean_response > 0:

            cv_percent = (
                std_response
                / mean_response
                * 100.0
            )

        else:

            cv_percent = float("inf")


        noise_3sigma = (
            noise_std[target_channel]
            * 3.0
        )

        if noise_3sigma > 0:

            signal_to_3sigma = (
                mean_response
                / noise_3sigma
            )

        else:

            signal_to_3sigma = 0.0


        # =================================================
        # Diagnostic Screening Flag
        # =================================================

        strong_signal = (
            signal_to_3sigma >= 3.0
        )

        stable_repeatability = (
            cv_percent <= 20.0
        )

        if (
            strong_signal
            and stable_repeatability
        ):

            screening_result = "GOOD"

        elif strong_signal:

            screening_result = "UNSTABLE"

        else:

            screening_result = "WEAK"


        all_results.append(
            {
                "channel": target_channel,
                "mean": mean_response,
                "median": median_response,
                "std": std_response,
                "cv": cv_percent,
                "three_sigma": noise_3sigma,
                "signal_ratio": signal_to_3sigma,
                "result": screening_result
            }
        )


        # =================================================
        # Output
        # =================================================

        print()
        print("-" * 72)

        print(
            f"C{target_channel:02d} Screening Summary"
        )

        print("-" * 72)

        print(
            "Trial responses: "
            + ", ".join(
                f"{value:.1f}"
                for value in trial_values
            )
        )

        print(
            f"Mean response: "
            f"{mean_response:.1f}"
        )

        print(
            f"Median response: "
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

        print(
            f"3-sigma reference: "
            f"{noise_3sigma:.1f}"
        )

        print(
            f"Signal / 3-sigma: "
            f"{signal_to_3sigma:.2f}"
        )

        print(
            f"Screening flag: "
            f"{screening_result}"
        )


        writer.writerow(
            [
                foot_name,
                target_channel,
                CALIBRATION_MASS_G,
                trial_values[0],
                trial_values[1],
                trial_values[2],
                mean_response,
                median_response,
                std_response,
                cv_percent,
                noise_3sigma,
                signal_to_3sigma,
                screening_result
            ]
        )


    # =====================================================
    # Final Summary
    # =====================================================

    print()
    print("=" * 72)
    print(
        f"{foot_name} Foot Final Screening Summary"
    )
    print("=" * 72)

    print()

    for result in all_results:

        print(
            f"C{result['channel']:02d} | "
            f"Mean {result['mean']:8.1f} | "
            f"CV {result['cv']:6.1f}% | "
            f"Signal/3sigma {result['signal_ratio']:5.2f} | "
            f"{result['result']}"
        )

    return all_results


# =========================================================
# Main
# =========================================================

try:

    print("=" * 72)
    print("FeetFit 2 kg FSR Screening Test")
    print("=" * 72)

    print()
    print(
        "This test checks whether 2 kg is suitable "
        "for final sensitivity calibration."
    )

    print()
    print("L = Left foot")
    print("R = Right foot")
    print()

    selection = input(
        "Select foot [L/R]: "
    ).strip().upper()


    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    filename = (
        f"fsr_2kg_screening_{timestamp}.csv"
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
                "mass_g",
                "trial_1",
                "trial_2",
                "trial_3",
                "mean_response",
                "median_response",
                "std_response",
                "cv_percent",
                "noise_3sigma",
                "signal_to_3sigma",
                "screening_flag"
            ]
        )


        if selection == "L":

            run_screening(
                "Left",
                EN_LEFT,
                EN_RIGHT,
                left_adc,
                LEFT_BASELINE,
                LEFT_NOISE_STD,
                writer
            )

        elif selection == "R":

            run_screening(
                "Right",
                EN_RIGHT,
                EN_LEFT,
                right_adc,
                RIGHT_BASELINE,
                RIGHT_NOISE_STD,
                writer
            )

        else:

            raise ValueError(
                "Invalid foot selection."
            )


    print()
    print("=" * 72)
    print("Screening Completed")
    print("=" * 72)

    print(
        f"CSV saved: {filename}"
    )


except KeyboardInterrupt:

    print()
    print(
        "Screening stopped by user."
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

