from typing import Literal

from pydantic import BaseModel


class MeasurementRequest(BaseModel):
    measurementSessionId: int


class EnvironmentMeasurementRequest(BaseModel):
    measurementSessionId: int

    task: Literal[
        "ENVIRONMENT_MEASUREMENT"
    ] = "ENVIRONMENT_MEASUREMENT"
