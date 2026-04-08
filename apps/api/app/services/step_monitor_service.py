import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.models import AlertType, ClinicalArea, DoctorAlert, VisitStep, VisitStepStatus
from app.routers.dashboard_ws import broadcast_to_clinic

logger = logging.getLogger(__name__)

OVERTIME_MARGIN_PCT = 0.15  # 15% over estimate triggers alert


async def check_overtime_steps() -> None:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(VisitStep, ClinicalArea)
            .join(ClinicalArea, VisitStep.clinical_area_id == ClinicalArea.id)
            .where(VisitStep.status == VisitStepStatus.IN_PROGRESS)
        )
        rows = result.all()

        for step, area in rows:
            if not step.started_at or not step.estimated_wait_minutes:
                continue

            elapsed_min = (datetime.now(timezone.utc) - step.started_at).total_seconds() / 60
            overtime_threshold = step.estimated_wait_minutes * (1 + OVERTIME_MARGIN_PCT)

            if elapsed_min <= overtime_threshold:
                continue

            # Deduplicate: skip if unresolved alert already exists
            existing_result = await db.execute(
                select(DoctorAlert).where(
                    DoctorAlert.visit_id == step.visit_id,
                    DoctorAlert.area_id == step.clinical_area_id,
                    DoctorAlert.alert_type == AlertType.OVERTIME,
                    DoctorAlert.resolved_at.is_(None),
                )
            )
            if existing_result.scalar_one_or_none() is not None:
                continue

            elapsed_int = int(elapsed_min)
            alert = DoctorAlert(
                clinic_id=area.clinic_id,
                area_id=step.clinical_area_id,
                visit_id=step.visit_id,
                alert_type=AlertType.OVERTIME,
                message=(
                    f"Consulta lleva {elapsed_int} min "
                    f"(estimado: {step.estimated_wait_minutes} min) "
                    f"en {area.name}"
                ),
            )
            db.add(alert)
            await db.flush()

            await broadcast_to_clinic(
                str(area.clinic_id),
                {
                    "event": "alert",
                    "data": {
                        "alert_type": "overtime",
                        "area_name": area.name,
                        "visit_id": str(step.visit_id),
                        "elapsed_minutes": elapsed_int,
                        "estimated_minutes": step.estimated_wait_minutes,
                        "message": alert.message,
                    },
                },
            )

        await db.commit()


async def run_step_monitor(interval_seconds: int = 60) -> None:
    while True:
        try:
            await check_overtime_steps()
        except Exception:
            logger.exception("step_monitor error")
        await asyncio.sleep(interval_seconds)
