from fastapi import (
    APIRouter,
    HTTPException
)

from models import (
    EnvironmentMeasurementRequest
)

from session_store import (
    get_session,
    update_session
)

from clients.backend_client import (
    patch_status,
    send_hardware_failed
)

from clients.ai_client import (
    send_environment
)

from hardware.environment import (
    measure_environment
)

from errors import (
    HardwareMeasurementError,
    AIRequestNotAccepted
)


router = APIRouter()


@router.post(
    "/measurement/environment/start",
    status_code=202
)
def environment_start(
    request:
        EnvironmentMeasurementRequest
):

    session_id = (
        request.measurementSessionId
    )


    try:

        # ==========================================
        # 온습도 측정 시작
        # ==========================================

        patch_status(
            session_id,
            "MEASURING_ENVIRONMENT"
        )


        # ==========================================
        # AFTER 온습도 측정
        # ==========================================

        after = (
            measure_environment()
        )


        update_session(

            session_id,

            afterTemperature=
                after["temperature"],

            afterHumidity=
                after["humidity"]
        )


        session = get_session(
            session_id
        )


        before_temperature = (
            session[
                "beforeTemperature"
            ]
        )

        before_humidity = (
            session[
                "beforeHumidity"
            ]
        )


        # ==========================================
        # AI 환경 API
        # ==========================================

        ai_result = (
            send_environment(

                session_id,

                before_temperature,

                before_humidity,

                after["temperature"],

                after["humidity"]
            )
        )


        # ==========================================
        # AI가 202를 줬을 때만
        # 압력 준비 단계 이동
        # ==========================================

        patch_status(
            session_id,
            "WAITING_FOR_PRESSURE"
        )


        update_session(
            session_id,
            environmentAccepted=True
        )


        return {

            "accepted":
                True,

            "measurementSessionId":
                session_id,

            "status":
                "WAITING_FOR_PRESSURE",

            "aiRequestId":
                ai_result.get(
                    "requestId"
                )
        }


    # ==============================================
    # 실제 온습도 센서 실패
    # ==============================================

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


    # ==============================================
    # AI 실패
    #
    # FAILED 전송 안 함
    # ==============================================

    except AIRequestNotAccepted as e:

        print(
            "[ENVIRONMENT AI STOP]",
            e.detail
        )

        raise HTTPException(
            status_code=502,
            detail=e.detail
        )
