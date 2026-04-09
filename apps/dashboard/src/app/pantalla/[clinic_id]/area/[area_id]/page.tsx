"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";

const WS_BASE = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/^http/, "ws");

interface AreaVisit {
  visit_id: string;
  ticket_number: string;
  current_area: string;
  current_area_id: string;
  status: string;
  waiting_since_minutes: number;
}

export default function AreaPantallaPage() {
  const { clinic_id, area_id } = useParams<{ clinic_id: string; area_id: string }>();
  const [visits, setVisits] = useState<AreaVisit[]>([]);
  const [areaName, setAreaName] = useState<string>("");
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

          if (msg.event === "overview_snapshot") {
            const all: AreaVisit[] = msg.data.active_visits ?? [];
            const filtered = all.filter((v) => v.current_area_id === area_id);
            setVisits(filtered);
            if (filtered.length > 0) setAreaName(filtered[0].current_area);
            else {
              // get area name from areas list in overview
              const area = (msg.data.areas ?? []).find((a: { area_id: string; area_name: string }) => a.area_id === area_id);
              if (area) setAreaName(area.area_name);
            }
          } else if (msg.event === "checkin_created") {
            const d = msg.data;
            if (d.current_area_id !== area_id) return;
            setAreaName(d.current_area);
            setVisits((prev) => [
              ...prev,
              {
                visit_id: d.visit_id,
                ticket_number: d.ticket_number ?? "",
                current_area: d.current_area ?? "",
                current_area_id: d.current_area_id ?? "",
                status: "pending",
                waiting_since_minutes: 0,
              },
            ]);
          } else if (msg.event === "visit_step_updated") {
            const d = msg.data;
            setVisits((prev) => {
              const updated = prev
                .map((v) => {
                  if (v.visit_id !== d.visit_id) return v;
                  // patient moved away from this area (step completed)
                  if (!d.next_step || d.next_step.area_id !== area_id) return null;
                  return { ...v, status: d.next_step.status ?? "in_progress", current_area_id: d.next_step.area_id, current_area: d.next_step.area_name };
                })
                .filter(Boolean) as AreaVisit[];

              // patient arriving at this area (not yet in list)
              if (d.next_step?.area_id === area_id) {
                const already = updated.find((v) => v.visit_id === d.visit_id);
                if (!already) {
                  updated.push({
                    visit_id: d.visit_id,
                    ticket_number: d.ticket_number ?? "",
                    current_area: d.next_step.area_name ?? areaName,
                    current_area_id: d.next_step.area_id,
                    status: d.next_step.status ?? "in_progress",
                    waiting_since_minutes: 0,
                  });
                }
              }
              return updated;
            });
          } else if (msg.event === "patient_arriving") {
            const d = msg.data;
            setVisits((prev) =>
              prev.map((v) =>
                v.visit_id === d.visit_id ? { ...v, status: "in_progress" } : v,
              ),
            );
          }
        } catch {}
      };

      ws.onclose = () => setTimeout(connect, 3000);
    }

    connect();
    return () => wsRef.current?.close();
  }, [clinic_id, area_id]);

  const sorted = [...visits].sort((a, b) => {
    const rank = { in_progress: 0, pending: 1 };
    const ra = rank[a.status as keyof typeof rank] ?? 1;
    const rb = rank[b.status as keyof typeof rank] ?? 1;
    if (ra !== rb) return ra - rb;
    return a.waiting_since_minutes - b.waiting_since_minutes;
  });

  const attending = sorted.filter((v) => v.status === "in_progress");
  const next = sorted.filter((v) => v.status === "pending");

  return (
    <div className="h-screen bg-white text-gray-900 flex flex-col select-none overflow-hidden">

      {/* Top bar */}
      <div className="flex items-center justify-between px-10 py-5 bg-[#00923f] shadow-md">
        <div className="flex items-center gap-3">
          <div className="w-2.5 h-2.5 rounded-full bg-white animate-pulse" />
          <span className="text-white/90 text-sm font-bold tracking-widest uppercase">
            {areaName || "Área"} · Turnos
          </span>
        </div>
        <span className="font-mono text-2xl font-bold text-white tabular-nums">
          {clock ? clock.toLocaleTimeString("es-MX", { hour: "2-digit", minute: "2-digit", second: "2-digit" }) : "--:--:--"}
        </span>
      </div>

      <div className="flex flex-1 overflow-hidden gap-0">

        {/* LEFT — En atención en esta área */}
        <div className="flex-1 flex flex-col border-r border-gray-200 p-10 gap-6 min-h-0">
          <h2 className="text-xs font-bold tracking-[0.3em] uppercase text-[#00923f] shrink-0">
            En atención
          </h2>

          <div className="flex flex-col gap-4 flex-1">
            {attending.length === 0 ? (
              <div className="flex items-center justify-center py-10">
                <span className="text-gray-300 text-2xl font-light">— —</span>
              </div>
            ) : (
              attending.map((v) => (
                <div
                  key={v.visit_id}
                  className="bg-[#00923f]/10 border-2 border-[#00923f]/40 rounded-3xl px-10 py-8 flex items-center gap-6"
                >
                  <span className="text-7xl font-black text-[#00923f] tracking-tight tabular-nums">
                    {v.ticket_number || "—"}
                  </span>
                </div>
              ))
            )}
          </div>

          {/* Próximos en esta área */}
          {next.length > 0 && (
            <div className="shrink-0 flex flex-col gap-3">
              <h2 className="text-xs font-bold tracking-[0.3em] uppercase text-orange-500">
                Próximo
              </h2>
              {next.slice(0, 4).map((v) => (
                <div
                  key={v.visit_id}
                  className="bg-orange-50 border border-orange-200 rounded-2xl px-8 py-5 flex items-center gap-5"
                >
                  <span className="text-5xl font-black text-orange-500 tabular-nums">
                    {v.ticket_number || "—"}
                  </span>
                  <p className="text-orange-400 text-sm">
                    Diríjase a {areaName || "esta área"}
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* RIGHT — Cola completa */}
        <div className="w-72 flex flex-col p-8 gap-4 bg-gray-50">
          <h2 className="text-xs font-bold tracking-[0.3em] uppercase text-gray-400">
            En espera
          </h2>
          {next.slice(4).length === 0 && attending.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <span className="text-gray-300 text-sm">Sin espera</span>
            </div>
          ) : (
            <div className="flex flex-col gap-2 overflow-y-auto">
              {next.slice(4).map((v, i) => (
                <div
                  key={v.visit_id}
                  className="flex items-center justify-between px-4 py-3 rounded-xl bg-white border border-gray-200"
                >
                  <span className="text-2xl font-bold text-gray-600 tabular-nums">
                    {v.ticket_number || "—"}
                  </span>
                  <span className="text-gray-400 text-sm">#{i + 5}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom bar */}
      <div className="px-10 py-4 border-t border-gray-200 bg-white flex items-center justify-between">
        <p className="text-gray-400 text-xs tracking-widest uppercase">
          {areaName || "Área"} · Salud Digna
        </p>
        <p className="text-gray-400 text-xs">
          {clock ? clock.toLocaleDateString("es-MX", { weekday: "long", day: "numeric", month: "long", year: "numeric" }) : ""}
        </p>
      </div>
    </div>
  );
}
