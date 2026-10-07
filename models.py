from typing import Literal

from pydantic import (
    BaseModel,
    Field
)


class MeasurementRequest(BaseModel):
    measurementSessionId: int


class PhotoCaptureRequest(BaseModel):
    measurementSessionId: int

    # 최초 촬영: 0
    # 재촬영: 1 ~ 3
    #
    # 백엔드에서 최초 촬영 시
    # photoCaptureAttempt를 보내지 않아도
    # 자동으로 0으로 처리
    photoCaptureAttempt: int = Field(
        default=0,
        ge=0,
        le=3
    )


class EnvironmentMeasurementRequest(BaseModel):
    measurementSessionId: int

    task: Literal[
        "ENVIRONMENT_MEASUREMENT"
    ] = "ENVIRONMENT_MEASUREMENT"
