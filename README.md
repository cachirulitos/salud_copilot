# SaludCopilot

Motor de orquestacion clinica para Salud Digna.
Genius Arena Hackathon 2026 — Equipo Cachirulitos

---

## Que es esto

Sistema que guia a pacientes de Salud Digna durante su visita via WhatsApp.
Calcula el orden optimo de estudios medicos, predice tiempos de espera con
vision computacional + ML, y da un dashboard en tiempo real al staff operativo.

---

## Estructura del monorepo

```
saludcopilot/
├── apps/
│   ├── api/          -> Backend FastAPI — logica de negocio, DB, WebSocket
│   ├── bot/          -> Chatbot WhatsApp + Gemini LLM
│   ├── dashboard/    -> Panel operativo Next.js
│   └── cv/           -> Vision computacional YOLOv8 (conteo de personas)
├── packages/
│   └── rules_engine/ -> Motor de reglas clinicas (modulo aislado, sin deps externas)
├── ml/               -> Modelo predictivo de tiempos de espera (RandomForest)
├── scripts/          -> Utilidades de desarrollo (seed, init SQL)
└── docker-compose.yml
```

**Regla clave:** solo la API escribe a PostgreSQL. Ningun otro modulo toca la DB directamente.

---

## Guia rapida para evaluadores

### Requisitos

- Docker Desktop (con Docker Compose v2)
- Python 3.12+ (solo para el CV Worker, que requiere acceso a webcam)
- Git

### Paso 1 — Clonar y configurar

```bash
git clone <url-del-repo>
cd saludcopilot
cp .env.example .env
```

Edita `.env` con tus credenciales. Las unicas variables que **necesitas llenar** para probar son:

| Variable | Donde obtenerla | Obligatoria para probar? |
|---|---|---|
| `LLM_API_KEY` | https://aistudio.google.com/apikey (gratis) | Solo si quieres probar el bot con Gemini |
| `WHATSAPP_TOKEN` | Meta for Developers | Solo para WhatsApp real |
| `WHATSAPP_PHONE_ID` | Meta for Developers | Solo para WhatsApp real |
| `WHATSAPP_PHONE_NUMBER` | Numero de WhatsApp Business (ej: `521XXXXXXXXXX`) | Solo para QR de check-in |

Las demas variables ya tienen valores funcionales para desarrollo local.

### Paso 2 — Levantar todo con un solo comando

```bash
docker compose up --build
```

Esto levanta **5 servicios**:

| Servicio | Puerto | URL |
|---|---|---|
| PostgreSQL | 5433 | (interno) |
| Redis | 6379 | (interno) |
| API (FastAPI) | 8000 | http://localhost:8000 |
| Bot (WhatsApp) | 8001 | http://localhost:8001 |
| Dashboard (Next.js) | 3000 | http://localhost:3000 |

### Paso 3 — Aplicar migraciones y seed (primera vez)

```bash
# Crear tablas en la DB
docker exec saludcopilot_api alembic upgrade head

# Cargar datos de prueba (clinica, areas, reglas)
docker exec saludcopilot_api python /app/scripts/seed.py
```

Si `seed.py` no esta disponible dentro del contenedor, ejecutar desde fuera:

```bash
pip install psycopg2-binary python-dotenv
python scripts/seed.py
```

### Paso 4 — Verificar que funciona

```bash
# API health
curl http://localhost:8000/health
# Esperado: {"status":"ok","service":"api",...}

# Bot health
curl http://localhost:8001/health
# Esperado: {"status":"ok","service":"bot",...}

# API docs interactivos (Swagger)
# Abrir en navegador: http://localhost:8000/docs

# Dashboard
# Abrir en navegador: http://localhost:3000
```

### Paso 5 — Probar el flujo completo (sin WhatsApp real)

