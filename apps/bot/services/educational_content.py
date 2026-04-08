EDUCATIONAL_CONTENT: dict[str, dict] = {
    "laboratorio": {
        "title": "¿Sabías esto sobre tu análisis de laboratorio?",
        "content": (
            "Tu muestra se procesa en menos de 2 horas.\n"
            "La glucosa en ayuno tiene rango normal de 70–100 mg/dL.\n"
            "El colesterol total ideal es menor a 200 mg/dL.\n"
            "Para interpretar tus resultados, consulta con un médico."
        ),
    },
    "ultrasonido": {
        "title": "¿Sabías esto sobre tu ultrasonido?",
        "content": (
            "El ultrasonido usa ondas de sonido, no radiación.\n"
            "El estudio tarda entre 15 y 30 minutos.\n"
            "Si te pidieron tomar agua, ayuda a obtener imágenes más claras.\n"
            "Un médico especialista revisará las imágenes."
        ),
    },
    "rayos_x": {
        "title": "¿Sabías esto sobre tu radiografía?",
        "content": (
            "La dosis de radiación es mínima y segura.\n"
            "El estudio tarda menos de 5 minutos.\n"
            "Las imágenes estarán listas para tu médico en pocas horas.\n"
            "Avisa si estás embarazada antes del estudio."
        ),
    },
    "electrocardiograma": {
        "title": "¿Sabías esto sobre tu electrocardiograma?",
        "content": (
            "El ECG mide la actividad eléctrica de tu corazón.\n"
            "El estudio dura menos de 10 minutos y no duele.\n"
            "Detecta ritmo cardíaco, frecuencia y patrones eléctricos.\n"
            "Los resultados los interpreta tu médico."
        ),
    },
    "papanicolaou": {
        "title": "¿Sabías esto sobre tu Papanicolaou?",
        "content": (
            "Es el estudio preventivo más importante para la salud femenina.\n"
            "La toma de muestra tarda menos de 5 minutos.\n"
            "Se recomienda realizarlo cada año.\n"
            "Los resultados los revisa tu médico en días."
        ),
    },
    "densitometria": {
        "title": "¿Sabías esto sobre tu densitometría?",
        "content": (
            "Mide la densidad mineral de tus huesos.\n"
            "El estudio dura entre 10 y 20 minutos.\n"
            "El calcio y la vitamina D son clave para la salud ósea.\n"
            "Tu médico interpretará los resultados con tu historial."
        ),
    },
    "tomografia": {
        "title": "¿Sabías esto sobre tu tomografía?",
        "content": (
            "La tomografía toma imágenes detalladas en secciones del cuerpo.\n"
            "El estudio tarda entre 15 y 45 minutos.\n"
            "Si usas medio de contraste, avisa si eres alérgico.\n"
            "Los resultados los interpreta el médico radiólogo."
        ),
    },
}


def get_educational_content(study_type: str) -> str | None:
    """
    Return formatted educational message for a study type, or None if unknown.
    study_type is matched against keys using partial string matching.
    """
    for key, data in EDUCATIONAL_CONTENT.items():
        if key in study_type.lower():
            return f"{data['title']}\n\n{data['content']}"
    return None
