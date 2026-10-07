import time

from fastapi import (
    APIRouter,
    BackgroundTasks
)

from config import (
    LED_STABILIZE_SECONDS
)

from models import (
    PhotoCaptureRequest
)

from clients.backend_client import (
    patch_status,
    send_hardware_failed
)

from clients.ai_client import (
    send_photo
)

from hardware.buzzer import (
    buzzer_error
)

from errors import (
    HardwareMeasurementError,
    AIRequestNotAccepted
)

from hardware.camera import (
    capture_all_photos
)

from hardware.led import (
    led_on,
    led_off
)

from session_store import (
    claim_photo_capture_attempt,
    update_photo_capture_attempt
)


router = APIRouter()


def run_photo_capture(
    session_id: int,
    attempt: int
):
    """
    실제 사진 촬영 작업.

    HTTP 요청에 대해서는 먼저 202를 반환한 뒤
    FastAPI BackgroundTasks에서 실행됩니다.

    중요:
    사진을 AI 서버로 전달했다고 해서
    WAITING_FOR_ENVIRONMENT로 변경하지 않습니다.

    사진 검증 이후 상태 결정은
    AI 서버가 담당합니다.
    """

    print(
        "[PHOTO START]",
        f"session={session_id}",
        f"attempt={attempt}"
    )

    try:

        # ==========================================
        # 1. 내부 상태 업데이트
        # ==========================================

        update_photo_capture_attempt(
            session_id,
            attempt,
            "CAPTURING"
        )

        # ==========================================
        # 2. Backend에 촬영 시작 전달
        # ==========================================

        patch_status(
            session_id,
            "CAPTURING_PHOTO",
            photo_capture_attempt=
                attempt
        )

        # ==========================================
        # 3. LED ON + 카메라 촬영
        # ==========================================

        try:

            print(
                "[PHOTO LED ON]",
                f"session={session_id}",
                f"attempt={attempt}"
            )

            led_on()

            # LED가 안정화될 시간을 기다림
            time.sleep(
                LED_STABILIZE_SECONDS
            )

            print(
                "[PHOTO CAPTURING]",
                f"session={session_id}",
                f"attempt={attempt}"
            )

            photos = capture_all_photos(
                session_id
            )

        finally:

            # 촬영 성공/실패와 관계없이
            # LED는 반드시 OFF
            try:

                led_off()

                print(
                    "[PHOTO LED OFF]",
                    f"session={session_id}",
                    f"attempt={attempt}"
                )

            except Exception as led_error:

                print(
                    "[PHOTO LED OFF ERROR]",
                    repr(
                        led_error
                    )
                )

        # ==========================================
        # 4. 촬영 완료
        # ==========================================

        update_photo_capture_attempt(
            session_id,
            attempt,
            "CAPTURED"
        )

        print(
            "[PHOTO CAPTURED]",
            f"session={session_id}",
            f"attempt={attempt}",
            f"photos={photos}"
        )

        # ==========================================
        # 5. AI 서버 전송
        # ==========================================

        ai_result = send_photo(
            session_id,
            attempt,
            photos
        )

        update_photo_capture_attempt(
            session_id,
            attempt,
            "SUBMITTED_TO_AI"
        )

        print(
            "[PHOTO AI ACCEPTED]",
            f"session={session_id}",
            f"attempt={attempt}",
            f"requestId="
            f"{ai_result.get('requestId')}"
        )

        # ==========================================
        # ★ 매우 중요
        #
        # 여기서 기존처럼
        #
        # patch_status(
        #     session_id,
        #     "WAITING_FOR_ENVIRONMENT"
        # )
        #
        # 를 호출하면 안 됩니다.
        #
        # AI 서버가 사진을 검증한 뒤:
        #
        # 정상:
        # WAITING_FOR_ENVIRONMENT
        #
        # 마커 가림:
        # WAITING_FOR_RECAPTURE
        #
        # 를 결정합니다.
        # ==========================================

        print(
            "[PHOTO HW FINISHED]",
            f"session={session_id}",
            f"attempt={attempt}",
            "AI validation pending"
        )

    # ==============================================
    # 실제 하드웨어 오류
    # ==============================================

    except HardwareMeasurementError as e:

        try:

            update_photo_capture_attempt(
                session_id,
                attempt,
                "HARDWARE_FAILED"
            )

        except Exception:
            pass

        try:

            buzzer_error()

        except Exception as buzzer_exception:

            print(
                "[BUZZER ERROR]",
                repr(
                    buzzer_exception
                )
            )

        # 카메라 등의 실제 HW 실패이므로
        # Backend FAILED 전송
        send_hardware_failed(
            session_id=
                session_id,

            reason=
                e.reason,

            message=
                e.message,

            detail=
                e.detail,

            photo_capture_attempt=
                attempt
        )

        print(
            "[PHOTO HARDWARE FAILED]",
            f"session={session_id}",
            f"attempt={attempt}",
            f"reason={e.reason}",
            f"detail={e.detail}"
        )

    # ==============================================
    # AI 서버가 202를 반환하지 않은 경우
    #
    # 이것은 하드웨어 고장이 아니므로
    # Backend FAILED를 보내지 않습니다.
    # ==============================================

    except AIRequestNotAccepted as e:

        try:

            update_photo_capture_attempt(
                session_id,
                attempt,
                "AI_REJECTED"
            )

        except Exception:
            pass

        try:

            buzzer_error()

        except Exception as buzzer_exception:

            print(
                "[BUZZER ERROR]",
                repr(
                    buzzer_exception
                )
            )

        print(
            "[PHOTO AI REJECTED]",
            f"session={session_id}",
            f"attempt={attempt}",
            f"detail={e.detail}"
        )

        # 중요:
        #
        # 여기서
        # WAITING_FOR_ENVIRONMENT X
        # FAILED X
        #
        # AI 접수 자체에 실패했다는 로그만 남김

    # ==============================================
    # 그 외 예외
    # ==============================================

    except Exception as e:

        try:

            update_photo_capture_attempt(
                session_id,
                attempt,
                "ERROR"
            )

        except Exception:
            pass

        try:

            buzzer_error()

        except Exception:
            pass

        print(
            "[PHOTO UNKNOWN ERROR]",
            f"session={session_id}",
            f"attempt={attempt}",
            repr(e)
        )