```bash
# 1. Hacer check-in de un paciente
curl -X POST http://localhost:8000/api/v1/visits/check-in \
  -H "Content-Type: application/json" \
  -d '{
    "phone_number": "+5215512345678",
    "clinic_id": "1db93003-d50e-4f56-80d0-8b994b98eaa8",
    "study_ids": ["f68c2295-9053-4304-bbf7-f70dcd917853"],
    "has_appointment": false,
    "is_urgent": false
  }'
# Devuelve: visit_id, secuencia de estudios, tiempo estimado

# 2. Consultar contexto de la visita (lo que el bot usa para responder)
curl http://localhost:8000/api/v1/visits/<VISIT_ID>/context

# 3. Avanzar paso (simula que termino un estudio)
curl -X POST http://localhost:8000/api/v1/visits/<VISIT_ID>/advance-step

# 4. Simular conteo de personas (como si el CV worker enviara datos)
curl -X POST http://localhost:8000/api/v1/areas/f68c2295-9053-4304-bbf7-f70dcd917853/occupancy \
  -H "Content-Type: application/json" \
  -d '{"people_count": 5, "timestamp": "2026-04-07T10:00:00Z"}'

# 5. Ver estimacion de espera
curl http://localhost:8000/api/v1/areas/f68c2295-9053-4304-bbf7-f70dcd917853/wait-time-estimate
```

### Paso 6 — Probar WebSocket del dashboard (tiempo real)

```bash
# Terminal 1 — conectar al WebSocket
websocat ws://localhost:8000/ws/dashboard/1db93003-d50e-4f56-80d0-8b994b98eaa8

# Terminal 2 — disparar un evento de ocupacion
curl -X POST http://localhost:8000/api/v1/areas/f68c2295-9053-4304-bbf7-f70dcd917853/occupancy \
  -H "Content-Type: application/json" \
  -d '{"people_count": 8, "timestamp": "2026-04-07T10:00:00Z"}'
# En terminal 1 llega el evento en tiempo real
```

---

## CV Worker (Vision Computacional)

El CV Worker usa YOLOv8 para detectar personas en una camara y publica el conteo
a la API. **Requiere acceso a webcam, por eso corre fuera de Docker.**

### Setup

```bash
cd apps/cv
python -m venv .venv
source .venv/bin/activate   # Linux/Mac
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### Ejecutar

**Docker compose debe estar corriendo primero.**

```bash
cd apps/cv
source .venv/bin/activate

# Con webcam real:
python main.py

# Modo demo (sin camara fisica, datos simulados):
python main.py --demo

# Sin ventana (headless):
python main.py --demo --no-window

# Con archivo de video:
python main.py --video path/to/video.mp4 --area-id f68c2295-9053-4304-bbf7-f70dcd917853
```

Presiona `q` para salir de la ventana de preview.

---

## Flujo del paciente (WhatsApp)

```
Paciente llega a clinica
        |
        v
Escanea QR en recepcion (codigo por area)
        |
        v
Se abre WhatsApp con mensaje pre-llenado "CHECKIN_{clinic}_{area}"
        |
        v
Paciente presiona "Enviar"
        |
        v
Bot recibe mensaje → registra visita via API → calcula secuencia optima
        |
        v
Bot envia por WhatsApp:
  "Hola! Tu secuencia: 1. Laboratorio (~15 min) 2. Rayos X (~10 min)"
        |
        v
Paciente puede escribir preguntas → Gemini responde (navegacion, no diagnostico)
        |
        v
