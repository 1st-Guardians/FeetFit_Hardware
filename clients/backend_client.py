import os
import requests

from session_store import get_session


BACKEND_BASE_URL = os.getenv(
    "BACKEND_BASE_URL",
    "http://34.209.169.111"
).rstrip("/")


def patch_status(
    session_id: int,
    status: str
):

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
            "status": status
        },
        timeout=15
    )

    response.raise_for_status()

    print(
        f"[BACKEND] {status} "
        f"? {response.status_code}"
    )

    return response


def send_hardware_failed(
    session_id: int,
    reason: str,
    message: str,
    detail: str
):

    session = get_session(
        session_id
    )

    url = (
        f"{BACKEND_BASE_URL}"
        f"/api/measurement-sessions/"
        f"{session_id}/status"
    )

    try:

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

                "failureMessage":
                    message,

                "failureDetail":
                    detail
            },
            timeout=15
        )

        print(
            "[HARDWARE FAILED]",
            response.status_code,
            response.text
        )

    except Exception as e:

        print(
            "[FAILED 전송 실패]",
            e
        )
