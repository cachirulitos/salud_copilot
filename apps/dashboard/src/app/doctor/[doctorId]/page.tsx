"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useDoctorData } from "@/lib/hooks/useDoctorData";
import type { StepDetail } from "@/lib/hooks/useDoctorData";
import { MetricCard } from "@/components/ui/MetricCard";
import WaitTimeChart from "@/components/ui/WaitTimeChart";
import NotificationsPanel, {
  StudyChangeNotification,
} from "@/components/ui/NotificationsPanel";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── Sub-components ────────────────────────────────────────────────────────────

function StepIcon({ status }: { status: string }) {
  if (status === "completed")
    return (
      <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-brand-green/10 text-brand-green text-xs font-bold border border-brand-green/20">
        ✓
      </span>
    );
  if (status === "in_progress")
    return (
      <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-brand-blue/10 text-brand-blue text-xs font-bold border border-brand-blue/20">
        ▶
      </span>
    );
  return (
    <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-surface-base text-content-secondary text-xs border border-surface-border">
      ○
    </span>
  );
}

function PatientCard({
  patient,
  onAdvance,
}: {
  patient: ReturnType<typeof useDoctorData>["patients"][number];
  onAdvance: (id: string) => void;
}) {
  const isInProgress = patient.step_status === "in_progress";
  const isOvertime =
    patient.elapsed_minutes !== null &&
    patient.expected_consultation_minutes !== null &&
    patient.elapsed_minutes > patient.expected_consultation_minutes + 5;

  const remainingMinutes = patient.steps
    .filter((s) => s.status !== "completed")
    .reduce((sum, s) => sum + (s.estimated_wait_minutes ?? 0), 0);

  const borderClass = isOvertime
    ? "border-alert-red ring-1 ring-alert-red/30"
    : isInProgress
    ? "border-brand-green ring-1 ring-brand-green/20"
    : "border-surface-border";

  return (
    <div className={`bg-surface-card border rounded-xl p-4 shadow-sm ${borderClass}`}>
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <p className="text-sm font-bold text-content-primary truncate">
              {patient.patient_name}
            </p>
            <span className="text-xs text-content-secondary tabular-nums shrink-0">
              Paso {patient.step_order}/{patient.total_steps}
            </span>
          </div>
          {(patient.coming_from_area || patient.next_area_after) && (
            <p className="text-xs text-content-secondary mt-0.5">
              {patient.coming_from_area && (
                <span>
                  Viene de{" "}
                  <span className="font-medium text-content-primary">
                    {patient.coming_from_area}
                  </span>
                </span>
              )}
              {patient.coming_from_area && patient.next_area_after && (
                <span className="mx-1">·</span>
              )}
              {patient.next_area_after && (
                <span>
                  Luego va a{" "}
                  <span className="font-medium text-brand-green">
                    {patient.next_area_after}
                  </span>
                </span>
              )}
            </p>
          )}
        </div>

        {/* Status + time */}
        <div className="shrink-0 text-right">
          {isInProgress ? (
            <span className="inline-flex items-center gap-1 text-xs font-semibold bg-brand-green/10 text-brand-green border border-brand-green/20 px-2 py-0.5 rounded-full">
              <span className="w-1.5 h-1.5 rounded-full bg-brand-green animate-pulse" />
              En atención
            </span>
          ) : (
            <span className="inline-flex items-center text-xs font-medium bg-surface-base text-content-secondary border border-surface-border px-2 py-0.5 rounded-full">
              En cola
            </span>
          )}
          {isInProgress && patient.elapsed_minutes !== null && (
            <p
              className={`text-xs font-semibold tabular-nums mt-1 ${
                isOvertime ? "text-alert-red" : "text-content-secondary"
              }`}>
              {patient.elapsed_minutes} / {patient.expected_consultation_minutes ?? "?"} min
              {isOvertime && " ⚠"}
            </p>
          )}
        </div>
      </div>

      {/* Journey steps */}
      {patient.steps.length > 0 && (
        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {patient.steps.map((step, idx) => (
            <div key={step.order} className="flex items-center gap-1.5">
              <div className="flex items-center gap-1">
                <StepIcon status={step.status} />
                <span
                  className={`text-xs max-w-[90px] truncate ${
                    step.status === "completed"
                      ? "line-through text-content-secondary"
                      : step.status === "in_progress"
                      ? "font-bold text-content-primary"
                      : "text-content-secondary"
                  }`}
                  title={step.area_name}>
                  {step.area_name}
                  {step.estimated_wait_minutes != null && (
                    <span className="ml-0.5 opacity-60">({step.estimated_wait_minutes}m)</span>
                  )}
                </span>
              </div>
              {idx < patient.steps.length - 1 && (
                <span className="text-content-secondary text-xs">→</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Footer */}
      <div className="mt-3 flex items-center justify-between">
        <p className="text-xs text-content-secondary">
          Tiempo restante estimado:{" "}
          <span className="font-semibold text-content-primary">
            {remainingMinutes} min
          </span>
        </p>
        <button
          disabled={!isInProgress}
          onClick={() => onAdvance(patient.visit_id)}
          className="text-xs font-medium bg-brand-green hover:bg-brand-green/90 disabled:opacity-30 disabled:cursor-not-allowed text-white px-3 py-1.5 rounded-lg transition-colors">
          Avanzar paso
        </button>
      </div>
    </div>
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
        isOvertime ? "bg-red-50 border-red-200" : "bg-yellow-50 border-yellow-200"
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
  const {
    patients,
    alerts,
    loading,
    error,
    advanceStep,
    resolveAlert,
    removeAlertLocally,
    refreshData,
    completedToday,
    kpis,
    waitTimeHistory,
  } = useDoctorData();

  const [notifications, setNotifications] = useState<StudyChangeNotification[]>([]);
  const [doctorName, setDoctorName] = useState("Doctor");
  const [areaName, setAreaName] = useState("");
  const [arrivingToast, setArrivingToast] = useState<{
    patient_name: string;
    from_area: string;
    next_area_after: string | null;
  } | null>(null);
  const [completedOpen, setCompletedOpen] = useState(false);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setDoctorName(localStorage.getItem("doctor_name") ?? "Doctor");
      setAreaName(localStorage.getItem("doctor_area_name") ?? "");
    }
  }, []);

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
          if (d.old_area === localStorage.getItem("doctor_area_name")) {
            refreshData();
          }
        } else if (msg.event === "doctor_overtime_alert") {
          const d = msg.data;
          // Only show overtime alerts for this doctor's own area
          if (d.area_name === localStorage.getItem("doctor_area_name")) {
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
        } else if (msg.event === "checkin_created") {
          const d = msg.data;
          if (d.current_area === localStorage.getItem("doctor_area_name")) {
            refreshData();
          }
        } else if (msg.event === "patient_arriving") {
          const d = msg.data;
          const myArea = localStorage.getItem("doctor_area_name");
          if (d.to_area === myArea) {
            setArrivingToast({
              patient_name: d.patient_name,
              from_area: d.from_area,
              next_area_after: d.next_area_after ?? null,
            });
            refreshData();
            setTimeout(() => setArrivingToast(null), 8000);
          }
        } else if (msg.type === "wait_time_updated") {
          // Only refresh if the update is for this doctor's area
          const myAreaId = localStorage.getItem("doctor_area_id");
          if (!myAreaId || msg.area_id === myAreaId) {
            refreshData();
          }
        } else if (msg.type === "alert_resolved") {
          removeAlertLocally(msg.alert_id);
        }
      } catch {
        // ignore parse errors
      }
    });

    return () => ws.close();
  }, []);

  const [hasTriggeredOvertime, setHasTriggeredOvertime] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const currentPatient = patients.find((p) => p.step_status === "in_progress");
    if (
      currentPatient &&
      currentPatient.elapsed_minutes !== null &&
      currentPatient.expected_consultation_minutes !== null
    ) {
      if (currentPatient.elapsed_minutes >= currentPatient.expected_consultation_minutes) {
        if (!hasTriggeredOvertime[currentPatient.visit_id]) {
          const patientsWaiting = patients.filter((p) => p.step_status === "pending").length;
          fetch(`${API_URL}/api/v1/notifications/doctor-overtime`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              clinic_id: process.env.NEXT_PUBLIC_CLINIC_ID ?? "default",
              area_name: areaName,
              patients_waiting: patientsWaiting,
            }),
            credentials: "include",
          }).catch(console.error);
          setHasTriggeredOvertime((prev) => ({ ...prev, [currentPatient.visit_id]: true }));
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

  // Filter chart series to this doctor's area
  const chartSeries = Object.fromEntries(
    Object.entries(waitTimeHistory.series).filter(([key]) =>
      key.toLowerCase().includes((areaName ?? "").toLowerCase()),
    ),
  );
  const seriesForChart =
    Object.keys(chartSeries).length > 0 ? chartSeries : waitTimeHistory.series;

  if (loading) {
    return (
      <div className="min-h-screen bg-surface-base flex items-center justify-center">
        <div className="flex flex-col items-center gap-3 text-content-secondary">
          <svg className="animate-spin w-5 h-5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
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
                  {" "}·{" "}
                  <span className="text-brand-green font-medium">{areaName}</span>
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

      <main className="max-w-6xl mx-auto px-6 py-6 space-y-6">
        {/* Alerts */}
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

        {/* Arriving toast */}
        {arrivingToast && (
          <div className="flex items-start gap-3 p-4 rounded-lg border border-brand-green/30 bg-brand-green/5 shadow-sm">
            <span className="mt-0.5 w-8 h-8 shrink-0 flex items-center justify-center rounded-full bg-brand-green/10 border border-brand-green/20">
              <svg className="w-4 h-4 text-brand-green" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
            </span>
            <div className="flex-1">
              <p className="text-sm font-semibold text-brand-green">Paciente en camino</p>
              <p className="text-sm text-content-primary mt-0.5">
                <span className="font-medium">{arrivingToast.patient_name}</span>
                {" viene de "}
                <span className="font-medium text-content-secondary">{arrivingToast.from_area}</span>
                {" y se dirige hacia aquí."}
              </p>
              {arrivingToast.next_area_after && (
                <p className="text-xs text-content-secondary mt-1">
                  Después continuará en{" "}
                  <span className="font-medium text-content-primary">{arrivingToast.next_area_after}</span>.
                  Indíquele la dirección al terminar.
                </p>
              )}
            </div>
            <button
              onClick={() => setArrivingToast(null)}
              className="text-content-secondary hover:text-content-primary transition-colors">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        )}

        {/* KPI row */}
        <div className="grid grid-cols-4 gap-4">
          <MetricCard label="En cola" value={kpis.queueSize} accentColor="#005B9F" />
          <MetricCard label="En atención" value={kpis.inAttention} accentColor="#008A4B" />
          <MetricCard label="Espera promedio" value={kpis.avgWait} unit="min" accentColor="#6B7280" />
          <MetricCard
            label="Tiempo excedido"
            value={kpis.overtimeCount}
            accentColor={kpis.overtimeCount > 0 ? "#DC2626" : "#008A4B"}
          />
        </div>

        {/* Main 3-col grid */}
        <div className="grid grid-cols-3 gap-6">
          {/* Left: patients + completed */}
          <div className="col-span-2 space-y-4">
            <h2 className="text-xs font-semibold text-content-secondary uppercase tracking-wider">
              Pacientes en tu área
            </h2>

            {patients.length === 0 ? (
              <div className="bg-surface-card border border-surface-border rounded-xl p-8 text-center text-sm text-content-secondary shadow-sm">
                No hay pacientes activos en tu área ahora mismo
              </div>
            ) : (
              <div className="space-y-3">
                {patients.map((p) => (
                  <PatientCard key={p.visit_id} patient={p} onAdvance={advanceStep} />
                ))}
              </div>
            )}

            {/* Completed today collapsible */}
            <div className="bg-surface-card border border-surface-border rounded-xl overflow-hidden shadow-sm">
              <button
                onClick={() => setCompletedOpen((o) => !o)}
                className="w-full flex items-center justify-between px-4 py-3 text-sm font-semibold text-content-primary hover:bg-surface-base transition-colors">
                <span className="flex items-center gap-2">
                  Completados hoy
                  <span className="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1.5 rounded-full bg-brand-green/10 text-brand-green text-xs font-bold border border-brand-green/20">
                    {completedToday.count}
                  </span>
                </span>
                <svg
                  className={`w-4 h-4 text-content-secondary transition-transform ${completedOpen ? "rotate-180" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                </svg>
              </button>
              {completedOpen && (
                <div className="border-t border-surface-border divide-y divide-surface-border">
                  {completedToday.patients.length === 0 ? (
                    <p className="px-4 py-3 text-sm text-content-secondary">
                      Sin pacientes completados hoy
                    </p>
                  ) : (
                    completedToday.patients.map((c) => (
                      <div key={c.visit_id} className="px-4 py-3 flex items-center justify-between">
                        <div>
                          <p className="text-sm font-medium text-content-primary">
                            {c.patient_name}
                          </p>
                          <p className="text-xs text-content-secondary">
                            {c.total_steps} pasos ·{" "}
                            {new Date(c.completed_at).toLocaleTimeString("es-MX", {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </p>
                        </div>
                        <span className="text-brand-green text-sm">✓</span>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Right: notifications + mini chart */}
          <div className="col-span-1 space-y-4">
            <NotificationsPanel
              notifications={notifications}
              onDismiss={(id) =>
                setNotifications((prev) => prev.filter((n) => n.id !== id))
              }
            />

            {/* Mini wait-time chart */}
            <div className="bg-surface-card border border-surface-border rounded-xl p-4 shadow-sm">
              <h3 className="text-xs font-semibold text-content-secondary uppercase tracking-wider mb-3">
                Historial de esperas
              </h3>
              {Object.keys(waitTimeHistory.series).length === 0 ? (
                <p className="text-xs text-content-secondary py-4 text-center">
                  Sin datos de historial disponibles
                </p>
              ) : (
                <WaitTimeChart
                  history={{ labels: waitTimeHistory.labels, series: seriesForChart }}
                />
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
