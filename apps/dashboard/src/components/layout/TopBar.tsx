"use client";

import { useEffect, useState } from "react";
import { Wifi, WifiOff } from "lucide-react";

interface TopBarProps {
  pageTitle?: string;
  isConnected?: boolean;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString("es-MX", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export default function TopBar({
  pageTitle = "Dashboard",
  isConnected = false,
}: TopBarProps) {
  const [currentTime, setCurrentTime] = useState<string>("");

  useEffect(() => {
    setCurrentTime(formatTime(new Date()));
    const interval = setInterval(() => {
      setCurrentTime(formatTime(new Date()));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <header
      style={{ height: 64, boxShadow: "0 1px 4px 0 rgba(0,0,0,0.06)" }}
      className="sticky top-0 z-40 flex items-center justify-between px-6 bg-surface-card border-b border-surface-border"
    >
      {/* ── Page title ───────────────────────────────────── */}
      <h1 className="text-content-primary font-semibold text-base tracking-tight">
        {pageTitle}
      </h1>

      {/* ── Right: clock + live badge ────────────────────── */}
      <div className="flex items-center gap-4">
        {/* Real-time clock */}
        <span className="text-content-secondary text-sm font-mono tabular-nums">
          {currentTime}
        </span>

        {/* Live / Demo badge */}
        {isConnected ? (
          <span className="flex items-center gap-1.5 text-xs font-semibold text-brand-green bg-brand-green/8 border border-brand-green/25 rounded-full px-3 py-1">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-green opacity-60" />
              <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-brand-green" />
            </span>
            <Wifi size={12} strokeWidth={2.5} />
            EN VIVO
          </span>
        ) : (
          <span className="flex items-center gap-1.5 text-xs font-medium text-content-secondary bg-surface-base border border-surface-border rounded-full px-3 py-1">
            <WifiOff size={12} strokeWidth={1.8} />
            DEMO
          </span>
        )}
      </div>
    </header>
  );
}
