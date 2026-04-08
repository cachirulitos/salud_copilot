"use client";

import { useState, useEffect } from "react";
import { useParams, useSearchParams } from "next/navigation";
import {
  Activity,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Phone,
  ClipboardList,
  Clock,
  ChevronUp,
  ChevronDown,
  Plus,
  Trash2,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Area {
  id: string;
  name: string;
  study_type: string;
}

interface SequenceStep {
  order: number;
  area_name: string;
  estimated_wait_minutes: number;
  rule_applied: string | null;
}

interface CheckinResult {
  visit_id: string;
  sequence: SequenceStep[];
  total_estimated_minutes: number;
}

export default function CheckinPage() {
  const { clinic_id } = useParams<{ clinic_id: string }>();
  const searchParams = useSearchParams();
  const preselectedArea = searchParams.get("area") ?? "";

  const [areas, setAreas] = useState<Area[]>([]);
  const [areasLoading, setAreasLoading] = useState(true);

  const [phone, setPhone] = useState("");
  const [selectedAreas, setSelectedAreas] = useState<Area[]>([]);
  const [dropdownValue, setDropdownValue] = useState("");
  const [hasAppointment, setHasAppointment] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<CheckinResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/api/v1/areas/?clinic_id=${clinic_id}`)
      .then((r) => r.json())
      .then((data: Area[]) => {
        setAreas(data);
        if (!preselectedArea && data.length > 0) {
          setDropdownValue(data[0].id);
        } else if (preselectedArea) {
          setDropdownValue(preselectedArea);
          const area = data.find((a) => a.id === preselectedArea);
          if (area) setSelectedAreas([area]);
        }
      })
      .catch(() => {})
      .finally(() => setAreasLoading(false));
  }, [clinic_id, preselectedArea]);

  function handleAddArea() {
    if (!dropdownValue) return;
    const area = areas.find((a) => a.id === dropdownValue);
    if (!area) return;
    if (selectedAreas.some((a) => a.id === area.id)) return;
    setSelectedAreas([...selectedAreas, area]);
  }

  function handleRemoveArea(id: string) {
    setSelectedAreas(selectedAreas.filter((a) => a.id !== id));
  }

  function handleMoveArea(index: number, direction: "up" | "down") {
    if (direction === "up" && index > 0) {
      const newArr = [...selectedAreas];
      [newArr[index - 1], newArr[index]] = [newArr[index], newArr[index - 1]];
      setSelectedAreas(newArr);
    } else if (direction === "down" && index < selectedAreas.length - 1) {
      const newArr = [...selectedAreas];
      [newArr[index], newArr[index + 1]] = [newArr[index + 1], newArr[index]];
      setSelectedAreas(newArr);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!phone.trim() || selectedAreas.length === 0) return;

    setSubmitting(true);
    setError(null);

    const normalizedPhone = phone.startsWith("+")
      ? phone.replace(/\s/g, "")
      : `+52${phone.replace(/\D/g, "")}`;

    try {
      const areaIds = selectedAreas.map((a) => a.id);
      const res = await fetch(`${API}/api/v1/visits/check-in`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          phone_number: normalizedPhone,
          clinic_id,
          study_ids: areaIds,
          proposed_sequence: areaIds,
          has_appointment: hasAppointment,
          is_urgent: false,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        if (body?.rules_violations && Array.isArray(body.rules_violations)) {
          throw new Error(body.rules_violations.join(" "));
        }
        throw new Error(body?.detail ?? body?.error ?? `Error ${res.status}`);
      }

      setResult(await res.json());
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Error inesperado. Intenta de nuevo.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  /* ── Confirmation screen ─────────────────────────────────────────── */
  if (result) {
    return (
      <div className="min-h-screen bg-surface-base flex items-start justify-center px-4 pt-10 pb-16">
        <div className="w-full max-w-sm space-y-5">
          {/* Header */}
          <div className="text-center space-y-1">
            <div className="flex justify-center mb-3">
              <CheckCircle2 className="w-14 h-14 text-brand-green" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900">
              ¡Registro exitoso!
            </h1>
            <p className="text-sm text-gray-500">
              Sigue el orden indicado. Recibirás actualizaciones por WhatsApp.
            </p>
          </div>

          {/* Steps */}
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
            <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
              <span className="font-semibold text-gray-900 text-sm">
                Tu secuencia de atención
              </span>
              <span className="text-xs text-gray-500 flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />~
                {result.total_estimated_minutes} min total
              </span>
            </div>
            <ul className="divide-y divide-gray-100">
              {result.sequence.map((step) => (
                <li
                  key={step.order}
                  className="px-5 py-4 flex items-center gap-4">
                  <span className="w-7 h-7 rounded-full bg-brand-green/10 text-brand-green text-xs font-bold flex items-center justify-center shrink-0">
                    {step.order}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900">
                      {step.area_name}
                    </p>
                    {step.rule_applied && (
                      <p className="text-xs text-gray-400 truncate">
                        {step.rule_applied}
                      </p>
                    )}
                  </div>
                  <span className="text-sm font-medium text-gray-500 shrink-0">
                    ~{step.estimated_wait_minutes} min
                  </span>
                </li>
              ))}
            </ul>
          </div>

          <p className="text-center text-xs text-gray-400">
            Folio de visita:{" "}
            <span className="font-mono text-gray-500">{result.visit_id}</span>
          </p>
        </div>
      </div>
    );
  }

  /* ── Check-in form ───────────────────────────────────────────────── */
  return (
    <div className="min-h-screen bg-surface-base flex items-start justify-center px-4 pt-10 pb-16">
      <div className="w-full max-w-sm space-y-6">
        {/* Brand */}
        <div className="text-center space-y-1">
          <div className="flex justify-center mb-3">
            <Activity className="w-9 h-9 text-brand-green" strokeWidth={2.5} />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">
            Registro de visita
          </h1>
          <p className="text-sm text-gray-500">
            Registra tu llegada para conocer tu turno estimado
          </p>
        </div>

        {/* Form */}
        <form
          onSubmit={handleSubmit}
          className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6 space-y-5">
          {/* Phone */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1.5">
              <span className="flex items-center gap-1.5 mb-1">
                <Phone className="w-3.5 h-3.5" />
                Número de teléfono
              </span>
            </label>
            <input
              type="tel"
              required
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="Ej. 5512345678"
              className="w-full border border-gray-200 rounded-xl px-4 py-3 text-base text-gray-900 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-green/30 focus:border-brand-green"
            />
            <p className="text-xs text-gray-400 mt-1">
              Recibirás tu turno y actualizaciones aquí
            </p>
          </div>

          {/* Study / area */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-1.5">
              <span className="flex items-center gap-1.5 mb-1">
                <ClipboardList className="w-3.5 h-3.5" />
                Estudios y Prioridad
              </span>
            </label>

            {areasLoading ? (
              <div className="flex items-center gap-2 text-gray-400 text-sm py-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Cargando servicios...
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex gap-2">
                  <select
                    value={dropdownValue}
                    onChange={(e) => setDropdownValue(e.target.value)}
                    className="flex-1 border border-gray-200 rounded-xl px-4 py-3 text-base text-gray-900 bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-green/30 focus:border-brand-green">
                    <option value="" disabled>
                      Añadir estudio a la visita...
                    </option>
                    {areas
                      .filter(
                        (area) => !selectedAreas.some((s) => s.id === area.id),
                      )
                      .map((area) => (
                        <option key={area.id} value={area.id}>
                          {area.name}
                        </option>
                      ))}
                  </select>
                  <button
                    type="button"
                    onClick={handleAddArea}
                    className="px-4 py-3 bg-gray-100 text-gray-700 font-semibold rounded-xl hover:bg-gray-200 transition-colors flex items-center justify-center">
                    <Plus className="w-5 h-5" />
                  </button>
                </div>

                {/* Priority List */}
                {selectedAreas.length > 0 && (
                  <div className="bg-gray-50 border border-gray-200 rounded-xl divide-y divide-gray-200 overflow-hidden">
                    {selectedAreas.map((area, index) => (
                      <div
                        key={area.id}
                        className="flex items-center px-3 py-2">
                        <div className="flex-1 min-w-0 pr-3">
                          <p className="text-sm font-medium text-gray-900 truncate">
                            <span className="text-gray-400 inline-block w-4 mr-2">
                              {index + 1}.
                            </span>
                            {area.name}
                          </p>
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          <button
                            type="button"
                            disabled={index === 0}
                            onClick={() => handleMoveArea(index, "up")}
                            className="p-1.5 text-gray-400 hover:text-gray-900 hover:bg-gray-200 rounded-lg disabled:opacity-30 disabled:hover:bg-transparent">
                            <ChevronUp className="w-4 h-4" />
                          </button>
                          <button
                            type="button"
                            disabled={index === selectedAreas.length - 1}
                            onClick={() => handleMoveArea(index, "down")}
                            className="p-1.5 text-gray-400 hover:text-gray-900 hover:bg-gray-200 rounded-lg disabled:opacity-30 disabled:hover:bg-transparent">
                            <ChevronDown className="w-4 h-4" />
                          </button>
                          <button
                            type="button"
                            onClick={() => handleRemoveArea(area.id)}
                            className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded-lg ml-1">
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Appointment */}
          <label className="flex items-center gap-3 cursor-pointer select-none">
            <div className="relative">
              <input
                type="checkbox"
                checked={hasAppointment}
                onChange={(e) => setHasAppointment(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-10 h-6 bg-gray-200 peer-checked:bg-brand-green rounded-full transition-colors" />
              <div className="absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform peer-checked:translate-x-4" />
            </div>
            <span className="text-sm font-medium text-gray-700">
              Tengo cita
            </span>
          </label>

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 bg-red-50 border border-red-200 rounded-xl p-3 text-red-700 text-sm">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={submitting || areasLoading || selectedAreas.length === 0}
            className="w-full bg-brand-green text-white font-semibold py-3.5 rounded-xl text-base hover:bg-brand-green/80 transition-colors disabled:opacity-50 flex items-center justify-center gap-2">
            {submitting ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Registrando...
              </>
            ) : (
              "Registrar mi llegada"
            )}
          </button>
        </form>

        <p className="text-center text-xs text-gray-400">
          SaludCopilot · Salud Digna
        </p>
      </div>
    </div>
  );
}
