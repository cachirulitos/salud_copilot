"""
Clinical rules engine tests.
One test per rule behavior. Run with: pytest packages/rules_engine/tests/ -v
"""

from rules_engine.engine import Study, calculate_sequence


def test_r00_urgent_patient_goes_first():
    # Arrange
    studies = [
        Study(id="1", type="laboratorio"),
        Study(id="2", type="ultrasonido", is_urgent=True),
    ]

    # Act
    result = calculate_sequence(studies)

    # Assert
    types = [step.study.type for step in result.steps]
    assert types[0] == "ultrasonido"


def test_r00_appointment_patient_before_walkin():
    # Arrange
    studies = [
        Study(id="1", type="laboratorio"),
        Study(id="2", type="ultrasonido", has_appointment=True),
    ]

    # Act
    result = calculate_sequence(studies)

    # Assert
    types = [step.study.type for step in result.steps]
    assert types[0] == "ultrasonido"


def test_r01_papanicolaou_before_transvaginal_ultrasound():
    # Arrange
    studies = [
        Study(id="1", type="ultrasonido_transvaginal"),
        Study(id="2", type="papanicolaou"),
    ]

    # Act
    result = calculate_sequence(studies)

    # Assert
    types = [step.study.type for step in result.steps]
    assert types.index("papanicolaou") < types.index("ultrasonido_transvaginal")
    assert result.steps[0].rule_applied == "R-01"


def test_r02_papanicolaou_first_in_vph_cultivo_combination():
    # Arrange
    studies = [
        Study(id="1", type="vph"),
        Study(id="2", type="cultivo_vaginal"),
        Study(id="3", type="papanicolaou"),
    ]

    # Act
    result = calculate_sequence(studies)

    # Assert
    types = [step.study.type for step in result.steps]
    assert types[0] == "papanicolaou"
    assert result.steps[0].rule_applied == "R-02"


def test_r03_densitometry_before_tomography():
    # Arrange
    studies = [
        Study(id="1", type="tomografia"),
        Study(id="2", type="densitometria"),
    ]

    # Act
    result = calculate_sequence(studies)

    # Assert
    types = [step.study.type for step in result.steps]
    assert types.index("densitometria") < types.index("tomografia")
    assert result.steps[0].rule_applied == "R-03"


def test_r03_densitometry_before_resonance():
    # Arrange
    studies = [
        Study(id="1", type="resonancia"),
        Study(id="2", type="densitometria"),
    ]

    # Act
    result = calculate_sequence(studies)

    # Assert
    types = [step.study.type for step in result.steps]
    assert types.index("densitometria") < types.index("resonancia")
    assert result.steps[0].rule_applied == "R-03"


def test_r04_fasting_lab_before_ultrasound():
    # Arrange
    studies = [
        Study(id="1", type="ultrasonido"),
        Study(id="2", type="laboratorio", requires_fasting=True),
    ]

    # Act
    result = calculate_sequence(studies)

    # Assert
    types = [step.study.type for step in result.steps]
    assert types.index("laboratorio") < types.index("ultrasonido")
    assert result.steps[0].rule_applied == "R-04"


def test_r04_non_fasting_lab_does_not_trigger_rule():
    # Arrange
    studies = [
        Study(id="1", type="ultrasonido"),
        Study(id="2", type="laboratorio", requires_fasting=False),
    ]

    # Act
    result = calculate_sequence(studies)

    # Assert
    for step in result.steps:
        assert step.rule_applied != "R-04"


def test_r05_no_preparation_before_preparation_required():
    # Arrange
    studies = [
        Study(id="1", type="laboratorio", requires_fasting=True),
        Study(id="2", type="electrocardiograma", requires_fasting=False),
    ]

    # Act
    result = calculate_sequence(studies)

    # Assert
    types = [step.study.type for step in result.steps]
    assert types.index("electrocardiograma") < types.index("laboratorio")


def test_single_study_returns_that_study():
    # Arrange
    studies = [Study(id="1", type="laboratorio")]

    # Act
    result = calculate_sequence(studies)

    # Assert
    assert len(result.steps) == 1
    assert result.steps[0].study.type == "laboratorio"


def test_empty_input_returns_empty_sequence():
    # Arrange
    studies = []

    # Act
    result = calculate_sequence(studies)

    # Assert
    assert result.steps == []
    assert result.estimated_time_minutes == 0


def test_time_estimate_two_studies_equals_35_minutes():
    # Arrange
    studies = [
        Study(id="1", type="laboratorio"),
        Study(id="2", type="electrocardiograma"),
    ]

    # Act
    result = calculate_sequence(studies)

    # Assert — 2 studies × 15min + 1 transfer × 5min = 35min
    assert result.estimated_time_minutes == 35


def test_rule_applied_code_stored_in_step():
    # Arrange
    studies = [
        Study(id="1", type="ultrasonido_transvaginal"),
        Study(id="2", type="papanicolaou"),
    ]

    # Act
    result = calculate_sequence(studies)

    # Assert
    rule_codes = [step.rule_applied for step in result.steps]
    assert "R-01" in rule_codes


def test_reason_is_in_spanish():
    # Arrange
    studies = [
        Study(id="1", type="ultrasonido_transvaginal"),
        Study(id="2", type="papanicolaou"),
    ]

    # Act
    result = calculate_sequence(studies)

    # Assert
    first_reason = result.steps[0].reason
    assert "debe" in first_reason or "Orden" in first_reason
