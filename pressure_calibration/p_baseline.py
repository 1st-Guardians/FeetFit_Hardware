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
# Measurement Configuration
# =========================================================

BASELINE_SECONDS = 30.0

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


# Actual hardware mapping
# Left foot  -> ADS1115 A0
# Right foot -> ADS1115 A1

left_adc = AnalogIn(
    ads,
    ADS1X15.Pin.A0
)

right_adc = AnalogIn(
    ads,
    ADS1X15.Pin.A1
)


# =========================================================
# MUX Address
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

def read_channel(channel, enable_pin, adc):

    # Disable MUX before switching
    GPIO.output(
        enable_pin,
        GPIO.HIGH
    )

    # Allow the previous signal to settle
    time.sleep(
        MUX_DISCHARGE_TIME
    )

    # Change the MUX address while disabled
    set_mux_address(
        channel
    )

    # Enable selected MUX
    GPIO.output(
        enable_pin,
        GPIO.LOW
    )

    # Allow the new channel to settle
    time.sleep(
        MUX_SETTLE_TIME
    )

    # Discard initial ADC readings
    for _ in range(DISCARD_READS):

        _ = adc.value

        time.sleep(
            ADC_SETTLE_TIME
        )

    # Collect stable ADC readings
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

    # Use median to reduce spikes
    return statistics.median(
        samples
    )


# =========================================================
# Read Left Foot
# =========================================================

def read_left():

    values = []

    # Keep right MUX disabled
    GPIO.output(
        EN_RIGHT,
        GPIO.HIGH
    )

    for channel in range(12):

        value = read_channel(
            channel,
            EN_LEFT,
            left_adc
        )

        values.append(
            float(value)
        )

    return values


# =========================================================
# Read Right Foot
# =========================================================

def read_right():

    values = []

    # Keep left MUX disabled
    GPIO.output(
        EN_LEFT,
        GPIO.HIGH
    )

    for channel in range(12):

        value = read_channel(
            channel,
            EN_RIGHT,
            right_adc
        )

        values.append(
            float(value)
        )

    return values


# =========================================================
# Baseline Measurement
# =========================================================

def measure_baseline(
    foot_name,
    read_function
):

    print()
    print("=" * 72)
    print(
        f"{foot_name} Foot Baseline Measurement"
    )
    print("=" * 72)

    input(
        f"Remove all pressure from the {foot_name.lower()} platform "
        "and press Enter: "
    )

    print()

    print(
        f"Measuring for {BASELINE_SECONDS:.0f} seconds..."
    )

    print(
        "Do not touch the platform."
    )

    samples = [
        []
        for _ in range(12)
    ]

    scan_count = 0

    start_time = time.time()

    while (
        time.time() - start_time
        < BASELINE_SECONDS
    ):

        values = read_function()

        for channel in range(12):

            samples[channel].append(
                values[channel]
            )

        scan_count += 1

        print(
            f"{foot_name.upper()} RAW:",
            [
                int(value)
                for value in values
            ]
        )

# =====================================================
    # Statistics
    # =====================================================

    averages = []
    medians = []
    std_devs = []
    minimums = []
    maximums = []

    for channel in range(12):

        channel_samples = samples[channel]

        averages.append(
            statistics.mean(
                channel_samples
            )
        )

        medians.append(
            statistics.median(
                channel_samples
            )
        )

        if len(channel_samples) > 1:

            std_devs.append(
                statistics.stdev(
                    channel_samples
                )
            )

        else:

            std_devs.append(
                0.0
            )

        minimums.append(
            min(channel_samples)
        )

        maximums.append(
            max(channel_samples)
        )


    # =====================================================
    # Output
    # =====================================================

    print()
    print("=" * 72)

    print(
        f"{foot_name} Baseline Completed"
    )

    print("=" * 72)

    print()

    print(
        f"Total scan count: {scan_count}"
    )

    print()

    for channel in range(12):

        print(
            f"C{channel:02d}: "
            f"Average {averages[channel]:8.1f} | "
            f"Median {medians[channel]:8.1f} | "
            f"StdDev {std_devs[channel]:8.1f} | "
            f"Min {minimums[channel]:8.1f} | "
            f"Max {maximums[channel]:8.1f}"
        )

    print()

    prefix = foot_name.upper()

    print(
        f"{prefix}_BASELINE = ["
        + ", ".join(
            f"{value:.1f}"
            for value in averages
        )
        + "]"
    )

    print()

    print(
        f"{prefix}_BASELINE_MEDIAN = ["
        + ", ".join(
            f"{value:.1f}"
            for value in medians
        )
        + "]"
    )

    print()

    print(
        f"{prefix}_NOISE_STD = ["
        + ", ".join(
            f"{value:.1f}"
            for value in std_devs
        )
        + "]"
    )

    return (
        averages,
        medians,
        std_devs
    )


# =========================================================
# Main
# =========================================================

try:

    print("=" * 72)
    print("FeetFit Final Pressure Baseline Calibration")
    print("=" * 72)

    print()
    print("Measurement configuration:")
    print("Left MUX  -> ADS1115 A0")
    print("Right MUX -> ADS1115 A1")

    print(
        f"MUX discharge: "
        f"{MUX_DISCHARGE_TIME * 1000:.0f} ms"
    )

    print(
        f"MUX settle: "
        f"{MUX_SETTLE_TIME * 1000:.0f} ms"
    )

    print(
        f"ADC discard reads: "
        f"{DISCARD_READS}"
    )

    print(
        f"ADC valid reads: "
        f"{VALID_READS}"
    )

    print()

    left_result = measure_baseline(
        "Left",
        read_left
    )

    print()
    print(
        "Left baseline measurement finished."
    )

    print()

    right_result = measure_baseline(
        "Right",
        read_right
    )

    print()
    print("=" * 72)
    print("All Baseline Measurements Completed")
    print("=" * 72)


except KeyboardInterrupt:

    print()
    print(
        "Measurement stopped by user."
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
