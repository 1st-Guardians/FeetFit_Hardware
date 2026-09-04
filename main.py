from fastapi import FastAPI

from routers.measurement_start import router as measurement_start_router
from routers.photo import router as photo_router
from routers.environment import router as environment_router
from routers.pressure import router as pressure_router
from routers.buzzer import (
    router as buzzer_router
)
from hardware.camera import configure_arducams_on_startup

app = FastAPI(
    title="FeetFit Hardware API",
    version="5.0.0"
)


app.include_router(measurement_start_router)
app.include_router(photo_router)
app.include_router(environment_router)
app.include_router(pressure_router)
app.include_router(buzzer_router)
@app.on_event("startup")
def startup():
    configure_arducams_on_startup()

@app.get("/health")
def health():
    return {
        "status": "ok"
    }
