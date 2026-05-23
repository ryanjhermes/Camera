from pathlib import Path
from threading import Lock
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from camera import Camera
from llm import ask_with_image

load_dotenv()

app = FastAPI()
camera = Camera(index=0)
image_bytes = None
image_lock = Lock()


@app.get("/")
def home():
    response = FileResponse(Path(__file__).parent / "templates" / "index.html")
    response.headers["Cache-Control"] = "no-store"
    return response

@app.get("/snapshot")
def snapshot():
    global image_bytes
    jpeg = camera.capture_jpeg()

    with image_lock:
        image_bytes = jpeg

    return Response(
        content=jpeg,
        media_type="image/jpeg",
        headers={"Cache-Control": "no-store, no-cache", "Pragma": "no-cache"},
    )

@app.post("/reset")
def reset():
    global image_bytes
    with image_lock:
        image_bytes = None
    return {"ok": True}

@app.post("/ask")
def ask(body: dict):
    question = body.get("question", "").strip()

    with image_lock:
        snapshot = image_bytes

    if not snapshot:
        raise HTTPException(status_code=400, detail="No snapshot yet. Take a picture first.")

    answer = ask_with_image(snapshot, question)

    return {"answer": answer}

@app.on_event("shutdown")
def _shutdown():
    camera.release()
