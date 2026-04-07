"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Building2, MapPin, ScrollText, Activity, LayoutDashboard } from "lucide-react";

const NAV_ITEMS = [
  { href: "/admin/clinicas",  label: "Clínicas",  Icon: Building2 },
  { href: "/admin/reglas",    label: "Reglas",    Icon: ScrollText },
];

export default function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside
      style={{ width: 240, boxShadow: "2px 0 8px 0 rgba(0,0,0,0.06)" }}
      className="fixed top-0 left-0 h-screen flex flex-col bg-surface-card border-r border-surface-border z-50"
    >
      {/* ── Brand ──────────────────────────────────────────────── */}
      <div className="px-5 py-6 border-b border-surface-border">
        <div className="flex items-center gap-2 mb-0.5">
          <Activity className="w-4 h-4 text-brand-green" strokeWidth={2.5} />
          <p className="text-brand-green font-bold text-lg leading-tight tracking-tight">
            SaludCopilot
          </p>
        </div>
        <p className="text-content-secondary text-xs mt-0.5 pl-6">Panel Admin</p>
      </div>

      {/* ── Nav ────────────────────────────────────────────────── */}
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
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {/* ── Link back to manager dashboard ─────────────────────── */}
      <div className="px-3 py-4 border-t border-surface-border">
        <Link
          href="/dashboard"
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-content-secondary hover:text-content-primary hover:bg-surface-base transition-colors"
        >
          <LayoutDashboard size={17} strokeWidth={1.8} />
          <span>Panel Gerente</span>
        </Link>
      </div>
    </aside>
  );
}
