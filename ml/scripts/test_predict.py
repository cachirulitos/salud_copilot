"""
Script simple para probar predicciones del modelo entrenado.

Uso:
  cd ml
  python scripts/test_predict.py
"""
import sys
from pathlib import Path

# Agregar la carpeta src al Path para importar predictor
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from predictor import WaitTimePredictor

def main():
    print("Iniciando predictor...")
    
    try:
        predictor = WaitTimePredictor()
    except Exception as e:
        print(f"Error al cargar el modelo: {e}")
        print("Asegúrate de que ya entrenaste el modelo (hay archivos en ml/artifacts/)")
        sys.exit(1)

    # Variables de entorno simuladas para la predicción
    # Ajusta 'clinic' al ID de alguna de tus sucursales (ej. 1 o 5)
    
    hour = 11               # 11:00 AM
    day = 1                 # Martes (Lunes=0)
    study = "ultrasonido"   # Estudio ya mapeado a string
    clinic = 1              # ID de sucursal CULIACAN (según el esquema)
    capacity = 2            # 2 consultorios disponibles
    queue = 4               # 4 personas esperando confirmadas
    appointment = False     # El paciente no tiene cita

    print("\n[+] Variables de Inferencia:")
    print(f"    - Hora del día: {hour}:00")
    print(f"    - Día: {day}")
    print(f"    - Tipo Estudio: {study}")
    print(f"    - Sucursal ID: {clinic}")
    print(f"    - Capacidad (cuartos): {capacity}")
    print(f"    - Longitud Fila: {queue}")
    print(f"    - Con cita previa: {appointment}")
    
    wait_time = predictor.predict_wait_minutes(
        hour_of_day=hour,
        day_of_week=day,
        study_type_raw_id=study,
        clinic_raw_id=clinic,
        simultaneous_capacity=capacity,
        current_queue_length=queue,
        has_appointment=appointment
    )
    
    print("\n==================================")
    print(f"⏳ Tiempo estimado de espera: {wait_time} minutos")
    print("==================================\n")

if __name__ == "__main__":
    main()
