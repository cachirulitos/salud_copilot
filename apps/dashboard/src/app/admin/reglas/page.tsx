"use client";

import { useState, useEffect } from "react";
import { BookOpen, AlertCircle, Loader2 } from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Rule {
  code: string;
  description: string;
  affected_types?: string[] | null;
  first?: string;
  condition?: string;
}

export default function ReglasPage() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function fetchRules() {
    try {
      const res = await fetch(`${API}/api/v1/admin/rules`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setRules(data);
    } catch (e) {
      setError("No se pudo conectar con la API al extraer las reglas del motor clínico.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchRules();
  }, []);

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-[var(--color-content-primary)]">Reglas de Operación (Motor Clínico)</h1>
          <p className="text-sm text-[var(--color-content-secondary)] mt-0.5">
            Éstas reglas se aplican dinámicamente y calculan automáticamente el orden de estudios de los pacientes en sus Check-Ins. 
          </p>
        </div>
      </div>

      {loading && (
        <div className="flex items-center gap-3 text-[var(--color-content-secondary)] py-8">
          <Loader2 className="w-5 h-5 animate-spin" />
          <span className="text-sm">Cargando reglas desde master_engine.py...</span>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-3 bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          {error}
        </div>
      )}

      {!loading && !error && (
        <div className="bg-[var(--color-surface-card)] border border-[var(--color-surface-border)] rounded-lg overflow-hidden">
          {rules.length === 0 ? (
            <div className="py-16 flex flex-col items-center gap-3 text-center">
              <BookOpen className="w-10 h-10 text-[var(--color-surface-border)]" />
              <p className="text-[var(--color-content-secondary)] text-sm">
                No hay reglas vinculadas al paquete.
              </p>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-[var(--color-surface-border)]">
              <thead className="bg-[var(--color-surface-base)]">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[var(--color-content-secondary)] uppercase tracking-wider w-24">
                    Código
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[var(--color-content-secondary)] uppercase tracking-wider">
                    Condición Principal
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[var(--color-content-secondary)] uppercase tracking-wider">
                    Atención Prioritaria (Toma 1)
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-[var(--color-content-secondary)] uppercase tracking-wider">
                    Contexto (Áreas Afectadas)
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--color-surface-border)]">
                {rules.map((rule, idx) => (
                  <tr key={`${rule.code}-${idx}`} className="hover:bg-[var(--color-surface-base)]">
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-semibold bg-gray-100 text-gray-800 border border-gray-200">
                        {rule.code}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm font-medium text-[var(--color-content-primary)]">
                        {rule.description}
                        {rule.condition && (
                            <div className="mt-1">
                                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-700 border border-purple-200">
                                   Si cumple: {rule.condition}
                                </span>
                            </div>
                        )}
                    </td>
                    <td className="px-6 py-4 text-sm text-[var(--color-content-secondary)]">
                      {rule.first ? (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200 uppercase">
                          ➔ {rule.first}
                        </span>
                      ) : (
                         "—"
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {rule.affected_types && rule.affected_types.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {rule.affected_types.map((type) => (
                            <span
                              key={type}
                              className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 border border-gray-200"
                            >
                              {type}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <span className="text-xs text-gray-400 italic">Genérico a todos los estudios</span>
                      )}
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
