"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  Loader2,
  Stethoscope,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface SequenceStep {
  order: number;
  area_id?: string;
  area_name: string;
  estimated_wait_minutes: number;
  rule_applied: string | null;
  status?: string;
  position_in_queue?: number;
}

interface VisitContext {
  visit_id: string;
  patient_name: string;
  current_step: SequenceStep;
  remaining_steps: SequenceStep[];
  total_estimated_minutes: number;
}

export default function PatientTestPage() {
  const { visit_id } = useParams<{ visit_id: string }>();

  const [context, setContext] = useState<VisitContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [advancing, setAdvancing] = useState(false);
  const [reordering, setReordering] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchContext = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/v1/visits/${visit_id}/context`);
      if (res.ok) {
        const data = await res.json();
        setContext(data);
      }
    } catch (err) {
      // Silently fail polling
    } finally {
      setLoading(false);
    }
  }, [visit_id]);

  useEffect(() => {
    fetchContext();
    const interval = setInterval(fetchContext, 5000);
    return () => clearInterval(interval);
  }, [fetchContext]);

  async function handleAdvanceStep() {
    setAdvancing(true);
    setError(null);
    try {
      const res = await fetch(`${API}/api/v1/visits/${visit_id}/advance-step`, {
        method: "POST",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body?.detail || body?.error || `Error ${res.status}`);
      }
      await fetchContext();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al avanzar paso.");
    } finally {
      setAdvancing(false);
    }
  }

  async function handleMoveArea(index: number, direction: "up" | "down") {
    if (!context) return;
    const pendingSteps = [
      ...(context.current_step?.status === "pending"
        ? [context.current_step]
        : []),
      ...context.remaining_steps,
    ].filter(Boolean);
    if (pendingSteps.length < 2) return;

    const newArr = [...pendingSteps];
    if (direction === "up" && index > 0) {
      [newArr[index - 1], newArr[index]] = [newArr[index], newArr[index - 1]];
    } else if (direction === "down" && index < newArr.length - 1) {
      [newArr[index], newArr[index + 1]] = [newArr[index + 1], newArr[index]];
    } else {
      return;
    }

    setReordering(true);
    setError(null);

    try {
      const proposed_sequence = newArr
        .map((s) => s.area_id)
        .filter(Boolean) as string[];
      const res = await fetch(
        `${API}/api/v1/visits/${visit_id}/reorder-sequence`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ proposed_sequence }),
        },
      );

      const body = await res.json().catch(() => ({}));

      if (!res.ok) {
        if (body?.rules_violations && Array.isArray(body.rules_violations)) {
          throw new Error(body.rules_violations.join("  |  "));
        }
        throw new Error(
          body?.detail || body?.error || body?.code || `Error ${res.status}`,
        );
      }

      if (body.accepted === false) {
        if (body.rules_violations?.length > 0) {
          throw new Error(body.rules_violations.join("  |  "));
        } else if (body.reorder_rejected_reason) {
          throw new Error(body.reorder_rejected_reason);
        }
      }

      await fetchContext();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al reordenar.");
      await fetchContext();
    } finally {
      setReordering(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-brand-green" />
      </div>
    );
  }

  if (!context) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <p className="text-gray-500">Visita no encontrada.</p>
      </div>
    );
  }

  const isFinished =
    !context.current_step && context.remaining_steps.length === 0;

  const pendingSteps = context
    ? [
        ...(context.current_step?.status === "pending"
          ? [context.current_step]
          : []),
        ...context.remaining_steps,
      ].filter(Boolean)
    : [];

  const inProgressStep =
    context?.current_step?.status === "in_progress"
      ? context.current_step
      : null;

  return (
    <div className="min-h-screen bg-surface-base px-4 py-10">
      <div className="max-w-xl mx-auto space-y-6">
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex justify-center mb-2">
            <Activity
              className="w-10 h-10 text-brand-green"
              strokeWidth={2.5}
            />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">
            Mi Visita
          </h1>
          <p className="text-sm text-gray-500">
            {context.patient_name} — {visit_id}
          </p>
        </div>

        {error && (
          <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl p-4 text-red-700 text-sm shadow-sm">
            <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
            <span className="font-medium">{error}</span>
          </div>
        )}

        {isFinished ? (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8 text-center space-y-4">
            <div className="flex justify-center flex-col items-center gap-2">
              <CheckCircle2 className="w-16 h-16 text-brand-green" />
              <h2 className="text-xl font-bold text-gray-900">
                Visita Completada
              </h2>
              <p className="text-gray-500 text-sm">
                El paciente ha finalizado todos sus estudios.
              </p>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-brand-green/20 shadow-sm overflow-hidden ring-1 ring-brand-green/10">
            <div className="px-5 py-4 bg-brand-green/5 border-b border-brand-green/10 flex justify-between items-center">
              <h2 className="font-semibold text-brand-green flex items-center gap-2">
                <Stethoscope className="w-4 h-4" />
                Atención y Próximos Estudios
              </h2>
              <span className="text-xs text-brand-green flex items-center gap-1 font-bold">
                <Clock className="w-3 h-3" />~{context.total_estimated_minutes}{" "}
                min
              </span>
            </div>

            {inProgressStep && (
              <div className="border-b border-gray-100 p-5 bg-brand-green/5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold px-2 py-1 bg-brand-green text-white rounded-md uppercase">
                    Dentro del Consultorio
                  </span>
                </div>
                <h3 className="text-lg font-bold text-gray-900">
                  {inProgressStep.area_name}
                </h3>
                <p className="text-sm text-gray-500 mt-1">
                  El doctor te está atendiendo en este momento.
                </p>

                <button
                  onClick={handleAdvanceStep}
                  disabled={advancing}
                  className="mt-4 w-full bg-brand-green text-white font-semibold py-3 rounded-xl text-sm hover:bg-brand-green/90 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 shadow-sm">
                  {advancing ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    "Terminar Cita Actual (Finalizar Paso)"
                  )}
                </button>
              </div>
            )}

            <div className="p-5 flex flex-col gap-4">
              {pendingSteps.length > 0 && !inProgressStep && (
                  <button
                    onClick={handleAdvanceStep}
                    disabled={advancing || pendingSteps[0].position_in_queue !== 0}
                    className={`w-full font-semibold py-3.5 rounded-xl text-sm flex items-center justify-center gap-2 shadow-sm transition-colors ${
                      pendingSteps[0].position_in_queue !== 0
                        ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                        : "bg-gray-900 text-white hover:bg-gray-800 disabled:opacity-50"
                    }`}>
                    {advancing ? (
                      <Loader2 className="w-5 h-5 animate-spin" />
                    ) : pendingSteps[0].position_in_queue !== 0 ? (
                      `Esperando turno en fila (${pendingSteps[0].position_in_queue} delante de ti)`
                    ) : (
                      `Finalizar el Paso en Espera (${pendingSteps[0].area_name})`
                    )}
                  </button>
              )}

              {pendingSteps.length > 0 && (
                <div className={`mt-2 rounded-xl border border-gray-100 divide-y divide-gray-100 bg-gray-50/50 ${reordering ? 'opacity-50 pointer-events-none' : ''}`}>
                  {pendingSteps.map((step, index) => {
                    const queueHeadLocked = step.position_in_queue === 0 || (index === 0 && context.current_step?.position_in_queue === 0);
                    const isLockedFromAbove = context.current_step?.position_in_queue === 0 && index === 1;

                    return (
                    <div key={`${step.area_name}-${index}`} className="px-4 py-3 flex items-center gap-4">
                      
                      {/* Priority Up/Down */}
                      <div className="flex flex-col gap-0.5 shrink-0">
                        <button
                          type="button"
                          disabled={index === 0 || isLockedFromAbove}
                          onClick={() => handleMoveArea(index, "up")}
                          className="p-1 text-gray-400 hover:text-gray-900 hover:bg-gray-200 rounded disabled:opacity-30 disabled:hover:bg-transparent">
                          <ChevronUp className="w-4 h-4" />
                        </button>
                        <button
                          type="button"
                          disabled={index === pendingSteps.length - 1 || queueHeadLocked}
                          onClick={() => handleMoveArea(index, "down")}
                          className="p-1 text-gray-400 hover:text-gray-900 hover:bg-gray-200 rounded disabled:opacity-30 disabled:hover:bg-transparent">
                          <ChevronDown className="w-4 h-4" />
                        </button>
                      </div>

                      <span className={`w-8 h-8 rounded-full text-xs font-bold flex items-center justify-center shrink-0 ${index === 0 && !inProgressStep ? 'bg-brand-green text-white shadow-sm' : 'bg-white border border-gray-200 text-gray-500'}`}>
                        {step.order}
                      </span>
                      <div className="flex-1 min-w-0">
                        <p className={`font-semibold text-sm ${index === 0 && !inProgressStep ? 'text-brand-green' : 'text-gray-900'}`}>
                          {step.area_name}
                          {queueHeadLocked && <span className="ml-2 text-[10px] uppercase font-bold text-gray-400 border border-gray-300 rounded px-1.5 py-0.5 bg-gray-100">Fijo (Próximo)</span>}
                        </p>
                        {step.rule_applied && (
                          <p className="text-[11px] text-gray-500 font-medium truncate mt-0.5">
                            Regla: {step.rule_applied}
                          </p>
                        )}
                      </div>
                      <span className="text-xs font-medium text-gray-400 shrink-0">
                        ~{step.estimated_wait_minutes}m
                      </span>
                    </div>
                  );})}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
