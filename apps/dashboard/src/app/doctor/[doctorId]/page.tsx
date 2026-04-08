"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useDoctorData } from "@/lib/hooks/useDoctorData";
import NotificationsPanel, {
  StudyChangeNotification,
} from "@/components/ui/NotificationsPanel";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Sub-components ────────────────────────────────────────────────────────────

function StepBadge({ status }: { status: string }) {
  if (status === "in_progress")
    return (
      <span className="inline-flex items-center gap-1 text-xs font-semibold bg-brand-green/10 text-brand-green border border-brand-green/20 px-2 py-0.5 rounded-full">
        <span className="w-1.5 h-1.5 rounded-full bg-brand-green animate-pulse" />
        En progreso
      </span>
    );
  return (
    <span className="inline-flex items-center text-xs font-medium bg-surface-base text-content-secondary border border-surface-border px-2 py-0.5 rounded-full">
      En cola
    </span>
  );
}

function ElapsedBadge({
  elapsed,
  estimated,
}: {
  elapsed: number | null;
  estimated: number | null;
}) {
  if (elapsed === null)
    return <span className="text-content-secondary text-xs">—</span>;
  const isOver = estimated !== null && elapsed > estimated + 5;
  return (
    <span
      className={`text-xs font-semibold tabular-nums ${isOver ? "text-alert-red" : "text-content-primary"}`}>
      {elapsed} min{isOver && " ⚠"}
    </span>
  );
}

