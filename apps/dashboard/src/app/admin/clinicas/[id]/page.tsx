"use client";

import { useState, useEffect } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ChevronLeft, Plus, Loader2, AlertCircle } from "lucide-react";
import { QRCard } from "@/components/admin/QRCard";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const STUDY_TYPES = [
  "laboratorio",
  "ultrasonido",
  "rayos_x",
  "electrocardiograma",
  "papanicolaou",
  "densitometria",
  "tomografia",
  "resonancia",
  "mastografia",
  "nutricion",
];

interface Area {
  id: string;
  name: string;
  study_type: string;
  simultaneous_capacity: number;
  active: boolean;
  navigation_instructions: string | null;
}

interface Clinic {
  id: string;
  name: string;
  address: string;
  active: boolean;
}

export default function ClinicDetailPage() {
  const { id: clinicId } = useParams<{ id: string }>();

  const [clinic, setClinic] = useState<Clinic | null>(null);
  const [areas, setAreas] = useState<Area[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({
    name: "",
    study_type: "laboratorio",
    simultaneous_capacity: 2,
    navigation_instructions: "",
  });

  async function fetchData() {
    setLoading(true);
    try {
      const [clinicsRes, areasRes] = await Promise.all([
        fetch(`${API}/api/v1/admin/clinics`),
        fetch(`${API}/api/v1/admin/clinics/${clinicId}/areas`),
      ]);
      if (!clinicsRes.ok || !areasRes.ok) throw new Error();
      const allClinics: Clinic[] = await clinicsRes.json();
      const found = allClinics.find((c) => c.id === clinicId) ?? null;
      setClinic(found);
      setAreas(await areasRes.json());
    } catch {
      setError("No se pudo conectar con la API.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchData();
  }, [clinicId]);

  async function handleCreateArea(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await fetch(`${API}/api/v1/admin/areas`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          clinic_id: clinicId,
          simultaneous_capacity: Number(form.simultaneous_capacity),
          navigation_instructions: form.navigation_instructions || null,
        }),
      });
      if (!res.ok) throw new Error();
      const created: Area = await res.json();
      setAreas((prev) => [...prev, created]);
      setForm({
        name: "",
        study_type: "laboratorio",
        simultaneous_capacity: 2,
        navigation_instructions: "",
      });
      setShowForm(false);
    } catch {
      alert("Error al crear el área.");
    } finally {
      setSubmitting(false);
    }
  }

  async function toggleAreaActive(area: Area) {
    try {
      const res = await fetch(`${API}/api/v1/admin/areas/${area.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active: !area.active }),
      });
      if (!res.ok) throw new Error();
      const updated: Area = await res.json();
      setAreas((prev) =>
        prev.map((a) => (a.id === area.id ? { ...a, ...updated } : a)),
      );
    } catch {
      alert("Error al actualizar el área.");
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-3 text-content-secondary py-8">
        <Loader2 className="w-5 h-5 animate-spin" />
        <span className="text-sm">Cargando...</span>
      </div>
    );
  }

  if (error || !clinic) {
    return (
      <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm max-w-xl">
        <AlertCircle className="w-5 h-5 shrink-0" />
        {error ?? "Clínica no encontrada."}
      </div>
    );
  }

  return (
    <div className="space-y-6 min-w-full">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2">
        <Link
          href="/admin/clinicas"
          className="flex items-center gap-1 text-sm text-content-secondary hover:text-content-primary transition-colors">
          <ChevronLeft className="w-4 h-4" />
          Clínicas
        </Link>
        <span className="text-surface-border">/</span>
        <span className="text-sm font-semibold text-content-primary">
          {clinic.name}
        </span>
      </div>

      {/* Clinic info */}
      <div className="bg-surface-card border border-surface-border rounded-lg p-5">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-content-primary">
              {clinic.name}
            </h1>
            <p className="text-sm text-content-secondary mt-0.5">
              {clinic.address}
            </p>
          </div>
          <span
            className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${
              clinic.active
                ? "bg-green-100 text-green-700 border-green-300"
                : "bg-gray-100 text-gray-500 border-gray-200"
            }`}>
            {clinic.active ? "Activa" : "Inactiva"}
          </span>
        </div>
        <p className="text-xs text-content-secondary font-mono mt-3">
          ID: {clinic.id}
        </p>
      </div>

      {/* Areas header */}
      <div className="flex items-center justify-between">
        <h2 className="font-semibold text-content-primary">
          Áreas clínicas
          <span className="ml-2 text-sm font-normal text-content-secondary">
            ({areas.length})
          </span>
        </h2>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="inline-flex items-center gap-2 bg-brand-green text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
          <Plus className="w-4 h-4" />
          Nueva área
        </button>
      </div>

      {/* Create area form */}
      {showForm && (
        <form
          onSubmit={handleCreateArea}
          className="bg-surface-card border border-surface-border rounded-lg p-5 space-y-4">
          <h3 className="font-semibold text-content-primary">
            Nueva área clínica
          </h3>
          <div className="grid grid-cols-3 gap-4">
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
                placeholder="Ej. Laboratorio 1"
                className="w-full border border-surface-border rounded-lg px-3 py-2 text-sm bg-surface-base focus:outline-none focus:ring-2 focus:ring-brand-green/30"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-content-secondary mb-1">
                Tipo de estudio *
              </label>
              <select
                value={form.study_type}
                onChange={(e) =>
                  setForm((f) => ({ ...f, study_type: e.target.value }))
                }
                className="w-full border border-surface-border rounded-lg px-3 py-2 text-sm bg-surface-base focus:outline-none focus:ring-2 focus:ring-brand-green/30">
                {STUDY_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-content-secondary mb-1">
                Capacidad simultánea *
              </label>
              <input
                type="number"
                min={1}
                max={20}
                required
                value={form.simultaneous_capacity}
                onChange={(e) =>
                  setForm((f) => ({
                    ...f,
                    simultaneous_capacity: Number(e.target.value),
                  }))
                }
                className="w-full border border-surface-border rounded-lg px-3 py-2 text-sm bg-surface-base focus:outline-none focus:ring-2 focus:ring-brand-green/30"
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-content-secondary mb-1">
              Instrucciones de navegación (para bot)
            </label>
            <input
              type="text"
              value={form.navigation_instructions}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  navigation_instructions: e.target.value,
                }))
              }
              placeholder="Ej. Sube al 2do piso, puerta azul a la derecha"
              className="w-full border border-surface-border rounded-lg px-3 py-2 text-sm bg-surface-base focus:outline-none focus:ring-2 focus:ring-brand-green/30"
            />
          </div>
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={submitting}
              className="inline-flex items-center gap-2 bg-brand-green text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors">
              {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
              Crear área
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

      {/* Areas grid with QR */}
      {areas.length === 0 ? (
        <div className="bg-surface-card border border-surface-border rounded-lg py-16 flex flex-col items-center gap-3">
          <p className="text-content-secondary text-sm">
            No hay áreas. Crea la primera.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-3 gap-4">
          {areas.map((area) => (
            <div key={area.id} className="space-y-3">
              {/* Area info row */}
              <div className="bg-surface-card border border-surface-border rounded-lg p-4">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-sm text-content-primary">
                    {area.name}
                  </h3>
                  <button
                    onClick={() => toggleAreaActive(area)}
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold border transition-colors ${
                      area.active
                        ? "bg-green-100 text-green-700 border-green-300 hover:bg-green-200"
                        : "bg-gray-100 text-gray-500 border-gray-200 hover:bg-gray-200"
                    }`}>
                    {area.active ? "Activa" : "Inactiva"}
                  </button>
                </div>
                <p className="text-xs text-content-secondary">
                  {area.study_type} · cap. {area.simultaneous_capacity}
                </p>
                {area.navigation_instructions && (
                  <p className="text-xs text-content-secondary mt-1 italic">
                    {area.navigation_instructions}
                  </p>
                )}
              </div>

              {/* QR card */}
              <QRCard
                areaId={area.id}
                areaName={area.name}
                clinicId={clinicId}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
