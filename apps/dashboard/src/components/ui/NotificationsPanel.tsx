"use client";

export interface StudyChangeNotification {
  id: string;
  visit_id: string;
  old_area: string;
  new_area: string;
  reason: string | null;
  received_at: string;
}

interface NotificationsPanelProps {
  notifications: StudyChangeNotification[];
  onDismiss: (id: string) => void;
}

export default function NotificationsPanel({
  notifications,
  onDismiss,
}: NotificationsPanelProps) {
  return (
    <div className="bg-surface-card border border-surface-border rounded-lg overflow-hidden shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 border-b border-surface-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-content-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
          </svg>
          <span className="text-sm font-semibold text-content-primary">
            Notificaciones
          </span>
        </div>
        {notifications.length > 0 && (
          <span className="text-xs bg-brand-blue/10 text-brand-blue border border-brand-blue/20 px-2 py-0.5 rounded-full font-medium">
            {notifications.length}
          </span>
        )}
      </div>

      {/* Body */}
      <div className="divide-y divide-surface-border max-h-72 overflow-y-auto">
        {notifications.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-content-secondary">
            Sin notificaciones pendientes
          </div>
        ) : (
          notifications.map((n) => (
            <div
              key={n.id}
              className="px-4 py-3 flex gap-3 items-start hover:bg-surface-base transition-colors"
            >
              {/* Icon */}
              <span className="mt-0.5 w-7 h-7 shrink-0 flex items-center justify-center rounded-full bg-brand-blue/10 border border-brand-blue/20">
                <svg className="w-3.5 h-3.5 text-brand-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
              </span>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-semibold text-content-primary mb-0.5">
                  Cambio de estudio recomendado
                </p>
                <p className="text-xs text-content-secondary leading-relaxed">
                  <span className="font-medium text-content-primary">{n.old_area}</span>
                  {" → "}
                  <span className="text-brand-green font-medium">{n.new_area}</span>
                </p>
                {n.reason && (
                  <p className="text-xs text-content-secondary mt-0.5 italic">
                    "{n.reason}"
                  </p>
                )}
                <p className="text-xs text-content-secondary mt-1">
                  {new Date(n.received_at).toLocaleTimeString("es-MX", {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>

              {/* Dismiss */}
              <button
                onClick={() => onDismiss(n.id)}
                className="mt-0.5 text-content-secondary hover:text-content-primary transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
