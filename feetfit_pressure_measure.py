
import csv
import json
import statistics as stats
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import board
import busio
import RPi.GPIO as GPIO
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1x15 import Pin


# ==========================================
# FeetFit 하드웨어 설정 (BCM)
# ==========================================

SELECT_PINS = (22, 23, 24, 25)

FOOT = {
    "left": {
        "en": 17,
        "adc_pin": Pin.A1,
        "prefix": "L",
    },
    "right": {
        "en": 27,
        "adc_pin": Pin.A0,
        "prefix": "R",
    },
}

I2C_ADDRESS = 0x48

CHANNELS = range(12)

BASELINE_SWEEPS = 10
LOADED_SWEEPS = 10

DISCARD_READS = 3
VALID_READS = 9


# ==========================================
# CSV 저장
# ==========================================

def write_csv(path, rows):
    if not rows:
        return

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0])
        )

        writer.writeheader()
        writer.writerows(rows)


# ==========================================
# MUX 채널 선택
# ==========================================

def choose_channel(side, channel):

    # 두 MUX 비활성화
    for info in FOOT.values():
        GPIO.output(info["en"], GPIO.HIGH)

    # C0 ~ C11 선택
    for bit, pin in enumerate(SELECT_PINS):
        value = GPIO.HIGH if channel & (1 << bit) else GPIO.LOW
        GPIO.output(pin, value)

    time.sleep(0.005)

    # 해당 발 MUX 활성화 (Active LOW)
    GPIO.output(FOOT[side]["en"], GPIO.LOW)

    time.sleep(0.010)


# ==========================================
# 센서 원시값 및 필터링
# ==========================================

def read_filtered(adc):

    # MUX 전환 직후 초기값 제외
    for _ in range(DISCARD_READS):
        _ = adc.value
        time.sleep(0.005)

    raw = []
    sample_times = []

    # 실제 ADC 원시값 9개 수집
    for _ in range(VALID_READS):
        raw.append(int(adc.value))
        sample_times.append(time.monotonic())
        time.sleep(0.010)

    # 3개씩 중앙값 계산
    medians = [
        stats.median(raw[i:i + 3])
        for i in (0, 3, 6)
    ]

    # 중앙값들의 평균
    filtered = stats.mean(medians)

    return raw, sample_times, medians, filtered


# ==========================================
# 측정 실행
# ==========================================

