"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MapPin,
  Bell,
  Clock,
} from "lucide-react";

interface SidebarProps {
  clinicName?: string;
  isConnected?: boolean;
  alertCount?: number;
}

const NAV_ITEMS = [
  { href: "/dashboard",          label: "Dashboard", Icon: LayoutDashboard },
  { href: "/dashboard/areas",    label: "Áreas",     Icon: MapPin },
  { href: "/dashboard/alertas",  label: "Alertas",   Icon: Bell },
  { href: "/dashboard/historial",label: "Historial", Icon: Clock },
];

export default function Sidebar({
  clinicName = "Clínica Demo",
  isConnected = false,
  alertCount = 0,
}: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      style={{ width: 240, boxShadow: "2px 0 8px 0 rgba(0,0,0,0.06)" }}
      className="fixed top-0 left-0 h-screen flex flex-col bg-surface-card border-r border-surface-border z-50"
    >
      {/* ── Logo / brand ───────────────────────────────────── */}
      <div className="px-5 py-6 border-b border-surface-border">
        <p className="text-brand-green font-bold text-lg leading-tight tracking-tight">
          SaludCopilot
        </p>
        <p className="text-content-secondary text-xs mt-0.5">Salud Digna</p>
      </div>

      {/* ── Navigation ─────────────────────────────────────── */}
      <nav className="flex-1 py-3 overflow-y-auto">
        <ul className="space-y-0.5 px-2">
          {NAV_ITEMS.map(({ href, label, Icon }) => {
            const isActive = pathname === href || pathname.startsWith(href + "/");

            return (
              <li key={href}>
                <Link
                  href={href}
                  className={[
                    "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors relative",
                    isActive
                      ? "text-brand-green bg-brand-green/8 font-medium border-l-[3px] border-brand-green pl-[9px]"
                      : "text-content-secondary hover:text-content-primary hover:bg-surface-base border-l-[3px] border-transparent",
                  ].join(" ")}
                >
                  <Icon size={17} strokeWidth={isActive ? 2.5 : 1.8} />
                  <span>{label}</span>

                  {/* Alert badge — only on "Alertas" nav item */}
                  {label === "Alertas" && alertCount > 0 && (
                    <span className="ml-auto bg-alert-red text-white text-xs font-semibold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
                      {alertCount > 99 ? "99+" : alertCount}
                    </span>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* ── Clinic + connection status ──────────────────────── */}
      <div className="px-5 py-4 border-t border-surface-border flex items-center gap-2.5">
        {/* Pulsing dot */}
        <span className="relative flex h-2 w-2 shrink-0">
          {isConnected ? (
            <>
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-green opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-brand-green" />
            </>
          ) : (
            <span className="relative inline-flex h-2 w-2 rounded-full bg-surface-border" />
          )}
        </span>

        <p className="text-content-secondary text-xs truncate">{clinicName}</p>
      </div>
    </aside>
  );
}
