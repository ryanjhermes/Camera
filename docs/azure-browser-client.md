# Azure public URL + phone browser camera

This document describes (1) whether to isolate work in a nested folder, (2) the Azure steps to go from zero to a configured web app, and (3) what to implement in this repo so Safari on a phone can capture frames while the API and OpenAI key stay on the server.

---

## 1. Nested folder vs one codebase

**Recommendation:** keep **one FastAPI app** (`main:app`) and **one `requirements.txt`** so behavior and dependencies do not fork. Use **environment variables** to switch modes (local OpenCV vs cloud client-upload only).

Use a **nested folder only for Azure ops artifacts**, not a second copy of the Python app:

| Location | Purpose |
|----------|---------|
| Repo root (`main.py`, `llm.py`, …) | Application code; small, explicit branches for “server camera” vs “client JPEG only” |
| `docs/azure-browser-client.md` | This guide |
| `deploy/azure/` (create when ready) | `Dockerfile`, optional `startup.sh`, notes for GitHub Actions — **no** duplicate `main.py` unless you later extract a shared library |

**Why not a full nested app folder (e.g. `azure-app/` with its own `main.py`)?** Duplication drifts: two `/ask` handlers, two history shapes, double fixes. The risk to “the rest of the project” is better controlled with **lazy OpenCV** (see agent checklist) and a **single template** or a second template only if the UI diverges a lot.

If you prefer a second HTML page only, `templates/index_client.html` next to `index.html` is fine; routing can choose by env.

---

## 2. Azure: steps from empty to configured

These steps assume you want a **simple managed web host** (Python + HTTPS + env vars). **Azure App Service (Linux) + Python 3.11** is the straightest path; Container Apps is fine too but adds container build/push.

### 2.1 Prereqs

- Azure account (subscription).
- Repo pushed to **GitHub** (or use ZIP deploy from your machine).
- For local OpenCV workflow unchanged: developers still run `uvicorn` on Mac/Windows; Azure only needs a mode **without** a physical datacenter camera.

### 2.2 Create an isolated resource group

1. Portal: **Resource groups** → **Create**.
2. **Subscription:** yours.
3. **Region:** pick one close to you (e.g. `East US 2`); same region for everything below reduces latency and billing noise.
4. **Name:** e.g. `rg-camera-assistant-dev`.
5. **Create**.

Everything below goes into this group so you can delete one resource group later and wipe the experiment.

### 2.3 App Service Plan (compute)

1. **Create a resource** → **App Service Plan**.
2. **OS:** Linux.
3. **Pricing tier:** for a personal MVP, **B1** (Basic) avoids some free-tier limits; **F1** Free is possible but has **CPU/memory and no SLA** — OK for smoke tests.
4. **Name / region / resource group:** link to `rg-camera-assistant-dev`, same region.

### 2.4 Web App (the site + runtime)

1. **Create a resource** → **Web App**.
2. **Publish:** Code (not Docker) if you want the simplest path; **Docker** is alternative if you add a `Dockerfile` under `deploy/azure/`.
3. **Runtime stack:** Python 3.11 (or 3.12 if offered and you match it locally).
4. **Linux Plan:** select the plan from 2.3.
5. **Name:** globally unique, e.g. `camera-assistant-<yourinitials>` → URL `https://camera-assistant-<yourinitials>.azurewebsites.net`.

### 2.5 Application settings (configuration)

In the Web App: **Settings** → **Environment variables** (or **Configuration** → **Application settings**):

| Name | Example / notes |
|------|------------------|
| `OPENAI_API_KEY` | Your secret (use **Key vault reference** later if you want; plain setting is OK for a locked-down MVP). |
| `OPENAI_MODEL` | e.g. `gpt-4o` |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` if using Oryx build from repo (installs `requirements.txt`). |
| `WEBSITES_PORT` | `8000` if your process listens on 8000 (see startup below). |

**New settings for the browser-camera design** (names illustrative; align with what you implement):

| Name | Purpose |
|------|---------|
| `CAMERA_SOURCE` | `server` (default, current behavior) vs `client` (Azure: no OpenCV device; accept JPEG from browser). |
| `APP_SHARED_SECRET` | Long random string; browser sends `X-App-Key` on upload so random crawlers cannot POST images to your billable OpenAI backend. |

**Optional hardening:**

- **IP restrictions** / **Private Endpoint** — overkill for first MVP; useful if the URL leaks.
- **Key Vault** + **managed identity** — store `OPENAI_API_KEY` as a secret reference in app settings.

Save configuration; the app restarts.

### 2.6 Startup command

App Service expects your process to listen on **`WEBSITES_PORT`** (often 8000). Under **Configuration** → **General settings** → **Startup Command**, example:

```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Or with Gunicorn + Uvicorn workers (production-ish):

```bash
gunicorn main:app -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000 --workers 1
```

