# ADVERTENCIAS.md — SaludCopilot

> Estas tres advertencias deben resolverse ANTES de que cualquier
> agente empiece a programar. Son problemas de arquitectura, no de código.
> Resolverlas ahora cuesta 30 minutos. Encontrarlas después cuesta horas.

---

## Advertencia 1 — Rules engine: importación rota fuera de Docker

**Problema:**
El TASK.md de la API usa `sys.path.insert(0, "/packages")` para importar
el motor de reglas. Ese path solo existe dentro del contenedor Docker.
Si alguien corre `uvicorn` directamente (sin Docker), la API no arranca.

**Dónde ocurre:**
`apps/api/app/routers/visits.py` — en el check-in endpoint.

**Solución — hacer antes de programar el check-in:**

1. Crear `packages/rules_engine/setup.py`:
```python
from setuptools import setup, find_packages

setup(
    name="rules_engine",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
)
```

2. Agregar al final de `apps/api/requirements.txt`:
```
-e ../../packages/rules_engine
```

3. El import en la API queda así (limpio, sin sys.path):
```python
from rules_engine.engine import calculate_sequence, Study
```

4. En Docker, el `docker-compose.yml` ya monta el volumen correctamente.
   Con el paquete instalado en editable mode, funciona igual en ambos entornos.

**Quién lo resuelve:** Dev 1 (API), antes de Task 3.

---

## Advertencia 2 — Bot: race condition en validación de preparación

**Problema:**
Cuando el bot manda la pregunta de preparación ("¿completaste el ayuno?"),
guarda `awaiting_preparation_confirmation: true` en Redis.
Si el paciente manda dos mensajes rápidos antes de que el primero se procese,
ambos entran al webhook handler simultáneamente. Los dos leen el flag como `true`,
los dos lo procesan como respuesta de preparación, y el segundo puede ejecutar
lógica duplicada (dos PatientEvents, dos WhatsApps de respuesta).

**Dónde ocurre:**
`apps/bot/handlers/webhook.py` — en el handler de mensajes entrantes.

**Solución — implementar en Task 5 del bot:**

Usar Redis como lock atómico. Antes de procesar cualquier mensaje entrante:

```python
# Patrón correcto — operación atómica SET NX
lock_key = f"processing:{phone_number}"
acquired = await redis.set(lock_key, "1", nx=True, ex=10)  # TTL 10 segundos

if not acquired:
    # Otro mensaje de este número está siendo procesado
    # Ignorar silenciosamente — Meta reintentará si es necesario
    return  # siempre 200

try:
    # procesar mensaje aquí
    # si awaiting_preparation_confirmation:
    #   leer flag
    #   BORRAR flag ANTES de hacer cualquier otra cosa
    #   await redis.delete(f"session_prep_flag:{phone_number}")
    #   luego procesar la respuesta
finally:
    await redis.delete(lock_key)
```

**Quién lo resuelve:** Dev 2 (Bot), durante Task 5.

---

## Advertencia 3 — Dashboard: WebSocket con clinic_id que no existe

**Problema:**
El dashboard se conecta al WebSocket con `NEXT_PUBLIC_CLINIC_ID` desde `.env.local`.
Si la base de datos no tiene seed data, ese UUID no existe en la tabla `clinics`
y el broadcast nunca llega al dashboard aunque todo lo demás funcione.
Este es el tipo de bug que aparece en el Día 2 a las 11 PM.

**Dónde ocurre:**
`apps/dashboard/lib/websocket-client.ts` + ausencia de seed data en la DB.

**Solución — crear antes del Día 1:**

Crear `scripts/seed.py`:

```python
"""
Seed data para demo del hackathon.
Crea una clínica con sus áreas y devuelve los UUIDs necesarios.
Correr una sola vez después de `alembic upgrade head`.

Uso:
  cd apps/api
  python ../../scripts/seed.py
"""
import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

CLINIC_ID = str(uuid.uuid4())
AREAS = [
    {"name": "Laboratorio",         "study_type": "laboratorio",        "capacity": 3},
    {"name": "Ultrasonido",         "study_type": "ultrasonido",         "capacity": 2},
    {"name": "Rayos X",             "study_type": "rayos_x",             "capacity": 2},
    {"name": "Electrocardiograma",  "study_type": "electrocardiograma",  "capacity": 1},
    {"name": "Papanicolaou",        "study_type": "papanicolaou",        "capacity": 2},
    {"name": "Densitometría",       "study_type": "densitometria",       "capacity": 1},
    {"name": "Tomografía",          "study_type": "tomografia",          "capacity": 1},
]

async def seed():
    # ... insert clinic and areas
    print("\n=== SEED DATA CREATED ===")
    print(f"CLINIC_ID={CLINIC_ID}")
    for area in AREAS:
        print(f"AREA_{area['study_type'].upper()}_ID={area['id']}")
    print("\nCopy these values to:")
    print("  apps/dashboard/.env.local → NEXT_PUBLIC_CLINIC_ID")
    print("  apps/cv/.env → CAMERA_TO_AREA_MAPPING")
    print("========================\n")

asyncio.run(seed())
```

El script imprime los UUIDs al final. Esos valores van directo al `.env.local`
del dashboard y al `CAMERA_TO_AREA_MAPPING` del CV worker.

**Quién lo resuelve:** Dev 1 (API), antes del Día 2.


## Advertencia 4 — navigation_instructions requiere cambio de schema

**Problema:**
El Task 1b del bot requiere el campo `navigation_instructions` en la tabla
`clinical_areas`. Si Dev 2 (Bot) implementa la navegación textual antes de
que Dev 1 (API) agregue la columna al modelo y corra la migración,
el bot va a fallar al intentar leer un campo que no existe.

**Dónde ocurre:**
`apps/api/app/models/models.py` — modelo ClinicalArea.
`apps/bot/services/whatsapp_service.py` — función send_welcome_message.

**Solución:**
Dev 1 agrega la columna al modelo ANTES de que Dev 2 implemente Task 1b:

En ClinicalArea:
navigation_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

Luego corre: alembic revision --autogenerate -m "add_navigation_instructions"
Luego: alembic upgrade head

Dev 2 puede implementar Task 1b solo después de que la migración esté aplicada.

**Quién lo resuelve:** Dev 1 (API), al mismo tiempo que Task 1 (modelos).
```

Y agrega al checklist:
```
- [ ] **A4** — columna navigation_instructions en ClinicalArea, migración
              aplicada antes de que Dev 2 implemente Task 1b



---

## Checklist de resolución

Marca cada una antes de empezar la integración del Día 2:

- [ ] **A1** — `setup.py` creado, `-e ../../packages/rules_engine` en requirements.txt,
              import limpio sin `sys.path` en visits.py
- [ ] **A2** — Redis lock atómica en webhook handler, flag de preparación
              se borra antes de procesar respuesta
- [ ] **A3** — `scripts/seed.py` creado y ejecutado, UUIDs copiados a
              `.env.local` del dashboard y `.env` del CV worker

---

## Regla general

Si algo solo funciona dentro de Docker pero no en local, es una advertencia A1.
Si hay estado compartido entre dos requests concurrentes, es una advertencia A2.
Si un módulo depende de un UUID que otro módulo tiene que crear primero, es una advertencia A3.