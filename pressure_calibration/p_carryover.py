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
# Noise Standard Deviation
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
# Measurement Configuration
# =========================================================

MUX_DISCHARGE_TIME = 0.010
MUX_SETTLE_TIME = 0.010
ADC_SETTLE_TIME = 0.003

DISCARD_READS = 3
VALID_READS = 3

FIXED_TEST_SECONDS = 5.0
SCAN_TEST_SECONDS = 10.0


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

    # Keep the opposite MUX disabled
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

    # Change channel while MUX is disabled
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

    # Collect valid ADC readings
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
# Correct Value
# =========================================================

def correct_value(
    raw,
    baseline
):

    value = raw - baseline

    if value < 0:
        value = 0.0

    return value

# =========================================================
# Fixed C0 Test
# =========================================================

def fixed_c0_test(
    enable_pin,
    other_enable_pin,
    adc,
    baseline
):

    values = []

    start_time = time.time()

    while (
        time.time() - start_time
        < FIXED_TEST_SECONDS
    ):

        raw = read_channel(
            0,
            enable_pin,
            other_enable_pin,
            adc
        )

        corrected = correct_value(
            raw,
            baseline[0]
        )

        values.append(
            corrected
        )

        print(
            f"C00 RAW {raw:8.1f} | "
            f"Corrected {corrected:8.1f}"
        )

    return values


# =========================================================
# Scan With Custom Order
# =========================================================

def scan_channels(
    order,
    enable_pin,
    other_enable_pin,
    adc,
    baseline
):

    result = {}

    for channel in order:

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

        result[channel] = (
            raw,
            corrected
        )

    return result


# =========================================================
# Repeated Scan Test
# =========================================================

def repeated_scan_test(
    order,
    enable_pin,
    other_enable_pin,
    adc,
    baseline
):

    c0_values = []
    c1_values = []
    c11_values = []

    scan_count = 0

    start_time = time.time()

    while (
        time.time() - start_time
        < SCAN_TEST_SECONDS
    ):

        result = scan_channels(
            order,
            enable_pin,
            other_enable_pin,
            adc,
            baseline
        )

        scan_count += 1

        c0 = result[0][1]
        c1 = result[1][1]
        c11 = result[11][1]

        # Ignore the first scan because the previous channel is unknown
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

        print(
            f"Scan {scan_count:02d} | "
            f"C00 {c0:8.1f} | "
            f"C01 {c1:8.1f} | "
            f"C11 {c11:8.1f}"
        )

    return (
        c0_values,
        c1_values,
        c11_values,
        scan_count
    )


# =========================================================
# Statistics
# =========================================================

def print_stats(
    name,
    values
):

    if not values:

        print(
            f"{name}: No data"
        )

        return

    print(
        f"{name}: "
        f"Average {statistics.mean(values):8.1f} | "
        f"Median {statistics.median(values):8.1f} | "
        f"Min {min(values):8.1f} | "
        f"Max {max(values):8.1f}"
    )

# =========================================================
# Main
# =========================================================

