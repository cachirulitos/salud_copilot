from services.sentiment_service import detect_frustration

def test_frustration_detected_in_common_phrases():
    assert detect_frustration("ya llevo mucho tiempo esperando") is True
    assert detect_frustration("cuánto falta para que me atiendan") is True
    assert detect_frustration("están tardando demasiado tiempo") is True

def test_normal_message_not_flagged():
    assert detect_frustration("gracias") is False
    assert detect_frustration("¿cuáles son los horarios?") is False
    assert detect_frustration("hola buenos días") is False

def test_case_insensitive():
    assert detect_frustration("CUANTO FALTA") is True
    assert detect_frustration("Mucho Tiempo") is True
