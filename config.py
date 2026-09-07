import os

from pathlib import Path
from dotenv import load_dotenv


# =========================================================
# .env 로드
# =========================================================

load_dotenv()


# =========================================================
# bool 환경변수 변환
#
# true / 1 / yes / on
# =========================================================

def env_bool(
    name: str,
    default: bool = False
) -> bool:

    value = os.getenv(
        name,
        str(default)
    )

    return (
        value
        .strip()
        .lower()
        in (
            "1",
            "true",
            "yes",
            "on"
        )
    )


# =========================================================
# Backend
# =========================================================

BACKEND_BASE_URL = os.getenv(
    "BACKEND_BASE_URL",
    "http://34.209.169.111"
).rstrip("/")


BACKEND_TIMEOUT_SECONDS = int(
    os.getenv(
        "BACKEND_TIMEOUT_SECONDS",
        "15"
    )
)


# =========================================================
# AI Server
# =========================================================

AI_BASE_URL = os.getenv(
    "AI_BASE_URL",
    ""
).rstrip("/")


AI_TIMEOUT_SECONDS = int(
    os.getenv(
        "AI_TIMEOUT_SECONDS",
        "30"
    )
)


# =========================================================
# 카메라
#
# 현재 USB 물리 연결 기준
#
# LEFT Arducam
# USB 1.2
# /dev/video0
#
# RIGHT Arducam
# USB 1.1.1
# /dev/video2
#
# DORSAL Webcam
# USB 1.1.4
# /dev/video4
#
# /dev/videoN 번호가 변경되어도
# 동일한 USB 물리 포트를 사용하도록 by-path 사용
# =========================================================


# ---------------------------------------------------------
# LEFT Arducam
# ---------------------------------------------------------

LEFT_CAMERA_DEVICE = os.getenv(
    "LEFT_CAMERA_DEVICE",
    (
        "/dev/v4l/by-path/"
        "platform-fd500000.pcie-"
        "pci-0000:01:00.0-"
        "usb-0:1.2:1.0-video-index0"
    )
)


LEFT_IMAGE_WIDTH = int(
    os.getenv(
        "LEFT_IMAGE_WIDTH",
        "3264"
    )
)


LEFT_IMAGE_HEIGHT = int(
    os.getenv(
        "LEFT_IMAGE_HEIGHT",
        "2448"
    )
)


LEFT_CAMERA_FRAMERATE = int(
    os.getenv(
        "LEFT_CAMERA_FRAMERATE",
        "15"
    )
)


# ---------------------------------------------------------
# RIGHT Arducam
# ---------------------------------------------------------

RIGHT_CAMERA_DEVICE = os.getenv(
    "RIGHT_CAMERA_DEVICE",
    (
        "/dev/v4l/by-path/"
        "platform-fd500000.pcie-"
        "pci-0000:01:00.0-"
        "usb-0:1.1.1:1.0-video-index0"
    )
)


RIGHT_IMAGE_WIDTH = int(
    os.getenv(
        "RIGHT_IMAGE_WIDTH",
        "3264"
    )
)


RIGHT_IMAGE_HEIGHT = int(
    os.getenv(
        "RIGHT_IMAGE_HEIGHT",
        "2448"
    )
)


RIGHT_CAMERA_FRAMERATE = int(
    os.getenv(
        "RIGHT_CAMERA_FRAMERATE",
        "15"
    )
)


# ---------------------------------------------------------
# DORSAL 일반 웹캠
# ---------------------------------------------------------

DORSAL_CAMERA_DEVICE = os.getenv(
    "DORSAL_CAMERA_DEVICE",
    (
        "/dev/v4l/by-path/"
        "platform-fd500000.pcie-"
        "pci-0000:01:00.0-"
        "usb-0:1.1.4:1.0-video-index0"
    )
)


DORSAL_IMAGE_WIDTH = int(
    os.getenv(
        "DORSAL_IMAGE_WIDTH",
        "1280"
    )
)


DORSAL_IMAGE_HEIGHT = int(
    os.getenv(
        "DORSAL_IMAGE_HEIGHT",
        "720"
    )
)


