import os
import subprocess
import time
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel


load_dotenv()

app = FastAPI(title="FeetFit Raspberry Pi Foot Reports API")

AI_BASE_URL = os.getenv("AI_BASE_URL", "").rstrip("/")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "").rstrip("/")

CAMERA_DEVICE = os.getenv("CAMERA_DEVICE", "/dev/video0")
IMAGE_WIDTH = os.getenv("IMAGE_WIDTH", "1280")
IMAGE_HEIGHT = os.getenv("IMAGE_HEIGHT", "720")
CAPTURE_DELAY_SECONDS = int(os.getenv("CAPTURE_DELAY_SECONDS", "10"))

IMAGE_DIR = Path("images")
IMAGE_DIR.mkdir(exist_ok=True)

TINA_PEDIS_PATH = "/api/reports/tina-pedis"
HALLUX_VALGUS_PATH = "/api/reports/hallux-valgus"


class FootReportRequest(BaseModel):
    measurementSessionId: int


def get_ai_url(ai_path: str) -> str:
    if not AI_BASE_URL:
        raise ValueError("AI_BASE_URL is empty. Please check your .env file.")

    if not ai_path.startswith("/"):
        raise ValueError("AI path must start with '/'.")

    return f"{AI_BASE_URL}{ai_path}"


def get_backend_url(path: str) -> str:
    if not BACKEND_BASE_URL:
        raise ValueError("BACKEND_BASE_URL is empty. Please check your .env file.")

    if not path.startswith("/"):
        raise ValueError("Backend path must start with '/'.")

    return f"{BACKEND_BASE_URL}{path}"


def get_image_path(measurement_session_id: int, foot: str) -> Path:
    return IMAGE_DIR / f"{measurement_session_id}_{foot}.jpg"


