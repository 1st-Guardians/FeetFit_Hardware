import time

from threading import (
    Lock,
    Thread
)

from gpiozero import Buzzer

from config import (
    BUZZER_GPIO_PIN,
    BUZZER_ACTIVE_HIGH
)


# =========================================================
# Buzzer Setup
# =========================================================

buzzer = Buzzer(
    BUZZER_GPIO_PIN,
    active_high=BUZZER_ACTIVE_HIGH,
    initial_value=False
)


buzzer_lock = Lock()


# =========================================================
# Buzzer Patterns
#
# (ON 시간, OFF 시간)
# =========================================================

READY_PATTERN = [
    (0.20, 0.0)
]


ERROR_PATTERN = [
    (0.12, 0.12),
    (0.12, 0.12),
    (0.12, 0.50),

    (0.12, 0.12),
    (0.12, 0.12),
    (0.12, 0.0)
]


COMPLETE_PATTERN = [
    (0.12, 0.10),
    (0.12, 0.15),
    (0.55, 0.0)
]


# =========================================================
# Pattern Player
# =========================================================

def _play_pattern(
    pattern,
    name: str
):

    with buzzer_lock:

        print(
            f"[BUZZER] {name}"
        )

        try:

            buzzer.off()

            for (
                on_seconds,
                off_seconds
            ) in pattern:

                buzzer.on()

                time.sleep(
                    on_seconds
                )

                buzzer.off()

                if off_seconds > 0:

                    time.sleep(
                        off_seconds
                    )

        except Exception as e:

            # 부저 오류 때문에
            # 전체 측정을 실패시키지는 않음
            print(
                "[BUZZER ERROR]",
                e
            )

        finally:

            try:
                buzzer.off()

            except Exception:
                pass


# =========================================================
# Async Player
#
# 부저가 울리는 동안 API 응답이 멈추지 않도록
# 별도 Thread에서 재생
# =========================================================

def _play_async(
    pattern,
    name: str
):

    thread = Thread(
        target=_play_pattern,
        args=(
            pattern,
            name
        ),
        daemon=True
    )

    thread.start()


# =========================================================
# Next Step Ready
#
# 삑 1회
# =========================================================

def buzzer_ready():

    _play_async(
        READY_PATTERN,
        "NEXT STEP READY"
    )


# =========================================================
# Error
#
# 삑삑삑 - 삑삑삑
# =========================================================

def buzzer_error():

    _play_async(
        ERROR_PATTERN,
        "ERROR"
    )


# =========================================================
# Measurement Completed
#
# 삑 삑 삐이익
# =========================================================

def buzzer_complete():

    _play_async(
        COMPLETE_PATTERN,
        "MEASUREMENT COMPLETE"
    )