Use **one worker** unless you add external session store (today’s app uses **in-memory** state per process).

### 2.7 Deployment

Pick one:

- **Deployment Center:** Web App → **Deployment** → **Deployment Center** → GitHub → select repo/branch → enable **build** so Oryx runs `pip install -r requirements.txt` on deploy.
- **ZIP deploy** / **VS Code Azure extension** for ad-hoc uploads.

Ensure project root contains `requirements.txt` and `main.py` at the paths Oryx expects (repo root is typical).

### 2.8 HTTPS and phone

App Service provides **HTTPS** by default. Mobile Safari generally requires **secure context** for `getUserMedia`; your `https://*.azurewebsites.net` URL satisfies that.

### 2.9 Smoke test before client camera exists

With `CAMERA_SOURCE=server` on Azure, `/snapshot` may still **fail** (no camera in cloud). That is expected until the **client-upload** path exists and the UI uses it. After implementation, set `CAMERA_SOURCE=client` in Azure and test upload + `/ask`.

### 2.10 Cost and cleanup

- Watch **OpenAI usage** (public URL + weak auth = abuse risk).
- Deleting **resource group** `rg-camera-assistant-dev` removes the Web App and plan (and stops compute billing subject to Azure billing rules).

---

## 3. Brief for an AI agent (codebase access)

Goal: **same product behavior** (snapshot → optional auto-question → chat with same image context, reset), but when `CAMERA_SOURCE=client`:

1. **No OpenCV / `VideoCapture` at import time** on Azure — today `main.py` does `camera = Camera(...)` at module load, which imports `cv2` and can fail or behave badly without devices. **Lazy-init** `Camera` only when `CAMERA_SOURCE=server` (or when first server snapshot is requested).

2. **New endpoint** (example contract):
   - `POST /snapshot/client` (or `PUT /snapshot`)  
   - **Body:** `multipart/form-data` with a single image field **or** `application/octet-stream` of raw JPEG bytes.  
   - **Header:** `X-App-Key: <APP_SHARED_SECRET>` when `APP_SHARED_SECRET` is set; reject with **401** if missing/wrong.  
   - **Behavior:** validate magic bytes / `image/jpeg`, size cap (e.g. ≤ 5–10 MB), then set `state.image_bytes` exactly like current `/snapshot` after capture. Return **200** + optional JSON `{ "ok": true }` or return the image like today for simpler UI reuse.

3. **`GET /snapshot`** when `CAMERA_SOURCE=client`: either **404** with a clear message, **redirect** to docs, or return a **placeholder** — avoid calling OpenCV.

4. **`POST /ask`:** already uses `state.image_bytes`; if missing and `CAMERA_SOURCE=client`, return **400** telling the user to upload a snapshot first (do not try `camera.capture_jpeg()`).

5. **Frontend (`templates/index.html` or `index_client.html`):**
   - `<video autoplay playsinline muted>` fed by `navigator.mediaDevices.getUserMedia({ video: { facingMode / deviceId } })`.
   - Optional: `enumerateDevices()` + `<select>` to pick camera (helps with USB webcams on iPad/iPhone where supported).
   - “Take picture”: draw current video frame to **canvas**, `canvas.toBlob('image/jpeg', quality)`, `fetch('/snapshot/client', { method: 'POST', headers: { 'X-App-Key': ... }, body: formData })`.  
   - **Never** embed `OPENAI_API_KEY` in the page; only `APP_SHARED_SECRET` if you accept a shared “gate” (still weak vs dedicated auth — document that).

6. **CORS:** not required if HTML and API are **same origin** (single FastAPI app serving templates and API). If you split static to a CDN later, add CORS then.

7. **`.env.example`:** document `CAMERA_SOURCE`, `APP_SHARED_SECRET`, Azure port notes.

8. **Dependencies:** In `client-only` deploys, **opencv** is unused but still installable (heavy). Optional follow-up: `requirements-azure.txt` without opencv + conditional imports — nice-to-have, not blocking if image size is acceptable.

9. **Local dev:** default `CAMERA_SOURCE=server` so today’s flow unchanged; test client path with `CAMERA_SOURCE=client` and browser upload against local `uvicorn`.

10. **Security note for the human:** Rotating `APP_SHARED_SECRET` and using **App Service Authentication** or **Front Door + WAF** is the next step if the URL is semi-public.

---

## 4. Order of operations (human + agent)

1. You: create resource group + App Service + settings skeleton (API key placeholder).
2. Agent: implement lazy camera + client snapshot endpoint + UI branch + env docs.
3. You: set real secrets, deploy, open `https://<app>.azurewebsites.net` on phone, verify camera permission + upload + ask + reset.
4. You: add abuse controls if the URL is shared.

This file is the single source for “why Azure pieces exist” and “what code must change” without forking the project into an unmaintained nested app.
