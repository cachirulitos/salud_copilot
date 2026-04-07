"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  Building2,
  ChevronRight,
  Plus,
  Loader2,
  AlertCircle,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Clinic {
  id: string;
  name: string;
  address: string;
  active: boolean;
}

export default function ClinicasPage() {
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ name: "", address: "" });

  async function fetchClinics() {
    try {
      const res = await fetch(`${API}/api/v1/admin/clinics`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setClinics(data);
    } catch (e) {
      setError("No se pudo conectar con la API. ¿Está corriendo el backend?");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchClinics();
  }, []);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim() || !form.address.trim()) return;
    setSubmitting(true);
    try {
      const res = await fetch(`${API}/api/v1/admin/clinics`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const created = await res.json();
      setClinics((prev) => [...prev, created]);
      setForm({ name: "", address: "" });
      setShowForm(false);
    } catch {
      alert("Error al crear la clínica. Revisa la consola.");
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleActive(clinic: Clinic) {
    try {
      const res = await fetch(`${API}/api/v1/admin/clinics/${clinic.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: !clinic.active }),
      });
      if (!res.ok) throw new Error();
      const updated = await res.json();
      setClinics((prev) => prev.map((c) => (c.id === clinic.id ? updated : c)));
    } catch {
      alert("Error al actualizar la clínica.");
    }
  }

  return (
    <div className="space-y-6 min-w-full">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-content-primary">
            Clínicas
          </h1>
          <p className="text-sm text-content-secondary mt-0.5">
            {clinics.length} clínica{clinics.length !== 1 ? "s" : ""} registrada
            {clinics.length !== 1 ? "s" : ""}
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="inline-flex items-center gap-2 bg-brand-green text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
          <Plus className="w-4 h-4" />
          Nueva clínica
        </button>
      </div>

      {/* Create form */}
      {showForm && (
        <form
          onSubmit={handleCreate}
          className="bg-surface-card border border-surface-border rounded-lg p-5 space-y-4">
          <h2 className="font-semibold text-content-primary">Nueva clínica</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-content-secondary mb-1">
                Nombre *
              </label>
              <input
                type="text"
                required
                value={form.name}
                onChange={(e) =>
                  setForm((f) => ({ ...f, name: e.target.value }))
                }
                placeholder="Ej. Clínica Reforma"
                className="w-full border border-surface-border rounded-lg px-3 py-2 text-sm text-content-primary bg-surface-base focus:outline-none focus:ring-2 focus:ring-brand-green/30"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-content-secondary mb-1">
                Dirección *
              </label>
              <input
                type="text"
                required
                value={form.address}
                onChange={(e) =>
                  setForm((f) => ({ ...f, address: e.target.value }))
                }
                placeholder="Ej. Av. Reforma 123, CDMX"
                className="w-full border border-surface-border rounded-lg px-3 py-2 text-sm text-content-primary bg-surface-base focus:outline-none focus:ring-2 focus:ring-brand-green/30"
              />
            </div>
          </div>
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-2 bg-brand-green text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50">
              {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
              Crear clínica
            </button>
            <button
              type="button"
              onClick={() => setShowForm(false)}
              className="text-sm text-content-secondary px-4 py-2 border border-surface-border rounded-lg hover:text-content-primary transition-colors">
              Cancelar
            </button>
          </div>
        </form>
      )}

      {/* State: loading */}
      {loading && (
        <div className="flex items-center gap-3 text-content-secondary py-8">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">Cargando clínicas...</span>
        </div>
      )}

      {/* State: error */}
      {error && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          {error}
        </div>
      )}

      {/* Clinic list */}
      {!loading && !error && (
        <div className="bg-surface-card border border-surface-border rounded-lg overflow-hidden">
          {clinics.length === 0 ? (
            <div className="py-16 flex flex-col items-center gap-3 text-center">
              <Building2 className="w-10 h-10 text-surface-border" />
              <p className="text-content-secondary text-sm">
                No hay clínicas. Crea la primera.
              </p>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-surface-border">
              <thead className="bg-surface-base">
                <tr>
                  {["Nombre", "Dirección", "Estado", "UUID", ""].map((h) => (
                    <th
                      key={h}
                      className="px-6 py-3 text-left text-xs font-medium text-content-secondary uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {clinics.map((clinic) => (
                  <tr key={clinic.id} className="hover:bg-surface-base">
                    <td className="px-6 py-4 text-sm font-semibold text-content-primary">
                      {clinic.name}
                    </td>
                    <td className="px-6 py-4 text-sm text-content-secondary">
                      {clinic.address}
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => toggleActive(clinic)}
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold border transition-colors ${
                          clinic.active
                            ? "bg-green-100 text-green-700 border-green-300 hover:bg-green-200"
                            : "bg-gray-100 text-gray-500 border-gray-200 hover:bg-gray-200"
                        }`}>
                        {clinic.active ? "Activa" : "Inactiva"}
                      </button>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-xs font-mono text-content-secondary">
                        {clinic.id}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        href={`/admin/clinicas/${clinic.id}`}
                        className="inline-flex items-center gap-1 text-sm text-brand-green hover:underline font-medium">
                        Ver áreas
                        <ChevronRight className="w-4 h-4" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
