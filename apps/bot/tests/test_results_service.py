from services.results_service import get_reference_context, DISCLAIMER

def test_known_study_includes_range():
    result = get_reference_context("glucosa en ayuno")
    assert "70–100" in result
    assert DISCLAIMER in result

def test_unknown_study_includes_only_disclaimer():
    result = get_reference_context("estudio_desconocido")
    assert DISCLAIMER in result
    assert "📊" not in result

def test_multiple_matches_included():
    result = get_reference_context("glucosa y colesterol total")
    assert "70–100" in result
    assert "200" in result

def test_disclaimer_always_last_line():
    result = get_reference_context("tsh")
    assert result.strip().endswith(DISCLAIMER)
