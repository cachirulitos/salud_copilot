"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function DoctorLoginPage() {
  const router = useRouter();
  const [employeeId, setEmployeeId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/api/v1/doctors/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ employee_id: employeeId, password }),
      });

      if (!res.ok) {
        const json = await res.json();
        setError(json.detail ?? "Error de autenticación");
        return;
      }

      const data = await res.json();
      localStorage.setItem("doctor_id", data.doctor_id);
      localStorage.setItem("doctor_name", data.full_name);
      localStorage.setItem("doctor_area_id", data.clinical_area_id);
      localStorage.setItem("doctor_area_name", data.clinical_area_name);

      router.push(`/doctor/${data.doctor_id}`);
    } catch {
      setError("No se pudo conectar con el servidor");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-surface-base flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo / branding */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-xl bg-brand-green/10 border border-brand-green/20 mb-4">
            <svg className="w-7 h-7 text-brand-green" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12h6m-3-3v6m-7 4h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-content-primary tracking-tight">Portal Médico</h1>
          <p className="text-sm text-content-secondary mt-1">SaludCopilot — Acceso para doctores</p>
        </div>

        {/* Card */}
        <form
          onSubmit={handleSubmit}
          className="bg-surface-card border border-surface-border rounded-xl p-8 shadow-sm space-y-5"
        >
          {/* Employee ID */}
          <div>
            <label className="block text-xs font-medium text-content-secondary mb-1.5 uppercase tracking-wider">
              Número de empleado
            </label>
            <input
              id="employee-id"
              type="text"
              inputMode="numeric"
              maxLength={4}
              pattern="\d{4}"
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value.replace(/\D/g, "").slice(0, 4))}
              required
              placeholder="1234"
              className="w-full bg-surface-base border border-surface-border text-content-primary placeholder-content-secondary/50 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent transition"
            />
          </div>

          {/* Password */}
          <div>
            <label className="block text-xs font-medium text-content-secondary mb-1.5 uppercase tracking-wider">
              Contraseña (8 dígitos)
            </label>
            <input
              id="doctor-password"
              type="password"
              inputMode="numeric"
              maxLength={8}
              pattern="\d{8}"
              value={password}
              onChange={(e) => setPassword(e.target.value.replace(/\D/g, "").slice(0, 8))}
              required
              placeholder="••••••••"
              className="w-full bg-surface-base border border-surface-border text-content-primary placeholder-content-secondary/50 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-green focus:border-transparent transition"
            />
          </div>

          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-alert-red text-sm rounded-lg px-4 py-3">
              <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            id="login-submit"
            type="submit"
            disabled={loading || employeeId.length < 4 || password.length < 8}
            className="w-full bg-brand-green hover:bg-brand-green/90 disabled:opacity-40 disabled:cursor-not-allowed text-white font-semibold rounded-lg px-4 py-2.5 text-sm transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8z" />
                </svg>
                Verificando…
              </>
            ) : (
              "Iniciar sesión"
            )}
          </button>
        </form>
      </div>
    </main>
  );
}
