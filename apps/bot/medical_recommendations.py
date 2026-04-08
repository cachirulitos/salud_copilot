"""
Medical Recommendation Engine — placeholder for future bot integration.

This module will be responsible for:
  - Analyzing patient symptoms and current study results
  - Recommending additional or alternative studies
  - Notifying the relevant doctors about study changes via the API

Future integration point:
  - Input:  patient data (visit_id, completed studies, current symptoms)
  - Output: list of recommended study area IDs + reasoning

Developer notes:
  - Integrate with the API via POST /api/v1/notifications/study-change
  - The `INTERNAL_BOT_TOKEN` env var is used to authenticate bot→API calls
  - See docs/INTEGRACION.md § Bot Integration for the full flow
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
INTERNAL_BOT_TOKEN = os.getenv("INTERNAL_BOT_TOKEN", "saludcopilot-internal-token-change-in-prod")


# ── Data contracts ────────────────────────────────────────────────────────────


@dataclass
class PatientContext:
    """Snapshot of current patient state passed to the recommendation engine."""
    visit_id: str
    completed_studies: list[str]      # list of study_type strings already done
    pending_studies: list[str]        # list of study_type strings still pending
    symptoms: list[str]               # free-text symptom tags from bot conversation
    is_urgent: bool


@dataclass
class StudyRecommendation:
    """Output of a single recommendation."""
    area_id: str                      # UUID of the ClinicalArea to add/swap
    action: str                       # "add" | "replace"
    replaces_area_id: Optional[str]   # UUID of area to remove (only for "replace")
    reasoning: str                    # human-readable explanation for the doctor


# ── Recommendation engine ─────────────────────────────────────────────────────


class MedicalRecommendationEngine:
    """
    Analyzes patient context and produces study recommendations.

    Usage (future implementation)::

        engine = MedicalRecommendationEngine()
        recommendations = engine.recommend_studies(patient_context)
        for rec in recommendations:
            engine.notify_study_change(patient_context.visit_id, rec)
    """

    def recommend_studies(self, patient: PatientContext) -> list[StudyRecommendation]:
        """
        Given the current patient context, return a list of study recommendations.

        Args:
            patient: Current patient visit state including completed/pending studies
                     and bot-extracted symptoms.

        Returns:
            List of StudyRecommendation objects (may be empty if no changes needed).

        Raises:
            NotImplementedError: until ML/LLM logic is implemented.
        """
        raise NotImplementedError(
            "recommend_studies() is not yet implemented. "
            "Integrate an LLM or rule-based engine here."
        )

    def notify_study_change(
        self,
        visit_id: str,
        recommendation: StudyRecommendation,
        requesting_doctor_id: str,
    ) -> None:
        """
        Send a study-change notification to the API so both doctors are informed.

        Calls POST /api/v1/notifications/study-change with the bot's internal token.

        Args:
            visit_id: UUID of the patient visit.
            recommendation: The approved StudyRecommendation to apply.
            requesting_doctor_id: UUID of the doctor who triggered the change.

        Raises:
            NotImplementedError: until HTTP call is implemented.
        """
        raise NotImplementedError(
            "notify_study_change() is not yet implemented. "
            "Make an authenticated POST to /api/v1/notifications/study-change."
        )
