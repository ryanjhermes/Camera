"""FastAPI app: webcam + OpenAI vision chat."""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field

from camera import Camera, CameraError
from llm import INITIAL_USER_MESSAGE, ChatTurn, ask_with_image

load_dotenv()

CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(title="Webcam-to-AI Screen Assistant")
camera = Camera(index=CAMERA_INDEX)


def _seed_history() -> list[ChatTurn]:
    return [{"role": "user", "content": INITIAL_USER_MESSAGE}]


class _State:
    """In-memory MVP state: latest snapshot + chat history."""

    def __init__(self) -> None:
        self.lock = Lock()
        self.image_bytes: bytes | None = None
        self.history: list[ChatTurn] = _seed_history()


state = _State()


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)


class AskResponse(BaseModel):
    answer: str
    history: list[ChatTurn]


@app.get("/")
def home() -> FileResponse:
    return FileResponse(TEMPLATES_DIR / "index.html")


@app.get("/history")
def get_history() -> dict:
    with state.lock:
        return {"history": list(state.history)}


@app.get("/snapshot")
def snapshot() -> Response:
    """Capture a fresh frame, store it as the active image, and return it."""
    try:
        jpeg = camera.capture_jpeg()
    except CameraError as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    with state.lock:
        state.image_bytes = jpeg

    return Response(content=jpeg, media_type="image/jpeg")


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    """Ask a question about the latest snapshot. Auto-captures if none yet."""
    with state.lock:
        image_bytes = state.image_bytes
        history_snapshot = list(state.history)

    if image_bytes is None:
        try:
            image_bytes = camera.capture_jpeg()
        except CameraError as exc:
            raise HTTPException(status_code=500, detail=str(exc))
        with state.lock:
            state.image_bytes = image_bytes

    try:
        answer = ask_with_image(
            image_bytes=image_bytes,
            history=history_snapshot,
            question=req.question,
        )
    except Exception as exc:  # noqa: BLE001 - surface real cause to the UI
        raise HTTPException(status_code=502, detail=f"LLM error: {exc}")

    with state.lock:
        state.history.append({"role": "user", "content": req.question})
        state.history.append({"role": "assistant", "content": answer})
        history_out = list(state.history)

    return AskResponse(answer=answer, history=history_out)


@app.post("/reset")
def reset() -> dict:
    with state.lock:
        state.history = _seed_history()
        state.image_bytes = None
        history_out = list(state.history)
    return {"ok": True, "history": history_out}


@app.on_event("shutdown")
def _shutdown() -> None:
    camera.release()
