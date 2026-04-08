REFERENCE_RANGES: dict[str, str] = {
    "glucosa": "Rango normal en ayuno: 70–100 mg/dL",
    "colesterol": "Rango normal total: menor a 200 mg/dL",
    "trigliceridos": "Rango normal: menor a 150 mg/dL",
    "hemoglobina": "Rango normal: 12–17.5 g/dL (varía por sexo y edad)",
    "creatinina": "Rango normal: 0.6–1.2 mg/dL",
    "acido urico": "Rango normal: 3.5–7.2 mg/dL",
    "tsh": "Rango normal: 0.4–4.0 mUI/L",
    "vitamina d": "Rango suficiente: mayor a 30 ng/mL",
    "hemoglobina glicosilada": "Objetivo: menor a 5.7% (sin diabetes)",
}

DISCLAIMER = "⚠️ Para interpretar tus resultados, consulta con un médico."

def get_reference_context(study_name: str) -> str:
    """
    Return reference range info for a study name, always ending with disclaimer.
    Matches partial strings case-insensitively.
    Returns only disclaimer if no match found.
    """
    study_lower = study_name.lower()
    matched_ranges = [
        f"📊 {range_text}"
        for keyword, range_text in REFERENCE_RANGES.items()
        if keyword in study_lower
    ]
    lines = matched_ranges + [DISCLAIMER]
    return "\n".join(lines)
