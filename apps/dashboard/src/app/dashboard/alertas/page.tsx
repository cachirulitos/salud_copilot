"use client";

import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { useDashboardContext } from "@/lib/context/dashboard-context";
import { AlertCircle, AlertTriangle, Info, CheckCircle2 } from "lucide-react";
import { Alert } from "@/components/ui/AlertsPanel";
import { useState } from "react";

type Severity = "all" | "critical" | "warning" | "info";

const SEVERITY_CONFIG = {
  critical: {
    label: "Crítica",
    border: "border-red-500",
    bg: "bg-red-50",
    icon: <AlertCircle className="w-5 h-5 text-red-600" />,
    badge: "bg-red-100 text-red-700 border-red-300",
  },
  warning: {
    label: "Alerta",
    border: "border-yellow-500",
    bg: "bg-yellow-50",
    icon: <AlertTriangle className="w-5 h-5 text-yellow-600" />,
    badge: "bg-yellow-100 text-yellow-700 border-yellow-300",
  },
  info: {
    label: "Info",
    border: "border-blue-400",
    bg: "bg-blue-50",
    icon: <Info className="w-5 h-5 text-blue-600" />,
    badge: "bg-blue-100 text-blue-700 border-blue-300",
  },
};

function getRelativeTime(iso: string) {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes === 0) return "hace un momento";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `hace ${hours}h ${minutes % 60}min`;
}

export default function AlertasPage() {
  const { setIsConnected, setAlertCount } = useDashboardContext();
  const { alerts, clearResolvedAlerts } = useDashboardData(
    process.env.NEXT_PUBLIC_CLINIC_ID ?? "default",
    setIsConnected,
    setAlertCount,
  );

  const [filter, setFilter] = useState<Severity>("all");

  const filtered =
    filter === "all" ? alerts : alerts.filter((a) => a.severity === filter);

  const counts = {
    all: alerts.length,
    critical: alerts.filter((a) => a.severity === "critical").length,
    warning: alerts.filter((a) => a.severity === "warning").length,
    info: alerts.filter((a) => a.severity === "info").length,
  };

  const FILTERS: { key: Severity; label: string }[] = [
    { key: "all", label: `Todas (${counts.all})` },
    { key: "critical", label: `Críticas (${counts.critical})` },
    { key: "warning", label: `Alertas (${counts.warning})` },
    { key: "info", label: `Info (${counts.info})` },
  ];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-content-primary">
            Alertas
          </h1>
          <p className="text-sm text-content-secondary mt-0.5">
            Notificaciones y eventos del sistema en tiempo real
          </p>
        </div>
        {alerts.length > 0 && (
          <button
            onClick={clearResolvedAlerts}
            className="text-sm text-content-secondary hover:text-content-primary border border-surface-border rounded-lg px-4 py-2 transition-colors">
            Limpiar no críticas
          </button>
        )}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {FILTERS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors border ${
              filter === key
                ? "bg-brand-green text-white border-brand-green"
                : "text-content-secondary border-surface-border hover:text-content-primary bg-surface-card"
            }`}>
            {label}
          </button>
        ))}
      </div>

      {/* Alert list */}
      {filtered.length === 0 ? (
        <div className="bg-surface-card border border-surface-border rounded-lg p-16 flex flex-col items-center gap-3">
          <CheckCircle2 className="w-12 h-12 text-brand-green" />
          <p className="font-medium text-content-primary">
            Sin alertas activas
          </p>
          <p className="text-sm text-content-secondary">
            Todo funciona correctamente
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {(filtered as Alert[]).map((alert) => {
            const cfg = SEVERITY_CONFIG[alert.severity];
            return (
              <div
                key={alert.id}
                className={`bg-surface-card border border-surface-border border-l-4 ${cfg.border} rounded-lg p-4 flex items-start gap-4`}>
                <div className="mt-0.5 shrink-0">{cfg.icon}</div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-semibold text-sm text-content-primary">
                      {alert.area_name}
                    </span>
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${cfg.badge}`}>
                      {cfg.label}
                    </span>
                  </div>
                  <p className="text-sm text-content-secondary">
                    {alert.message}
                  </p>
                </div>
                <span className="text-xs text-content-secondary shrink-0 mt-0.5">
                  {getRelativeTime(alert.triggered_at)}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
