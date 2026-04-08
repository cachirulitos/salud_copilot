from services.educational_content import get_educational_content

def test_laboratorio_returns_content():
    result = get_educational_content("laboratorio")
    assert result is not None
    assert "médico" in result

def test_unknown_study_returns_none():
    result = get_educational_content("estudio_desconocido_xyz")
    assert result is None

def test_partial_match_works():
    result = get_educational_content("sala de rayos_x digital")
    assert result is not None

def test_medical_disclaimer_always_present():
    for study in ["laboratorio", "ultrasonido", "rayos_x",
                  "electrocardiograma", "papanicolaou", "densitometria", "tomografia"]:
        result = get_educational_content(study)
        assert result is not None
        assert "médico" in result.lower(), f"Missing disclaimer for {study}"
