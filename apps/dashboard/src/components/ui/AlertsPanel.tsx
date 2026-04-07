import { CheckCircle2, AlertCircle, AlertTriangle, Info } from 'lucide-react';

export interface Alert {
  id: string;
  severity: "critical" | "warning" | "info";
  area_name: string;
  message: string;
  triggered_at: string;
}

interface AlertsPanelProps {
  alerts: Alert[];
  onClearResolved?: () => void;
}

export default function AlertsPanel({ alerts, onClearResolved }: AlertsPanelProps) {
  // Relative time formatter (simple mock version for now, updates conceptually every minute)
  const getRelativeTime = (isoString: string) => {
    const diff = Date.now() - new Date(isoString).getTime();
    const minutes = Math.floor(diff / 60000);
    if (minutes === 0) return "hace un momento";
    return `hace ${minutes} minuto${minutes !== 1 ? 's' : ''}`;
  };

  const severityConfig = {
    critical: { border: "border-red-600", icon: <AlertCircle className="w-5 h-5 text-red-600" /> },
    warning: { border: "border-yellow-500", icon: <AlertTriangle className="w-5 h-5 text-yellow-500" /> },
    info: { border: "border-blue-500", icon: <Info className="w-5 h-5 text-blue-500" /> },
  };

  return (
    <div className="bg-[var(--color-surface-card)] border border-[var(--color-surface-border)] rounded-lg flex flex-col h-full">
      <div className="p-4 border-b border-[var(--color-surface-border)] flex justify-between items-center">
        <h2 className="text-[var(--color-content-primary)] font-semibold">Alertas Activas</h2>
        {alerts.length > 0 && (
          <button 
            onClick={onClearResolved}
            className="text-xs text-[var(--color-content-secondary)] hover:text-[var(--color-content-primary)] transition-colors"
          >
            Limpiar resueltas
          </button>
        )}
      </div>

      <div className="p-4 flex-1 overflow-y-auto space-y-3">
        {alerts.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center py-8">
            <CheckCircle2 className="w-12 h-12 text-[var(--color-brand-green)] mb-3" />
            <p className="text-[var(--color-brand-green)] font-medium">Sin alertas activas</p>
            <p className="text-sm text-[var(--color-content-secondary)] mt-1">Todo funciona correctamente</p>
          </div>
        ) : (
          alerts.map((alert) => {
            const config = severityConfig[alert.severity];
            return (
              <div 
                key={alert.id} 
                className={`bg-[#FAFAFA] border border-[var(--color-surface-border)] border-l-4 ${config.border} rounded-md p-3 shadow-sm`}
              >
                <div className="flex justify-between items-start mb-1">
                  <div className="flex items-center space-x-2">
                    {config.icon}
                    <span className="font-semibold text-sm text-[var(--color-content-primary)]">{alert.area_name}</span>
                  </div>
                  <span className="text-xs text-[var(--color-content-secondary)]">{getRelativeTime(alert.triggered_at)}</span>
                </div>
                <p className="text-sm text-[var(--color-content-secondary)] mt-2 pl-7">
                  {alert.message}
                </p>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
