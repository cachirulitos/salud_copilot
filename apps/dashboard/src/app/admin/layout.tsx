import { ReactNode } from "react";
import AdminSidebar from "@/components/layout/AdminSidebar";

export default function AdminLayout({ children }: { children: ReactNode }) {
  return (
    <>
      <AdminSidebar />
      <div style={{ marginLeft: 240 }} className="flex flex-col min-h-screen">
        <header
          style={{ height: 64 }}
          className="sticky top-0 z-40 flex items-center px-6 bg-surface-card border-b border-surface-border"
        >
          <h1 className="text-content-primary font-semibold text-base tracking-tight">
            Administración
          </h1>
        </header>
        <main className="flex-1 p-6">{children}</main>
      </div>
    </>
  );
}