def update_measurement_status(
    measurement_session_id: int,
    status: str,
    authorization: str,
    measurement_duration_sec: int | None = None,
) -> dict[str, Any]:
    url = get_backend_url(f"/api/measurement-sessions/{measurement_session_id}/status")

    headers = {
        "accept": "application/json",
        "Authorization": authorization,
        "ngrok-skip-browser-warning": "true",
    }

    params: dict[str, Any] = {
        "status": status,
    }

    if measurement_duration_sec is not None:
        params["measurementDurationSec"] = measurement_duration_sec

    response = requests.patch(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    print(f"[status] request url: {response.url}")
    print(f"[status] response status: {response.status_code}")
    print(f"[status] response body: {response.text}")

    response.raise_for_status()

    try:
        return response.json()
    except ValueError:
        return {
            "rawResponse": response.text,
        }


def capture_image(image_path: Path) -> None:
    command = [
        "fswebcam",
        "-d",
        CAMERA_DEVICE,
        "-r",
        f"{IMAGE_WIDTH}x{IMAGE_HEIGHT}",
        "--no-banner",
        "--jpeg",
        "95",
        str(image_path),
    ]

    result = subprocess.run(
        command,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr)

    if not image_path.exists():
        raise FileNotFoundError(f"Image file was not created: {image_path}")

    if image_path.stat().st_size == 0:
        raise RuntimeError(f"Image file is empty: {image_path}")


def capture_left_then_right(measurement_session_id: int) -> tuple[Path, Path]:
    left_path = get_image_path(measurement_session_id, "left")
    right_path = get_image_path(measurement_session_id, "right")

    print("Starting left foot capture.")
    capture_image(left_path)
    print(f"Left foot image captured: {left_path}, size={left_path.stat().st_size} bytes")

    print(f"Waiting {CAPTURE_DELAY_SECONDS} seconds before capturing the right foot.")
    time.sleep(CAPTURE_DELAY_SECONDS)

    print("Starting right foot capture.")
    capture_image(right_path)
    print(f"Right foot image captured: {right_path}, size={right_path.stat().st_size} bytes")

    return left_path, right_path


def send_images_to_ai(
    report_type: str,
    ai_path: str,
    measurement_session_id: int,
    left_path: Path,
    right_path: Path,
    authorization: str,
) -> dict[str, Any]:
    if not left_path.exists():
        raise FileNotFoundError("Left foot image does not exist.")

    if not right_path.exists():
        raise FileNotFoundError("Right foot image does not exist.")

    print(f"[{report_type}] AI URL: {get_ai_url(ai_path)}")
    print(f"[{report_type}] left image: {left_path}, size={left_path.stat().st_size} bytes")
    print(f"[{report_type}] right image: {right_path}, size={right_path.stat().st_size} bytes")

    headers = {
        "accept": "application/json",
        "Authorization": authorization,
        "ngrok-skip-browser-warning": "true",
    }

    data = {
        "measurementSessionId": str(measurement_session_id),
    }

    with left_path.open("rb") as left_file, right_path.open("rb") as right_file:
        files = {
            "leftFootImage": (left_path.name, left_file, "image/jpeg"),
            "rightFootImage": (right_path.name, right_file, "image/jpeg"),
        }

        response = requests.post(
            get_ai_url(ai_path),
            headers=headers,
            data=data,
            files=files,
            timeout=180,
        )

    print(f"[{report_type}] AI response status: {response.status_code}")
    print(f"[{report_type}] AI response body: {response.text}")

    response.raise_for_status()

    try:
        response_body = response.json()
    except ValueError:
        response_body = {
            "rawResponse": response.text,
        }

    return {
        "reportType": report_type,
        "success": True,
        "statusCode": response.status_code,
        "response": response_body,
    }


def send_to_ai_servers_sequentially(
    measurement_session_id: int,
    left_path: Path,
    right_path: Path,
    authorization: str,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    print("[flow] Sending images to tina-pedis AI server first.")
    tina_pedis_result = send_images_to_ai(
        report_type="tina-pedis",
        ai_path=TINA_PEDIS_PATH,
        measurement_session_id=measurement_session_id,
        left_path=left_path,
        right_path=right_path,
        authorization=authorization,
    )
    results.append(tina_pedis_result)
    print("[flow] tina-pedis AI server request completed.")

    print("[flow] Sending images to hallux-valgus AI server next.")
    hallux_valgus_result = send_images_to_ai(
        report_type="hallux-valgus",
        ai_path=HALLUX_VALGUS_PATH,
        measurement_session_id=measurement_session_id,
        left_path=left_path,
        right_path=right_path,
        authorization=authorization,
    )
    results.append(hallux_valgus_result)
    print("[flow] hallux-valgus AI server request completed.")

    return results


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/reports/all")
def create_all_reports(
    request: FootReportRequest,
    authorization: str | None = Header(default=None),
) -> dict[str, object]:
    if authorization is None:
        raise HTTPException(
            status_code=401,
            detail="Authorization header is required.",
        )

    start_time = time.monotonic()

    try:
        left_path, right_path = capture_left_then_right(
            measurement_session_id=request.measurementSessionId,
        )

        update_measurement_status(
            measurement_session_id=request.measurementSessionId,
            status="TRANSFERRING",
            authorization=authorization,
        )

        results = send_to_ai_servers_sequentially(
            measurement_session_id=request.measurementSessionId,
            left_path=left_path,
            right_path=right_path,
            authorization=authorization,
        )

        measurement_duration_sec = int(time.monotonic() - start_time)

        completed_status_response = update_measurement_status(
            measurement_session_id=request.measurementSessionId,
            status="COMPLETED",
            authorization=authorization,
            measurement_duration_sec=measurement_duration_sec,
        )

        return {
            "success": True,
            "measurementSessionId": request.measurementSessionId,
            "measurementDurationSec": measurement_duration_sec,
            "message": "Images were sent to tina-pedis first, then hallux-valgus. Measurement status was changed to COMPLETED.",
            "results": results,
            "completedStatusResponse": completed_status_response,
        }

    except Exception as error:
        print(f"[flow] error occurred: {error}")

        try:
            update_measurement_status(
                measurement_session_id=request.measurementSessionId,
                status="FAILED",
                authorization=authorization,
            )
        except Exception as status_error:
            print(f"[status] failed to update status to FAILED: {status_error}")

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )
