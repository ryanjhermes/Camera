# Raspberry Pi autostart (systemd)

Starts the app automatically when the Pi boots. No Mac or SSH required for daily use.

## One-time install (on the Pi)

```bash
cd ~/Camera
bash deploy/install-service.sh
```

Requires `~/Camera/venv` and `~/Camera/.env` already set up.

## Daily use

1. Power on the Pi (wait ~1–2 minutes on first boot)
2. Plug in the EMEET
3. On your phone (same Wi‑Fi): **http://ryanhermespi.local:8000**

## Useful commands (on the Pi)

```bash
sudo systemctl status camera      # is it running?
sudo systemctl restart camera     # after code or .env changes
sudo systemctl stop camera         # stop the app
sudo journalctl -u camera -f       # live logs
```

## After updating code from your Mac

```bash
rsync -av --exclude venv --exclude __pycache__ --exclude .env \
  /Users/ryanhermes/Desktop/BIZTECH/Camera/ \
  ryanhermes@ryanhermespi.local:~/Camera/
```

On the Pi:

```bash
cd ~/Camera
source venv/bin/activate
pip install -r requirements.txt   # only if requirements.txt changed
sudo systemctl restart camera
```

## Remove autostart

```bash
sudo systemctl disable camera
sudo systemctl stop camera
sudo rm /etc/systemd/system/camera.service
sudo systemctl daemon-reload
```