DORSAL_CAMERA_FRAMERATE = int(
    os.getenv(
        "DORSAL_CAMERA_FRAMERATE",
        "30"
    )
)


# =========================================================
# Arducam 촬영 설정
#
# 현재 기준
#
# 해상도:
# 3264 x 2448
#
# Auto Exposure:
# OFF / Manual
#
# Exposure:
# 200
# → LED 배치 확정 후 최종 조정
#
# Gain:
# 0
#
# Auto White Balance:
# ON
#
# Auto Focus:
# OFF
#
# Focus:
# 350
#
# Sharpness:
# 3
# =========================================================


# ---------------------------------------------------------
# 노출
#
# Arducam V4L2에서
# auto_exposure=1 → Manual Exposure
# ---------------------------------------------------------

ARDUCAM_AUTO_EXPOSURE = int(
    os.getenv(
        "ARDUCAM_AUTO_EXPOSURE",
        "1"
    )
)


ARDUCAM_EXPOSURE = int(
    os.getenv(
        "ARDUCAM_EXPOSURE",
        "200"
    )
)


ARDUCAM_GAIN = int(
    os.getenv(
        "ARDUCAM_GAIN",
        "0"
    )
)


ARDUCAM_BACKLIGHT_COMPENSATION = int(
    os.getenv(
        "ARDUCAM_BACKLIGHT_COMPENSATION",
        "0"
    )
)


ARDUCAM_EXPOSURE_DYNAMIC_FRAMERATE = int(
    os.getenv(
        "ARDUCAM_EXPOSURE_DYNAMIC_FRAMERATE",
        "0"
    )
)


# 대한민국 상용 전원 주파수 60 Hz
ARDUCAM_POWER_LINE_FREQUENCY = int(
    os.getenv(
        "ARDUCAM_POWER_LINE_FREQUENCY",
        "2"
    )
)


# ---------------------------------------------------------
# White Balance
#
# 수동 WB에서 초록빛 문제가 있었으므로
# Auto White Balance 사용
# ---------------------------------------------------------

ARDUCAM_AUTO_WHITE_BALANCE = env_bool(
    "ARDUCAM_AUTO_WHITE_BALANCE",
    True
)


# ---------------------------------------------------------
# 색상 / 이미지 설정
# ---------------------------------------------------------

ARDUCAM_BRIGHTNESS = int(
    os.getenv(
        "ARDUCAM_BRIGHTNESS",
        "0"
    )
)


ARDUCAM_CONTRAST = int(
    os.getenv(
        "ARDUCAM_CONTRAST",
        "32"
    )
)


ARDUCAM_SATURATION = int(
    os.getenv(
        "ARDUCAM_SATURATION",
        "64"
    )
)


ARDUCAM_HUE = int(
    os.getenv(
        "ARDUCAM_HUE",
        "0"
    )
)


ARDUCAM_HUE_AUTOMATIC = int(
    os.getenv(
        "ARDUCAM_HUE_AUTOMATIC",
        "0"
    )
)


ARDUCAM_GAMMA = int(
    os.getenv(
        "ARDUCAM_GAMMA",
        "100"
    )
)


ARDUCAM_SHARPNESS = int(
    os.getenv(
        "ARDUCAM_SHARPNESS",
        "3"
    )
)


# ---------------------------------------------------------
# Focus
#
# Auto Focus OFF
# Manual Focus 350
# ---------------------------------------------------------

ARDUCAM_AUTO_FOCUS = int(
    os.getenv(
        "ARDUCAM_AUTO_FOCUS",
        "0"
    )
)


ARDUCAM_FOCUS_ABSOLUTE = int(
    os.getenv(
        "ARDUCAM_FOCUS_ABSOLUTE",
        "350"
    )
)


# ---------------------------------------------------------
# Arducam 설정 적용 후 안정화 시간
# ---------------------------------------------------------

ARDUCAM_CONTROL_SETTLE_SECONDS = float(
    os.getenv(
        "ARDUCAM_CONTROL_SETTLE_SECONDS",
        "0.3"
    )
)


