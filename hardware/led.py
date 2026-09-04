from gpiozero import OutputDevice

from config import (
    LED_GPIO_PIN,
    LED_ACTIVE_HIGH,
)


# =========================================================
# LED BAR 제어
#
# 하드웨어 문서 기준
#
# Raspberry Pi BCM GPIO26
# → NPN transistor
# → Relay
# → 12V LED BAR
#
# ACTIVE HIGH
#
# GPIO LOW  = LED OFF
# GPIO HIGH = LED ON
# =========================================================


led = OutputDevice(
    LED_GPIO_PIN,
    active_high=LED_ACTIVE_HIGH,
    initial_value=False
)


# =========================================================
# LED ON
# =========================================================

def led_on():

    print()
    print("========================================")
    print("[LED BAR] ON")
    print(f"[GPIO] BCM {LED_GPIO_PIN}")
    print("========================================")

    led.on()


# =========================================================
# LED OFF
# =========================================================

def led_off():

    print()
    print("========================================")
    print("[LED BAR] OFF")
    print(f"[GPIO] BCM {LED_GPIO_PIN}")
    print("========================================")

    led.off()


# =========================================================
# 예외 발생 시 안전하게 LED OFF
# =========================================================

def ensure_led_off():

    try:

        led.off()

        print(
            f"[LED BAR] SAFETY OFF "
            f"- GPIO BCM {LED_GPIO_PIN}"
        )

    except Exception as e:

        print(
            "[LED BAR] OFF 실패:",
            e
        )
