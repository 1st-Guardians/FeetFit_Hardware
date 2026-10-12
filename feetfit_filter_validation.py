
#!/usr/bin/env python3
# FeetFit - FSR 신호 필터링 검증 실험

import argparse
import csv
import json
import statistics
import time

from datetime import datetime
from pathlib import Path

import board
import busio
import RPi.GPIO as GPIO

from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn
from adafruit_ads1x15.ads1x15 import Pin


# ==========================================
# 1. FeetFit 하드웨어 설정
# ==========================================

# CD74HC4067 선택핀 (BCM)
S_PINS = (22, 23, 24, 25)

# 최신 FeetFit 배선 기준
FEET = {
    "left": {
        "enable": 17,
        "adc": Pin.A1
    },
    "right": {
        "enable": 27,
        "adc": Pin.A0
    }
}

I2C_ADDRESS = 0x48

# ADS1115 설정
GAIN = 1
DATA_RATE = 250

# 필터링 설정
DISCARD_INITIAL = 3
READS_PER_WINDOW = 9
READ_DELAY_SEC = 0.010

# 실험 반복 횟수
BASELINE_WINDOWS = 30
LOADED_BLOCKS = 3
LOADED_WINDOWS_PER_BLOCK = 40


# ==========================================
# 2. CSV 저장
# ==========================================

