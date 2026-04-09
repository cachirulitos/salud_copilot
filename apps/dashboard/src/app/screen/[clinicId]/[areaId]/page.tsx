"use client";

import { useEffect, useState, use } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Shift {
  visit_id: string;
  turn_number: string;
  patient_name: string;
  status: "pending" | "in_progress" | "completed";
  step_order: number;
}

export default function AreaScreenPage({
  params,
}: {
  params: Promise<{ clinicId: string; areaId: string }>;
}) {
  const { areaId } = use(params);
  const [shifts, setShifts] = useState<Shift[]>([]);

  const fetchShifts = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/areas/${areaId}/shifts`);
      if (res.ok) {
        const data = await res.json();
        setShifts(data);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchShifts();
    const intervalId = setInterval(fetchShifts, 5000); // Polling cada 5s para máxima inmediatez y resiliencia
    return () => clearInterval(intervalId);
  }, [areaId]);

  const inProgress = shifts.filter((s) => s.status === "in_progress");
  const pending = shifts.filter((s) => s.status === "pending");

  return (
    <div className="max-h-screen bg-surface-base text-content-primary flex flex-col font-sans p-10">
      <header className="flex items-center justify-between border-b-4 border-brand-green/20 pb-8 mb-10">
        <h1 className="text-6xl font-extrabold uppercase tracking-widest text-brand-green flex items-center gap-6">
          <div className="bg-brand-green text-surface-base w-20 h-20 flex items-center justify-center rounded-3xl shadow-lg">
            <svg
              className="w-12 h-12"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2.5}>
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
              />
            </svg>
          </div>
          Módulo de Atención
        </h1>
        <div className="text-right">
          <p className="text-3xl font-bold text-content-secondary tracking-widest uppercase">
            Espera tu llamado
          </p>
        </div>
      </header>

      <main className="flex-1 grid grid-cols-5 gap-16">
        {/* ── Izquierda: En Módulo (Consultando ahora) ── */}
        <section className="col-span-2 flex flex-col h-full">
          <div className="bg-brand-green text-white rounded-t-[40px] text-center py-8 shadow-md z-10">
            <h2 className="text-5xl font-black uppercase tracking-widest">
              En Módulo
            </h2>
          </div>
          <div className="flex-1 bg-surface-card border-8 border-brand-green rounded-b-[40px] flex flex-col p-12 items-center justify-center shadow-2xl relative -mt-4">
            {inProgress.length > 0 ? (
              inProgress.map((s) => (
                <div
                  key={s.visit_id}
                  className="text-center animate-pulse w-full">
                  <div className="text-[180px] font-black leading-none tracking-tighter text-brand-green pb-6 border-b border-surface-border">
                    {s.turn_number}
                  </div>
                  <div className="text-5xl font-bold mt-10 text-content-primary">
                    {s.patient_name}
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center opacity-30 mt-6">
                <div className="text-[160px] font-black leading-none">—</div>
                <div className="text-5xl font-medium mt-10">Disponible</div>
              </div>
            )}
          </div>
        </section>

        {/* ── Derecha: Próximos ── */}
        <section className="col-span-3 flex flex-col h-full">
          <div className="bg-surface-border text-content-primary rounded-t-[40px] px-10 py-8 flex items-center justify-between shadow-sm">
            <h2 className="text-4xl font-black uppercase tracking-widest text-content-secondary">
              Fila de espera
            </h2>
            <span className="text-3xl font-black bg-surface-base px-6 py-2 rounded-2xl shadow-sm border border-surface-border text-brand-green">
              {pending.length} formados
            </span>
          </div>
          <div className="bg-surface-card rounded-b-[40px] flex-1 p-10 shadow-xl border-x-4 border-b-4 border-surface-border flex flex-col">
            {pending.length > 0 ? (
              <div className="grid grid-cols-1 gap-8 w-full">
                {pending.slice(0, 2).map((s, idx) => (
                  <div
                    key={s.visit_id}
                    className="flex flex-row items-center justify-between bg-surface-base p-8 rounded-3xl border-2 border-surface-border shadow-sm overflow-hidden">
                    <div className="flex items-center gap-10">
                      <span className="text-5xl font-bold text-content-secondary w-12 text-center opacity-40">
                        {idx + 1}
                      </span>
                      <span className="text-7xl font-black text-content-primary tracking-tight">
                        {s.turn_number}
                      </span>
                    </div>
                    <div className="text-5xl font-semibold text-content-secondary truncate max-w-md text-right ml-4">
                      {s.patient_name}
                    </div>
                  </div>
                ))}
                {pending.length > 6 && (
                  <div className="text-center p-6 bg-surface-base rounded-3xl border-2 border-surface-border border-dashed">
                    <span className="text-3xl font-bold text-content-secondary opacity-60">
                      ...y {pending.length - 6} más en espera
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex items-center justify-center text-5xl text-content-secondary opacity-40 font-medium pb-20">
                Ninguna persona formada
              </div>
            )}
          </div>
        </section>
      </main>
    </div>
  );
}
