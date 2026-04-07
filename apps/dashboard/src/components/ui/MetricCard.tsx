import { ArrowUpRight, ArrowDownRight } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: number | string;
  unit?: string;
  accentColor: string;
  trend?: number;
}

export function MetricCard({ label, value, unit, accentColor, trend }: MetricCardProps) {
  return (
    <div
      className="bg-[var(--color-surface-card)] border border-[var(--color-surface-border)] rounded-lg p-6 relative overflow-hidden"
      style={{ borderTop: `4px solid ${accentColor}` }}
    >
      <p className="text-sm text-[var(--color-content-secondary)] mb-2 font-medium">{label}</p>
      
      <div className="flex items-baseline mb-2">
        <span className="text-5xl font-bold" style={{ color: accentColor }}>
          {value}
        </span>
        {unit && (
          <span className="text-sm text-[var(--color-content-secondary)] ml-1 font-medium">
            {unit}
          </span>
        )}
      </div>

      {trend !== undefined && (
        <div className="absolute bottom-6 right-6 flex items-center text-sm font-medium">
          {trend > 0 ? (
            <span className="text-green-600 flex items-center bg-green-50 px-2 py-0.5 rounded-full">
              <ArrowUpRight className="w-4 h-4 mr-1" />
              {trend}%
            </span>
          ) : trend < 0 ? (
            <span className="text-red-600 flex items-center bg-red-50 px-2 py-0.5 rounded-full">
              <ArrowDownRight className="w-4 h-4 mr-1" />
              {Math.abs(trend)}%
            </span>
          ) : (
            <span className="text-gray-500 bg-gray-50 px-2 py-0.5 rounded-full">
              0%
            </span>
          )}
        </div>
      )}
    </div>
  );
}
