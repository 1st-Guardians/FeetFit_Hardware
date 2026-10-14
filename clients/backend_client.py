import os

import requests

from session_store import get_session


BACKEND_BASE_URL = os.getenv(
    "BACKEND_BASE_URL",
    "http://34.209.169.111",
).rstrip("/")


# ============================================================
# BACKEND STATUS PATCH
# ============================================================

def patch_status(
    session_id: int,
    status: str,
    photo_capture_attempt: int | None = None,
    pressure_measurement_attempt: int | None = None,
    failure_reason: str | None = None,
    failure_detail: str | None = None,
):
    session = get_session(session_id)

    url = (
        f"{BACKEND_BASE_URL}"
        f"/api/measurement-sessions/{session_id}/status"
    )

    params = {
        "status": status
    }

    if photo_capture_attempt is not None:
        params["photoCaptureAttempt"] = (
            photo_capture_attempt
        )

    if pressure_measurement_attempt is not None:
        params["pressureMeasurementAttempt"] = (
            pressure_measurement_attempt
        )

    if failure_reason is not None:
        params["failureReason"] = failure_reason

    if failure_detail is not None:
        params["failureDetail"] = failure_detail

    # 요청 로그
    print(
        "[BACKEND PATCH REQUEST]",
        f"session={session_id}",
        f"params={params}",
        flush=True,
    )

    response = requests.patch(
        url,
        headers={
            "Authorization": session["authorization"],
        },
        params=params,
        timeout=15,
    )

    # 응답 로그 - 409도 출력
    print(
        "[BACKEND PATCH RESPONSE]",
        f"session={session_id}",
        f"http={response.status_code}",
        f"body={response.text[:1000]}",
        flush=True,
    )

    response.raise_for_status()

    return response


# ============================================================
# HARDWARE FAILED
# ============================================================

def send_hardware_failed(
    session_id: int,
    reason: str,
    message: str,
    detail: str,
    photo_capture_attempt: int | None = None,
    pressure_measurement_attempt: int | None = None,
):
    session = get_session(session_id)

    url = (
        f"{BACKEND_BASE_URL}"
        f"/api/measurement-sessions/{session_id}/status"
    )

    params = {
        "status": "FAILED",
        "failureReason": reason,
        "failureMessage": message,
        "failureDetail": detail,
    }

    if photo_capture_attempt is not None:
        params["photoCaptureAttempt"] = (
            photo_capture_attempt
        )

    if pressure_measurement_attempt is not None:
        params["pressureMeasurementAttempt"] = (
            pressure_measurement_attempt
        )

    try:
        print(
            "[HARDWARE FAILED REQUEST]",
            f"session={session_id}",
            f"params={params}",
            flush=True,
        )

        response = requests.patch(
            url,
            headers={
                "Authorization": session["authorization"],
            },
            params=params,
            timeout=15,
        )

        print(
            "[HARDWARE FAILED RESPONSE]",
            f"session={session_id}",
            f"http={response.status_code}",
            f"body={response.text[:1000]}",
            flush=True,
        )

        return response

    except Exception as e:
        print(
            "[FAILED 전송 실패]",
            f"session={session_id}",
            repr(e),
            flush=True,
        )

        return None
