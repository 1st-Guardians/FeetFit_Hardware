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
# Final Baseline
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
# Measurement Configuration
# =========================================================

MEASUREMENT_SECONDS = 10.0

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

# Left MUX SIG -> A0
left_adc = AnalogIn(
    ads,
    ADS1X15.Pin.A0
)

# Right MUX SIG -> A1
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

def read_channel(
    channel,
    enable_pin,
    other_enable_pin,
    adc
):

    # Keep both MUXes disabled before switching
    GPIO.output(
        EN_LEFT,
        GPIO.HIGH
    )

    GPIO.output(
        EN_RIGHT,
        GPIO.HIGH
    )

    time.sleep(
        MUX_DISCHARGE_TIME
    )

    # Select MUX channel
    set_mux_address(
        channel
    )

    # Enable only the target MUX
    GPIO.output(
        enable_pin,
        GPIO.LOW
    )

    GPIO.output(
        other_enable_pin,
        GPIO.HIGH
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

    # Collect valid ADC readings
    samples = []

    for _ in range(VALID_READS):

        samples.append(
            adc.value
        )

        time.sleep(
            ADC_SETTLE_TIME
        )

    # Disable the target MUX
    GPIO.output(
        enable_pin,
        GPIO.HIGH
    )

    # Median reduces single-sample spikes
    return float(
        statistics.median(samples)
    )


# =========================================================
# Read Both Feet
# =========================================================

def read_both_feet():

    left_values = []
    right_values = []

    for channel in range(12):

        left_value = read_channel(
            channel,
            EN_LEFT,
            EN_RIGHT,
            left_adc
        )

        right_value = read_channel(
            channel,
            EN_RIGHT,
            EN_LEFT,
            right_adc
        )

        left_values.append(
            left_value
        )

        right_values.append(
            right_value
        )

    return (
        left_values,
        right_values
    )


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
# Relative Value
# =========================================================

def calculate_relative(
    corrected_values
):

    max_value = max(
        corrected_values
    )

    if max_value <= 0:

        return [0.0] * 12

    return [
        value / max_value * 100.0
        for value in corrected_values
    ]


# =========================================================
# Main
# =========================================================

try:

    print("=" * 84)
    print("FeetFit Bilateral Pressure Measurement")
    print("=" * 84)

    print()
    print(
        "Place both feet on the measurement platform."
    )

    input(
        "Press Enter when ready: "
    )

    print()
    print(
        f"Measuring both feet for "
        f"{MEASUREMENT_SECONDS:.0f} seconds..."
    )

    print(
        "Keep both feet still during measurement."
    )

    print()

    left_sums = [0.0] * 12
    right_sums = [0.0] * 12

    scan_count = 0

    start_time = time.time()

    while (
        time.time() - start_time
        < MEASUREMENT_SECONDS
    ):

        (
            left_values,
            right_values
        ) = read_both_feet()

        for channel in range(12):

            left_sums[channel] += (
                left_values[channel]
            )

            right_sums[channel] += (
                right_values[channel]
            )

        scan_count += 1

        print(
            f"Scan {scan_count:02d} | "
            f"Left Max {max(left_values):8.1f} | "
            f"Right Max {max(right_values):8.1f}"
        )


    # =====================================================
    # Average RAW
    # =====================================================

    left_raw_average = [
        value / scan_count
        for value in left_sums
    ]

    right_raw_average = [
        value / scan_count
        for value in right_sums
    ]


    # =====================================================
    # Baseline Correction
    # =====================================================

    left_corrected = apply_baseline(
        left_raw_average,
        LEFT_BASELINE
    )

    right_corrected = apply_baseline(
        right_raw_average,
        RIGHT_BASELINE
    )


    # =====================================================
    # Relative Pressure
    # =====================================================

    left_relative = calculate_relative(
        left_corrected
    )

    right_relative = calculate_relative(
        right_corrected
    )


    # =====================================================
    # Result
    # =====================================================

    print()
    print("=" * 84)
    print("LEFT FOOT RESULT")
    print("=" * 84)

    print()

    for channel in range(12):

        print(
            f"C{channel:02d} | "
            f"RAW {left_raw_average[channel]:9.1f} | "
            f"BASELINE {LEFT_BASELINE[channel]:7.1f} | "
            f"CORRECTED {left_corrected[channel]:9.1f} | "
            f"RELATIVE {left_relative[channel]:6.1f}%"
        )


    print()
    print("=" * 84)
    print("RIGHT FOOT RESULT")
    print("=" * 84)

    print()

    for channel in range(12):

        print(
            f"C{channel:02d} | "
            f"RAW {right_raw_average[channel]:9.1f} | "
            f"BASELINE {RIGHT_BASELINE[channel]:7.1f} | "
            f"CORRECTED {right_corrected[channel]:9.1f} | "
            f"RELATIVE {right_relative[channel]:6.1f}%"
        )


    # =====================================================
    # Arrays For Later Processing
    # =====================================================

    print()
    print("=" * 84)
    print("OUTPUT ARRAYS")
    print("=" * 84)

    print()

    print(
        "LEFT_RAW = ["
        + ", ".join(
            f"{value:.1f}"
            for value in left_raw_average
        )
        + "]"
    )

    print()

    print(
        "LEFT_CORRECTED = ["
        + ", ".join(
            f"{value:.1f}"
            for value in left_corrected
        )
        + "]"
    )

    print()

    print(
        "LEFT_RELATIVE = ["
        + ", ".join(
            f"{value:.1f}"
            for value in left_relative
        )
        + "]"
    )

    print()

    print(
        "RIGHT_RAW = ["
        + ", ".join(
            f"{value:.1f}"
            for value in right_raw_average
        )
        + "]"
    )

    print()

    print(
        "RIGHT_CORRECTED = ["
        + ", ".join(
            f"{value:.1f}"
            for value in right_corrected
        )
        + "]"
    )

    print()

    print(
        "RIGHT_RELATIVE = ["
        + ", ".join(
            f"{value:.1f}"
            for value in right_relative
        )
        + "]"
    )

    print()

    print(
        f"Total scan count: {scan_count}"
    )

    print()
    print("=" * 84)
    print("Measurement Completed")
    print("=" * 84)


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