function AlertCard({
  alert,
  onResolve,
}: {
  alert: ReturnType<typeof useDoctorData>["alerts"][number];
  onResolve: (id: string) => void;
}) {
  const isOvertime = alert.alert_type === "overtime";
  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-lg border ${
        isOvertime
          ? "bg-red-50 border-red-200"
          : "bg-yellow-50 border-yellow-200"
      }`}>
      <span
        className={`mt-1 w-2 h-2 rounded-full shrink-0 ${
          isOvertime ? "bg-alert-red" : "bg-alert-yellow"
        }`}
      />
      <div className="flex-1 min-w-0">
        <p
          className={`text-xs font-semibold ${isOvertime ? "text-alert-red" : "text-alert-yellow"}`}>
          {isOvertime ? "Tiempo excedido" : "Alerta de cola"}
        </p>
        <p className="text-xs text-content-secondary mt-0.5 leading-relaxed">
          {alert.message}
        </p>
      </div>
      <button
        onClick={() => onResolve(alert.id)}
        className="text-xs text-content-secondary hover:text-content-primary underline transition-colors">
        Resolver
      </button>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function DoctorDashboardPage({
  params,
}: {
  params: { doctorId: string };
}) {
  const router = useRouter();
  const { patients, alerts, loading, error, advanceStep, resolveAlert } =
    useDoctorData();

  const [notifications, setNotifications] = useState<StudyChangeNotification[]>(
    [],
  );
  const [doctorName, setDoctorName] = useState("Doctor");
  const [areaName, setAreaName] = useState("");

  useEffect(() => {
    if (typeof window !== "undefined") {
      setDoctorName(localStorage.getItem("doctor_name") ?? "Doctor");
      setAreaName(localStorage.getItem("doctor_area_name") ?? "");
    }
  }, []);

  // Listen for study_change_notification WebSocket events
  useEffect(() => {
    const wsUrl =
      (process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000") +
      `/ws/dashboard/${process.env.NEXT_PUBLIC_CLINIC_ID ?? "default"}`;
    const ws = new WebSocket(wsUrl);

    ws.addEventListener("message", (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.event === "study_change_notification") {
          const d = msg.data;
          setNotifications((prev) => [
            {
              id: crypto.randomUUID(),
              visit_id: d.visit_id,
              old_area: d.old_area,
              new_area: d.new_area,
              reason: d.reason ?? null,
              received_at: new Date().toISOString(),
            },
            ...prev,
          ]);
        } else if (msg.event === "doctor_overtime_alert") {
          const d = msg.data;
          setNotifications((prev) => [
            {
              id: crypto.randomUUID(),
              visit_id: "alert",
              old_area: d.area_name,
              new_area: "Advertencia",
              reason: d.message,
              received_at: new Date().toISOString(),
            },
            ...prev,
          ]);
        }
      } catch {
        // ignore parse errors
      }
    });

    return () => ws.close();
  }, []);

  // UseEffect to trigger alert when a patient passes the regular estimated time
  const [hasTriggeredOvertime, setHasTriggeredOvertime] = useState<Record<string, boolean>>({});
  
  useEffect(() => {
    const currentPatient = patients.find(p => p.step_status === "in_progress");
    if (currentPatient && currentPatient.elapsed_minutes !== null && currentPatient.expected_consultation_minutes !== null) {
      if (currentPatient.elapsed_minutes >= currentPatient.expected_consultation_minutes) {
        if (!hasTriggeredOvertime[currentPatient.visit_id]) {
          const patientsWaiting = patients.filter(p => p.step_status === "pending").length;
          
          fetch(`${API_URL}/api/v1/notifications/doctor-overtime`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              clinic_id: process.env.NEXT_PUBLIC_CLINIC_ID ?? "default",
              area_name: areaName,
              patients_waiting: patientsWaiting,
            }),
            credentials: "include",
          }).catch(console.error);

          setHasTriggeredOvertime(prev => ({ ...prev, [currentPatient.visit_id]: true }));
        }
      }
    }
  }, [patients, hasTriggeredOvertime, areaName]);

  const handleLogout = async () => {
    await fetch(`${API_URL}/api/v1/doctors/logout`, {
      method: "POST",
      credentials: "include",
    });
    localStorage.clear();
    router.push("/doctor/login");
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-content-secondary">
          <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8v8z"
            />
          </svg>
          <span className="text-sm">Cargando pacientes…</span>
        </div>
      </div>
    );
  }

  if (error === "not_authenticated") {
    if (typeof window !== "undefined") router.replace("/doctor/login");
    return null;
  }

  return (
    <div className="min-h-screen bg-surface-base">
      {/* Top bar */}
      <header className="bg-surface-card border-b border-surface-border px-6 py-4 flex items-center justify-between shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-brand-green/10 border border-brand-green/20 flex items-center justify-center">
            <svg
              className="w-4 h-4 text-brand-green"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12h6m-3-3v6m-7 4h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
              />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-bold text-content-primary leading-tight">
              Portal Médico
            </h1>
            <p className="text-xs text-content-secondary leading-tight">
              {doctorName}
              {areaName && (
                <>
                  {" "}
                  ·{" "}
                  <span className="text-brand-green font-medium">
                    {areaName}
                  </span>
                </>
              )}
            </p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="text-xs text-content-secondary hover:text-surface-base hover:bg-alert-red/80 hover:border-alert-red/80 border border-surface-border px-3 py-1.5 rounded-lg transition-colors bg-surface-base">
          Cerrar sesión
        </button>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-6 space-y-6">
        {/* ── Alerts ───────────────────────────────────────────────────── */}
        {alerts.length > 0 && (
          <section>
            <h2 className="text-xs font-semibold text-content-secondary uppercase tracking-wider mb-3">
              Alertas activas
            </h2>
            <div className="space-y-2">
              {alerts.map((a) => (
                <AlertCard key={a.id} alert={a} onResolve={resolveAlert} />
              ))}
            </div>
          </section>
        )}

        {/* ── Patient list + Notifications ─────────────────────────────── */}
        <div className="grid grid-cols-3 gap-4">
          {/* Patient table */}
          <div className="col-span-2 space-y-3">
            <h2 className="text-xs font-semibold text-content-secondary uppercase tracking-wider">
              Pacientes en tu área
            </h2>

            {patients.length === 0 ? (
              <div className="bg-surface-card border border-surface-border rounded-lg p-8 text-center text-sm text-content-secondary shadow-sm">
                No hay pacientes activos en tu área ahora mismo
              </div>
            ) : (
              <div className="bg-surface-card border border-surface-border rounded-lg overflow-hidden shadow-sm">
                <table className="min-w-full divide-y divide-surface-border">
                  <thead className="bg-surface-base">
                    <tr>
                      {[
                        "Paciente",
                        "Estado",
                        "Est. / Transcurrido",
                        "Paso",
                        "",
                      ].map((h) => (
                        <th
                          key={h}
                          className="px-5 py-3 text-left text-xs font-medium text-content-secondary uppercase tracking-wider">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-surface-border bg-surface-card">
                    {patients.map((p) => {
                      const isOvertime =
                        p.elapsed_minutes !== null &&
                        p.expected_consultation_minutes !== null &&
                        p.elapsed_minutes > p.expected_consultation_minutes + 5;
                      return (
                        <tr
                          key={p.visit_id}
                          className={isOvertime ? "bg-red-50" : ""}>
                          <td className="px-5 py-4 text-sm font-semibold text-content-primary whitespace-nowrap">
                            {p.patient_name}
                          </td>
                          <td className="px-5 py-4 whitespace-nowrap">
                            <StepBadge status={p.step_status} />
                          </td>
                          <td className="px-5 py-4 whitespace-nowrap text-xs text-content-secondary">
                            <span className="tabular-nums">
                              {p.expected_consultation_minutes ?? "—"} min
                            </span>
                            {" / "}
                            <ElapsedBadge
                              elapsed={p.elapsed_minutes}
                              estimated={p.expected_consultation_minutes}
                            />
                          </td>
                          <td className="px-5 py-4 whitespace-nowrap text-xs text-content-secondary tabular-nums">
                            {p.step_order}/{p.total_steps}
                          </td>
                          <td className="px-5 py-4 whitespace-nowrap text-right">
                            <button
                              id={`advance-${p.visit_id}`}
                              disabled={p.step_status !== "in_progress"}
                              onClick={() => advanceStep(p.visit_id)}
                              className="text-xs font-medium bg-brand-green hover:bg-brand-green/90 disabled:opacity-30 disabled:cursor-not-allowed text-white px-3 py-1.5 rounded-lg transition-colors">
                              Avanzar paso
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Notifications panel */}
          <NotificationsPanel
            notifications={notifications}
            onDismiss={(id) =>
              setNotifications((prev) => prev.filter((n) => n.id !== id))
            }
          />
        </div>
      </main>
    </div>
  );
}
