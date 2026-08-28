import os
import requests

from errors import AIRequestNotAccepted
from session_store import get_session


AI_BASE_URL = os.getenv(
    "AI_BASE_URL",
    ""
).rstrip("/")


def check_ai_202(
    response: requests.Response,
    name: str
):

    print(
        f"[AI {name}] "
        f"{response.status_code} "
        f"{response.text}"
    )

    if response.status_code != 202:

        raise AIRequestNotAccepted(
            status_code=response.status_code,
            detail=(
                f"{name} AI 요청이"
                f"202 Accepted 되지 않았습니다. "
                f"{response.text}"
            )
        )

    data = response.json()

    if data.get("accepted") is not True:

        raise AIRequestNotAccepted(
            status_code=202,
            detail=(
                f"{name} AI accepted=false"
            )
        )

    return data

def send_photo(
    session_id: int,
    photos: dict
):

    session = get_session(
        session_id
    )

    url = (
        f"{AI_BASE_URL}"
        "/api/reports/photo-analysis"
    )

    with (
        open(photos["dorsal"], "rb")
        as dorsal_file,

        open(photos["left"], "rb")
        as left_file,

        open(photos["right"], "rb")
        as right_file
    ):

        response = requests.post(
            url,
            headers={
                "Authorization":
                    session["authorization"]
            },
            data={
                "measurementSessionId":
                    str(session_id)
            },
            files={
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
            },
            timeout=30
        )

    return check_ai_202(
        response,
        "PHOTO"
    )

def send_environment(
    session_id: int,
    before_temperature: float,
    before_humidity: float,
    after_temperature: float,
    after_humidity: float
):

    session = get_session(
        session_id
    )

    url = (
        f"{AI_BASE_URL}"
        "/api/reports/"
        "daily-foot-analysis/"
        "environment"
    )

    response = requests.post(
        url,
        headers={
            "Authorization":
                session["authorization"]
        },
        json={
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
        },
        timeout=30
    )

    return check_ai_202(
        response,
        "ENVIRONMENT"
    )

def send_pressure(
    session_id: int,
    left_values: list,
    right_values: list
):

    session = get_session(
        session_id
    )

    url = (
        f"{AI_BASE_URL}"
        "/api/reports/"
        "daily-foot-analysis/"
        "pressure-heatmap"
    )

    response = requests.post(
        url,
        headers={
            "Authorization":
                session["authorization"]
        },
        json={
            "measurementSessionId":
                session_id,

            "leftPressureValues":
                left_values,

            "rightPressureValues":
                right_values
        },
        timeout=30
    )

    return check_ai_202(
        response,
        "PRESSURE"
    )