@router.post(
    "/measurement/photo/start",
    status_code=202
)
def photo_start(
    request: PhotoCaptureRequest,
    background_tasks: BackgroundTasks
):
    """
    Backend로부터 사진 촬영 요청을 받습니다.

    예:

    최초 촬영:
    {
        "measurementSessionId": 79,
        "photoCaptureAttempt": 0
    }

    재촬영:
    {
        "measurementSessionId": 79,
        "photoCaptureAttempt": 1
    }

    최초 촬영의 경우 photoCaptureAttempt를
    생략하면 자동으로 0입니다.
    """

    session_id = (
        request.measurementSessionId
    )

    attempt = (
        request.photoCaptureAttempt
    )

    print(
        "[PHOTO REQUEST]",
        f"session={session_id}",
        f"attempt={attempt}"
    )

    # ==============================================
    # 1. 같은 session + attempt 중복 요청 방지
    # ==============================================

    claimed = (
        claim_photo_capture_attempt(
            session_id,
            attempt
        )
    )

    if not claimed:

        print(
            "[PHOTO DUPLICATE REQUEST]",
            f"session={session_id}",
            f"attempt={attempt}",
            "촬영하지 않음"
        )

        # HTTP 자체는 정상 접수로 반환
        #
        # 백엔드가 네트워크 문제로 같은 요청을
        # 재전송했을 가능성이 있으므로
        # 오류로 취급하지 않습니다.

        return {
            "accepted":
                True,

            "duplicate":
                True,

            "measurementSessionId":
                session_id,

            "photoCaptureAttempt":
                attempt,

            "message":
                (
                    "동일한 촬영 회차가 "
                    "이미 접수되었습니다."
                )
        }

    # ==============================================
    # 2. 실제 촬영은 BackgroundTask로 실행
    # ==============================================

    background_tasks.add_task(
        run_photo_capture,
        session_id,
        attempt
    )

    # ==============================================
    # 3. Backend에는 즉시 202 반환
    # ==============================================

    return {
        "accepted":
            True,

        "duplicate":
            False,

        "measurementSessionId":
            session_id,

        "photoCaptureAttempt":
            attempt,

        "status":
            "QUEUED"
    }
