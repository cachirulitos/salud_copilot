"use client";

import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { useDashboardContext } from "@/lib/context/dashboard-context";
import { MetricCard } from "@/components/ui/MetricCard";
import { AreaTable } from "@/components/ui/AreaTable";
import { Camera, Users, AlertTriangle, Clock } from "lucide-react";

export default function AreasPage() {
  const { setIsConnected, setAlertCount } = useDashboardContext();
  const { areas, summary } = useDashboardData(
    process.env.NEXT_PUBLIC_CLINIC_ID ?? "default",
    setIsConnected,
    setAlertCount,
  );

  console.log(areas);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-[var(--color-content-primary)]">
          Estado de Áreas
        </h1>
        <p className="text-sm text-[var(--color-content-secondary)] mt-0.5">
          Monitoreo en tiempo real de todas las áreas clínicas
        </p>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard
          label="Áreas activas"
          value={areas.length}
          accentColor="#008A4B"
        />
        <MetricCard
          label="Personas detectadas (CV)"
          value={areas.reduce((s, a) => s + a.people_in_area, 0)}
          accentColor="#005B9F"
        />
        <MetricCard
          label="En cola total"
          value={summary.total_waiting_patients}
          accentColor="#37415180"
        />
        <MetricCard
          label="Áreas en riesgo"
          value={summary.areas_at_risk}
          accentColor={summary.areas_at_risk > 0 ? "#E53E3E" : "#008A4B"}
        />
      </div>

      {/* Area cards grid */}
      <div className="grid grid-cols-2 gap-4">
        {areas.map((area) => {
          const statusColor =
            area.status === "saturated"
              ? {
                  bg: "bg-red-50",
                  border: "border-red-200",
                  text: "text-red-700",
                  dot: "bg-red-500",
                }
              : area.status === "warning"
                ? {
                    bg: "bg-yellow-50",
                    border: "border-yellow-200",
                    text: "text-yellow-700",
                    dot: "bg-yellow-500",
                  }
                : {
                    bg: "bg-green-50",
                    border: "border-green-200",
                    text: "text-green-700",
                    dot: "bg-green-500",
                  };

          const statusLabel =
            area.status === "saturated"
              ? "Saturado"
              : area.status === "warning"
                ? "Alerta"
                : "Normal";

          return (
            <div
              key={area.area_id}
              className="bg-[var(--color-surface-card)] border border-[var(--color-surface-border)] rounded-lg p-5 space-y-4">
              {/* Header */}
              <div className="flex items-start justify-between">
                <h3 className="font-semibold text-[var(--color-content-primary)] text-base">
                  {area.area_name}
                </h3>
                <span
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold border ${statusColor.bg} ${statusColor.border} ${statusColor.text}`}>
                  <span
                    className={`w-1.5 h-1.5 rounded-full ${statusColor.dot}`}
                  />
                  {statusLabel}
                </span>
              </div>

              {/* Stats row */}
              <div className="grid grid-cols-3 gap-3">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-1 text-xs text-[var(--color-content-secondary)]">
                    <Camera className="w-3.5 h-3.5" />
                    Personas físicas
                  </div>
                  <span className="text-2xl font-bold text-[var(--color-content-primary)]">
                    {area.people_in_area}
                  </span>
                </div>
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-1 text-xs text-[var(--color-content-secondary)]">
                    <Users className="w-3.5 h-3.5" />
                    En cola
                  </div>
                  <span className="text-2xl font-bold text-[var(--color-content-primary)]">
                    {area.current_queue_length}
                  </span>
                </div>
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-1 text-xs text-[var(--color-content-secondary)]">
                    <Clock className="w-3.5 h-3.5" />
                    Espera est.
                  </div>
                  <span className="text-2xl font-bold text-[var(--color-content-primary)]">
                    {area.estimated_wait_minutes}
                    <span className="text-sm font-normal text-[var(--color-content-secondary)] ml-1">
                      min
                    </span>
                  </span>
                </div>
              </div>

              {/* Occupancy bar */}
              <div>
                <div className="flex justify-between text-xs text-[var(--color-content-secondary)] mb-1">
                  <span>Ocupación de cola</span>
                  <span>
                    {Math.min(
                      Math.round((area.current_queue_length / 10) * 100),
                      100,
                    )}
                    %
                  </span>
                </div>
                <div className="h-1.5 bg-[var(--color-surface-border)] rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      area.status === "saturated"
                        ? "bg-red-500"
                        : area.status === "warning"
                          ? "bg-yellow-500"
                          : "bg-[var(--color-brand-green)]"
                    }`}
                    style={{
                      width: `${Math.min(Math.round((area.current_queue_length / 10) * 100), 100)}%`,
                    }}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Full table below */}
      <AreaTable areas={areas} />
    </div>
  );
}
