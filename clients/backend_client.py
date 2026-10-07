import os

import requests

from session_store import get_session


BACKEND_BASE_URL = os.getenv(
    "BACKEND_BASE_URL",
    "http://34.209.169.111"
).rstrip("/")


def patch_status(
    session_id: int,
    status: str,
    photo_capture_attempt: int | None = None
):
    """
    측정 세션 상태를 Backend로 전송합니다.

    일반 단계:
        patch_status(
            session_id,
            "MEASURING_PRESSURE"
        )

    사진 단계:
        patch_status(
            session_id,
            "CAPTURING_PHOTO",
            photo_capture_attempt=1
        )
    """

    session = get_session(
        session_id
    )

    url = (
        f"{BACKEND_BASE_URL}"
        f"/api/measurement-sessions/"
        f"{session_id}/status"
    )

    params = {
        "status": status
    }

    # 사진 촬영 관련 상태인 경우에만
    # photoCaptureAttempt를 추가
    if photo_capture_attempt is not None:

        params[
            "photoCaptureAttempt"
        ] = photo_capture_attempt

    response = requests.patch(
        url,
        headers={
            "Authorization":
                session["authorization"]
        },
        params=params,
        timeout=15
    )

    response.raise_for_status()

    print(
        "[BACKEND STATUS]",
        f"session={session_id}",
        f"status={status}",
        f"attempt={photo_capture_attempt}",
        f"http={response.status_code}"
    )

    return response


def send_hardware_failed(
    session_id: int,
    reason: str,
    message: str,
    detail: str,
    photo_capture_attempt: int | None = None
):
    """
    실제 하드웨어 측정 실패를
    Backend에 FAILED 상태로 전달합니다.

    주의:
    ArUco 마커 가림 등
    AI 검증 실패에는 사용하지 않습니다.
    """

    session = get_session(
        session_id
    )

    url = (
        f"{BACKEND_BASE_URL}"
        f"/api/measurement-sessions/"
        f"{session_id}/status"
    )

    params = {
        "status":
            "FAILED",

        "failureReason":
            reason,

        "failureMessage":
            message,

        "failureDetail":
            detail
    }

    if photo_capture_attempt is not None:

        params[
            "photoCaptureAttempt"
        ] = photo_capture_attempt

    try:

        response = requests.patch(
            url,
            headers={
                "Authorization":
                    session["authorization"]
            },
            params=params,
            timeout=15
        )

        print(
            "[HARDWARE FAILED]",
            f"session={session_id}",
            f"attempt={photo_capture_attempt}",
            f"http={response.status_code}",
            response.text
        )

        return response

    except Exception as e:

        print(
            "[FAILED 전송 실패]",
            f"session={session_id}",
            repr(e)
        )

        return None
