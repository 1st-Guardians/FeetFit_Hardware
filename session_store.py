from threading import Lock
from typing import Dict

from errors import HardwareMeasurementError


sessions: Dict[int, dict] = {}

session_lock = Lock()


def create_session(
    session_id: int,
    authorization: str
):

    with session_lock:

        sessions[session_id] = {
            "measurementSessionId": session_id,
            "authorization": authorization,

            "status": "WAITING_FOR_PHOTO",

            "failed": False,

            "beforeTemperature": None,
            "beforeHumidity": None,

            "afterTemperature": None,
            "afterHumidity": None,

            "photoAccepted": False,
            "environmentAccepted": False,
            "pressureAccepted": False,
        }


def get_session(
    session_id: int
) -> dict:

    with session_lock:

        session = sessions.get(
            session_id
        )

        if session is not None:
            session = dict(session)

    if session is None:

        raise HardwareMeasurementError(
            reason="UNKNOWN",
            message="측정 세션 정보를 찾을 수 없습니다.",
            detail=(
                f"measurementSessionId={session_id}"
            )
        )

    return session


def update_session(
    session_id: int,
    **kwargs
):

    with session_lock:

        if session_id not in sessions:

            raise HardwareMeasurementError(
                reason="UNKNOWN",
                message="측정 세션 정보를 찾을 수 없습니다..",
                detail=(
                    f"measurementSessionId={session_id}"
                )
            )

        sessions[
            session_id
        ].update(kwargs)