Bot notifica cuando su turno se acerca en cada area
```

El QR genera un link `wa.me` que abre WhatsApp directo. No requiere navegador,
no requiere estar en la misma red WiFi, no requiere IP del servidor.

---

## Endpoints de la API

| Endpoint | Metodo | Descripcion |
|---|---|---|
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI interactivo |
| `/api/v1/visits/check-in` | POST | Registrar visita con secuencia optima |
| `/api/v1/visits/{id}/context` | GET | Contexto de visita (para bot/dashboard) |
| `/api/v1/visits/{id}/advance-step` | POST | Avanzar paso de visita |
| `/api/v1/areas/?clinic_id=` | GET | Listar areas de una clinica |
| `/api/v1/areas/{id}/occupancy` | POST | Reportar conteo de personas (CV) |
| `/api/v1/areas/{id}/wait-time-estimate` | GET | Estimacion de espera |
| `/api/v1/admin/clinics` | GET | Listar clinicas |
| `/api/v1/admin/rules` | GET | Listar reglas clinicas |
| `/ws/dashboard/{clinic_id}` | WS | WebSocket tiempo real |

---

## Motor de reglas (packages/rules_engine)

Modulo aislado que calcula el orden optimo de estudios. No importa nada de la API.

**Reglas implementadas:**
- R-00: Urgentes primero, luego con cita, luego sin cita
- R-01: Papanicolaou antes que ultrasonido transvaginal
- R-02: En combinacion VPH + Pap + cultivo vaginal, Pap primero
- R-03: Densitometria antes que tomografia o resonancia
- R-04: Laboratorio con ayuno antes que ultrasonido
- R-05: Estudios sin preparacion antes que con preparacion

```bash
# Correr tests del motor de reglas
docker exec saludcopilot_api python -m pytest /packages/rules_engine/tests/ -v
```

---

## ML Pipeline (Modelo Predictivo)

```bash
cd ml
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Entrenar modelo (requiere CSVs en ml/data/)
cd src && python train.py
```

Genera artefactos en `ml/artifacts/`: `model.pkl` y `encodings.pkl`.
La API carga estos artefactos automaticamente para predecir tiempos de espera.

---

## Variables de entorno

Todas van en `.env` en la raiz. **NUNCA commitear `.env`** (esta en `.gitignore`).

| Variable | Para que | Valor default |
|---|---|---|
| `DATABASE_URL` | Conexion PostgreSQL | Configurado en docker-compose |
| `REDIS_URL` | Conexion Redis | Configurado en docker-compose |
| `SECRET_KEY` | JWT y seguridad | `cambia-esto-en-produccion` |
| `LLM_API_KEY` | API key Google Gemini | (vacio) |
| `WHATSAPP_TOKEN` | Token WhatsApp Cloud API | (vacio) |
| `WHATSAPP_PHONE_ID` | Phone ID de WhatsApp | (vacio) |
| `WHATSAPP_PHONE_NUMBER` | Numero para links wa.me | (vacio) |
| `INTERNAL_BOT_TOKEN` | Auth API-a-Bot | Token de desarrollo incluido |
| `INTERNAL_API_TOKEN` | Auth Bot-a-API | Token de desarrollo incluido |
| `INTERNAL_CV_TOKEN` | Auth CV-a-API | Token de desarrollo incluido |
| `CAMERA_TO_AREA_MAPPING` | Mapeo camara-area | `{"0":"<AREA_UUID>"}` |

---

## Seed data (UUIDs de prueba)

Despues de correr `seed.py`:

```
CLINIC_ID=1db93003-d50e-4f56-80d0-8b994b98eaa8

AREA_LABORATORIO=f68c2295-9053-4304-bbf7-f70dcd917853
AREA_ULTRASONIDO=bc09ede9-6f4d-4314-b681-5da0547ee513
AREA_RAYOS_X=55fae6ed-af60-4f9d-aca6-8e1619df6d86
AREA_ELECTROCARDIOGRAMA=879d301c-ff14-4512-921d-f496e9ec198e
AREA_PAPANICOLAOU=faab0f80-e5d1-4470-9fca-7ee5a6e7d77a
AREA_DENSITOMETRIA=a645f546-2351-4c1d-aae9-f8b8919edd7a
AREA_TOMOGRAFIA=d58be12a-36cd-442e-bce2-bf63aef724bb
```

---

## Documentacion adicional

| Archivo | Contenido |
|---|---|
| `docs/ARQUITECTURA.md` | Contratos entre modulos, schema de DB, flujos |
| `docs/ADVERTENCIAS.md` | Problemas conocidos y como resolverlos |
| `docs/INTEGRACION.md` | Guia detallada de integracion entre modulos |

---

## Convenciones

- **Variables, funciones, clases, endpoints:** en ingles
- **Nombres explicitos:** `calculate_study_sequence` no `calc_seq`
- **SQLAlchemy 2.0:** `Mapped` + `mapped_column`
- **Sin magic numbers:** constante con nombre en UPPER_SNAKE_CASE

### Commits

```
feat(api): add check-in endpoint with rules engine integration
fix(bot): handle duplicate webhook messages with Redis lock
docs(readme): update setup instructions
```