try:

    print("=" * 72)
    print("FeetFit MUX Carryover Test")
    print("=" * 72)

    print()
    print("L = Left foot")
    print("R = Right foot")
    print()

    foot = input(
        "Select foot [L/R]: "
    ).strip().upper()


    if foot == "L":

        foot_name = "Left"

        enable_pin = EN_LEFT
        other_enable_pin = EN_RIGHT

        adc = left_adc
        baseline = LEFT_BASELINE
        noise_std = LEFT_NOISE_STD


    elif foot == "R":

        foot_name = "Right"

        enable_pin = EN_RIGHT
        other_enable_pin = EN_LEFT

        adc = right_adc
        baseline = RIGHT_BASELINE
        noise_std = RIGHT_NOISE_STD


    else:

        raise ValueError(
            "Invalid foot selection."
        )


    print()
    print("=" * 72)
    print(
        f"{foot_name} Foot Carryover Test"
    )
    print("=" * 72)


    # =====================================================
    # TEST A1
    # C0 fixed without pressure
    # =====================================================

    print()
    print("=" * 72)
    print("TEST A1 - Fixed C0 Without Pressure")
    print("=" * 72)

    input(
        "Do not press any sensor. Press Enter to start: "
    )

    no_pressure_c0 = fixed_c0_test(
        enable_pin,
        other_enable_pin,
        adc,
        baseline
    )

    print()

    print_stats(
        "C00 without pressure",
        no_pressure_c0
    )


    # =====================================================
    # TEST A2
    # C0 fixed while C11 is pressed
    # =====================================================

    print()
    print("=" * 72)
    print("TEST A2 - Fixed C0 While C11 Is Pressed")
    print("=" * 72)

    input(
        "Press and hold C11 strongly, then press Enter: "
    )

    fixed_pressed_c0 = fixed_c0_test(
        enable_pin,
        other_enable_pin,
        adc,
        baseline
    )

    print()

    print_stats(
        "C00 while C11 pressed",
        fixed_pressed_c0
    )

    input(
        "Release C11, then press Enter: "
    )


    # =====================================================
    # TEST B
    # Normal scan order
    # C11 -> C0 occurs between scans
    # =====================================================

    print()
    print("=" * 72)
    print("TEST B - Normal Scan Order")
    print("=" * 72)

    print()
    print(
        "Scan order:"
    )

    print(
        "C0 -> C1 -> C2 -> ... -> C11"
    )

    print(
        "Between scans, C11 is followed by C0."
    )

    print()

    input(
        "Press and hold C11 strongly, then press Enter: "
    )

    normal_order = list(
        range(12)
    )

    (
        normal_c0,
        normal_c1,
        normal_c11,
        normal_count
    ) = repeated_scan_test(
        normal_order,
        enable_pin,
        other_enable_pin,
        adc,
        baseline
    )

    print()

    print_stats(
        "Normal order C00",
        normal_c0
    )

    print_stats(
        "Normal order C01",
        normal_c1
    )

    print_stats(
        "Normal order C11",
        normal_c11
    )

    input(
        "Release C11, then press Enter: "
    )
    # =====================================================
    # TEST C
    # C1 -> C0
    # C11 -> C1 occurs between scans
    # =====================================================

    print()
    print("=" * 72)
    print("TEST C - Reordered Scan")
    print("=" * 72)

    print()
    print(
        "Scan order:"
    )

    print(
        "C1 -> C0 -> C2 -> C3 -> ... -> C11"
    )

    print(
        "Between scans, C11 is followed by C1."
    )

    print(
        "C0 is now preceded by C1."
    )

    print()

    input(
        "Press and hold C11 strongly, then press Enter: "
    )

    reordered = [
        1, 0, 2, 3, 4, 5,
        6, 7, 8, 9, 10, 11
    ]

    (
        reorder_c0,
        reorder_c1,
        reorder_c11,
        reorder_count
    ) = repeated_scan_test(
        reordered,
        enable_pin,
        other_enable_pin,
        adc,
        baseline
    )

    print()

    print_stats(
        "Reordered C00",
        reorder_c0
    )

    print_stats(
        "Reordered C01",
        reorder_c1
    )

    print_stats(
        "Reordered C11",
        reorder_c11
    )


    # =====================================================
    # Final Comparison
    # =====================================================

    print()
    print("=" * 72)
    print("FINAL COMPARISON")
    print("=" * 72)

    print()

    print_stats(
        "A1 C00 no pressure",
        no_pressure_c0
    )

    print_stats(
        "A2 C00 with C11 pressed",
        fixed_pressed_c0
    )

    print()

    print_stats(
        "B Normal C00",
        normal_c0
    )

    print_stats(
        "B Normal C01",
        normal_c1
    )

    print()

    print_stats(
        "C Reordered C00",
        reorder_c0
    )

    print_stats(
        "C Reordered C01",
        reorder_c1
    )

    print()

    print(
        f"C00 noise standard deviation: "
        f"{noise_std[0]:.1f}"
    )

    print(
        f"C00 3-sigma reference: "
        f"{noise_std[0] * 3:.1f}"
    )

    print()
    print(
        "Test completed."
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
