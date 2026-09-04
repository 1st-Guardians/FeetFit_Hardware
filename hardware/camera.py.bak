import subprocess
import time

from pathlib import Path
from threading import Lock

from config import (
    # 카메라 장치
    LEFT_CAMERA_DEVICE,
    RIGHT_CAMERA_DEVICE,
    DORSAL_CAMERA_DEVICE,

    # 왼발
    LEFT_IMAGE_WIDTH,
    LEFT_IMAGE_HEIGHT,
    LEFT_CAMERA_FRAMERATE,

    # 오른발
    RIGHT_IMAGE_WIDTH,
    RIGHT_IMAGE_HEIGHT,
    RIGHT_CAMERA_FRAMERATE,

    # 상단
    DORSAL_IMAGE_WIDTH,
    DORSAL_IMAGE_HEIGHT,
    DORSAL_CAMERA_FRAMERATE,

    # Arducam 설정
    ARDUCAM_AUTO_EXPOSURE,
    ARDUCAM_EXPOSURE,
    ARDUCAM_GAIN,
    ARDUCAM_BACKLIGHT_COMPENSATION,
    ARDUCAM_EXPOSURE_DYNAMIC_FRAMERATE,
    ARDUCAM_POWER_LINE_FREQUENCY,
    ARDUCAM_AUTO_WHITE_BALANCE,
    ARDUCAM_BRIGHTNESS,
    ARDUCAM_CONTRAST,
    ARDUCAM_SATURATION,
    ARDUCAM_HUE,
    ARDUCAM_HUE_AUTOMATIC,
    ARDUCAM_GAMMA,
    ARDUCAM_SHARPNESS,
    ARDUCAM_AUTO_FOCUS,
    ARDUCAM_FOCUS_ABSOLUTE,
    ARDUCAM_CONTROL_SETTLE_SECONDS,
    ARDUCAM_CONFIGURE_BEFORE_CAPTURE,
    ARDUCAM_CONFIGURE_ON_STARTUP,

    # 촬영
    CAMERA_WARMUP_FRAMES,
    CAMERA_SWITCH_DELAY_SECONDS,
    PHOTO_DIR,
)

from errors import HardwareMeasurementError


# =========================================================
# 카메라 Lock
#
# 서로 다른 측정 세션에서 동시에 카메라 API가 호출되어도
# 한 번에 하나의 촬영 흐름만 실행 
# =========================================================

camera_lock = Lock()

# =========================================================
# Arducam 설정 적용
#
# 왼발 / 오른발 Arducam에만 사용
#
# 현재 정상 색으로 확인한 값:
# - Manual Exposure
# - Exposure 100
# - Gain 0
# - Auto White Balance
# =========================================================

def configure_arducam(
    device: str,
    camera_name: str
):

    # -----------------------------------------------------
    # 장치 존재 여부
    # -----------------------------------------------------

    if not Path(device).exists():

        raise HardwareMeasurementError(
            reason="DEVICE_DISCONNECTED",

            message=(
                "?? ??? ??????. "
                "?? ??????."
            ),

            detail=(
                f"{camera_name} Arducam ??? "
                f"?? ? ????: {device}"
            )
        )


    # -----------------------------------------------------
    # v4l2 control
    # -----------------------------------------------------

    controls = [

        f"auto_exposure="
        f"{ARDUCAM_AUTO_EXPOSURE}",

        f"exposure_time_absolute="
        f"{ARDUCAM_EXPOSURE}",

        f"gain="
        f"{ARDUCAM_GAIN}",

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

        f"brightness="
        f"{ARDUCAM_BRIGHTNESS}",

        f"contrast="
        f"{ARDUCAM_CONTRAST}",

        f"saturation="
        f"{ARDUCAM_SATURATION}",

        f"hue="
        f"{ARDUCAM_HUE}",

        f"hue_automatic="
        f"{ARDUCAM_HUE_AUTOMATIC}",

        f"gamma="
        f"{ARDUCAM_GAMMA}",

        f"sharpness="
        f"{ARDUCAM_SHARPNESS}",

        (
            "focus_automatic_continuous="
            f"{ARDUCAM_AUTO_FOCUS}"
        ),

        f"focus_absolute="
        f"{ARDUCAM_FOCUS_ABSOLUTE}"
    ]


    command = [

        "v4l2-ctl",

        "-d",
        device,

        "--set-ctrl="
        + ",".join(controls)
    ]


    print()
    print(
        "========================================"
    )

    print(
        f"[ARDUCAM CONFIG] {camera_name}"
    )

    print(
        f"[DEVICE] {device}"
    )

    print(
        f"[EXPOSURE] {ARDUCAM_EXPOSURE}"
    )

    print(
        f"[GAIN] {ARDUCAM_GAIN}"
    )

    print(
        f"[AUTO WB] {ARDUCAM_AUTO_WHITE_BALANCE}"
    )

    print(
        "========================================"
    )

    # -----------------------------------------------------
    # 설정 실행
    # -----------------------------------------------------

    try:

        result = subprocess.run(

            command,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            text=True,

            timeout=5
        )


    except FileNotFoundError:

        raise HardwareMeasurementError(
            reason="CAMERA_ERROR",

            message=(
                "사진 촬영에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                "v4l2-ctl 명령을 찾을 수 없습니다."
            )
        )


    except subprocess.TimeoutExpired:

        raise HardwareMeasurementError(
            reason="CAMERA_ERROR",

            message=(
                "사진 촬영에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                f"{camera_name} Arducam "
                "설정 timeout"
            )
        )


    # -----------------------------------------------------
    # v4l2 설정 자체 실패
    # -----------------------------------------------------

    if result.returncode != 0:

        raise HardwareMeasurementError(
            reason="CAMERA_ERROR",

            message=(
                "사진 촬영에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                f"{camera_name} Arducam 설정 실패: "
                f"{result.stderr.strip()}"
            )
        )


    # -----------------------------------------------------
    # 설정 안정화
    # -----------------------------------------------------

    if (
        ARDUCAM_CONTROL_SETTLE_SECONDS
        > 0
    ):

        time.sleep(
            ARDUCAM_CONTROL_SETTLE_SECONDS
        )


    print(
        f"[ARDUCAM CONFIG COMPLETE] "
        f"{camera_name}"
    )
