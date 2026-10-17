
from fastapi import APIRouter, HTTPException

from models import PressureStartRequest
from hardware.pressure import measure_pressure
from hardware.buzzer import buzzer_complete, buzzer_error
from clients.ai_client import send_pressure
from clients.backend_client import patch_status, send_hardware_failed
from errors import HardwareMeasurementError, AIRequestNotAccepted


router = APIRouter()


@router.post("/measurement/pressure/start", status_code=202)
def pressure_start(request: PressureStartRequest):
    session_id = request.measurementSessionId
    attempt = request.pressureMeasurementAttempt

    print("\n" + "=" * 60, flush=True)
    print(
        "[PRESSURE REQUEST ACCEPTED]",
        f"measurementSessionId={session_id}",
        f"pressureMeasurementAttempt={attempt}",
        flush=True,
    )
    print("=" * 60, flush=True)

    try:
        # 1. 백엔드에 측정 시작 알림 (받은 회차 그대로 사용)
        print("[PRESSURE STATUS] MEASURING_PRESSURE", flush=True)
        patch_status(
            session_id,
            "MEASURING_PRESSURE",
            pressure_measurement_attempt=attempt,
        )

        # 2. 기존 압력 센서 측정 함수 실행
        print("[PRESSURE SENSOR] 측정 시작", flush=True)
        pressure = measure_pressure()
        print(
            "[PRESSURE SENSOR] 측정 완료",
            f"left_count={len(pressure['left'])}",
            f"right_count={len(pressure['right'])}",
            flush=True,
        )

        # 3. AI에도 정확히 같은 회차 전송
        print("[PRESSURE AI] 분석 요청", f"attempt={attempt}", flush=True)
        ai_result = send_pressure(
            session_id=session_id,
            pressure_measurement_attempt=attempt,
            left_values=pressure["left"],
            right_values=pressure["right"],
        )

        # 4. AI 요청 접수(202) 후 분석 중 상태 알림
        print("[PRESSURE STATUS] ANALYZING", flush=True)
        patch_status(
            session_id,
            "ANALYZING",
            pressure_measurement_attempt=attempt,
        )

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

    except HardwareMeasurementError as exc:
        print(
            "[PRESSURE HARDWARE ERROR]",
            f"session={session_id}",
            f"attempt={attempt}",
            f"reason={exc.reason}",
            f"detail={exc.detail}",
            flush=True,
        )
        buzzer_error()
        send_hardware_failed(
            session_id=session_id,
            reason=exc.reason,
            message=exc.message,
            detail=exc.detail,
            pressure_measurement_attempt=attempt,
        )
        raise HTTPException(status_code=500, detail=exc.message) from exc

    except AIRequestNotAccepted as exc:
        # AI가 접수하지 못했더라도 센서 실패로 보고하지는 않음
        buzzer_error()
        print(
            "[PRESSURE AI STOP]",
            f"session={session_id}",
            f"attempt={attempt}",
            f"detail={exc.detail}",
            flush=True,
        )
        raise HTTPException(status_code=502, detail=exc.detail) from exc
