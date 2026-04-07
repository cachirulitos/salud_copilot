"use client";

import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { useDashboardContext } from "@/lib/context/dashboard-context";
import { MetricCard } from "@/components/ui/MetricCard";
import { AreaTable } from "@/components/ui/AreaTable";
import WaitTimeChart from "@/components/ui/WaitTimeChart";
import AlertsPanel from "@/components/ui/AlertsPanel";
import { ActiveVisitsTable } from "@/components/ui/ActiveVisitsTable";
import { Alert } from "@/components/ui/AlertsPanel";

export default function DashboardPage() {
  const { setIsConnected, setAlertCount } = useDashboardContext();

  const {
    areas,
    activeVisits,
    summary,
    alerts,
    waitTimeHistory,
    clearResolvedAlerts,
  } = useDashboardData(
    process.env.NEXT_PUBLIC_CLINIC_ID ?? "default",
    setIsConnected,
    setAlertCount,
  );

  return (
    <div className="space-y-6">
      {/* ── KPI row ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-4 gap-4">
        <MetricCard
          label="Personas en clínica"
          value={summary.total_active_visits}
          accentColor="#008A4B"
        />
        <MetricCard
          label="En cola total"
          value={summary.total_waiting_patients}
          accentColor="#005B9F"
        />
        <MetricCard
          label="Espera promedio"
          value={summary.average_wait_minutes}
          unit="min"
          accentColor="#37415180"
        />
        <MetricCard
          label="Áreas en riesgo"
          value={summary.areas_at_risk}
          accentColor={summary.areas_at_risk > 0 ? "#E53E3E" : "#008A4B"}
        />
      </div>

      {/* ── Chart + Alerts row ───────────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-4">
        <div className="col-span-2 bg-surface-card rounded-lg p-4 border border-surface-border shadow-sm">
          <h2 className="text-content-secondary text-sm mb-4 font-medium">
            Tiempos de espera — Últimos 60 min
          </h2>
          <WaitTimeChart history={waitTimeHistory} />
        </div>
        <AlertsPanel
          alerts={alerts as Alert[]}
          onClearResolved={clearResolvedAlerts}
        />
      </div>

      {/* ── Areas status table ───────────────────────────────────────── */}
      <AreaTable areas={areas} />

      {/* ── Active patient flow table ────────────────────────────────── */}
      <ActiveVisitsTable visits={activeVisits} />
    </div>
  );
}
