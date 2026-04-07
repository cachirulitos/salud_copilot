import Link from "next/link";
import {
  Camera,
  BrainCircuit,
  MessageCircle,
  ArrowRight,
  Activity,
} from "lucide-react";

const FEATURES = [
  {
    Icon: Camera,
    title: "Monitoreo por visión artificial",
    description:
      "Cámaras IP con detección YOLOv8 cuentan personas en cada área en tiempo real. Sin apps, sin fricción para el paciente.",
    color: "#008A4B",
  },
  {
    Icon: BrainCircuit,
    title: "Predicción de tiempos de espera",
    description:
      "Modelo RandomForest entrenado con datos históricos de Salud Digna estima el tiempo de espera por área y tipo de estudio.",
    color: "#005B9F",
  },
  {
    Icon: MessageCircle,
    title: "Alertas por WhatsApp",
    description:
      "El paciente recibe su tiempo estimado y alertas de cambio directamente en WhatsApp. Cero descargas, cero registros.",
    color: "#7C3AED",
  },
];

const STATS = [
  { value: "< 5s", label: "Latencia de actualización" },
  { value: "255", label: "Clínicas en la red" },
  { value: "YOLOv8m", label: "Modelo de detección" },
  { value: "100%", label: "Sin app requerida" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white text-gray-900 font-sans">
      {/* ── Nav ──────────────────────────────────────────────────────────── */}
      <nav className="sticky top-0 z-50 border-b border-gray-100 bg-white/90 backdrop-blur-sm">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Activity className="w-5 h-5 text-brand-green" strokeWidth={2.5} />
            <span className="font-bold text-lg tracking-tight text-gray-900">
              SaludCopilot
            </span>
            <span className="text-xs text-gray-400 font-normal ml-1">
              by Cachirulitos
            </span>
          </div>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 bg-brand-green text-white text-sm font-semibold px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
            Entrar al panel
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </nav>

      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="max-w-6xl mx-auto px-6 pt-24 pb-20 text-center">
        <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-brand-green bg-green-50 border border-green-200 rounded-full px-3 py-1 mb-6">
          <span className="relative flex h-1.5 w-1.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand-green opacity-60" />
            <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-brand-green" />
          </span>
          Operando en tiempo real
        </span>

        <h1 className="text-5xl font-extrabold tracking-tight text-gray-900 max-w-3xl mx-auto leading-tight">
          Menos espera.
          <br />
          <span className="text-brand-green">Más atención.</span>
        </h1>

        <p className="mt-6 text-xl text-gray-500 max-w-2xl mx-auto leading-relaxed">
          Plataforma de operaciones en tiempo real para clínicas Salud Digna.
          Visión artificial + IA predicen tiempos de espera y alertan por
          WhatsApp antes de que el paciente lo pregunte.
        </p>

        <div className="mt-10 flex items-center justify-center gap-4">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 bg-brand-green text-white font-semibold px-6 py-3 rounded-xl text-base hover:bg-green-700 transition-colors shadow-sm">
            Ver dashboard en vivo
            <ArrowRight className="w-4 h-4" />
          </Link>
          <a
            href="#como-funciona"
            className="inline-flex items-center gap-2 text-gray-600 font-medium px-6 py-3 rounded-xl text-base border border-gray-200 hover:border-gray-300 hover:text-gray-900 transition-colors">
            Cómo funciona
          </a>
        </div>
      </section>

      {/* ── Stats strip ──────────────────────────────────────────────────── */}
      <section className="border-y border-gray-100 bg-gray-50">
        <div className="max-w-6xl mx-auto px-6 py-10 grid grid-cols-4 divide-x divide-gray-200">
          {STATS.map(({ value, label }) => (
            <div key={label} className="px-8 first:pl-0 last:pr-0 text-center">
              <p className="text-3xl font-extrabold text-gray-900">{value}</p>
              <p className="text-sm text-gray-500 mt-1">{label}</p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Features ─────────────────────────────────────────────────────── */}
      <section id="como-funciona" className="max-w-6xl mx-auto px-6 py-24">
        <div className="text-center mb-14">
          <h2 className="text-3xl font-bold text-gray-900">
            Tres capas de inteligencia
          </h2>
          <p className="text-gray-500 mt-3 text-lg max-w-xl mx-auto">
            Cada componente resuelve un problema real de operación clínica.
          </p>
        </div>

        <div className="grid grid-cols-3 gap-6">
          {FEATURES.map(({ Icon, title, description, color }) => (
            <div
              key={title}
              className="bg-white border border-gray-100 rounded-2xl p-7 shadow-sm hover:shadow-md transition-shadow">
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center mb-5"
                style={{ backgroundColor: `${color}15` }}>
                <Icon className="w-5 h-5" style={{ color }} strokeWidth={2} />
              </div>
              <h3 className="font-semibold text-gray-900 text-base mb-2">
                {title}
              </h3>
              <p className="text-sm text-gray-500 leading-relaxed">
                {description}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA section ──────────────────────────────────────────────────── */}
      <section className="bg-brand-green">
        <div className="max-w-6xl mx-auto px-6 py-20 text-center">
          <h2 className="text-3xl font-bold text-white">Listo para operar</h2>
          <p className="text-green-100 mt-3 text-lg max-w-lg mx-auto">
            El panel muestra datos en vivo de todas las áreas de tu clínica.
          </p>
          <Link
            href="/dashboard"
            className="mt-8 inline-flex items-center gap-2 bg-white text-brand-green font-bold px-7 py-3.5 rounded-xl text-base hover:bg-green-50 transition-colors shadow-sm">
            Abrir panel operativo
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────────────────── */}
      <footer className="border-t border-gray-100 bg-white">
        <div className="max-w-6xl mx-auto px-6 py-8 flex items-center justify-between text-sm text-gray-400">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-brand-green" />
            <span className="font-semibold text-gray-600">SaludCopilot</span>
          </div>
          <span>Hackathon GeniusArena 2026 · Salud Digna</span>
        </div>
      </footer>
    </div>
  );
}