# =========================================================
# 서버 시작 시 Arducam 초기 설정
#
# main.py startup에서 호출
#
# 여기서는 서버 자체를 죽이지 않고 warning만 출력.
# 실제 촬영 직전에 configure_arducam()을 다시 호출함.
# =========================================================

def configure_arducams_on_startup():

    if not ARDUCAM_CONFIGURE_ON_STARTUP:
        return

    cameras = [

        (
            "left_plantar",
            LEFT_CAMERA_DEVICE
        ),

        (
            "right_plantar",
            RIGHT_CAMERA_DEVICE
        )
    ]


    for (
        camera_name,
        device
    ) in cameras:

        try:

            configure_arducam(
                device=device,
                camera_name=camera_name
            )


        except HardwareMeasurementError as e:

            print()
            print(
                "[ARDUCAM STARTUP WARNING]"
            )

            print(
                f"Camera : {camera_name}"
            )

            print(
                f"Reason : {e.reason}"
            )

            print(
                f"Detail : {e.detail}"
            )


# =========================================================
# 카메라 한 대 촬영
# =========================================================

def capture_photo(
    session_id: int,
    camera_name: str,
    device: str,
    width: int,
    height: int,
    framerate: int
) -> Path:


    # -----------------------------------------------------
    # 장치 존재 확인
    # -----------------------------------------------------

    if not Path(
        device
    ).exists():

        raise HardwareMeasurementError(
            reason="DEVICE_DISCONNECTED",

            message=(
                "사진 촬영에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                f"{camera_name} 카메라 장치를 "
                f"찾을 수 없습니다: {device}"
            )
        )


    # -----------------------------------------------------
    # 파일명
    # -----------------------------------------------------

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
        f"[RESOLUTION] "
        f"{width}x{height}"
    )

    print(
        f"[FPS] {framerate}"
    )

    print(
        "========================================"
    )

    # -----------------------------------------------------
    # ffmpeg 명령
    # -----------------------------------------------------

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


    # -----------------------------------------------------
    # Auto WB 안정화용 warmup
    #
    # 처음 N frame 버리고 다음 프레임 저장
    # -----------------------------------------------------

    if CAMERA_WARMUP_FRAMES > 0:

        command.extend([

            "-vf",

            (
                "select="
                f"gte(n\\,{CAMERA_WARMUP_FRAMES})"
            )
        ])


    # -----------------------------------------------------
    # JPEG 한 장 저장
    # -----------------------------------------------------

    command.extend([

        "-frames:v",
        "1",

        "-q:v",
        "2",

        "-y",

        str(filename)
    ])


    # -----------------------------------------------------
    # ffmpeg 실행
    # -----------------------------------------------------

    try:

        result = subprocess.run(

            command,

            stdout=subprocess.PIPE,

            stderr=subprocess.PIPE,

            text=True,

            timeout=30
        )


    except subprocess.TimeoutExpired:

        raise HardwareMeasurementError(
            reason="CAMERA_ERROR",

            message=(
                "사진 촬영에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                f"{camera_name} "
                "카메라 촬영 timeout"
            )
        )


    except FileNotFoundError:

        raise HardwareMeasurementError(
            reason="CAMERA_ERROR",

            message=(
                "사진 촬영에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                "ffmpeg 명령을 찾을 수 없습니다."
            )
        )
    # -----------------------------------------------------
    # ffmpeg 오류
    # -----------------------------------------------------

    if result.returncode != 0:

        raise HardwareMeasurementError(
            reason="CAMERA_ERROR",

            message=(
                "사진 촬영에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                f"{camera_name} 카메라 촬영 실패: "
                f"{result.stderr.strip()}"
            )
        )


    # -----------------------------------------------------
    # 파일 검증
    # -----------------------------------------------------

    if not filename.exists():

        raise HardwareMeasurementError(
            reason="CAMERA_ERROR",

            message=(
                "사진 촬영에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                f"{camera_name} "
                "이미지 파일이 생성되지 않았습니다."
            )
        )


    if filename.stat().st_size == 0:

        raise HardwareMeasurementError(
            reason="CAMERA_ERROR",

            message=(
                "사진 촬영에 실패했습니다. "
                "다시 시도해주세요."
            ),

            detail=(
                f"{camera_name} "
                "이미지 파일 크기가 0 byte입니다."
            )
        )


    print()
    print(
        f"[CAMERA SAVE] {filename}"
    )


    return filename


