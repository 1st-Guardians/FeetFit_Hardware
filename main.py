from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from routers.measurement_start import router as measurement_start_router
from routers.photo import router as photo_router
from routers.environment import router as environment_router
from routers.pressure import router as pressure_router
from routers.buzzer import router as buzzer_router

from hardware.camera import configure_arducams_on_startup


app = FastAPI(
    title="FeetFit Hardware API",
    version="5.0.0",
)

app.include_router(measurement_start_router)
app.include_router(photo_router)
app.include_router(environment_router)
app.include_router(pressure_router)
app.include_router(buzzer_router)


# ============================================================
# 422 VALIDATION ERROR LOG
# ============================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    if request.url.path == "/measurement/pressure/start":

        body = await request.body()

        errors_for_log = [
            {
                "type": item.get("type"),
                "loc": item.get("loc"),
                "msg": item.get("msg"),
            }
            for item in exc.errors()
        ]

        print("\n" + "=" * 60, flush=True)

        print(
            "[PRESSURE 422 VALIDATION ERROR]",
            flush=True,
        )

        print(
            f"[REQUEST] {request.method} {request.url.path}",
            flush=True,
        )

        print(
            "[CONTENT-TYPE]",
            request.headers.get("content-type"),
            flush=True,
        )

        print(
            "[REQUEST BODY]",
            body[:2000].decode(
                "utf-8",
                errors="replace",
            ),
            flush=True,
        )

        print(
            "[VALIDATION ERRORS]",
            errors_for_log,
            flush=True,
        )

        print("=" * 60 + "\n", flush=True)

    return JSONResponse(
        status_code=422,
        content={
            "detail": jsonable_encoder(exc.errors())
        },
    )


# ============================================================
# STARTUP
# ============================================================

@app.on_event("startup")
def startup():
    configure_arducams_on_startup()


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "ok"
    }
