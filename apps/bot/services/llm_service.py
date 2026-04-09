import json
import logging

from google import genai

from config import settings

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.5-flash"
MAX_OUTPUT_TOKENS = 800

SYSTEM_PROMPT = (
    "Eres SaludCopilot, asistente del paciente en clínicas Salud Digna. "
    "Ayudas al paciente a navegar su visita: secuencia de estudios, "
    "tiempos de espera, instrucciones de preparación e información general.\n\n"
    "REGLAS ESTRICTAS — nunca las violes:\n"
    "- Nunca interpretes, diagnostiques ni expliques qué significan los resultados clínicamente.\n"
    "- Nunca recomiendes medicamentos, tratamientos ni dosis específicas.\n"
    "- Si te preguntan sobre resultados, responde ÚNICAMENTE: "
    "'Para interpretar tus resultados, consulta con un médico.'\n"
    "- Responde SIEMPRE en español.\n"
    "- Sé cálido, claro y tan detallado como el paciente necesite.\n\n"
    "Contexto actual del paciente:\n{context_json}"
)

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Lazily initialize the Gemini client so tests don't fail without an API key."""
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.llm_api_key)
    return _client


async def generate_response(patient_message: str, visit_context: dict) -> str | None:
    """Send the patient message to Gemini with visit context and return the response text."""
    context_json = json.dumps(visit_context, ensure_ascii=False, indent=2)
    system_instruction = SYSTEM_PROMPT.format(context_json=context_json)

    try:
        client = _get_client()
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=patient_message,
            config=genai.types.GenerateContentConfig(
                system_instruction=system_instruction,
                max_output_tokens=MAX_OUTPUT_TOKENS,
            ),
        )
        return response.text
    except Exception:
        logger.exception("Gemini API error for message: %s", patient_message[:50])
        return None