# =========================================================
# 카메라 3대 순차 촬영
#
# 순서:
#
# LEFT Arducam
# ?
# RIGHT Arducam
# ?
# DORSAL Webcam
#
# 동시에 카메라 스트림을 열지 않음.
# =========================================================

def capture_all_photos(
    session_id: int
) -> dict:


    with camera_lock:


        print()
        print(
            "========================================"
        )

        print(
            "[CAMERA SEQUENCE START]"
        )

        print(
            "LEFT -> RIGHT -> DORSAL"
        )

        print(
            "========================================"
        )


        # =================================================
        # 1. LEFT
        # =================================================

        print()
        print(
            "[CAMERA 1/3] LEFT OPEN"
        )


        # 촬영 직전 Arducam 설정 재적용
        if ARDUCAM_CONFIGURE_BEFORE_CAPTURE:

            configure_arducam(

                device=
                    LEFT_CAMERA_DEVICE,

                camera_name=
                    "left_plantar"
            )


        left = capture_photo(

            session_id=
                session_id,

            camera_name=
                "left_plantar",

            device=
                LEFT_CAMERA_DEVICE,

            width=
                LEFT_IMAGE_WIDTH,

            height=
                LEFT_IMAGE_HEIGHT,

            framerate=
                LEFT_CAMERA_FRAMERATE
        )


        print(
            "[CAMERA 1/3] LEFT CLOSED"
        )


        # 카메라 전환 안정화
        if CAMERA_SWITCH_DELAY_SECONDS > 0:

            time.sleep(
                CAMERA_SWITCH_DELAY_SECONDS
            )
        # =================================================
        # 2. RIGHT
        # =================================================

        print()
        print(
            "[CAMERA 2/3] RIGHT OPEN"
        )


        if ARDUCAM_CONFIGURE_BEFORE_CAPTURE:

            configure_arducam(

                device=
                    RIGHT_CAMERA_DEVICE,

                camera_name=
                    "right_plantar"
            )


        right = capture_photo(

            session_id=
                session_id,

            camera_name=
                "right_plantar",

            device=
                RIGHT_CAMERA_DEVICE,

            width=
                RIGHT_IMAGE_WIDTH,

            height=
                RIGHT_IMAGE_HEIGHT,

            framerate=
                RIGHT_CAMERA_FRAMERATE
        )


        print(
            "[CAMERA 2/3] RIGHT CLOSED"
        )


        if CAMERA_SWITCH_DELAY_SECONDS > 0:

            time.sleep(
                CAMERA_SWITCH_DELAY_SECONDS
            )


        # =================================================
        # 3. DORSAL
        # =================================================

        print()
        print(
            "[CAMERA 3/3] DORSAL OPEN"
        )


        dorsal = capture_photo(

            session_id=
                session_id,

            camera_name=
                "dorsal",

            device=
                DORSAL_CAMERA_DEVICE,

            width=
                DORSAL_IMAGE_WIDTH,

            height=
                DORSAL_IMAGE_HEIGHT,

            framerate=
                DORSAL_CAMERA_FRAMERATE
        )


        print(
            "[CAMERA 3/3] DORSAL CLOSED"
        )


        print()
        print(
            "========================================"
        )

        print(
            "[CAMERA SEQUENCE COMPLETE]"
        )

        print(
            "========================================"
        )


        return {

            "left":
                left,

            "right":
                right,

            "dorsal":
                dorsal
        }


# =========================================================
# 카메라 상태 확인
# =========================================================

def get_camera_status():

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
