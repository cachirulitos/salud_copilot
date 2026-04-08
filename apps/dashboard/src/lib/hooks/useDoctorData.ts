"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const CLINIC_ID = process.env.NEXT_PUBLIC_CLINIC_ID ?? "default";
const POLL_MS = 15_000;

export interface DoctorPatient {
  visit_id: string;
  patient_name: string;
  step_status: "pending" | "in_progress" | "completed";
  step_order: number;
  total_steps: number;
  estimated_wait_minutes: number | null;
  elapsed_minutes: number | null;
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
    const res = await fetch(
      `${API_URL}/api/v1/notifications/alerts?clinic_id=${CLINIC_ID}&resolved=false`,
      { credentials: "include" },
    );
    if (!res.ok) return [];
    return res.json() as Promise<DoctorAlert[]>;
  };

  const load = async () => {
    try {
      const [p, a] = await Promise.all([fetchPatients(), fetchAlerts()]);
      setPatients(p);
      setAlerts(a);
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

  const advanceStep = async (visitId: string) => {
    await fetch(`${API_URL}/api/v1/visits/${visitId}/advance-step`, {
      method: "POST",
      credentials: "include",
    });
    // Refresh immediately
    await load();
  };

  const resolveAlert = async (alertId: string) => {
    await fetch(`${API_URL}/api/v1/notifications/alerts/${alertId}/resolve`, {
      method: "POST",
      credentials: "include",
    });
    setAlerts((prev) => prev.filter((a) => a.id !== alertId));
  };

  return { patients, alerts, loading, error, advanceStep, resolveAlert };
}
