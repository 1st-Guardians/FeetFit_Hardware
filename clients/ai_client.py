
import os
from pathlib import Path

import requests

from errors import AIRequestNotAccepted
from session_store import get_session


AI_BASE_URL = os.getenv("AI_BASE_URL", "").rstrip("/")


def check_ai_202(response: requests.Response, name: str) -> dict:
    """AI 서버가 202 Accepted와 accepted=true를 반환했는지 확인합니다."""
    print(
        f"[AI {name} RESPONSE]",
        f"http={response.status_code}",
        f"body={response.text[:1000]}",
        flush=True,
    )

    if response.status_code != 202:
        raise AIRequestNotAccepted(
            status_code=response.status_code,
            detail=(
                f"{name} AI 요청이 202 Accepted 되지 않았습니다. "
                f"{response.text}"
            ),
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise AIRequestNotAccepted(
            status_code=202,
            detail=f"{name} AI 응답을 JSON으로 해석할 수 없습니다. {exc}",
        ) from exc

    if not isinstance(data, dict) or data.get("accepted") is not True:
        raise AIRequestNotAccepted(
            status_code=202,
            detail=f"{name} AI 응답에 accepted=true가 없습니다: {data}",
        )

    return data


def send_photo(
    session_id: int,
    photo_capture_attempt: int,
    photos: dict,
):
    """발등·좌측 발바닥·우측 발바닥 사진을 AI 서버에 전달합니다."""
    session = get_session(session_id)
    url = f"{AI_BASE_URL}/api/reports/photo-analysis"

    print(
        "[AI PHOTO REQUEST]",
        f"session={session_id}",
        f"attempt={photo_capture_attempt}",
        f"url={url}",
        flush=True,
    )

    with (
        open(photos["dorsal"], "rb") as dorsal_file,
        open(photos["left"], "rb") as left_file,
        open(photos["right"], "rb") as right_file,
    ):
        response = requests.post(
            url,
            headers={"Authorization": session["authorization"]},
            data={
                "measurementSessionId": str(session_id),
                "photoCaptureAttempt": str(photo_capture_attempt),
            },
            files={
                "dorsalFootImage": (
                    Path(photos["dorsal"]).name,
                    dorsal_file,
                    "image/jpeg",
                ),
                "leftPlantarFootImage": (
                    Path(photos["left"]).name,
                    left_file,
                    "image/jpeg",
                ),
                "rightPlantarFootImage": (
                    Path(photos["right"]).name,
                    right_file,
                    "image/jpeg",
                ),
            },
            timeout=30,
        )

    return check_ai_202(response, "PHOTO")


def send_environment(
    session_id: int,
    before_temperature: float,
    before_humidity: float,
    after_temperature: float,
    after_humidity: float,
):
    """발 근접 전후의 온습도 측정 결과를 AI 서버에 전달합니다."""
    session = get_session(session_id)
    url = f"{AI_BASE_URL}/api/reports/daily-foot-analysis/environment"

    response = requests.post(
        url,
        headers={"Authorization": session["authorization"]},
        json={
            "measurementSessionId": session_id,
            "beforeTemperatureCelsius": before_temperature,
            "beforeHumidityPercent": before_humidity,
            "afterTemperatureCelsius": after_temperature,
            "afterHumidityPercent": after_humidity,
        },
        timeout=30,
    )

    return check_ai_202(response, "ENVIRONMENT")


def send_pressure(
    session_id: int,
    pressure_measurement_attempt: int,
    left_values: list,
    right_values: list,
):
    """백엔드에서 받은 압력 측정 회차와 FSR 값을 AI 서버로 그대로 전달합니다."""
    session = get_session(session_id)
    url = f"{AI_BASE_URL}/api/reports/daily-foot-analysis/pressure-heatmap"

    payload = {
        "measurementSessionId": session_id,
        "pressureMeasurementAttempt": pressure_measurement_attempt,
        "leftPressureValues": left_values,
        "rightPressureValues": right_values,
    }

    print(
        "[AI PRESSURE REQUEST]",
        f"session={session_id}",
        f"attempt={pressure_measurement_attempt}",
        f"left_count={len(left_values)}",
        f"right_count={len(right_values)}",
        flush=True,
    )
    print("[AI PRESSURE BODY]", payload, flush=True)

    response = requests.post(
        url,
        headers={"Authorization": session["authorization"]},
        json=payload,
        timeout=30,
    )

    return check_ai_202(response, "PRESSURE")
