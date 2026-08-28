from typing import Optional

from fastapi import (
    APIRouter,
    Header,
    HTTPException
)

from models import MeasurementRequest

from session_store import (
    create_session,
    update_session
)

from hardware.environment import (
    measure_environment
)

from errors import HardwareMeasurementError

from clients.backend_client import (
    send_hardware_failed
)


router = APIRouter()


@router.post(
    "/measurement/start"
)
def measurement_start(

    request: MeasurementRequest,

    authorization: Optional[str] = Header(
        default=None
    )
):

    if authorization is None:

        raise HTTPException(
            status_code=401,
            detail="Authorization ??? ????."
        )


    session_id = (
        request.measurementSessionId
    )


    create_session(
        session_id,
        authorization
    )


    try:

        before = (
            measure_environment()
        )


        update_session(
            session_id,

            beforeTemperature=
                before["temperature"],

            beforeHumidity=
                before["humidity"]
        )


        return {
            "accepted": True,

            "measurementSessionId":
                session_id,

            "status":
                "WAITING_FOR_PHOTO"
        }


    except HardwareMeasurementError as e:

        send_hardware_failed(
            session_id,
            e.reason,
            e.message,
            e.detail
        )

        raise HTTPException(
            status_code=500,
            detail=e.message
        )
