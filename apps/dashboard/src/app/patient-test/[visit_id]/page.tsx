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
    const pendingSteps = [context.current_step, ...context.remaining_steps].filter(Boolean);
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
      const proposed_sequence = newArr.map((s) => s.area_id).filter(Boolean) as string[];
      const res = await fetch(`${API}/api/v1/visits/${visit_id}/reorder-sequence`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ proposed_sequence }),
      });

      const body = await res.json().catch(() => ({}));

      if (!res.ok) {
        if (body?.rules_violations && Array.isArray(body.rules_violations)) {
          throw new Error(body.rules_violations.join("  |  "));
        }
        throw new Error(body?.detail || body?.error || body?.code || `Error ${res.status}`);
      }

      if (body.accepted === false && body.rules_violations?.length > 0) {
        throw new Error(body.rules_violations.join("  |  "));
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

  const isFinished = !context.current_step && context.remaining_steps.length === 0;

  const pendingSteps = context ? [context.current_step, ...context.remaining_steps].filter(Boolean) : [];

  return (
    <div className="min-h-screen bg-surface-base px-4 py-10">
      <div className="max-w-xl mx-auto space-y-6">
        
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="flex justify-center mb-2">
            <Activity className="w-10 h-10 text-brand-green" strokeWidth={2.5} />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Patient Flow Tester</h1>
          <p className="text-sm text-gray-500">{context.patient_name} — {visit_id}</p>
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
                <h2 className="text-xl font-bold text-gray-900">Visita Completada</h2>
                <p className="text-gray-500 text-sm">El paciente ha finalizado todos sus estudios.</p>
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
                  <Clock className="w-3 h-3" />~{context.total_estimated_minutes} min
                </span>
            </div>
            
            <div className="p-5 flex flex-col gap-4">
              <button
                onClick={handleAdvanceStep}
                disabled={advancing}
                className="w-full bg-gray-900 text-white font-semibold py-3.5 rounded-xl text-sm hover:bg-gray-800 transition-colors disabled:opacity-50 flex items-center justify-center gap-2 shadow-sm">
                {advancing ? <Loader2 className="w-5 h-5 animate-spin" /> : `Finalizar el Paso #1 (${pendingSteps[0].area_name})`}
              </button>

              <div className={`mt-2 rounded-xl border border-gray-100 divide-y divide-gray-100 bg-gray-50/50 ${reordering ? 'opacity-50 pointer-events-none' : ''}`}>
                {pendingSteps.map((step, index) => (
                  <div key={`${step.area_name}-${index}`} className="px-4 py-3 flex items-center gap-4">
                    
                    {/* Priority Up/Down */}
                    <div className="flex flex-col gap-0.5 shrink-0">
                      <button
                        type="button"
                        disabled={index === 0}
                        onClick={() => handleMoveArea(index, "up")}
                        className="p-1 text-gray-400 hover:text-gray-900 hover:bg-gray-200 rounded disabled:opacity-30 disabled:hover:bg-transparent">
                        <ChevronUp className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        disabled={index === pendingSteps.length - 1}
                        onClick={() => handleMoveArea(index, "down")}
                        className="p-1 text-gray-400 hover:text-gray-900 hover:bg-gray-200 rounded disabled:opacity-30 disabled:hover:bg-transparent">
                        <ChevronDown className="w-4 h-4" />
                      </button>
                    </div>

                    <span className={`w-8 h-8 rounded-full text-xs font-bold flex items-center justify-center shrink-0 ${index === 0 ? 'bg-brand-green text-white shadow-sm' : 'bg-white border border-gray-200 text-gray-500'}`}>
                      {step.order}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className={`font-semibold text-sm ${index === 0 ? 'text-brand-green' : 'text-gray-900'}`}>{step.area_name}</p>
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
                ))}
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
