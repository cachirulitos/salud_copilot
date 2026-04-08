# SaludCopilot — Bot WhatsApp

Chatbot conversacional vía WhatsApp Cloud API + Claude API.

## Setup

```bash
cd apps/bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../../.env.example .env
# Completa WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, ANTHROPIC_API_KEY
python main.py
```

## Exponer webhook con ngrok

```bash
ngrok http 8001
# Copia la URL https://xxxx.ngrok.io/webhook
# Regístrala en Meta Developers → WhatsApp → Webhooks
```

## Dos modos

- **Proactivo** (paciente con cita): bot inicia contacto al agendar, manda preparación y recordatorio 24h antes.
- **Reactivo** (sin cita): bot se activa en recepción, permanece silencioso salvo notificaciones de turno.
