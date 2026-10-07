from threading import Lock
from typing import Dict

from errors import HardwareMeasurementError


sessions: Dict[int, dict] = {}

session_lock = Lock()


def create_session(
    session_id: int,
    authorization: str
):
    """
    측정 세션 생성.

    measurement/start에서 최초 한 번 호출됩니다.
    """

    with session_lock:

        sessions[session_id] = {
            "measurementSessionId":
                session_id,

            "authorization":
                authorization,

            "status":
                "WAITING_FOR_PHOTO",

            "failed":
                False,

            # =========================
            # 환경 측정
            # =========================

            "beforeTemperature":
                None,

            "beforeHumidity":
                None,

            "afterTemperature":
                None,

            "afterHumidity":
                None,

            # =========================
            # AI 접수 여부
            # =========================

            "photoAccepted":
                False,

            "environmentAccepted":
                False,

            "pressureAccepted":
                False,

            # =========================
            # 사진 촬영 회차
            # =========================

            # 현재 촬영 회차
            "photoCaptureAttempt":
                None,

            # 이미 처리한 촬영 회차
            #
            # 예:
            # {
            #     0: "SUBMITTED_TO_AI",
            #     1: "CAPTURING"
            # }
            "photoCaptureAttempts":
                {}
        }


def get_session(
    session_id: int
) -> dict:
    """
    세션 정보를 반환합니다.

    원본 dictionary가 아닌 복사본을 반환합니다.
    """

    with session_lock:

        session = sessions.get(
            session_id
        )

        if session is not None:
            session = dict(
                session
            )

    if session is None:

        raise HardwareMeasurementError(
            reason="UNKNOWN",
            message=(
                "측정 세션 정보를 "
                "찾을 수 없습니다."
            ),
            detail=(
                f"measurementSessionId="
                f"{session_id}"
            )
        )

    return session


def update_session(
    session_id: int,
    **kwargs
):
    """
    일반적인 세션 데이터 업데이트.
    """

    with session_lock:

        if session_id not in sessions:

            raise HardwareMeasurementError(
                reason="UNKNOWN",
                message=(
                    "측정 세션 정보를 "
                    "찾을 수 없습니다."
                ),
                detail=(
                    f"measurementSessionId="
                    f"{session_id}"
                )
            )

        sessions[
            session_id
        ].update(
            kwargs
        )


def claim_photo_capture_attempt(
    session_id: int,
    attempt: int
) -> bool:
    """
    특정 사진 촬영 회차를 선점합니다.

    같은 session_id + attempt가
    이미 처리되고 있다면 False를 반환합니다.

    확인 + 등록을 같은 Lock 내부에서 처리하여
    동시에 같은 요청이 들어와도
    중복 촬영되지 않게 합니다.
    """

    with session_lock:

        if session_id not in sessions:

            raise HardwareMeasurementError(
                reason="UNKNOWN",
                message=(
                    "측정 세션 정보를 "
                    "찾을 수 없습니다."
                ),
                detail=(
                    f"measurementSessionId="
                    f"{session_id}"
                )
            )

        session = sessions[
            session_id
        ]

        attempts = session.setdefault(
            "photoCaptureAttempts",
            {}
        )

        # -------------------------
        # 중복 요청 확인
        # -------------------------

        if attempt in attempts:

            print(
                "[PHOTO ATTEMPT DUPLICATE]",
                f"session={session_id}",
                f"attempt={attempt}",
                f"status={attempts[attempt]}"
            )

            return False

        # -------------------------
        # 촬영 회차 선점
        # -------------------------

        attempts[
            attempt
        ] = "QUEUED"

        session[
            "photoCaptureAttempt"
        ] = attempt

        print(
            "[PHOTO ATTEMPT CLAIMED]",
            f"session={session_id}",
            f"attempt={attempt}"
        )

        return True


def update_photo_capture_attempt(
    session_id: int,
    attempt: int,
    status: str
):
    """
    특정 사진 촬영 회차 상태를 업데이트합니다.

    예:
        QUEUED
        CAPTURING
        CAPTURED
        SUBMITTED_TO_AI
        HARDWARE_FAILED
        AI_REJECTED
    """

    with session_lock:

        if session_id not in sessions:

            raise HardwareMeasurementError(
                reason="UNKNOWN",
                message=(
                    "측정 세션 정보를 "
                    "찾을 수 없습니다."
                ),
                detail=(
                    f"measurementSessionId="
                    f"{session_id}"
                )
            )

        session = sessions[
            session_id
        ]

        attempts = session.setdefault(
            "photoCaptureAttempts",
            {}
        )

        attempts[
            attempt
        ] = status

        session[
            "photoCaptureAttempt"
        ] = attempt

        print(
            "[PHOTO ATTEMPT UPDATE]",
            f"session={session_id}",
            f"attempt={attempt}",
            f"status={status}"
        )
