class HardwareMeasurementError(Exception):
    """
    실제 하드웨어 측정 자체가 실패한 경우.

    이 예외만 Backend에 FAILED를 보냄
    """

    def __init__(
        self,
        reason: str,
        message: str,
        detail: str
    ):
        self.reason = reason
        self.message = message
        self.detail = detail

        super().__init__(detail)


class AIRequestNotAccepted(Exception):
    """
    AI 서버가 202를 반환하지 않은 경우.

    * Backend에 FAILED를 보내면 안 됨.

    AI 서버가 자체적으로 Backend에 FAILED를 전달하므로
    하드웨어는 진행만 중단한다.
    """

    def __init__(
        self,
        status_code: int,
        detail: str
    ):
        self.status_code = status_code
        self.detail = detail

        super().__init__(detail)