def write_csv(path, rows, fieldnames):

    with open(
        path,
        "w",
        encoding="utf-8-sig",
        newline=""
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(rows)


# ==========================================
# 3. GPIO 및 MUX 설정
# ==========================================

def configure_gpio(foot, channel):

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    # 모든 MUX 비활성화
    for info in FEET.values():
        GPIO.setup(
            info["enable"],
            GPIO.OUT,
            initial=GPIO.HIGH
        )

    # 선택 채널 설정
    for bit, pin in enumerate(S_PINS):

        value = (
            GPIO.HIGH
            if channel & (1 << bit)
            else GPIO.LOW
        )

        GPIO.setup(
            pin,
            GPIO.OUT,
            initial=value
        )

    # 선택한 발의 MUX 활성화
    # CD74HC4067 EN: LOW = 활성화
    GPIO.output(
        FEET[foot]["enable"],
        GPIO.LOW
    )

    time.sleep(0.100)


# ==========================================
# 4. 초기 ADC값 제외
# ==========================================

def discard_first(adc):

    for _ in range(DISCARD_INITIAL):

        _ = adc.value
        time.sleep(READ_DELAY_SEC)


# ==========================================
# 5. 원시값 수집 및 중앙값 필터링
# ==========================================

def acquire_windows(
    adc,
    phase,
    block,
    count,
    t0,
    raw_rows,
    window_rows
):

    # 단계 시작 시 초기 3회 제외
    discard_first(adc)

    for window in range(1, count + 1):

        values = []
        times = []

        # 원시 ADC값 9개 수집
        for i in range(READS_PER_WINDOW):

            value = int(adc.value)

            values.append(value)

            times.append(
                time.monotonic() - t0
            )

            time.sleep(READ_DELAY_SEC)

        # 3개씩 그룹화하여 중앙값 계산
        medians = [
            statistics.median(
                values[i:i + 3]
            )
            for i in (0, 3, 6)
        ]

        # 원시값 9개의 일반 평균
        raw_mean = statistics.mean(values)

        # 중앙값 3개의 평균
        filtered = statistics.mean(medians)

        # 모든 원시 샘플 저장
        for i, (val, t) in enumerate(
            zip(values, times)
        ):

            raw_rows.append({
                "phase": phase,
                "block": block,
                "window": window,
                "sample_in_window": i + 1,
                "elapsed_s": round(t, 5),
                "raw_adc": val,
                "median_of_group3": medians[i // 3],
                "filtered_window_adc": round(
                    filtered, 3
                )
            })

        # 필터링 결과 저장
        window_rows.append({
            "phase": phase,
            "block": block,
            "window": window,
            "elapsed_s": round(
                statistics.mean(times), 5
            ),
            "raw_mean_9_adc": round(
                raw_mean, 3
            ),
            "filtered_median3_mean_adc": round(
                filtered, 3
            )
        })

        if window % 10 == 0:

            print(
                f"[{phase} / block {block}] "
                f"{window}/{count} 완료",
                flush=True
            )


# ==========================================
# 6. 표준편차 및 변동 감소율 계산
# ==========================================

def summarize(window_rows, phase, block):

    rows = [
        r for r in window_rows
        if r["phase"] == phase
        and r["block"] == block
    ]

    raw = [
        float(r["raw_mean_9_adc"])
        for r in rows
    ]

    filtered = [
        float(r["filtered_median3_mean_adc"])
        for r in rows
    ]

    # 구간 평균값들의 표준편차
    raw_sd = statistics.stdev(raw)
    filtered_sd = statistics.stdev(filtered)

    # 표준편차 변화율
    if raw_sd > 0:

        reduction = (
            (raw_sd - filtered_sd)
            / raw_sd
            * 100
        )

    else:
        reduction = None

    return {
        "phase": phase,
        "block": block,
        "n_windows": len(rows),
        "raw_mean_adc": round(
            statistics.mean(raw), 3
        ),
        "filtered_mean_adc": round(
            statistics.mean(filtered), 3
        ),
        "raw_window_sd_adc": round(
            raw_sd, 3
        ),
        "filtered_window_sd_adc": round(
            filtered_sd, 3
        ),
        "sd_change_pct": (
            round(reduction, 2)
            if reduction is not None
            else ""
        )
    }


# ==========================================
# 7. 그래프 생성
# ==========================================

def plot_results(folder, raw_rows, summary_rows):

    try:
        import matplotlib

        matplotlib.use("Agg")

        import matplotlib.pyplot as plt

    except ImportError:

        print(
            "matplotlib 없음: "
            "CSV만 저장합니다."
        )

        return

    # --------------------------------------
    # 그래프 1: 원시값 vs 필터링 결과
    # --------------------------------------

    first = [
        r for r in raw_rows
        if r["phase"] == "loaded"
        and r["block"] == 1
    ]

    xs = [
        r["elapsed_s"] - first[0]["elapsed_s"]
        for r in first
    ]

    raw = [
        r["raw_adc"]
        for r in first
    ]

    filtered = [
        r["filtered_window_adc"]
        for r in first
    ]

    fig, ax = plt.subplots(
        figsize=(12, 4.4)
    )

    ax.plot(
        xs,
        raw,
        color="#9CA3AF",
        linewidth=0.85,
        alpha=0.65,
        label="Raw ADC"
    )

    ax.plot(
        xs,
        filtered,
        color="#2563EB",
        linewidth=1.8,
        label="Median Filter"
    )

    ax.set_title(
        "FeetFit | FSR Signal Filtering"
    )

    ax.set_xlabel("Time (s)")
    ax.set_ylabel("ADC Value")

    ax.grid(alpha=0.2)
    ax.legend()

    fig.tight_layout()

    fig.savefig(
        folder / "01_filter_signal.png",
        dpi=200
    )

    plt.close(fig)

    # --------------------------------------
    # 그래프 2: 필터링 전후 표준편차
    # --------------------------------------

    loaded = [
        r for r in summary_rows
        if r["phase"] == "loaded"
    ]

    labels = [
        f"Block {r['block']}"
        for r in loaded
    ]

    x = list(range(len(loaded)))

    width = 0.36

    fig, ax = plt.subplots(
        figsize=(8, 4.6)
    )

    ax.bar(
        [i - width / 2 for i in x],
        [
            r["raw_window_sd_adc"]
            for r in loaded
        ],
        width=width,
        color="#9CA3AF",
        label="Raw Mean"
    )

    ax.bar(
        [i + width / 2 for i in x],
        [
            r["filtered_window_sd_adc"]
            for r in loaded
        ],
        width=width,
        color="#2563EB",
        label="Median Filter"
    )

    ax.set_xticks(x, labels)

    ax.set_ylabel(
        "Standard Deviation (ADC)"
    )

    ax.set_title(
        "FeetFit | Filtering Variability"
    )

    ax.legend()
    ax.grid(axis="y", alpha=0.2)

    fig.tight_layout()

    fig.savefig(
        folder / "02_filter_variability.png",
        dpi=200
    )

    plt.close(fig)


# ==========================================
# 8. 메인 실험
# ==========================================

def main():

    parser = argparse.ArgumentParser(
        description="FeetFit FSR Filter Test"
    )

    parser.add_argument(
        "--foot",
        required=True,
        choices=("left", "right")
    )

    parser.add_argument(
        "--channel",
        type=int,
        required=True,
        choices=range(12),
        metavar="0..11"
    )

    args = parser.parse_args()

    # --------------------------------------
    # 결과 저장 폴더
    # --------------------------------------

    now = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    folder = (
        Path(__file__).resolve().parent
        / "filter_validation_logs"
        / f"{now}_{args.foot}_C{args.channel:02d}"
    )

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    raw_rows = []
    window_rows = []

    print("\n==============================")
    print(" FeetFit FSR Filtering Test")
    print("==============================")

    print(
        f"선택 센서: "
        f"{args.foot} C{args.channel}"
    )

    print(
        "LEFT  = EN GPIO17 / ADS A1"
    )

    print(
        "RIGHT = EN GPIO27 / ADS A0"
    )

    gpio_started = False

    try:

        # ----------------------------------
        # GPIO 초기화
        # ----------------------------------

        configure_gpio(
            args.foot,
            args.channel
        )

        gpio_started = True

        # ----------------------------------
        # ADS1115 초기화
        # ----------------------------------

        i2c = busio.I2C(
            board.SCL,
            board.SDA
        )

        ads = ADS1115(
            i2c,
            address=I2C_ADDRESS
        )

        ads.gain = GAIN
        ads.data_rate = DATA_RATE

        adc = AnalogIn(
            ads,
            FEET[args.foot]["adc"]
        )

        t0 = time.monotonic()

        # ----------------------------------
        # 실험 1: 무하중 측정
        # ----------------------------------

        input(
            "\n[1/2] 센서에 아무것도 "
            "올리지 않은 상태에서 "
            "Enter를 누르세요: "
        )

        acquire_windows(
            adc=adc,
            phase="baseline",
            block=0,
            count=BASELINE_WINDOWS,
            t0=t0,
            raw_rows=raw_rows,
            window_rows=window_rows
        )

        baseline = summarize(
            window_rows,
            "baseline",
            0
        )

        print(
            "\n무하중 평균 ADC:",
            baseline["filtered_mean_adc"]
        )

        # ----------------------------------
        # 실험 2: 일정 하중 측정
        # ----------------------------------

        input(
            "\n[2/2] 선택한 센서에 "
            "일정한 무게를 올리고 "
            "안정화된 뒤 Enter를 누르세요: "
        )

        time.sleep(0.5)

        for block in range(
            1,
            LOADED_BLOCKS + 1
        ):

            print(
                f"\n하중 측정 Block {block}"
            )

            acquire_windows(
                adc=adc,
                phase="loaded",
                block=block,
                count=LOADED_WINDOWS_PER_BLOCK,
                t0=t0,
                raw_rows=raw_rows,
                window_rows=window_rows
            )

        # ----------------------------------
        # 실험 결과 계산
        # ----------------------------------

        summary_rows = [baseline]

        for block in range(
            1,
            LOADED_BLOCKS + 1
        ):

            result = summarize(
                window_rows,
                "loaded",
                block
            )

            summary_rows.append(result)

        # ----------------------------------
        # CSV 저장
        # ----------------------------------

        write_csv(
            folder / "01_raw_samples.csv",
            raw_rows,
            [
                "phase",
                "block",
                "window",
                "sample_in_window",
                "elapsed_s",
                "raw_adc",
                "median_of_group3",
                "filtered_window_adc"
            ]
        )

        write_csv(
            folder / "02_window_results.csv",
            window_rows,
            [
                "phase",
                "block",
                "window",
                "elapsed_s",
                "raw_mean_9_adc",
                "filtered_median3_mean_adc"
            ]
        )

        write_csv(
            folder / "03_summary.csv",
            summary_rows,
            [
                "phase",
                "block",
                "n_windows",
                "raw_mean_adc",
                "filtered_mean_adc",
                "raw_window_sd_adc",
                "filtered_window_sd_adc",
                "sd_change_pct"
            ]
        )

        # ----------------------------------
        # JSON 저장
        # ----------------------------------

        loaded_means = [
            r["filtered_mean_adc"]
            for r in summary_rows
            if r["phase"] == "loaded"
        ]

        loaded_mean = statistics.mean(
            loaded_means
        )

        payload = {
            "foot": args.foot,
            "channel": args.channel,
            "baseline_adc": (
                baseline["filtered_mean_adc"]
            ),
            "loaded_adc": round(
                loaded_mean, 3
            ),
            "response_difference_adc": round(
                loaded_mean
                - baseline["filtered_mean_adc"],
                3
            ),
            "filter": {
                "discard": DISCARD_INITIAL,
                "reads": READS_PER_WINDOW,
                "method": (
                    "median of each 3 samples "
                    "then average"
                )
            },
            "summary": summary_rows
        }

        (
            folder / "metadata.json"
        ).write_text(
            json.dumps(
                payload,
                indent=2,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

        # ----------------------------------
        # 그래프 생성
        # ----------------------------------

        plot_results(
            folder,
            raw_rows,
            summary_rows
        )

        # ----------------------------------
        # 터미널 결과 출력
        # ----------------------------------

        print("\n==============================")
        print(" 측정 결과")
        print("==============================")

        for result in summary_rows:

            print(
                f"\n{result['phase']} "
                f"Block {result['block']}"
            )

            print(
                "원시 평균 표준편차:",
                result["raw_window_sd_adc"]
            )

            print(
                "필터링 표준편차:",
                result["filtered_window_sd_adc"]
            )

            print(
                "표준편차 변화율(%):",
                result["sd_change_pct"]
            )

        print(
            "\n하중 반응 차이(ADC):",
            payload["response_difference_adc"]
        )

        print(
            "\n저장 경로:",
            folder
        )

    finally:

        # 모든 MUX 비활성화
        if gpio_started:

            for info in FEET.values():

                GPIO.output(
                    info["enable"],
                    GPIO.HIGH
                )

            GPIO.cleanup()


if __name__ == "__main__":
    main()
