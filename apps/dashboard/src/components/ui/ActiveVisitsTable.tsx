import { Clock, CheckCircle2, Loader2 } from "lucide-react";
import { useState } from "react";

export interface ActiveVisit {
  visit_id: string;
  patient_name: string;
  current_area: string;
  step_order: number;
  total_steps: number;
  status: string;
  waiting_since_minutes: number;
}

interface ActiveVisitsTableProps {
  visits: ActiveVisit[];
}

const URGENCY_THRESHOLD_MINUTES = 15;

function WaitBadge({ minutes }: { minutes: number }) {
  if (minutes >= URGENCY_THRESHOLD_MINUTES) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-red-100 text-red-700 border border-red-300">
        <Clock className="w-3 h-3" />
        {minutes} min
      </span>
    );
  }
  if (minutes >= 8) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold bg-yellow-100 text-yellow-700 border border-yellow-300">
        <Clock className="w-3 h-3" />
        {minutes} min
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium text-content-secondary">
      <Clock className="w-3 h-3" />
      {minutes} min
    </span>
  );
}

function StepProgress({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className="flex gap-1">
        {Array.from({ length: total }).map((_, i) => (
          <span
            key={i}
            className={`block h-1.5 w-5 rounded-full ${
              i < current ? "bg-brand-green" : "bg-surface-border"
            }`}
          />
        ))}
      </div>
      <span className="text-xs text-content-secondary tabular-nums">
        {current}/{total}
      </span>
    </div>
  );
}

export function ActiveVisitsTable({ visits }: ActiveVisitsTableProps) {
  const [hiddenVisits, setHiddenVisits] = useState<Set<string>>(new Set());

  const nextStep = async (visit_id: string) => {
    // Hide immediately in UI
    setHiddenVisits(prev => new Set(prev).add(visit_id));
    
    try {
      const res = await fetch(
        `http://localhost:8000/api/v1/visits/${visit_id}/advance-step`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        },
      );
    } catch (error: unknown) {
      if (error instanceof Error) {
        return console.error(error.message);
      }
      console.log(error);
    }
  };

  const displayVisits = visits.filter((v) => !hiddenVisits.has(v.visit_id));

  if (displayVisits.length === 0) {
    return (
      <div className="bg-surface-card border border-surface-border rounded-lg p-8 flex flex-col items-center gap-2 text-center">
        <CheckCircle2 className="w-10 h-10 text-brand-green" />
        <p className="font-medium text-content-primary">Sin visitas activas</p>
        <p className="text-sm text-content-secondary">
          No hay pacientes en flujo ahora mismo
        </p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden bg-surface-card shadow-sm ring-1 ring-surface-border rounded-lg">
      <div className="px-6 py-4 border-b border-surface-border flex items-center justify-between">
        <h2 className="font-semibold text-content-primary">
          Pacientes en flujo
        </h2>
        <span className="text-sm text-content-secondary">
          {displayVisits.length} activo{displayVisits.length !== 1 ? "s" : ""}
        </span>
      </div>

      <table className="min-w-full divide-y divide-surface-border">
        <thead className="bg-surface-base">
          <tr>
            {[
              "Paciente",
              "Área actual",
              "Progreso",
              "En espera",
              "Estado",
              "Acciones",
            ].map((h) => (
              <th
                key={h}
                className="px-6 py-3 text-left text-xs font-medium text-content-secondary uppercase tracking-wider">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-border">
          {displayVisits.map((v) => (
            <tr
              key={v.visit_id}
              className={
                v.waiting_since_minutes >= URGENCY_THRESHOLD_MINUTES
                  ? "bg-red-50"
                  : "bg-surface-card"
              }>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="text-sm font-semibold text-content-primary">
                  {v.patient_name}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-content-secondary">
                {v.current_area}
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <StepProgress current={v.step_order} total={v.total_steps} />
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <WaitBadge minutes={v.waiting_since_minutes} />
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="inline-flex items-center gap-1.5 text-xs font-medium text-content-secondary">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  En progreso
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-content-secondary">
                <button
                  onClick={() => nextStep(v.visit_id)}
                  className="bg-brand-green text-white px-2 py-1 rounded-md hover:bg-brand-green/80 cursor-pointer">
                  Avanzar paso
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
