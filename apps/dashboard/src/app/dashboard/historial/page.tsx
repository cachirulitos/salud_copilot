"use client";

import { useDashboardData } from "@/lib/hooks/useDashboardData";
import { useDashboardContext } from "@/lib/context/dashboard-context";
import WaitTimeChart from "@/components/ui/WaitTimeChart";
import { MetricCard } from "@/components/ui/MetricCard";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";

function trendForSeries(data: number[]): {
  delta: number;
  Icon: React.FC<{ className?: string }>;
} {
  if (data.length < 2) return { delta: 0, Icon: Minus };
  const first = data[0];
  const last = data[data.length - 1];
  if (first === 0) return { delta: 0, Icon: Minus };
  const delta = Math.round(((last - first) / first) * 100);
  return {
    delta,
    Icon: delta > 0 ? TrendingUp : delta < 0 ? TrendingDown : Minus,
  };
}

export default function HistorialPage() {
  const { setIsConnected, setAlertCount } = useDashboardContext();
  const { areas, waitTimeHistory } = useDashboardData(
    process.env.NEXT_PUBLIC_CLINIC_ID ?? "default",
    setIsConnected,
    setAlertCount,
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-content-primary">
          Historial de tiempos
        </h1>
        <p className="text-sm text-content-secondary mt-0.5">
          Evolución de tiempos de espera — últimos 60 minutos
        </p>
      </div>

      {/* Trend cards per area */}
      <div className="grid grid-cols-4 gap-4">
        {Object.entries(waitTimeHistory.series || {}).map(
          ([areaName, rawData]: [string, any]) => {
            const data = rawData as number[];
            const { delta, Icon } = trendForSeries(data);
            const current = data[data.length - 1] ?? 0;
            const isUp = delta > 0;
            return (
              <div
                key={areaName}
                className="bg-surface-card border border-surface-border rounded-lg p-5">
                <p className="text-sm text-content-secondary font-medium mb-2 truncate">
                  {areaName}
                </p>
                <div className="flex items-baseline gap-2">
                  <span className="text-4xl font-bold text-content-primary">
                    {current}
                  </span>
                  <span className="text-sm text-content-secondary">min</span>
                </div>
                <div
                  className={`flex items-center gap-1 mt-2 text-xs font-medium ${
                    delta === 0
                      ? "text-content-secondary"
                      : isUp
                        ? "text-red-600"
                        : "text-green-600"
                  }`}>
                  <Icon className="w-3.5 h-3.5" />
                  {delta === 0
                    ? "Sin cambio"
                    : `${isUp ? "+" : ""}${delta}% vs hace 60 min`}
                </div>
              </div>
            );
          },
        )}
      </div>

      {/* Main chart */}
      <div className="bg-surface-card border border-surface-border rounded-lg p-6 shadow-sm">
        <h2 className="text-content-secondary text-sm font-medium mb-6">
          Tiempos de espera por área — Últimos 60 min
        </h2>
        <WaitTimeChart history={waitTimeHistory} />
      </div>

      {/* Summary table */}
      <div className="bg-surface-card border border-surface-border rounded-lg overflow-hidden shadow-sm">
        <div className="px-6 py-4 border-b border-surface-border">
          <h2 className="font-semibold text-content-primary">
            Resumen del período
          </h2>
        </div>
        <table className="min-w-full divide-y divide-surface-border">
          <thead className="bg-surface-base">
            <tr>
              {[
                "Área",
                "Mínimo",
                "Máximo",
                "Promedio",
                "Actual",
                "Tendencia",
              ].map((h) => (
                <th
                  key={h}
                  className="px-6 py-3 text-left text-xs font-medium text-content-secondary uppercase tracking-wider">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border bg-surface-card">
            {Object.entries(waitTimeHistory.series || {}).map(
              ([areaName, rawData]: [string, any]) => {
                const data = rawData as number[];
                const min = Math.min(...data);
                const max = Math.max(...data);
                const avg = Math.round(
                  data.reduce((s, v) => s + v, 0) / data.length,
                );
                const current = data[data.length - 1] ?? 0;
                const { delta, Icon } = trendForSeries(data);
                const isUp = delta > 0;
                return (
                  <tr key={areaName}>
                    <td className="px-6 py-4 text-sm font-medium text-content-primary">
                      {areaName}
                    </td>
                    <td className="px-6 py-4 text-sm text-content-secondary">
                      {min} min
                    </td>
                    <td className="px-6 py-4 text-sm text-content-secondary">
                      {max} min
                    </td>
                    <td className="px-6 py-4 text-sm text-content-secondary">
                      {avg} min
                    </td>
                    <td className="px-6 py-4 text-sm font-semibold text-content-primary">
                      {current} min
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`inline-flex items-center gap-1 text-xs font-medium ${
                          delta === 0
                            ? "text-content-secondary"
                            : isUp
                              ? "text-red-600"
                              : "text-green-600"
                        }`}>
                        <Icon className="w-3.5 h-3.5" />
                        {delta === 0
                          ? "Estable"
                          : `${isUp ? "+" : ""}${delta}%`}
                      </span>
                    </td>
                  </tr>
                );
              },
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
