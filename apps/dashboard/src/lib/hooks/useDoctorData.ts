"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const CLINIC_ID = process.env.NEXT_PUBLIC_CLINIC_ID ?? "default";
const POLL_MS = 15_000;

function getAreaId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("doctor_area_id");
}

export interface StepDetail {
  order: number;
  area_name: string;
  status: "pending" | "in_progress" | "completed";
  estimated_wait_minutes: number | null;
  actual_wait_minutes: number | null;
}

export interface CompletedPatientEntry {
  visit_id: string;
  patient_name: string;
  completed_at: string;
  total_steps: number;
}

export interface CompletedToday {
  count: number;
  patients: CompletedPatientEntry[];
}

export interface DoctorPatient {
  visit_id: string;
  patient_name: string;
  step_status: "pending" | "in_progress" | "completed";
  step_order: number;
  total_steps: number;
  estimated_wait_minutes: number | null;
  expected_consultation_minutes: number | null;
  elapsed_minutes: number | null;
  coming_from_area: string | null;
  next_area_after: string | null;
  steps: StepDetail[];
}

export interface DoctorAlert {
  id: string;
  clinic_id: string;
  area_id: string;
  visit_id: string | null;
  alert_type: string;
  message: string;
  triggered_at: string;
  resolved_at: string | null;
}

export function useDoctorData() {
  const [patients, setPatients] = useState<DoctorPatient[]>([]);
  const [alerts, setAlerts] = useState<DoctorAlert[]>([]);
  const [completedToday, setCompletedToday] = useState<CompletedToday>({ count: 0, patients: [] });
  const [waitTimeHistory, setWaitTimeHistory] = useState<{ labels: string[]; series: Record<string, number[]> }>({ labels: [], series: {} });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPatients = async () => {
    const res = await fetch(`${API_URL}/api/v1/doctors/me/patients`, {
      credentials: "include",
    });
    if (res.status === 401) throw new Error("not_authenticated");
    if (!res.ok) throw new Error("failed_to_fetch_patients");
    return res.json() as Promise<DoctorPatient[]>;
  };

  const fetchAlerts = async () => {
    const areaId = getAreaId();
    const params = new URLSearchParams({ clinic_id: CLINIC_ID, resolved: "false" });
    if (areaId) params.set("area_id", areaId);
    const res = await fetch(
      `${API_URL}/api/v1/notifications/alerts?${params}`,
      { credentials: "include" },
    );
    if (!res.ok) return [];
    return res.json() as Promise<DoctorAlert[]>;
  };

  const fetchCompletedToday = async (): Promise<CompletedToday> => {
    const res = await fetch(`${API_URL}/api/v1/doctors/me/completed-today`, {
      credentials: "include",
    });
    if (!res.ok) return { count: 0, patients: [] };
    return res.json();
  };

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/dashboard/${CLINIC_ID}/history`, {
        credentials: "include",
      });
      if (!res.ok) return;
      const data = await res.json();
      if (data.labels && data.series) setWaitTimeHistory(data);
    } catch {
      // history is non-critical, ignore network errors
    }
  };

  const load = async () => {
    try {
      const [p, a, c] = await Promise.all([fetchPatients(), fetchAlerts(), fetchCompletedToday()]);
      setPatients(p);
      setAlerts(a);
      setCompletedToday(c);
      setError(null);
    } catch (e: any) {
      setError(e?.message ?? "unknown_error");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, POLL_MS);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    fetchHistory();
  }, []);

  const advanceStep = async (visitId: string) => {
    try {
      const res = await fetch(`${API_URL}/api/v1/visits/${visitId}/advance-step`, {
        method: "POST",
        credentials: "include",
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        console.error("advance-step failed", res.status, body);
      }
    } catch (e) {
      console.error("advance-step network error", e);
    }
    await load();
  };

  const resolveAlert = async (alertId: string) => {
    await fetch(`${API_URL}/api/v1/notifications/alerts/${alertId}/resolve`, {
      method: "POST",
      credentials: "include",
    });
    setAlerts((prev) => prev.filter((a) => a.id !== alertId));
  };

  const queueSize = patients.filter((p) => p.step_status === "pending").length;
  const inAttention = patients.filter((p) => p.step_status === "in_progress").length;
  const avgWait =
    patients.length > 0
      ? Math.round(
          patients.reduce((s, p) => s + (p.estimated_wait_minutes ?? 0), 0) / patients.length,
        )
      : 0;
  const overtimeCount = alerts.filter((a) => a.alert_type === "overtime").length;

  const removeAlertLocally = (alertId: string) => {
    setAlerts((prev) => prev.filter((a) => a.id !== alertId));
  };

  return {
    patients,
    alerts,
    loading,
    error,
    advanceStep,
    resolveAlert,
    removeAlertLocally,
    refreshData: load,
    completedToday,
    kpis: { queueSize, inAttention, avgWait, overtimeCount },
    waitTimeHistory,
  };
}
