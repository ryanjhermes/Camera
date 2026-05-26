# Camera

Point a webcam at your screen, capture a snapshot, and ask GPT-4o vision questions about what it sees.

## Setup

```bash
python -m venv venv
source venv/bin/activate   # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env       # or create .env with OPENAI_API_KEY=
uvicorn main:app --reload
```

Open http://127.0.0.1:8000

More detail: [docs/architecture.md](docs/architecture.md)  
Pi autostart: [docs/raspberry-pi-autostart.md](docs/raspberry-pi-autostart.md)  
Deploy to Pi: [docs/deploy.md](docs/deploy.md)