def main():

    folder = (
        Path(__file__).resolve().parent
        / "pressure_logs"
        / datetime.now().strftime("%Y%m%d_%H%M%S")
    )

    folder.mkdir(parents=True, exist_ok=True)

    samples = []
    scans = []
    per_sensor = defaultdict(list)

    t0 = time.monotonic()

    # GPIO 초기화
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    for info in FOOT.values():
        GPIO.setup(
            info["en"],
            GPIO.OUT,
            initial=GPIO.HIGH
        )

    for pin in SELECT_PINS:
        GPIO.setup(
            pin,
            GPIO.OUT,
            initial=GPIO.LOW
        )

    try:

        # ADS1115 초기화
        i2c = busio.I2C(board.SCL, board.SDA)

        ads = ADS1115(
            i2c,
            address=I2C_ADDRESS
        )

        ads.gain = 1
        ads.data_rate = 250

        adc = {
            side: AnalogIn(ads, info["adc_pin"])
            for side, info in FOOT.items()
        }

        # ==================================
        # 24채널 반복 측정
        # ==================================

        def acquire(phase, total):

            for scan in range(1, total + 1):

                for side in ("left", "right"):

                    for ch in CHANNELS:

                        choose_channel(side, ch)

                        try:
                            raw, times, medians, filtered = (
                                read_filtered(adc[side])
                            )
                        finally:
                            GPIO.output(
                                FOOT[side]["en"],
                                GPIO.HIGH
                            )

                        sensor = (
                            f"{FOOT[side]['prefix']}{ch:02d}"
                        )

                        per_sensor[
                            (phase, sensor)
                        ].append(filtered)

                        scans.append({
                            "phase": phase,
                            "scan": scan,
                            "sensor": sensor,
                            "raw_mean": round(
                                stats.mean(raw), 3
                            ),
                            "median_filtered": round(
                                filtered, 3
                            ),
                        })

                        # 개별 원시 샘플 저장
                        for j, value in enumerate(raw):

                            samples.append({
                                "phase": phase,
                                "scan": scan,
                                "sensor": sensor,
                                "sample_index": j + 1,
                                "time_s": round(
                                    times[j] - t0, 4
                                ),
                                "raw_adc": value,
                                "median_3": medians[j // 3],
                                "filtered_scan": round(
                                    filtered, 3
                                ),
                            })

                print(
                    f"{phase}: {scan}/{total}회 완료",
                    flush=True
                )

        print("\n=== FeetFit 압력센서 측정 ===")
        print("Left : GPIO17 / ADS A1")
        print("Right: GPIO27 / ADS A0")

        # ==================================
        # 1단계: 무하중 측정
        # ==================================

        input(
            "\n[1] 양발을 발판에서 내린 뒤 "
            "Enter를 누르세요: "
        )

        acquire(
            "baseline",
            BASELINE_SWEEPS
        )

        # ==================================
        # 2단계: 하중 측정
        # ==================================

        input(
            "\n[2] 양발을 올리고 안정적으로 선 뒤 "
            "Enter를 누르세요: "
        )

        acquire(
            "loaded",
            LOADED_SWEEPS
        )

        # ==================================
        # 3단계: 영점 보정
        # ==================================

        summary = []

        for side in ("left", "right"):

            for ch in CHANNELS:

                sensor = (
                    f"{FOOT[side]['prefix']}{ch:02d}"
                )

                baseline = stats.mean(
                    per_sensor[("baseline", sensor)]
                )

                measured = stats.mean(
                    per_sensor[("loaded", sensor)]
                )

                corrected = max(
                    0.0,
                    measured - baseline
                )

                summary.append({
                    "sensor": sensor,
                    "side": side,
                    "channel": ch,
                    "baseline_adc": round(baseline, 3),
                    "loaded_adc": round(measured, 3),
                    "corrected_adc": round(corrected, 3),
                })

        # ==================================
        # 4단계: 0~100% 정규화
        # ==================================

        high = max(
            row["corrected_adc"]
            for row in summary
        )

        for row in summary:

            if high > 0:
                relative = (
                    100 * row["corrected_adc"] / high
                )
            else:
                relative = 0.0

            row["relative_0_100"] = round(
                relative, 2
            )

        # ==================================
        # 5단계: 파일 저장
        # ==================================

        write_csv(
            folder / "01_raw_samples.csv",
            samples
        )

        write_csv(
            folder / "02_filtered_scans.csv",
            scans
        )

        write_csv(
            folder / "03_sensor_summary.csv",
            summary
        )

        # 반응이 가장 큰 센서 선택
        best = max(
            summary,
            key=lambda r: r["corrected_adc"]
        )["sensor"]

        example = [
            r for r in samples
            if r["phase"] == "loaded"
            and r["sensor"] == best
        ]

        write_csv(
            folder / "01_filter_example.csv",
            example
        )

        # 공간 보간용 센서 좌표 양식
        positions = [
            {
                "sensor": r["sensor"],
                "x_cm": "",
                "y_cm": ""
            }
            for r in summary
        ]

        write_csv(
            folder / "04_sensor_positions_fill_in.csv",
            positions
        )

        # JSON 저장
        payload = {
            "wiring": {
                "left": "GPIO17 ADS A1",
                "right": "GPIO27 ADS A0"
            },
            "filter": (
                "discard 3, read 9, "
                "median each 3, average medians"
            ),
            "unit": "ADC raw counts",
            "filter_example_sensor": best,
            "left": [
                r for r in summary
                if r["side"] == "left"
            ],
            "right": [
                r for r in summary
                if r["side"] == "right"
            ]
        }

        (
            folder / "measurement.json"
        ).write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        # ==================================
        # 결과 출력
        # ==================================

        print("\n=== 측정 결과 ===")

        for r in summary:
            print(
                f"{r['sensor']} | "
                f"baseline={r['baseline_adc']:.1f} | "
                f"loaded={r['loaded_adc']:.1f} | "
                f"corrected={r['corrected_adc']:.1f} | "
                f"relative={r['relative_0_100']:.1f}%"
            )

        if high <= 0:
            print(
                "경고: 모든 보정값이 0입니다. "
                "배선과 센서 반응을 확인하세요."
            )

        print(f"\n저장 경로: {folder}")
        print(f"필터링 비교 센서: {best}")

    finally:

        for info in FOOT.values():
            GPIO.output(
                info["en"],
                GPIO.HIGH
            )

        GPIO.cleanup()


if __name__ == "__main__":
    main()
