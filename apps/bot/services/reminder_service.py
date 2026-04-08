import logging

from services.whatsapp_service import send_text_message

logger = logging.getLogger(__name__)


async def send_appointment_confirmation(
    phone_number: str,
    patient_name: str,
    appointment_date: str,
    study_names: list[str],
    preparation_instructions: list[str],
) -> bool:
    """Send an appointment confirmation message with study list and preparation instructions."""
    studies_text = ", ".join(study_names)
    preparation_list = "\n".join(f"• {inst}" for inst in preparation_instructions)
    message = (
        f"✅ Cita confirmada, {patient_name}.\n"
        f"📅 {appointment_date}\n"
        f"🔬 Estudios: {studies_text}\n\n"
        f"📋 Preparación requerida:\n"
        f"{preparation_list}\n\n"
        f"Te enviaremos un recordatorio 24 horas antes."
    )
    return await send_text_message(phone_number, message)


async def send_appointment_reminder(
    phone_number: str,
    patient_name: str,
    appointment_date: str,
    preparation_instructions: list[str],
) -> bool:
    """Send a 24-hour reminder with preparation instructions."""
    preparation_list = "\n".join(f"• {inst}" for inst in preparation_instructions)
    message = (
        f"⏰ Recordatorio, {patient_name}.\n"
        f"Mañana tienes cita: {appointment_date}\n\n"
        f"📋 No olvides:\n"
        f"{preparation_list}"
    )
    return await send_text_message(phone_number, message)
