import math
import os
import subprocess
import time

from pathlib import Path
from threading import Lock
from typing import Dict, Optional

import requests

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from gpiozero import OutputDevice
from pydantic import BaseModel


# =========================================================
# ?? ??
# =========================================================

load_dotenv()


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(
        name,
        str(default)
    )

    return value.strip().lower() in (
        "1",
        "true",
        "yes",
        "on"
    )


# =========================================================
# Backend / AI
# =========================================================

BACKEND_BASE_URL = os.getenv(
    "BACKEND_BASE_URL",
    "http://34.209.169.111"
).rstrip("/")


AI_BASE_URL = os.getenv(
    "AI_BASE_URL",
    ""
).rstrip("/")


BACKEND_TIMEOUT_SECONDS = int(
    os.getenv(
        "BACKEND_TIMEOUT_SECONDS",
        "15"
    )
)


AI_TIMEOUT_SECONDS = int(
    os.getenv(
        "AI_TIMEOUT_SECONDS",
        "30"
    )
)


# =========================================================
# ??? ??
#
# USB ?? ?? ?? by-path ??
# - 1.2   ? ?? ?? Arducam (Raspberry Pi ?? ??)
# - 1.1.4 ? ??? ?? Arducam (??? ??)
# - 1.1.3 ? ?? ?? (??? ??)
#
# /dev/videoN ??? ?????? ?? USB ?? ??? ??
# =========================================================

LEFT_CAMERA_DEVICE = os.getenv(
    "LEFT_CAMERA_DEVICE",
    "/dev/v4l/by-path/platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.2:1.0-video-index0"
)

LEFT_IMAGE_WIDTH = int(
    os.getenv(
        "LEFT_IMAGE_WIDTH",
        "1280"
    )
)

LEFT_IMAGE_HEIGHT = int(
    os.getenv(
        "LEFT_IMAGE_HEIGHT",
        "720"
    )
)

LEFT_CAMERA_FRAMERATE = int(
    os.getenv(
        "LEFT_CAMERA_FRAMERATE",
        "30"
    )
)


RIGHT_CAMERA_DEVICE = os.getenv(
    "RIGHT_CAMERA_DEVICE",
    "/dev/v4l/by-path/platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.1.4:1.0-video-index0"
)

RIGHT_IMAGE_WIDTH = int(
    os.getenv(
        "RIGHT_IMAGE_WIDTH",
        "1280"
    )
)

RIGHT_IMAGE_HEIGHT = int(
    os.getenv(
        "RIGHT_IMAGE_HEIGHT",
        "720"
    )
)

RIGHT_CAMERA_FRAMERATE = int(
    os.getenv(
        "RIGHT_CAMERA_FRAMERATE",
        "30"
    )
)


