from typing import Literal

from pydantic import BaseModel, Field


class MeasurementRequest(BaseModel):
    measurementSessionId: int


class PhotoCaptureRequest(BaseModel):
    measurementSessionId: int

    # 기존 사진 최초 촬영 요청과의 호환성 유지
    photoCaptureAttempt: int = Field(
        default=0,
        ge=0,
        le=3,
    )


class PressureStartRequest(BaseModel):
    measurementSessionId: int

    # 백엔드가 보낸 압력 회차를 그대로 사용
    # 누락 시 HTTP 422 반환
    pressureMeasurementAttempt: int = Field(
        ge=0,
    )


class EnvironmentMeasurementRequest(BaseModel):
    measurementSessionId: int

    task: Literal[
        "ENVIRONMENT_MEASUREMENT"
    ] = "ENVIRONMENT_MEASUREMENT"
