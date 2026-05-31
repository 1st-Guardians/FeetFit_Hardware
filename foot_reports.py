import os
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel


load_dotenv()

app = FastAPI(title="FeetFit Raspberry Pi Foot Reports API")

AI_BASE_URL = os.getenv("AI_BASE_URL", "").rstrip("/")

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


def get_image_path(measurement_session_id: int, foot: str) -> Path:
    return IMAGE_DIR / f"{measurement_session_id}_{foot}.jpg"


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

def capture_left_then_right(measurement_session_id: int) -> tuple[Path, Path]:
    left_path = get_image_path(measurement_session_id, "left")
    right_path = get_image_path(measurement_session_id, "right")

    print("Starting left foot capture.")
    capture_image(left_path)
    print(f"Left foot image captured: {left_path}")

    print(f"Waiting {CAPTURE_DELAY_SECONDS} seconds before capturing the right foot.")
    time.sleep(CAPTURE_DELAY_SECONDS)

    print("Starting right foot capture.")
    capture_image(right_path)
    print(f"Right foot image captured: {right_path}")

    return left_path, right_path


def send_images_to_ai(
    report_type: str,
    ai_path: str,
    measurement_session_id: int,
    left_path: Path,
    right_path: Path,
    authorization: str | None = None,
) -> dict[str, Any]:
    if not left_path.exists():
        raise FileNotFoundError("Left foot image does not exist.")

    if not right_path.exists():
        raise FileNotFoundError("Right foot image does not exist.")

    headers = {
        "accept": "application/json",
        "ngrok-skip-browser-warning": "true",
    }

    if authorization is not None:
        headers["Authorization"] = authorization

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

    response.raise_for_status()

    return {
        "reportType": report_type,
        "success": True,
        "statusCode": response.status_code,
    }

def send_to_all_ai_servers(
    measurement_session_id: int,
    left_path: Path,
    right_path: Path,
    authorization: str,
) -> list[dict[str, Any]]:
    tasks = [
        {
            "report_type": "tina-pedis",
            "ai_path": TINA_PEDIS_PATH,
            "authorization": authorization,
        },
        {
            "report_type": "hallux-valgus",
            "ai_path": HALLUX_VALGUS_PATH,
            "authorization": authorization,
        },
    ]

    results: list[dict[str, Any]] = []

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_map = {
            executor.submit(
                send_images_to_ai,
                task["report_type"],
                task["ai_path"],
                measurement_session_id,
                left_path,
                right_path,
                task["authorization"],
            ): task
            for task in tasks
        }

        for future in as_completed(future_map):
            task = future_map[future]

            try:
                result = future.result()
                results.append(result)

            except Exception as error:
                results.append(
                    {
                        "reportType": task["report_type"],
                        "success": False,
                        "error": str(error),
                    }
                )

    failed_results = [result for result in results if not result["success"]]

    if failed_results:
        raise RuntimeError(f"Some AI server requests failed: {failed_results}")

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

    try:
        left_path, right_path = capture_left_then_right(
            measurement_session_id=request.measurementSessionId,
        )

        results = send_to_all_ai_servers(
            measurement_session_id=request.measurementSessionId,
            left_path=left_path,
            right_path=right_path,
            authorization=authorization,
        )

        return {
            "success": True,
            "measurementSessionId": request.measurementSessionId,
            "message": "Images were captured once and sent to both tina-pedis and hallux-valgus AI servers successfully.",
            "results": results,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )
