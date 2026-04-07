import asyncio
import uuid
import sys
from pathlib import Path

# Agregar el directorio raíz de la API al path para poder importar módulos
API_DIR = Path(__file__).resolve().parent
sys.path.append(str(API_DIR))
ROOT_DIR = API_DIR.parent.parent
sys.path.append(str(ROOT_DIR))

from app.core.database import AsyncSessionLocal
from app.models.models import Clinic, ClinicalArea, Patient, Visit, VisitStatus, VisitStep, VisitStepStatus, WaitTimeEstimate

# UUIDs estáticos para facilitar las pruebas
CLINIC_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
AREA_LAB_ID = uuid.UUID("22222222-2222-2222-2222-222222222221")
AREA_ULTRASONIDO_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
AREA_RAYOS_X_ID = uuid.UUID("22222222-2222-2222-2222-222222222223")

PATIENT_1_ID = uuid.UUID("33333333-3333-3333-3333-333333333331")
VISIT_1_ID = uuid.UUID("44444444-4444-4444-4444-444444444441")

async def seed_data():
    print("Iniciando carga de datos mock...")
    async with AsyncSessionLocal() as db:
        # 1. Crear Clínica
        clinic = await db.get(Clinic, CLINIC_ID)
        if not clinic:
            print("Creando clínica...")
            clinic = Clinic(
                id=CLINIC_ID,
                name="Clínica Salud Digna (Mock)",
                address="Av. Siempre Viva 123",
                active=True,
            )
            db.add(clinic)

        # 2. Crear Áreas Clínicas
        areas_data = [
            (AREA_LAB_ID, "Laboratorio", "laboratorio", 10),
            (AREA_ULTRASONIDO_ID, "Ultrasonido", "ultrasonido", 2),
            (AREA_RAYOS_X_ID, "Rayos X", "rayos_x", 3),
        ]
        
        for area_id, name, study_type, capacity in areas_data:
            area = await db.get(ClinicalArea, area_id)
            if not area:
                print(f"Creando área {name}...")
                db.add(ClinicalArea(
                    id=area_id,
                    clinic_id=CLINIC_ID,
                    name=name,
                    study_type=study_type,
                    simultaneous_capacity=capacity,
                    active=True
                ))

        # 3. Crear un Paciente de Prueba
        patient = await db.get(Patient, PATIENT_1_ID)
        if not patient:
            print("Creando paciente de prueba...")
            patient = Patient(
                id=PATIENT_1_ID,
                phone_number="+521234567890",
                full_name="Paciente de Prueba",
            )
            db.add(patient)

        # 4. Crear una Visita de Prueba con Pasos (Visitas previas para Advance Step)
        visit = await db.get(Visit, VISIT_1_ID)
        if not visit:
            print("Creando visita de prueba (In Progress)...")
            visit = Visit(
                id=VISIT_1_ID,
                patient_id=PATIENT_1_ID,
                clinic_id=CLINIC_ID,
                status=VisitStatus.IN_PROGRESS,
                has_appointment=True,
                is_urgent=False,
            )
            db.add(visit)
            
            # Paso 1: Laboratorio (Completado)
            db.add(VisitStep(
                visit_id=VISIT_1_ID,
                clinical_area_id=AREA_LAB_ID,
                step_order=1,
                status=VisitStepStatus.COMPLETED,
                estimated_wait_minutes=15,
                actual_wait_minutes=12
            ))
            
            # Paso 2: Ultrasonido (En Progreso)
            db.add(VisitStep(
                visit_id=VISIT_1_ID,
                clinical_area_id=AREA_ULTRASONIDO_ID,
                step_order=2,
                status=VisitStepStatus.IN_PROGRESS,
                estimated_wait_minutes=20,
            ))
            
            # Paso 3: Rayos X (Pendiente)
            db.add(VisitStep(
                visit_id=VISIT_1_ID,
                clinical_area_id=AREA_RAYOS_X_ID,
                step_order=3,
                status=VisitStepStatus.PENDING,
                estimated_wait_minutes=15,
            ))

        await db.commit()
        print("✅ ¡Datos mock cargados exitosamente!")
        print("\n--- UUIDs para pruebas API ---")
        print(f"clinic_id: {CLINIC_ID}")
        print(f"study_id (Laboratorio): {AREA_LAB_ID}")
        print(f"study_id (Ultrasonido): {AREA_ULTRASONIDO_ID}")
        print(f"visit_id (para Advance Step): {VISIT_1_ID}")

if __name__ == "__main__":
    asyncio.run(seed_data())
