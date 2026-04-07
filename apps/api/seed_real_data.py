import asyncio
import uuid
import sys
from pathlib import Path

# Configurar PYTHONPATH para importar módulos de la API
API_DIR = Path(__file__).resolve().parent
sys.path.append(str(API_DIR))
ROOT_DIR = API_DIR.parent.parent
sys.path.append(str(ROOT_DIR))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.models import Clinic, ClinicalArea

# Diccionario de Sucursales Reales (id_sucursal -> nombre)
SUCURSALES = {
    1: "CULIACAN",
    5: "LOS MOCHIS",
    74: "ATIZAPAN DE ZARAGOZA",
    75: "VALLE DE GUADALUPE",
    76: "IZTAPALAPA",
    77: "SAN LUIS POTOSI",
    78: "CHIHUAHUA",
    79: "TLALPAN",
    80: "MIGUEL HIDALGO",
    81: "IXTAPALUCA",
    82: "GUADALAJARA CIRCUNVALACION",
    83: "NEZAHUALCÓYOTL",
    84: "TUXTLA GUTIERREZ",
    85: "TECAMAC",
    86: "IZTAPALAPA CENTRO",
    87: "LOS REYES-LA PAZ",
    88: "RIO DE LOS REMEDIOS",
    89: "CHIMALHUACAN",
    91: "SALINA CRUZ",
    92: "CHALCO",
    93: "ECATEPEC SAN AGUSTIN",
    94: "CENTRO DE ENTRENAMIENTO Y CERTIFICACION",
    95: "IZTACALCO LA VIGA",
    96: "CULHUACAN",
    97: "PUEBLA CAPU",
    98: "COACALCO",
    99: "TULTITLAN",
    100: "GUSTAVO A.MADERO PROVIDENCIA"
}

# Diccionario de Estudios/Áreas Reales (id_estudio -> nombre)
ESTUDIOS = {
    1: "DENSITOMETRIA",
    2: "LABORATORIO",
    3: "MASTOGRAFIA",
    4: "PAPANICOLAOU",
    5: "RAYOS X",
    6: "ULTRASONIDO",
    7: "CONSULTA MEDICA",
    8: "DENTAL",
    9: "ELECTROCARDIOGRAMA",
    10: "MEDICINA",
    11: "TOMOGRAFIA",
    12: "RESONANCIA MAGNETICA",
    15: "PRUEBA DE HIBRIDOS",
    16: "NUTRICION",
    18: "MIDO",
    24: "OPTICA",
    34: "HEMODIALISIS",
    35: "VACUNACION",
    38: "PET-CT",
    40: "CONSULTA ESPECIALIZADA",
    41: "QUIRÓFANO",
    42: "ONCOLOGIA QUIMIOTERAPIA",
    43: "ONCOLOGIA RADIOTERAPIA",
    44: "SALA DE PROCEDIMIENTOS",
    49: "EPI PSICOLOGIA",
    50: "EPI MEDICINA GENERAL",
    52: "SALUD OCUPACIONAL - EMPRESAS",
    56: "BIOPSIAS",
    57: "TOMOSÍNTESIS",
    58: "MASTOGRAFIA CONTRASTADA",
    59: "BIOPSIAS MASTOGRAFIA"
}

STUDY_ID_TO_TYPE = {
    1:  "densitometria",
    2:  "laboratorio",
    3:  "mastografia",
    4:  "papanicolaou",
    5:  "rayos_x",
    6:  "ultrasonido",
    9:  "electrocardiograma",
    11: "tomografia",
    12: "resonancia",
    16: "nutricion",
}

def get_stable_uuid(prefix: str, numeric_id: int) -> uuid.UUID:
    """Genera un UUID estable a partir del ID histórico de la DB para evitar duplicados en mútliples corridas."""
    return uuid.uuid5(uuid.NAMESPACE_DNS, f"saludcopilot.com/{prefix}/{numeric_id}")


async def seed_real_data():
    print("Iniciando inyección de datos REALES a PostgreSQL...")
    async with AsyncSessionLocal() as db:
        
        # 1. Insertar o actualizar Clínicas
        for idx, name in SUCURSALES.items():
            clinic_uuid = get_stable_uuid("clinic", idx)
            clinic = await db.get(Clinic, clinic_uuid)
            
            if not clinic:
                print(f"🏥 Creando Clínica: {name} (ID Real: {idx})")
                clinic = Clinic(
                    id=clinic_uuid,
                    name=name,
                    address="Dirección pendiente", # Puedes llenar mas tarde
                    active=True,
                )
                db.add(clinic)
            
            # En cada clínica, insertemos al menos un bloque base de las Áreas más concurridas para empezar
            # Posteriormente puedes ampliar este array
            common_studies = [2, 5, 6, 9]  # Laboratorio, Rayos X, Ultrasonido, Electrocardiograma
            
            for study_id in common_studies:
                area_uuid = get_stable_uuid(f"area_{idx}", study_id)
                area_name = ESTUDIOS.get(study_id)
                
                # Verify clinical area
                result = await db.execute(
                    select(ClinicalArea).where(ClinicalArea.id == area_uuid)
                )
                existing_area = result.scalar_one_or_none()
                correct_study_type_str = STUDY_ID_TO_TYPE.get(study_id, f"estudio_{study_id}")

                if not existing_area:
                    db.add(ClinicalArea(
                        id=area_uuid,
                        clinic_id=clinic_uuid,
                        name=f"Área de {area_name.title()}",
                        study_type=correct_study_type_str,
                        simultaneous_capacity=10 if study_id == 2 else 3,
                        active=True
                    ))
                else:
                    existing_area.study_type = correct_study_type_str

        await db.commit()
        print("\n✅ ¡Datos base de clínicas y áreas insertados exitosamente!")
        
        print("\n=== Ejemplo de UUIDs listos para YOLO (Computer Vision) ===")
        # Imprime 2 o 3 UUIDs para que sepas como conectar las camaras inmediatamente
        culiacan_id = get_stable_uuid("clinic", 1)
        lab_culiacan_id = get_stable_uuid("area_1", 2)
        print(f"Culiacan Clinic UUID -> {culiacan_id}")
        print(f"Culiacan Laboratorio Area UUID -> {lab_culiacan_id}  <-- Mapealo en CV CAMERA_TO_AREA_MAPPING")

if __name__ == "__main__":
    asyncio.run(seed_real_data())