DORSAL_CAMERA_DEVICE = os.getenv(
    "DORSAL_CAMERA_DEVICE",
    "/dev/v4l/by-path/platform-fd500000.pcie-pci-0000:01:00.0-usb-0:1.1.3:1.0-video-index0"
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
# Arducam ?? ???
#
# ?? ????? ?? ??? ??? ??????.
# - ??: Manual / 100
# - Gain: 0
# - White Balance: Auto
#
# USB ???/????? UVC ??? ???? ? ????
# ? ?? ? ? ?, ??? ?? ?? ??? ?? ?????.
#
# Auto WB? ??? ?? red_balance / blue_balance /
# white_balance_temperature? ??? ???? ????.
# =========================================================

ARDUCAM_AUTO_EXPOSURE = int(
    os.getenv(
        "ARDUCAM_AUTO_EXPOSURE",
        "1"
    )
)

ARDUCAM_EXPOSURE = int(
    os.getenv(
        "ARDUCAM_EXPOSURE",
        "100"
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

# ???? ?? ?? ???: 60 Hz
ARDUCAM_POWER_LINE_FREQUENCY = int(
    os.getenv(
        "ARDUCAM_POWER_LINE_FREQUENCY",
        "2"
    )
)

ARDUCAM_AUTO_WHITE_BALANCE = env_bool(
    "ARDUCAM_AUTO_WHITE_BALANCE",
    True
)

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

ARDUCAM_AUTO_FOCUS = int(
    os.getenv(
        "ARDUCAM_AUTO_FOCUS",
        "0"
    )
)

ARDUCAM_FOCUS_ABSOLUTE = int(
    os.getenv(
        "ARDUCAM_FOCUS_ABSOLUTE",
        "144"
    )
)

ARDUCAM_CONTROL_SETTLE_SECONDS = float(
    os.getenv(
        "ARDUCAM_CONTROL_SETTLE_SECONDS",
        "0.3"
    )
)

ARDUCAM_CONFIGURE_ON_STARTUP = env_bool(
    "ARDUCAM_CONFIGURE_ON_STARTUP",
    True
)

ARDUCAM_CONFIGURE_BEFORE_CAPTURE = env_bool(
    "ARDUCAM_CONFIGURE_BEFORE_CAPTURE",
    True
)

# Auto WB? ?? ?? ????? ???? ??? ?? ??
# ?? ? ???? ??? ? ?? ???? ?????.
CAMERA_WARMUP_FRAMES = int(
    os.getenv(
        "CAMERA_WARMUP_FRAMES",
        "15"
    )
)


# =========================================================
# LED
# =========================================================

LED_GPIO_PIN = int(
    os.getenv(
        "LED_GPIO_PIN",
        "18"
    )
)

LED_ACTIVE_HIGH = env_bool(
    "LED_ACTIVE_HIGH",
    True
)

LED_STABILIZE_SECONDS = float(
    os.getenv(
        "LED_STABILIZE_SECONDS",
        "1"
    )
)

# =========================================================
# ??
# =========================================================

CAPTURE_DELAY_SECONDS = int(
    os.getenv(
        "CAPTURE_DELAY_SECONDS",
        "5"
    )
)


CAMERA_SWITCH_DELAY_SECONDS = float(
    os.getenv(
        "CAMERA_SWITCH_DELAY_SECONDS",
        "2"
    )
)


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
# Mock sensor
# =========================================================

USE_MOCK_SENSORS = env_bool(
    "USE_MOCK_SENSORS",
    True
)


# =========================================================
# FastAPI
# =========================================================

app = FastAPI(
    title="FeetFit Hardware API",
    version="4.1.0"
)


# =========================================================
# LED ???
# =========================================================

led = OutputDevice(
    LED_GPIO_PIN,
    active_high=LED_ACTIVE_HIGH,
    initial_value=False
)


# =========================================================
# ?? ??
#
# ???? ? ??? ??????
# measurementSessionId?? ?? ??
# =========================================================

sessions: Dict[int, dict] = {}

session_lock = Lock()

# ??? ?? ?? ?? Lock
# ?? ?? ?? ???? ??? ?? API? ??? ????
# ??? ??? ? ?? ? ?? ??? ????? ??
camera_lock = Lock()


# =========================================================
# Request DTO
# =========================================================

class MeasurementRequest(BaseModel):
    measurementSessionId: int


# =========================================================
# ??? ?? ??
# =========================================================

class HardwareFlowError(Exception):

    def __init__(
        self,
        reason: str,
        detail: str
    ):

        self.reason = reason
        self.detail = detail

        super().__init__(detail)


# =========================================================
# ?? ??
# =========================================================

def get_session(
    session_id: int
) -> dict:

    with session_lock:

        session = sessions.get(
            session_id
        )

        if session is not None:
            # ???? ??? ???? ??? ??
            session = dict(session)

    if session is None:

        raise HardwareFlowError(
            "UNKNOWN",
            f"?? ?? {session_id}? ?? ? ????."
        )

    return session


def update_session(
    session_id: int,
    **kwargs
):

    with session_lock:

        if session_id not in sessions:

            raise HardwareFlowError(
                "UNKNOWN",
                f"?? ?? {session_id}? ?? ? ????."
            )

        sessions[
            session_id
        ].update(kwargs)


# =========================================================
# Backend ?? ??
# =========================================================

def patch_backend_status(
    session_id: int,
    status: str,
    failure_reason: Optional[str] = None,
    failure_detail: Optional[str] = None
):

    session = get_session(
        session_id
    )


    url = (
        f"{BACKEND_BASE_URL}"
        f"/api/measurement-sessions/"
        f"{session_id}/status"
    )


    headers = {
        "Authorization":
            session["authorization"]
    }


    params = {
        "status":
            status
    }


    if failure_reason is not None:

        params[
            "failureReason"
        ] = failure_reason


    if failure_detail is not None:

        params[
            "failureDetail"
        ] = failure_detail


    print()
    print(
        "========================================"
    )

    print(
        f"[BACKEND STATUS] {status}"
    )

    print(
        f"[SESSION] {session_id}"
    )

    print(
        "========================================"
    )


    try:

        response = requests.patch(
            url,
            headers=headers,
            params=params,
            timeout=BACKEND_TIMEOUT_SECONDS
        )


    except requests.Timeout:

        raise HardwareFlowError(
            "NETWORK_ERROR",
            "??? ?? ?? ?? timeout"
        )


    except requests.RequestException as e:

        raise HardwareFlowError(
            "NETWORK_ERROR",
            f"??? ?? ??: {e}"
        )


    print(
        "[BACKEND RESPONSE]",
        response.status_code,
        response.text
    )


    if response.status_code in (
        401,
        403
    ):

        raise HardwareFlowError(
            "TOKEN_EXPIRED",
            "??? ?? ??? ???? ????."
        )


    if not response.ok:

        raise HardwareFlowError(
            "UNKNOWN",
            (
                "??? ?? ?? ??: "
                f"{response.status_code} "
                f"{response.text}"
            )
        )


    update_session(
        session_id,
        status=status
    )


    return response

# =========================================================
# FAILED ??
# =========================================================

def send_failed(
    session_id: int,
    reason: str,
    detail: str
):

    print()
    print(
        "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    )

    print(
        "[MEASUREMENT FAILED]"
    )

    print(
        f"Session : {session_id}"
    )

    print(
        f"Reason  : {reason}"
    )

    print(
        f"Detail  : {detail}"
    )

    print(
        "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
    )


    # LED? ?? ????? OFF
    try:
        led.off()

    except Exception:
        pass


    try:

        update_session(
            session_id,
            failed=True,
            status="FAILED"
        )

    except Exception:
        pass


    # ?? PATCH
    try:

        session = get_session(
            session_id
        )


        url = (
            f"{BACKEND_BASE_URL}"
            f"/api/measurement-sessions/"
            f"{session_id}/status"
        )


        response = requests.patch(

            url,

            headers={
                "Authorization":
                    session["authorization"]
            },

            params={
                "status":
                    "FAILED",

                "failureReason":
                    reason,

                "failureDetail":
                    detail
            },

            timeout=
                BACKEND_TIMEOUT_SECONDS
        )


        print(
            "[FAILED PATCH]",
            response.status_code,
            response.text
        )


    except Exception as e:

        print(
            "[FAILED ?? ?? ??]",
            e
        )


# =========================================================
# AI 202 Accepted ??
# =========================================================

def validate_ai_202(
    response: requests.Response,
    api_name: str
) -> dict:

    print()
    print(
        "========================================"
    )

    print(
        f"[AI {api_name}]"
    )

    print(
        f"HTTP {response.status_code}"
    )

    print(
        response.text
    )

    print(
        "========================================"
    )


    if response.status_code in (
        401,
        403
    ):

        raise HardwareFlowError(
            "TOKEN_EXPIRED",
            (
                f"{api_name} API "
                "Authorization ??"
            )
        )


    if response.status_code in (
        400,
        422
    ):

        raise HardwareFlowError(
            "INVALID_CAPTURE_DATA",
            (
                f"{api_name} ??? ?? ??: "
                f"{response.text}"
            )
        )


    if response.status_code >= 500:

        raise HardwareFlowError(
            "AI_SERVER_ERROR",
            (
                f"{api_name} AI ?? ??: "
                f"{response.status_code} "
                f"{response.text}"
            )
        )


    if response.status_code != 202:

        raise HardwareFlowError(
            "AI_SERVER_ERROR",
            (
                f"{api_name} ???? ?? ??: "
                f"{response.status_code} "
                f"{response.text}"
            )
        )


    try:

        data = response.json()

    except Exception:

        raise HardwareFlowError(
            "AI_SERVER_ERROR",
            f"{api_name} ?? JSON ?? ??"
        )


    if data.get(
        "accepted"
    ) is not True:

        raise HardwareFlowError(
            "AI_SERVER_ERROR",
            (
                f"{api_name} ??? "
                "accepted? true? ????."
            )
        )


    return data

# =========================================================
# LED
# =========================================================

def led_on():

    print()
    print(
        f"[LED] ON - GPIO BCM {LED_GPIO_PIN}"
    )

    led.on()


def led_off():

    print()
    print(
        f"[LED] OFF - GPIO BCM {LED_GPIO_PIN}"
    )

    led.off()


# =========================================================
# Arducam ?? ?? ??
# =========================================================

def configure_arducam(
    device: str,
    camera_name: str
):

    if not Path(device).exists():

        raise HardwareFlowError(
            "DEVICE_DISCONNECTED",
            (
                f"{camera_name} Arducam? ????: "
                f"{device}"
            )
        )


    controls = [
        f"auto_exposure={ARDUCAM_AUTO_EXPOSURE}",
        f"exposure_time_absolute={ARDUCAM_EXPOSURE}",
        f"gain={ARDUCAM_GAIN}",
        (
            "backlight_compensation="
            f"{ARDUCAM_BACKLIGHT_COMPENSATION}"
        ),
        (
            "exposure_dynamic_framerate="
            f"{ARDUCAM_EXPOSURE_DYNAMIC_FRAMERATE}"
        ),
        (
            "power_line_frequency="
            f"{ARDUCAM_POWER_LINE_FREQUENCY}"
        ),
        (
            "white_balance_automatic="
            f"{1 if ARDUCAM_AUTO_WHITE_BALANCE else 0}"
        ),
        f"brightness={ARDUCAM_BRIGHTNESS}",
        f"contrast={ARDUCAM_CONTRAST}",
        f"saturation={ARDUCAM_SATURATION}",
        f"hue={ARDUCAM_HUE}",
        f"hue_automatic={ARDUCAM_HUE_AUTOMATIC}",
        f"gamma={ARDUCAM_GAMMA}",
        f"sharpness={ARDUCAM_SHARPNESS}",
        (
            "focus_automatic_continuous="
            f"{ARDUCAM_AUTO_FOCUS}"
        ),
        f"focus_absolute={ARDUCAM_FOCUS_ABSOLUTE}"
    ]


    command = [
        "v4l2-ctl",
        "-d",
        device,
        "--set-ctrl=" + ",".join(controls)
    ]


    print()
    print("========================================")
    print(f"[ARDUCAM CONFIG] {camera_name}")
    print(f"[DEVICE] {device}")
    print(f"[EXPOSURE] {ARDUCAM_EXPOSURE}")
    print(f"[GAIN] {ARDUCAM_GAIN}")
    print(
        "[AUTO WB] "
        f"{ARDUCAM_AUTO_WHITE_BALANCE}"
    )
    print("========================================")


    try:

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )

    except FileNotFoundError:

        raise HardwareFlowError(
            "CAMERA_ERROR",
            "v4l2-ctl ??? ?? ? ????."
        )

    except subprocess.TimeoutExpired:

        raise HardwareFlowError(
            "CAMERA_ERROR",
            f"{camera_name} Arducam ?? timeout"
        )


    if result.returncode != 0:

        raise HardwareFlowError(
            "CAMERA_ERROR",
            (
                f"{camera_name} Arducam ?? ??: "
                f"{result.stderr.strip()}"
            )
        )


    if ARDUCAM_CONTROL_SETTLE_SECONDS > 0:

        time.sleep(
            ARDUCAM_CONTROL_SETTLE_SECONDS
        )


    print(
        f"[ARDUCAM CONFIG COMPLETE] {camera_name}"
    )

# =========================================================
# ? ?? ? Arducam ??? ?? ??
#
# ?? ? ???? ?? ???? ?? ???? ??? ??? ??
# ??? ?????. ?? ?? ??? ?? ????? ?? ????
# ??? ???? ?? ?????.
# =========================================================

@app.on_event("startup")
def configure_arducams_on_startup():

    if not ARDUCAM_CONFIGURE_ON_STARTUP:
        return


    for camera_name, device in (
        ("left_plantar", LEFT_CAMERA_DEVICE),
        ("right_plantar", RIGHT_CAMERA_DEVICE)
    ):

        try:

            configure_arducam(
                device=device,
                camera_name=camera_name
            )

        except HardwareFlowError as e:

            print(
                "[ARDUCAM STARTUP WARNING]",
                camera_name,
                e.reason,
                e.detail
            )


# =========================================================
# ??? ? ? ??
# =========================================================

def capture_photo(
    session_id: int,
    camera_name: str,
    device: str,
    width: int,
    height: int,
    framerate: int
) -> Path:


    if not Path(
        device
    ).exists():

        raise HardwareFlowError(
            "DEVICE_DISCONNECTED",
            (
                f"{camera_name} ???? ????: "
                f"{device}"
            )
        )


    timestamp = time.strftime(
        "%Y%m%d_%H%M%S"
    )


    filename = (
        PHOTO_DIR
        / (
            f"session_{session_id}_"
            f"{camera_name}_"
            f"{timestamp}.jpg"
        )
    )


    print()
    print(
        "========================================"
    )

    print(
        f"[CAMERA] {camera_name}"
    )

    print(
        f"[DEVICE] {device}"
    )

    print(
        f"[RESOLUTION] {width}x{height}"
    )

    print(
        f"[FPS] {framerate}"
    )

    print(
        "========================================"
    )


    command = [

        "ffmpeg",

        "-hide_banner",

        "-loglevel",
        "error",

        "-f",
        "v4l2",

        "-input_format",
        "mjpeg",

        "-video_size",
        f"{width}x{height}",

        "-framerate",
        str(framerate),

        "-i",
        device,
    ]


    # Auto WB? ?? ???? ?? ? ??????
    # ?? CAMERA_WARMUP_FRAMES ???? ?? ? ? ? ?????.
    if CAMERA_WARMUP_FRAMES > 0:

        command.extend([
            "-vf",
            f"select=gte(n\\,{CAMERA_WARMUP_FRAMES})"
        ])


    command.extend([

        "-frames:v",
        "1",

        "-q:v",
        "2",

        "-y",

        str(filename)
    ])


    try:

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30
        )


    except subprocess.TimeoutExpired:

        raise HardwareFlowError(
            "CAMERA_ERROR",
            f"{camera_name} ??? ?? timeout"
        )


    if result.returncode != 0:

        raise HardwareFlowError(
            "CAMERA_ERROR",
            (
                f"{camera_name} ??? ?? ??: "
                f"{result.stderr}"
            )
        )


    if (
        not filename.exists()
        or filename.stat().st_size == 0
    ):

        raise HardwareFlowError(
            "INVALID_CAPTURE_DATA",
            (
                f"{camera_name} ??? ??? "
                "????? ???? ?????."
            )
        )


    print(
        f"[CAMERA SAVE] {filename}"
    )


    return filename

# =========================================================
# ??? 3? ?? ??
# =========================================================

def capture_all_photos(
    session_id: int
) -> dict:

    # ??? 3?? USB? ?? ???? ???
    # ?? ?? ???? ? ?? ??? OPEN???.
    # capture_photo()? subprocess.run()? ??? ffmpeg? ????
    # ?? ??? ???? ?? ? ?? ???? ?????.

    with camera_lock:

        print()
        print("========================================")
        print("[CAMERA SEQUENCE START]")
        print("LEFT ? RIGHT ? DORSAL")
        print("========================================")

        # 1. ?? ?? Arducam
        print()
        print("[CAMERA 1/3] LEFT OPEN")

        if ARDUCAM_CONFIGURE_BEFORE_CAPTURE:

            configure_arducam(
                device=LEFT_CAMERA_DEVICE,
                camera_name="left_plantar"
            )

        left = capture_photo(
            session_id=session_id,
            camera_name="left_plantar",
            device=LEFT_CAMERA_DEVICE,
            width=LEFT_IMAGE_WIDTH,
            height=LEFT_IMAGE_HEIGHT,
            framerate=LEFT_CAMERA_FRAMERATE
        )

        print("[CAMERA 1/3] LEFT CLOSED")

        time.sleep(
            CAMERA_SWITCH_DELAY_SECONDS
        )

        # 2. ??? ?? Arducam
        print()
        print("[CAMERA 2/3] RIGHT OPEN")

        if ARDUCAM_CONFIGURE_BEFORE_CAPTURE:

            configure_arducam(
                device=RIGHT_CAMERA_DEVICE,
                camera_name="right_plantar"
            )

        right = capture_photo(
            session_id=session_id,
            camera_name="right_plantar",
            device=RIGHT_CAMERA_DEVICE,
            width=RIGHT_IMAGE_WIDTH,
            height=RIGHT_IMAGE_HEIGHT,
            framerate=RIGHT_CAMERA_FRAMERATE
        )

        print("[CAMERA 2/3] RIGHT CLOSED")

        time.sleep(
            CAMERA_SWITCH_DELAY_SECONDS
        )

        # 3. ?? ?? ??
        print()
        print("[CAMERA 3/3] DORSAL OPEN")

        dorsal = capture_photo(
            session_id=session_id,
            camera_name="dorsal",
            device=DORSAL_CAMERA_DEVICE,
            width=DORSAL_IMAGE_WIDTH,
            height=DORSAL_IMAGE_HEIGHT,
            framerate=DORSAL_CAMERA_FRAMERATE
        )

        print("[CAMERA 3/3] DORSAL CLOSED")

        print()
        print("========================================")
        print("[CAMERA SEQUENCE COMPLETE]")
        print("========================================")

        return {
            "left": left,
            "right": right,
            "dorsal": dorsal
        }
# =========================================================
# AI ? ?? ??
# =========================================================

def send_photo_to_ai(
    session_id: int,
    photos: dict
) -> dict:


    session = get_session(
        session_id
    )


    url = (
        f"{AI_BASE_URL}"
        "/api/reports/photo-analysis"
    )


    headers = {
        "Authorization":
            session["authorization"]
    }


    data = {
        "measurementSessionId":
            str(session_id)
    }


    try:

        with (

            open(
                photos["dorsal"],
                "rb"
            ) as dorsal_file,

            open(
                photos["left"],
                "rb"
            ) as left_file,

            open(
                photos["right"],
                "rb"
            ) as right_file

        ):


            files = {

                "dorsalFootImage": (

                    photos["dorsal"].name,

                    dorsal_file,

                    "image/jpeg"
                ),


                "leftPlantarFootImage": (

                    photos["left"].name,

                    left_file,

                    "image/jpeg"
                ),


                "rightPlantarFootImage": (

                    photos["right"].name,

                    right_file,

                    "image/jpeg"
                )
            }


            response = requests.post(

                url,

                headers=headers,

                data=data,

                files=files,

                timeout=
                    AI_TIMEOUT_SECONDS
            )


    except requests.Timeout:

        raise HardwareFlowError(
            "NETWORK_ERROR",
            "?? ?? AI ?? timeout"
        )


    except requests.RequestException as e:

        raise HardwareFlowError(
            "NETWORK_ERROR",
            (
                "?? ?? AI ???? ??: "
                f"{e}"
            )
        )


    return validate_ai_202(
        response,
        "PHOTO"
    )


# =========================================================
# ?? ??? ??
# =========================================================

def validate_pressure_values(
    left: list,
    right: list
):


    if len(left) != 12:

        raise HardwareFlowError(
            "INVALID_CAPTURE_DATA",
            (
                "?? ???? "
                f"12?? ????: {len(left)}"
            )
        )


    if len(right) != 12:

        raise HardwareFlowError(
            "INVALID_CAPTURE_DATA",
            (
                "??? ???? "
                f"12?? ????: {len(right)}"
            )
        )


    for value in left + right:

        try:

            number = float(
                value
            )


        except Exception:

            raise HardwareFlowError(
                "INVALID_CAPTURE_DATA",
                (
                    "???? ??? ?? "
                    "???? ????."
                )
            )


        if not math.isfinite(
            number
        ):

            raise HardwareFlowError(
                "INVALID_CAPTURE_DATA",
                (
                    "???? NaN ?? "
                    "Infinity? ????."
                )
            )

# =========================================================
# ?? ???? ??
#
# ? ? ??? ?? ??
# ADS1115 + CD74HC4067 ?? ??
# =========================================================

def measure_pressure() -> dict:


    print()
    print(
        "========================================"
    )

    print(
        "[PRESSURE] ?? ??"
    )

    print(
        "========================================"
    )


    if not USE_MOCK_SENSORS:

        raise HardwareFlowError(
            "PRESSURE_SENSOR_ERROR",
            (
                "measure_pressure()? "
                "?? FSR ?? ??? ???? ???."
            )
        )


    # -----------------------------------------------------
    # ????
    # -----------------------------------------------------

    left = [
        92.2,
        1.0,
        605.4,
        8.6,
        29.3,
        8430.6,
        7289.3,
        34.5,
        4151.6,
        14356.8,
        272.2,
        15257.0
    ]


    right = [
        546.9,
        752.2,
        683.4,
        101.4,
        33.0,
        1982.6,
        3446.1,
        64.3,
        6026.4,
        16111.5,
        11520.5,
        13116.1
    ]


    validate_pressure_values(
        left,
        right
    )


    print(
        "[LEFT PRESSURE]",
        left
    )

    print(
        "[RIGHT PRESSURE]",
        right
    )


    return {

        "left":
            left,

        "right":
            right
    }


# =========================================================
# AI ? ?? ??
# =========================================================

def send_pressure_to_ai(
    session_id: int,
    pressure: dict
) -> dict:


    session = get_session(
        session_id
    )


    left = pressure[
        "left"
    ]

    right = pressure[
        "right"
    ]


    validate_pressure_values(
        left,
        right
    )


    url = (
        f"{AI_BASE_URL}"
        "/api/reports/"
        "daily-foot-analysis/"
        "pressure-heatmap"
    )


    payload = {

        "measurementSessionId":
            session_id,

        "leftPressureValues":
            left,

        "rightPressureValues":
            right
    }


    try:

        response = requests.post(

            url,

            headers={
                "Authorization":
                    session["authorization"]
            },

            json=payload,

            timeout=
                AI_TIMEOUT_SECONDS
        )


    except requests.Timeout:

        raise HardwareFlowError(
            "NETWORK_ERROR",
            "?? ?? AI ?? timeout"
        )


    except requests.RequestException as e:

        raise HardwareFlowError(
            "NETWORK_ERROR",
            (
                "?? ?? AI ???? ??: "
                f"{e}"
            )
        )


    return validate_ai_202(
        response,
        "PRESSURE"
    )


# =========================================================
# ?? ?? ??
#
# ? ?? ??? ?? ??? ??
# =========================================================

def measure_environment() -> dict:


    print()
    print(
        "========================================"
    )

    print(
        "[ENVIRONMENT] ??? ??"
    )

    print(
        "========================================"
    )


    if not USE_MOCK_SENSORS:

        raise HardwareFlowError(
            "INVALID_CAPTURE_DATA",
            (
                "measure_environment()? "
                "?? ??? ?? ??? ???? ???."
            )
        )


    # ????
    temperature = 28.1
    humidity = 52.0


    print(
        f"[TEMPERATURE] {temperature}"
    )

    print(
        f"[HUMIDITY] {humidity}"
    )


    return {

        "temperature":
            temperature,

        "humidity":
            humidity
    }

# =========================================================
# ??? ??
# =========================================================

def validate_environment_values(
    before_temperature,
    before_humidity,
    after_temperature,
    after_humidity
):


    values = [

        before_temperature,

        before_humidity,

        after_temperature,

        after_humidity
    ]


    for value in values:

        if value is None:

            raise HardwareFlowError(
                "INVALID_CAPTURE_DATA",
                "??? ???? ???????."
            )


        try:

            number = float(
                value
            )


        except Exception:

            raise HardwareFlowError(
                "INVALID_CAPTURE_DATA",
                "??? ???? ??? ????."
            )


        if not math.isfinite(
            number
        ):

            raise HardwareFlowError(
                "INVALID_CAPTURE_DATA",
                "??? ???? ???? ????."
            )


    if not (
        0
        <= float(before_humidity)
        <= 100
    ):

        raise HardwareFlowError(
            "INVALID_CAPTURE_DATA",
            "?? ? ???? 0~100 ??? ??????."
        )


    if not (
        0
        <= float(after_humidity)
        <= 100
    ):

        raise HardwareFlowError(
            "INVALID_CAPTURE_DATA",
            "?? ? ???? 0~100 ??? ??????."
        )

# =========================================================
# AI ? ?? ??
# =========================================================

def send_environment_to_ai(
    session_id: int,
    before_temperature: float,
    before_humidity: float,
    after_temperature: float,
    after_humidity: float
) -> dict:


    session = get_session(
        session_id
    )


    validate_environment_values(

        before_temperature,

        before_humidity,

        after_temperature,

        after_humidity
    )


    url = (
        f"{AI_BASE_URL}"
        "/api/reports/"
        "daily-foot-analysis/"
        "environment"
    )


    payload = {

        "measurementSessionId":
            session_id,

        "beforeTemperatureCelsius":
            before_temperature,

        "beforeHumidityPercent":
            before_humidity,

        "afterTemperatureCelsius":
            after_temperature,

        "afterHumidityPercent":
            after_humidity
    }


    try:

        response = requests.post(

            url,

            headers={
                "Authorization":
                    session["authorization"]
            },

            json=payload,

            timeout=
                AI_TIMEOUT_SECONDS
        )


    except requests.Timeout:

        raise HardwareFlowError(
            "NETWORK_ERROR",
            "?? ?? AI ?? timeout"
        )


    except requests.RequestException as e:

        raise HardwareFlowError(
            "NETWORK_ERROR",
            (
                "?? ?? AI ???? ??: "
                f"{e}"
            )
        )


    return validate_ai_202(
        response,
        "ENVIRONMENT"
    )

# =========================================================
# API - Arducam ??? ?? ???
#
# ???? ?? ???? ?? ???? ?? ? ?? ??:
# POST /cameras/configure
# =========================================================

@app.post(
    "/cameras/configure"
)
def configure_cameras():

    with camera_lock:

        configure_arducam(
            device=LEFT_CAMERA_DEVICE,
            camera_name="left_plantar"
        )

        configure_arducam(
            device=RIGHT_CAMERA_DEVICE,
            camera_name="right_plantar"
        )


    return {
        "configured": True,
        "left": LEFT_CAMERA_DEVICE,
        "right": RIGHT_CAMERA_DEVICE,
        "exposure": ARDUCAM_EXPOSURE,
        "gain": ARDUCAM_GAIN,
        "autoWhiteBalance": ARDUCAM_AUTO_WHITE_BALANCE
    }


# =========================================================
# API - health
# =========================================================

@app.get(
    "/health"
)
def health():

    return {

        "status":
            "ok",

        "ledGPIO":
            LED_GPIO_PIN
    }


# =========================================================
# API - ??? ??
# =========================================================

@app.get(
    "/cameras"
)
def cameras():

    return {

        "leftPlantar": {

            "device":
                LEFT_CAMERA_DEVICE,

            "exists":
                Path(
                    LEFT_CAMERA_DEVICE
                ).exists()
        },


        "rightPlantar": {

            "device":
                RIGHT_CAMERA_DEVICE,

            "exists":
                Path(
                    RIGHT_CAMERA_DEVICE
                ).exists()
        },


        "dorsal": {

            "device":
                DORSAL_CAMERA_DEVICE,

            "exists":
                Path(
                    DORSAL_CAMERA_DEVICE
                ).exists()
        }
    }

# =========================================================
# API - LED ???
#
# ?? ????? Backend? ??? ?? ??.
# ?? ????
# =========================================================

@app.post(
    "/led/on"
)
def test_led_on():

    led_on()

    return {
        "status":
            "on"
    }


@app.post(
    "/led/off"
)
def test_led_off():

    led_off()

    return {
        "status":
            "off"
    }


# =========================================================
# 0. ?? ?? ??
#
# Backend ? Raspberry Pi
#
# POST /measurement/start
#
# ???:
#
# - sessionId ??
# - Authorization ??
# - ?? ? ??? ??
#
# ??? ?? ???? ??.
# =========================================================

@app.post(
    "/measurement/start"
)
def measurement_start(

    request:
        MeasurementRequest,

    authorization:
        Optional[str]
        = Header(
            default=None
        )
):


    if authorization is None:

        raise HTTPException(
            status_code=401,
            detail=(
                "Authorization ??? ????."
            )
        )


    session_id = (
        request.measurementSessionId
    )


    # ?? ??
    with session_lock:

        sessions[
            session_id
        ] = {

            "measurementSessionId":
                session_id,

            "authorization":
                authorization,

            "status":
                "WAITING_FOR_PHOTO",

            "failed":
                False,

            "photoInProgress":
                False,

            "photoAccepted":
                False,

            "sensorInProgress":
                False,

            "pressureAccepted":
                False,

            "environmentAccepted":
                False,

            "hardwareFinished":
                False,

            "createdAt":
                time.time()
        }


    print()
    print(
        "========================================"
    )

    print(
        "[NEW SESSION]"
    )

    print(
        f"measurementSessionId = {session_id}"
    )

    print(
        "Authorization ?? ??"
    )

    print(
        "========================================"
    )


    try:

        # -------------------------------------------------
        # ?? ? ???
        # -------------------------------------------------

        before = (
            measure_environment()
        )


        update_session(

            session_id,

            beforeTemperature=
                before[
                    "temperature"
                ],

            beforeHumidity=
                before[
                    "humidity"
                ]
        )


        print(
            "[BEFORE ENVIRONMENT SAVED]"
        )


        return {

            "accepted":
                True,

            "measurementSessionId":
                session_id,

            "status":
                "WAITING_FOR_PHOTO",

            "beforeEnvironmentMeasured":
                True
        }


    except HardwareFlowError as e:

        send_failed(
            session_id,
            e.reason,
            e.detail
        )


        raise HTTPException(
            status_code=500,
            detail=e.detail
        )


    except Exception as e:

        send_failed(
            session_id,
            "UNKNOWN",
            str(e)
        )


        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# =========================================================
# 1. ?? ?? API
#
# Backend ? Pi
#
# POST /measurement/photo/start
#
# CAPTURING_PHOTO
# ?
# LED ON
# ?
# 3? ??? ??
# ?
# LED OFF
# ?
# AI PHOTO API
# ?
# 202
# ?
# WAITING_FOR_PRESSURE
# =========================================================

@app.post(
    "/measurement/photo/start",
    status_code=202
)
def measurement_photo_start(
    request:
        MeasurementRequest
):


    session_id = (
        request.measurementSessionId
    )


    try:

        session = get_session(
            session_id
        )


        if session.get(
            "failed",
            False
        ):

            raise HardwareFlowError(
                "UNKNOWN",
                "?? FAILED ??? ?????."
            )


        if session.get(
            "photoInProgress",
            False
        ):

            raise HardwareFlowError(
                "UNKNOWN",
                "?? ??? ?? ?? ????."
            )


        if session.get(
            "photoAccepted",
            False
        ):

            raise HardwareFlowError(
                "UNKNOWN",
                "?? ?? ?? ??? ??? ?????."
            )


        update_session(
            session_id,
            photoInProgress=True
        )


        # -------------------------------------------------
        # ?? ??
        # -------------------------------------------------

        patch_backend_status(
            session_id,
            "CAPTURING_PHOTO"
        )


        photos = None


        # -------------------------------------------------
        # LED + ??
        #
        # ?? ??? ?? finally?? LED OFF
        # -------------------------------------------------

        try:

            print()
            print(
                f"[CAMERA] "
                f"{CAPTURE_DELAY_SECONDS}? ? ??"
            )


            time.sleep(
                CAPTURE_DELAY_SECONDS
            )


            # LED ON
            led_on()


            # ?? ???
            time.sleep(
                LED_STABILIZE_SECONDS
            )


            # ?? 3?
            photos = (
                capture_all_photos(
                    session_id
                )
            )


        finally:

            # ? ?? ??/?? ???? ??? LED OFF
            led_off()


        # -------------------------------------------------
        # ?? ?? ??
        # -------------------------------------------------

        update_session(

            session_id,

            dorsalImage=
                str(
                    photos["dorsal"]
                ),

            leftPlantarImage=
                str(
                    photos["left"]
                ),

            rightPlantarImage=
                str(
                    photos["right"]
                )
        )

        # -------------------------------------------------
        # AI ?? API
        #
        # ?? ??? ???
        # ?? ?? ? 202??? ???.
        # -------------------------------------------------

        ai_result = (
            send_photo_to_ai(
                session_id,
                photos
            )
        )


        update_session(

            session_id,

            photoInProgress=
                False,

            photoAccepted=
                True,

            photoRequestId=
                ai_result.get(
                    "requestId"
                ),

            photoPipeline=
                ai_result.get(
                    "pipeline"
                )
        )


        # -------------------------------------------------
        # ?? ?? ?
        # -------------------------------------------------

        patch_backend_status(
            session_id,
            "WAITING_FOR_PRESSURE"
        )


        print()
        print(
            "========================================"
        )

        print(
            "[PHOTO STEP COMPLETE]"
        )

        print(
            "AI PHOTO ? 202 Accepted"
        )

        print(
            "Status ? WAITING_FOR_PRESSURE"
        )

        print(
            "========================================"
        )


        return {

            "accepted":
                True,

            "status":
                "QUEUED",

            "measurementSessionId":
                session_id,

            "analysisType":
                "PHOTO",

            "aiRequestId":
                ai_result.get(
                    "requestId"
                )
        }


    except HardwareFlowError as e:

        try:

            update_session(
                session_id,
                photoInProgress=False
            )

        except Exception:
            pass


        send_failed(
            session_id,
            e.reason,
            e.detail
        )


        raise HTTPException(
            status_code=500,
            detail=e.detail
        )


    except Exception as e:

        try:

            update_session(
                session_id,
                photoInProgress=False
            )

        except Exception:
            pass


        send_failed(
            session_id,
            "UNKNOWN",
            str(e)
        )


        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
# =========================================================
# 2. ?? + ??? API
#
# Backend ? Pi
#
# POST /measurement/sensor/start
#
# MEASURING_PRESSURE
# ?
# FSR ?? 12?
# ?
# ?? ? ???
# ?
# AI PRESSURE ? 202
# ?
# AI ENVIRONMENT ? 202
# ?
# ANALYZING
# ?
# ? ???? ?? ?
# =========================================================

@app.post(
    "/measurement/sensor/start",
    status_code=202
)
def measurement_sensor_start(
    request:
        MeasurementRequest
):


    session_id = (
        request.measurementSessionId
    )


    try:

        session = get_session(
            session_id
        )


        if session.get(
            "failed",
            False
        ):

            raise HardwareFlowError(
                "UNKNOWN",
                "?? FAILED ??? ?????."
            )


        if not session.get(
            "photoAccepted",
            False
        ):

            raise HardwareFlowError(
                "INVALID_CAPTURE_DATA",
                (
                    "?? ?? ??? ?? "
                    "202 Accepted ?? ?????."
                )
            )


        if session.get(
            "sensorInProgress",
            False
        ):

            raise HardwareFlowError(
                "UNKNOWN",
                "?? ??? ?? ?? ????."
            )


        if session.get(
            "hardwareFinished",
            False
        ):

            raise HardwareFlowError(
                "UNKNOWN",
                "?? ???? ??? ??? ?????."
            )


        update_session(
            session_id,
            sensorInProgress=True
        )


        # -------------------------------------------------
        # ?? ?? ??
        # -------------------------------------------------

        patch_backend_status(
            session_id,
            "MEASURING_PRESSURE"
        )


        # -------------------------------------------------
        # 1. FSR
        # -------------------------------------------------

        pressure = (
            measure_pressure()
        )


        left_values = (
            pressure["left"]
        )

        right_values = (
            pressure["right"]
        )


        validate_pressure_values(
            left_values,
            right_values
        )


        # -------------------------------------------------
        # 2. ?? ? ???
        # -------------------------------------------------

        after = (
            measure_environment()
        )


        after_temperature = (
            after[
                "temperature"
            ]
        )

        after_humidity = (
            after[
                "humidity"
            ]
        )


        update_session(

            session_id,

            leftPressureValues=
                left_values,

            rightPressureValues=
                right_values,

            afterTemperature=
                after_temperature,

            afterHumidity=
                after_humidity
        )


        # ?? session ?? ????
        session = get_session(
            session_id
        )


        before_temperature = (
            session.get(
                "beforeTemperature"
            )
        )

        before_humidity = (
            session.get(
                "beforeHumidity"
            )
        )
        # -------------------------------------------------
        # 3. AI ?? API
        # -------------------------------------------------

        pressure_result = (
            send_pressure_to_ai(
                session_id,
                pressure
            )
        )


        update_session(

            session_id,

            pressureAccepted=
                True,

            pressureRequestId=
                pressure_result.get(
                    "requestId"
                )
        )


        # -------------------------------------------------
        # 4. AI ?? API
        # -------------------------------------------------

        environment_result = (
            send_environment_to_ai(

                session_id,

                before_temperature,

                before_humidity,

                after_temperature,

                after_humidity
            )
        )


        update_session(

            session_id,

            environmentAccepted=
                True,

            environmentRequestId=
                environment_result.get(
                    "requestId"
                )
        )


        # -------------------------------------------------
        # 5. ???? ??? ??
        # -------------------------------------------------

        patch_backend_status(
            session_id,
            "ANALYZING"
        )


        update_session(

            session_id,

            sensorInProgress=
                False,

            hardwareFinished=
                True
        )


        print()
        print(
            "========================================"
        )

        print(
            "????? HARDWARE FLOW COMPLETE ?????"
        )

        print()

        print(
            "PHOTO       ? 202 Accepted"
        )

        print(
            "PRESSURE    ? 202 Accepted"
        )

        print(
            "ENVIRONMENT ? 202 Accepted"
        )

        print(
            "STATUS      ? ANALYZING"
        )

        print()

        print(
            "COMPLETED? Backend? ?? ?????."
        )

        print(
            "========================================"
        )


        return {

            "accepted":
                True,

            "status":
                "ANALYZING",

            "measurementSessionId":
                session_id,

            "pressureRequestId":
                pressure_result.get(
                    "requestId"
                ),

            "environmentRequestId":
                environment_result.get(
                    "requestId"
                ),

            "hardwareFinished":
                True
        }


    except HardwareFlowError as e:

        try:

            update_session(
                session_id,
                sensorInProgress=False
            )

        except Exception:
            pass


        send_failed(
            session_id,
            e.reason,
            e.detail
        )


        raise HTTPException(
            status_code=500,
            detail=e.detail
        )


    except Exception as e:

        try:

            update_session(
                session_id,
                sensorInProgress=False
            )

        except Exception:
            pass


        send_failed(
            session_id,
            "UNKNOWN",
            str(e)
        )


        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
# =========================================================
# ???? ?? ??
#
# Authorization? ???? ??.
# =========================================================

@app.get(
    "/measurement/{session_id}"
)
def measurement_status(
    session_id: int
):


    try:

        session = get_session(
            session_id
        )


    except HardwareFlowError as e:

        raise HTTPException(
            status_code=404,
            detail=e.detail
        )


    return {

        key: value

        for key, value
        in session.items()

        if key != "authorization"
    }
