# Architecture

A small local web app: webcam → JPEG snapshot → OpenAI vision → short answer in the browser.

## Components

| File | Role |
|------|------|
| `main.py` | FastAPI server, routes, cached snapshot |
| `camera.py` | Webcam capture (OpenCV + Pillow → JPEG bytes) |
| `llm.py` | OpenAI vision API call |
| `templates/index.html` | UI: preview, chat log, Take Picture / Ask / Clear |

## Request flow

```
Browser                    main.py                 camera.py / llm.py
───────                    ───────                 ──────────────────

GET  /                     → serve index.html

GET  /snapshot             → capture_jpeg()        → open webcam, read frame, JPEG
                           → store image_bytes
                           ← JPEG (preview)

POST /ask { question }     → read image_bytes      → ask_with_image(bytes, question)
                           ← { answer }            → GPT-4o vision
```

**Take Picture** (main path): browser calls `/snapshot`, then `/ask` with a default question (`"What's the answer?"`).

**Manual Ask**: if there is no snapshot yet, the browser calls `/snapshot` first, then `/ask`.

**Clear**: client-only — wipes chat and preview. The next capture overwrites the server cache.

## Design choices

### Cached snapshot (`image_bytes`)

The server keeps one JPEG in memory. `/snapshot` writes it; `/ask` reads it. That way you can ask multiple questions about the same picture without capturing again.

`image_lock` prevents two requests from reading/writing that cache at the same time.

### Stateless LLM calls

Each `/ask` sends only:

- system prompt (instructions + practice-exam context)
- current question + current image

No chat history is sent to OpenAI. That keeps token cost flat across many questions (e.g. 60–70 exam items). Follow-ups on the **same** image still work; the model does not remember prior Q&A text unless you restate it.

### `Camera` class

The webcam connection and settings persist across captures (device index, JPEG quality, thread lock). One `Camera` instance is created at startup in `main.py` and reused.

### No server `/reset`

Clearing the session is handled in the browser. A new `/snapshot` replaces the cached image.

## Environment

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Required — OpenAI API key |
| `SYSTEM_PROMPT` | Required — instructions sent to the model on every ask |

Model is hardcoded to `gpt-4o` in `llm.py`.

## Shutdown

On server stop, `camera.release()` closes the webcam device.
