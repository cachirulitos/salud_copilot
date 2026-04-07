import { Camera } from "lucide-react";

export interface AreaData {
  area_id: string;
  area_name: string;
  current_queue_length: number;
  estimated_wait_minutes: number;
  people_in_area: number;
  status: "normal" | "warning" | "saturated" | string;
}

interface AreaTableProps {
  areas: AreaData[];
}

export function AreaTable({ areas }: AreaTableProps) {
  const getStatusBadge = (status: string) => {
    switch (status) {
      case "normal":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-400/60 text-green-600 border border-green-600">
            Normal
          </span>
        );
      case "warning":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-400/60 text-yellow-600 border border-yellow-600">
            Alerta
          </span>
        );
      case "saturated":
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-400/60 text-red-600 border border-red-600">
            Saturado
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-800 text-gray-300">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="overflow-hidden bg-[var(--color-surface-card)] shadow-sm ring-1 ring-[var(--color-surface-border)] rounded-lg">
      <table className="min-w-full divide-y divide-[var(--color-surface-border)]">
        <thead className="bg-[#FAFBFD]">
          <tr>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-[var(--color-content-secondary)] uppercase tracking-wider">
              Área
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-[var(--color-content-secondary)] uppercase tracking-wider">
              Pacientes en cola
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-[var(--color-content-secondary)] uppercase tracking-wider">
              <div className="flex justify-center items-center">
                <Camera className="w-4 h-4 mr-1.5" />
                Personas físicas
              </div>
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-center text-xs font-medium text-[var(--color-content-secondary)] uppercase tracking-wider">
              Espera est.
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium text-[var(--color-content-secondary)] uppercase tracking-wider">
              Estado
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-surface-border)] relative">
          {areas.map((area) => (
            <tr
              key={area.area_id}
              className={
                area.status === "saturated" ? "bg-red-100" : "bg-white"
              }>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-[var(--color-content-primary)]">
                {area.area_name}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-[var(--color-content-secondary)] text-center font-medium">
                {area.current_queue_length}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-[var(--color-content-secondary)] text-center font-medium">
                {area.people_in_area}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-[var(--color-content-secondary)] text-center font-medium">
                {area.estimated_wait_minutes} min
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                {getStatusBadge(area.status)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
