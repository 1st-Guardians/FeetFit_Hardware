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
# Diagnostic reference only
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
# Calibration Configuration
# =========================================================

CALIBRATION_MASS_G = 500.0

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


# Left foot  -> A0
# Right foot -> A1

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

    # Disable target MUX
    GPIO.output(
        enable_pin,
        GPIO.HIGH
    )

    time.sleep(
        MUX_DISCHARGE_TIME
    )

    # Change channel while disabled
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

    # Collect valid readings
    samples = []

    for _ in range(VALID_READS):

        samples.append(
            adc.value
        )

        time.sleep(
            ADC_SETTLE_TIME
        )

    # Disable MUX after reading
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

        value = read_channel(
            channel,
            enable_pin,
            other_enable_pin,
            adc
        )

        values.append(
            value
        )

    return values


# =========================================================
# Measure For Fixed Duration
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

            sums[channel] += (
                values[channel]
            )

        scan_count += 1

    averages = [
        sums[channel] / scan_count
        for channel in range(12)
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

        if value < 0:
            value = 0.0

        corrected.append(
            value
        )

    return corrected


# =========================================================
# Find Strongest Other Channel
# =========================================================

def find_strongest_other(
    corrected,
    target_channel
):

    candidates = []

    for channel in range(12):

        if channel == target_channel:
            continue

        candidates.append(
            (
                corrected[channel],
                channel
            )
        )

    strongest_value, strongest_channel = max(
        candidates
    )

    return (
        strongest_channel,
        strongest_value
    )


# =========================================================
# Calibrate One Foot
# =========================================================

def calibrate_foot(
    foot_name,
    enable_pin,
    other_enable_pin,
    adc,
    baseline,
    noise_std,
    trial_writer,
    summary_writer
):

    print()
    print("=" * 72)
    print(
        f"{foot_name} Foot Sensitivity Calibration"
    )
    print("=" * 72)

    print()
    print(
        f"Calibration mass: {CALIBRATION_MASS_G:.1f} g"
    )

    print(
        f"Trials per channel: {TRIALS_PER_CHANNEL}"
    )

    print()

    channel_mean_responses = []

    # =====================================================
    # C0 ~ C11
    # =====================================================

    for target_channel in range(12):

        trial_responses = []

        print()
        print("=" * 72)
        print(
            f"{foot_name} C{target_channel:02d}"
        )
        print("=" * 72)

        for trial in range(
            1,
            TRIALS_PER_CHANNEL + 1
        ):

            print()
            print(
                f"Trial {trial}/{TRIALS_PER_CHANNEL}"
            )

            input(
                f"Place the calibration mass at the center of "
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

            trial_responses.append(
                target_corrected
            )

            (
                strongest_other_channel,
                strongest_other_value
            ) = find_strongest_other(
                corrected,
                target_channel
            )


            # =================================================
            # Trial Result
            # =================================================

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
                f"Scan count: "
                f"{scan_count}"
            )

            print(
                f"Strongest other channel: "
                f"C{strongest_other_channel:02d} "
                f"({strongest_other_value:.1f})"
            )

            print()


            # =================================================
            # Save Trial CSV
            # =================================================

            row = [
                foot_name,
                target_channel,
                trial,
                CALIBRATION_MASS_G,
                scan_count,
                target_raw,
                target_corrected,
                strongest_other_channel,
                strongest_other_value
            ]

            row.extend(
                raw_average
            )

            row.extend(
                corrected
            )

            trial_writer.writerow(
                row
            )


            # =================================================
            # Recovery
            # =================================================

            input(
                "Remove the calibration mass, then press Enter: "
            )

            print(
                f"Waiting {RECOVERY_SECONDS:.0f} seconds "
                "for sensor recovery..."
            )

            time.sleep(
                RECOVERY_SECONDS
            )

       # =====================================================
        # Channel Summary
        # =====================================================

        mean_response = statistics.mean(
            trial_responses
        )

        median_response = statistics.median(
            trial_responses
        )

        std_response = statistics.stdev(
            trial_responses
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
            noise_std[target_channel]
            * 3.0
        )

        if three_sigma > 0:

            signal_to_3sigma = (
                mean_response
                / three_sigma
            )

        else:

            signal_to_3sigma = 0.0


        channel_mean_responses.append(
            mean_response
        )


        print()
        print("-" * 72)

        print(
            f"C{target_channel:02d} Calibration Summary"
        )

        print("-" * 72)

        print(
            "Trial responses: "
            + ", ".join(
                f"{value:.1f}"
                for value in trial_responses
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
            f"3-sigma diagnostic reference: "
            f"{three_sigma:.1f}"
        )

        print(
            f"Signal / 3-sigma: "
            f"{signal_to_3sigma:.2f}"
        )

        print()


        summary_writer.writerow(
            [
                foot_name,
                target_channel,
                CALIBRATION_MASS_G,
                trial_responses[0],
                trial_responses[1],
                trial_responses[2],
                mean_response,
                median_response,
                std_response,
                cv_percent,
                three_sigma,
                signal_to_3sigma
            ]
        )


    # =====================================================
    # Calculate Relative Sensitivity Gain
    # =====================================================

    valid_responses = [
        value
        for value in channel_mean_responses
        if value > 0
    ]

    reference_response = statistics.median(
        valid_responses
    )


    gains = []

    for response in channel_mean_responses:

        if response > 0:

            gain = (
                reference_response
                / response
            )

        else:

            gain = 0.0

        gains.append(
            gain
        )


    print()
    print("=" * 72)

    print(
        f"{foot_name} Foot Final Calibration Result"
    )

    print("=" * 72)

    print()

    print(
        f"Reference response: "
        f"{reference_response:.1f}"
    )

    print()

    print(
        "CHANNEL_MEAN_RESPONSES = ["
    )

    print(
        "    "
        + ", ".join(
            f"{value:.1f}"
            for value in channel_mean_responses
        )
    )

    print(
        "]"
    )

    print()

    print(
        "SENSITIVITY_GAINS = ["
    )

    print(
        "    "
        + ", ".join(
            f"{value:.4f}"
            for value in gains
        )
    )

    print(
        "]"
    )

    print()

    print(
        "Do not apply the gains yet."
    )

    print(
        "Review repeatability and cross-channel response first."
    )

    print()

    return (
        channel_mean_responses,
        gains
    )

# =========================================================
# Main
# =========================================================

try:

    print("=" * 72)
    print("FeetFit FSR Sensitivity Calibration")
    print("=" * 72)

    print()
    print("L = Left foot")
    print("R = Right foot")
    print("B = Both feet")
    print()

    selection = input(
        "Select calibration target [L/R/B]: "
    ).strip().upper()


    # =====================================================
    # CSV Files
    # =====================================================

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    trial_filename = (
        f"fsr_calibration_trials_{timestamp}.csv"
    )

    summary_filename = (
        f"fsr_calibration_summary_{timestamp}.csv"
    )


    with open(
        trial_filename,
        "w",
        newline=""
    ) as trial_file, open(
        summary_filename,
        "w",
        newline=""
    ) as summary_file:

        trial_writer = csv.writer(
            trial_file
        )

        summary_writer = csv.writer(
            summary_file
        )


        # =================================================
        # Trial CSV Header
        # =================================================

        trial_header = [
            "foot",
            "target_channel",
            "trial",
            "mass_g",
            "scan_count",
            "target_raw_average",
            "target_corrected",
            "strongest_other_channel",
            "strongest_other_corrected"
        ]

        for channel in range(12):

            trial_header.append(
                f"raw_C{channel:02d}"
            )

        for channel in range(12):

            trial_header.append(
                f"corrected_C{channel:02d}"
            )

        trial_writer.writerow(
            trial_header
        )


        # =================================================
        # Summary CSV Header
        # =================================================

        summary_writer.writerow(
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
                "signal_to_3sigma"
            ]
        )


        # =================================================
        # Left Foot
        # =================================================

        if selection in ["L", "B"]:

            calibrate_foot(
                "Left",
                EN_LEFT,
                EN_RIGHT,
                left_adc,
                LEFT_BASELINE,
                LEFT_NOISE_STD,
                trial_writer,
                summary_writer
            )


        # =================================================
        # Right Foot
        # =================================================

        if selection in ["R", "B"]:

            calibrate_foot(
                "Right",
                EN_RIGHT,
                EN_LEFT,
                right_adc,
                RIGHT_BASELINE,
                RIGHT_NOISE_STD,
                trial_writer,
                summary_writer
            )


        if selection not in [
            "L",
            "R",
            "B"
        ]:

            raise ValueError(
                "Invalid calibration target."
            )


    print()
    print("=" * 72)
    print("Calibration Completed")
    print("=" * 72)

    print()

    print(
        f"Trial data saved: "
        f"{trial_filename}"
    )

    print(
        f"Summary data saved: "
        f"{summary_filename}"
    )


except KeyboardInterrupt:

    print()
    print(
        "Calibration stopped by user."
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
