from fastapi import APIRouter

from models import MeasurementRequest

from hardware.buzzer import (
    buzzer_ready,
    buzzer_error,
    buzzer_complete
)


router = APIRouter()


# =========================================================
# Test / Backend Buzzer API
# =========================================================

@router.post(
    "/buzzer/ready"
)
def play_ready(
    request: MeasurementRequest
):

    buzzer_ready()

    return {
        "accepted": True,
        "measurementSessionId":
            request.measurementSessionId,
        "buzzer":
            "READY"
    }


@router.post(
    "/buzzer/error"
)
def play_error(
    request: MeasurementRequest
):

    buzzer_error()

    return {
        "accepted": True,
        "measurementSessionId":
            request.measurementSessionId,
        "buzzer":
            "ERROR"
    }


@router.post(
    "/buzzer/complete"
)
def play_complete(
    request: MeasurementRequest
):

    buzzer_complete()

    return {
        "accepted": True,
        "measurementSessionId":
            request.measurementSessionId,
        "buzzer":
            "COMPLETE"
    }
