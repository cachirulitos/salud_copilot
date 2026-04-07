"use client";

import { ReactNode } from "react";
import { DashboardProvider, useDashboardContext } from "@/lib/context/dashboard-context";
import Sidebar from "@/components/layout/Sidebar";
import TopBar from "@/components/layout/TopBar";

function DashboardShell({ children }: { children: ReactNode }) {
  const { isConnected, alertCount } = useDashboardContext();

  return (
    <>
      <Sidebar
        clinicName="Clínica Demo"
        isConnected={isConnected}
        alertCount={alertCount}
      />
      <div style={{ marginLeft: 240 }} className="flex flex-col min-h-screen">
        <TopBar pageTitle="Panel Operativo" isConnected={isConnected} />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </>
  );
}

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <DashboardProvider>
      <DashboardShell>{children}</DashboardShell>
    </DashboardProvider>
  );
}
