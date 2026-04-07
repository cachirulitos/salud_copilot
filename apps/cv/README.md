# SaludCopilot — Computer Vision

Conteo de personas en sala de espera con YOLOv8 + OpenCV.
Publica el conteo al backend cada N segundos via HTTP.

## Setup

```bash
cd apps/cv
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Para el demo

Apunta la webcam a la sala simulada. El script detecta personas
y publica el conteo a: POST http://localhost:8000/api/v1/turnos/afluencia
