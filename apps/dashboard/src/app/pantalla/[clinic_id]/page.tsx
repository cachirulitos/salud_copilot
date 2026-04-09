"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const WS_BASE = API.replace(/^http/, "ws");

interface ActiveVisit {
  visit_id: string;
  ticket_number: string;
  current_area: string;
  step_order: number;
  total_steps: number;
  status: string;
  waiting_since_minutes: number;
}

export default function PantallaPage() {
  const { clinic_id } = useParams<{ clinic_id: string }>();
  const [visits, setVisits] = useState<ActiveVisit[]>([]);
  const [clock, setClock] = useState<Date | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    setClock(new Date());
    const t = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(`${WS_BASE}/ws/dashboard/${clinic_id}`);
      wsRef.current = ws;

      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          if (msg.event === "checkin_created") {
            const d = msg.data;
            setVisits((prev) => [
              ...prev,
              {
                visit_id: d.visit_id,
                ticket_number: d.ticket_number ?? "",
                current_area: d.current_area ?? "",
                step_order: d.step_order ?? 1,
                total_steps: d.total_steps ?? 1,
                status: d.visit_status ?? "pending",
                waiting_since_minutes: 0,
              },
            ]);
          } else if (msg.event === "overview_snapshot") {
            if (msg.data.active_visits) setVisits(msg.data.active_visits);
          } else if (msg.event === "visit_step_updated") {
            const d = msg.data;
            setVisits((prev) =>
              prev
                .map((v) =>
                  v.visit_id === d.visit_id
                    ? {
                        ...v,
                        status: d.next_step ? "pending" : "completed",
                        current_area: d.next_step?.area_name ?? v.current_area,
                        step_order: d.next_step?.order ?? v.step_order,
                      }
                    : v,
                )
                .filter((v) => v.status !== "completed"),
            );
          } else if (msg.event === "patient_arriving") {
            const d = msg.data;
            setVisits((prev) =>
              prev.map((v) =>
                v.visit_id === d.visit_id
                  ? { ...v, status: "in_progress", current_area: d.to_area ?? v.current_area }
                  : v,
              ),
            );
          }
        } catch {}
      };

      ws.onclose = () => setTimeout(connect, 3000);
    }

    connect();
    return () => wsRef.current?.close();
  }, [clinic_id]);

  const sorted = [...visits].sort((a, b) => {
    const rank = { in_progress: 0, pending: 1 };
    const ra = rank[a.status as keyof typeof rank] ?? 1;
    const rb = rank[b.status as keyof typeof rank] ?? 1;
    if (ra !== rb) return ra - rb;
    return a.waiting_since_minutes - b.waiting_since_minutes;
  });

  const attending = sorted.filter((v) => v.status === "in_progress");
  const nextUp = sorted.filter((v) => v.status === "pending").slice(0, 1);
  const waiting = sorted.filter((v) => v.status === "pending").slice(1);

  return (
    <div className="h-screen bg-[#0a0f1e] text-white flex flex-col select-none overflow-hidden">

      {/* Top bar */}
      <div className="flex items-center justify-between px-10 py-5 border-b border-white/10">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-white/50 text-sm font-medium tracking-widest uppercase">
            Salud Digna · Turnos
          </span>
        </div>
        <span className="font-mono text-2xl font-bold text-white/80 tabular-nums">
          {clock ? clock.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "--:--:--"}
        </span>
      </div>

      <div className="flex flex-1 gap-0 overflow-hidden">

        {/* LEFT — En atención */}
        <div className="flex-1 flex flex-col border-r border-white/10 p-10 gap-6 min-h-0">
          <h2 className="text-xs font-bold tracking-[0.3em] uppercase text-emerald-400 shrink-0">
            En atención
          </h2>

          <div className="flex flex-col gap-4 flex-1">
            {attending.length === 0 ? (
              <div className="flex items-center justify-center py-10">
                <span className="text-white/20 text-2xl font-light">— —</span>
              </div>
            ) : (
              attending.map((v) => (
                <div
                  key={v.visit_id}
                  className="bg-emerald-500/10 border border-emerald-500/30 rounded-3xl px-10 py-8 flex items-center gap-6"
                >
                  <span className="text-7xl font-black text-emerald-400 tracking-tight tabular-nums">
                    {v.ticket_number || "—"}
                  </span>
                  <div className="w-px h-16 bg-emerald-500/30" />
                  <div>
                    <p className="text-emerald-300 text-xs font-semibold uppercase tracking-widest mb-1">
                      Diríjase a
                    </p>
                    <p className="text-white text-3xl font-bold capitalize">
                      {v.current_area || "Recepción"}
                    </p>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Next up */}
          {nextUp.length > 0 && (
            <div className="shrink-0">
              <h2 className="text-xs font-bold tracking-[0.3em] uppercase text-amber-400 mb-3">
                Próximo
              </h2>
              {nextUp.map((v) => (
                <div
                  key={v.visit_id}
                  className="bg-amber-500/10 border border-amber-500/30 rounded-2xl px-8 py-5 flex items-center gap-5"
                >
                  <span className="text-5xl font-black text-amber-400 tabular-nums">
                    {v.ticket_number || "—"}
                  </span>
                  <p className="text-amber-200/70 text-sm font-medium">
                    Preséntese en recepción
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* RIGHT — En espera */}
        <div className="w-72 flex flex-col p-8 gap-4">
          <h2 className="text-xs font-bold tracking-[0.3em] uppercase text-white/40">
            En espera
          </h2>

          {waiting.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <span className="text-white/20 text-sm">Sin espera</span>
            </div>
          ) : (
            <div className="flex flex-col gap-2 overflow-y-auto">
              {waiting.map((v, i) => (
                <div
                  key={v.visit_id}
                  className="flex items-center justify-between px-4 py-3 rounded-xl bg-white/5 border border-white/5"
                >
                  <span className="text-2xl font-bold text-white/70 tabular-nums">
                    {v.ticket_number || "—"}
                  </span>
                  <span className="text-white/30 text-sm">
                    #{i + 2}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom bar */}
      <div className="px-10 py-4 border-t border-white/10 flex items-center justify-between">
        <p className="text-white/20 text-xs tracking-widest uppercase">
          Para seguir tu recorrido completo, consulta tu WhatsApp
        </p>
        <p className="text-white/20 text-xs">
          {clock ? clock.toLocaleDateString("es-MX", { weekday: "long", day: "numeric", month: "long", year: "numeric" }) : ""}
        </p>
      </div>
    </div>
  );
}
