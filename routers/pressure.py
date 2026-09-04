from fastapi import (
    APIRouter,
    HTTPException
)
from hardware.buzzer import (
    buzzer_error
)
from models import MeasurementRequest

from hardware.pressure import (
    measure_pressure
)

from clients.ai_client import (
    send_pressure
)

from clients.backend_client import (
    patch_status,
    send_hardware_failed
)

from errors import (
    HardwareMeasurementError,
    AIRequestNotAccepted
)


router = APIRouter()


@router.post(
    "/measurement/pressure/start",
    status_code=202
)
def pressure_start(
    request: MeasurementRequest
):

    session_id = (
        request.measurementSessionId
    )


    try:

        # ==========================================
        # 압력 측정 시작
        # ==========================================

        patch_status(
            session_id,
            "MEASURING_PRESSURE"
        )


        pressure = (
            measure_pressure()
        )


        # ==========================================
        # AI 압력 분석
        # ==========================================

        ai_result = (
            send_pressure(

                session_id,

                pressure["left"],

                pressure["right"]
            )
        )


        # ==========================================
        # AI가 202를 준 경우
        #
        # 하드웨어 최종 단계
        # ==========================================

        patch_status(
            session_id,
            "ANALYZING"
        )


        return {

            "accepted":
                True,

            "measurementSessionId":
                session_id,

            "status":
                "ANALYZING",

            "aiRequestId":
                ai_result.get(
                    "requestId"
                )
        }


    # ==============================================
    # 실제 압력센서 실패
    # ==============================================
    
    except HardwareMeasurementError as e:
        buzzer_error()
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


    # ==============================================
    # AI ??
    #
    # ? FAILED PATCH ? ?
    # ==============================================

    except AIRequestNotAccepted as e:
        buzzer_error()
        print(
            "[PRESSURE AI STOP]",
            e.detail
        )

        raise HTTPException(
            status_code=502,
            detail=e.detail
        )
