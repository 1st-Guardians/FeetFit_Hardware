from fastapi import APIRouter, HTTPException

from models import PressureStartRequest

from hardware.pressure import measure_pressure

from hardware.buzzer import (
    buzzer_complete,
    buzzer_error,
)

from clients.ai_client import send_pressure

from clients.backend_client import (
    patch_status,
    send_hardware_failed,
)

from errors import (
    HardwareMeasurementError,
    AIRequestNotAccepted,
)


router = APIRouter()


@router.post(
    "/measurement/pressure/start",
    status_code=202,
)
def pressure_start(request: PressureStartRequest):

    session_id = request.measurementSessionId
    attempt = request.pressureMeasurementAttempt

    # ========================================================
    # 1. 요청 수신
    # ========================================================

    print("\n" + "=" * 60, flush=True)

    print(
        "[PRESSURE REQUEST ACCEPTED]",
        flush=True,
    )

    print(
        f"measurementSessionId={session_id}",
        flush=True,
    )

    print(
        f"pressureMeasurementAttempt={attempt}",
        flush=True,
    )

    print("=" * 60, flush=True)

    try:
        # ====================================================
        # 2. 압력 측정 시작
        # ====================================================

        print(
            "[PRESSURE STATUS] MEASURING_PRESSURE",
            flush=True,
        )

        patch_status(
            session_id,
            "MEASURING_PRESSURE",
            pressure_measurement_attempt=attempt,
        )

        # ====================================================
        # 3. 압력 센서 측정
        # ====================================================

        print(
            "[PRESSURE SENSOR] 측정 시작",
            flush=True,
        )

        pressure = measure_pressure()

        print(
            "[PRESSURE SENSOR] 측정 완료",
            f"left_count={len(pressure['left'])}",
            f"right_count={len(pressure['right'])}",
            flush=True,
        )

        # ====================================================
        # 4. AI 서버 전송
        # ====================================================

        print(
            "[PRESSURE AI] 분석 요청",
            flush=True,
        )

        ai_result = send_pressure(
            session_id,
            pressure["left"],
            pressure["right"],
        )

        # ====================================================
        # 5. ANALYZING 상태 변경
        # ====================================================

        print(
            "[PRESSURE STATUS] ANALYZING",
            flush=True,
        )

        patch_status(
            session_id,
            "ANALYZING",
            pressure_measurement_attempt=attempt,
        )

        # ====================================================
        # 6. 정상 완료
        # ====================================================

        buzzer_complete()

        print(
            "[PRESSURE SUCCESS]",
            f"session={session_id}",
            f"attempt={attempt}",
            flush=True,
        )

        return {
            "accepted": True,
            "measurementSessionId": session_id,
            "pressureMeasurementAttempt": attempt,
            "status": "ANALYZING",
            "aiRequestId": ai_result.get("requestId"),
        }

    # ========================================================
    # 실제 하드웨어 측정 실패
    # ========================================================

    except HardwareMeasurementError as e:

        print(
            "[PRESSURE HARDWARE ERROR]",
            f"session={session_id}",
            f"attempt={attempt}",
            f"reason={e.reason}",
            f"detail={e.detail}",
            flush=True,
        )

        buzzer_error()

        send_hardware_failed(
            session_id=session_id,
            reason=e.reason,
            message=e.message,
            detail=e.detail,
            pressure_measurement_attempt=attempt,
        )

        raise HTTPException(
            status_code=500,
            detail=e.message,
        ) from e

    # ========================================================
    # AI 요청 미접수
    # ========================================================

    except AIRequestNotAccepted as e:

        buzzer_error()

        print(
            "[PRESSURE AI STOP]",
            f"session={session_id}",
            f"attempt={attempt}",
            f"detail={e.detail}",
            flush=True,
        )

        # AI 접수 실패는 하드웨어 오류가 아니므로
        # FAILED 콜백을 보내지 않음

        raise HTTPException(
            status_code=502,
            detail=e.detail,
        ) from e