# 서버 시작 시 Arducam 설정 적용
ARDUCAM_CONFIGURE_ON_STARTUP = env_bool(
    "ARDUCAM_CONFIGURE_ON_STARTUP",
    True
)


# 실제 촬영 직전 Arducam 설정 재적용
ARDUCAM_CONFIGURE_BEFORE_CAPTURE = env_bool(
    "ARDUCAM_CONFIGURE_BEFORE_CAPTURE",
    True
)


# =========================================================
# Auto White Balance Warmup
#
# 스트림을 시작한 직후에는
# Auto WB가 완전히 안정화되지 않을 수 있으므로
# 초기 프레임을 버린 뒤 사진 저장
# =========================================================

CAMERA_WARMUP_FRAMES = int(
    os.getenv(
        "CAMERA_WARMUP_FRAMES",
        "15"
    )
)


# =========================================================
# 카메라 전환 대기
#
# LEFT 촬영
# ↓
# 대기
# ↓
# RIGHT 촬영
# ↓
# 대기
# ↓
# DORSAL 촬영
# =========================================================

CAMERA_SWITCH_DELAY_SECONDS = float(
    os.getenv(
        "CAMERA_SWITCH_DELAY_SECONDS",
        "2"
    )
)


# =========================================================
# 사진 저장 폴더
# =========================================================

PHOTO_DIR = Path(
    os.getenv(
        "PHOTO_DIR",
        str(
            Path.home()
            / "feetfit-api"
            / "photos"
        )
    )
)


PHOTO_DIR.mkdir(
    parents=True,
    exist_ok=True
)


# =========================================================
# 사진 촬영 전 대기
#
# 사진 측정 API 호출 후 실제 촬영까지 대기 시간
# =========================================================

CAPTURE_DELAY_SECONDS = float(
    os.getenv(
        "CAPTURE_DELAY_SECONDS",
        "5"
    )
)


# =========================================================
# LED
#
# GPIO26
#
# LED ON
# ↓
# 2초 안정화
# ↓
# 카메라 촬영
# ↓
# LED OFF
# =========================================================

LED_GPIO_PIN = int(
    os.getenv(
        "LED_GPIO_PIN",
        "26"
    )
)


LED_ACTIVE_HIGH = env_bool(
    "LED_ACTIVE_HIGH",
    True
)


LED_STABILIZE_SECONDS = float(
    os.getenv(
        "LED_STABILIZE_SECONDS",
        "2"
    )
)


# =========================================================
# Mock Sensor
#
# 실제 센서 연결 전:
# true
#
# 실제 압력 / 온습도 코드 연결 후:
# false
# =========================================================

USE_MOCK_SENSORS = env_bool(
    "USE_MOCK_SENSORS",
    True
)


# =========================================================
# BME280 온습도 센서
#
# I2C Bus: 1
# Address: 0x76
# SDA: GPIO2
# SCL: GPIO3
# Power: 3.3V
# =========================================================

BME280_I2C_BUS = int(
    os.getenv(
        "BME280_I2C_BUS",
        "1"
    )
)


BME280_I2C_ADDRESS = int(
    os.getenv(
        "BME280_I2C_ADDRESS",
        "0x76"
    ),
    0
)


BME280_SAMPLE_COUNT = int(
    os.getenv(
        "BME280_SAMPLE_COUNT",
        "5"
    )
)


BME280_SAMPLE_INTERVAL_SECONDS = float(
    os.getenv(
        "BME280_SAMPLE_INTERVAL_SECONDS",
        "0.2"
    )
)


# =========================================================
# Buzzer
# =========================================================

BUZZER_GPIO_PIN = int(
    os.getenv(
        "BUZZER_GPIO_PIN",
        "12"
    )
)


BUZZER_ACTIVE_HIGH = env_bool(
    "BUZZER_ACTIVE_HIGH",
    True
)


# =========================================================
# Pressure
# =========================================================

PRESSURE_FIXED_INPUT = env_bool(
    "PRESSURE_FIXED_INPUT",
    False
)


PRESSURE_FIXED_SCAN_COUNT = int(
    os.getenv(
        "PRESSURE_FIXED_SCAN_COUNT",
        "9"
    )
)
