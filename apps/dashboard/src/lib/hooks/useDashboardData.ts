import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { DashboardWebSocketClient, DashboardEvent } from "../websocket-client";

const CHART_WINDOW = 12;

export function useDashboardData(
  clinicId: string,
  onConnectionChange?: (connected: boolean) => void,
  onAlertCountChange?: (count: number) => void,
) {
  const [areas, setAreas] = useState<any[]>([]);
  const [activeVisits, setActiveVisits] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [waitTimeHistory, setWaitTimeHistory] = useState<any>({
    labels: [],
    series: {},
  });
  const [isConnected, setIsConnected] = useState(false);

  const wsClientRef = useRef<DashboardWebSocketClient | null>(null);

  // Derived summary
  const summary = useMemo(() => {
    const totalWaiting = areas.reduce(
      (s, a) => s + (a.current_queue_length || 0),
      0,
    );
    const totalPeople = activeVisits.length;
    const areasAtRisk = areas.filter(
      (a) => a.status === "warning" || a.status === "saturated",
    ).length;
    const avgWait =
      areas.length > 0
        ? Math.round(
            areas.reduce((s, a) => s + (a.estimated_wait_minutes || 0), 0) /
              areas.length,
          )
        : 0;

    return {
      total_active_visits: activeVisits.length,
      total_waiting_patients: activeVisits.filter((v) => v.status === "pending")
        .length,
      average_wait_minutes: avgWait,
      areas_at_risk: areasAtRisk,
    };
  }, [areas, activeVisits]);

  useEffect(() => {
    onAlertCountChange?.(
      alerts.filter((a) => a.severity === "critical").length,
    );
  }, [alerts, onAlertCountChange]);

  const handleWebSocketEvent = useCallback((event: any) => {
    switch (event.event) {
      case "overview_snapshot":
        console.log(event.data);
        setAreas(event.data.areas || []);
        setActiveVisits(event.data.active_visits || []);
        setAlerts(event.data.alerts || []);
        break;

      case "wait_time_updated":
        setAreas((prev) => {
          const updated = prev.map((area) =>
            area.area_id === event.area_id
              ? {
                  ...area,
                  estimated_wait_minutes: event.data.estimated_minutes,
                  people_in_area: event.data.people_count,
                }
              : area,
          );

          // Slide chart window
          const targetArea = updated.find((a) => a.area_id === event.area_id);
          if (targetArea) {
            setWaitTimeHistory((hist: any) => {
              if (!hist || !hist.series) return hist;
              const existingSeries =
                hist.series[targetArea.area_name] ??
                Array(CHART_WINDOW).fill(0);
              const newSeries = [
                ...existingSeries.slice(1),
                event.data.estimated_minutes,
              ];
              const nowLabel = new Date().toLocaleTimeString("es-MX", {
                hour: "2-digit",
                minute: "2-digit",
                hour12: false,
              });

              // Only push label if we are pushing real data
              const newLabels = [
                ...(hist.labels || Array(CHART_WINDOW).fill("")).slice(1),
                nowLabel,
              ];
              return {
                labels: newLabels,
                series: { ...hist.series, [targetArea.area_name]: newSeries },
              };
            });
          }

          return updated;
        });
        break;

      case "visit_updated":
        // Optional handling if needed, usually we would just rewrite active_visits
        break;

      case "queue_changed":
        setAreas((prev) =>
          prev.map((area) =>
            area.area_id === event.area_id
              ? {
                  ...area,
                  current_queue_length: event.data.current_queue_length,
                  status: event.data.status ?? area.status,
                }
              : area,
          ),
        );
        break;

      case "alert": {
        const newAlert = event.data;
        setAlerts((prev) => [newAlert, ...prev].slice(0, 50));
        break;
      }
      case "checkin_created":
        if (event.data.is_transfer) {
          setActiveVisits((prev) =>
            prev.map((v) =>
              v.visit_id === event.data.visit_id
                ? { ...v, current_area_name: event.data.current_area }
                : v
            )
          );
        } else {
          setActiveVisits((prev) => {
            const exists = prev.find(v => v.visit_id === event.data.visit_id);
            if (exists) return prev;
            return [event.data, ...prev];
          });
        }
        break;

      case "visit_step_updated":
        setActiveVisits((prev) =>
          prev.map((v) =>
            v.visit_id === event.data.visit_id
              ? {
                  ...v,
                  visit_status: event.data.visit_status,
                  current_step: event.data.next_step ?? null,
                  completed_steps: [
                    ...(v.completed_steps || []),
                    event.data.completed_step,
                  ],
                }
              : v,
          ),
        );
        break;
    }
  }, []);

  const handleConnectionStatus = useCallback(
    (status: boolean) => {
      setIsConnected(status);
      onConnectionChange?.(status);
    },
    [onConnectionChange],
  );

  useEffect(() => {
    if (!clinicId) return;

    // Fetch initial history
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/dashboard/${clinicId}/history`)
      .then((r) => r.json())
      .then((data) => {
        if (data.labels && data.series) {
          setWaitTimeHistory(data);
        }
      })
      .catch(console.error);

    const client = new DashboardWebSocketClient();
    wsClientRef.current = client;
    client.connect(
      clinicId,
      handleWebSocketEvent as any,
      handleConnectionStatus,
    );

    return () => {
      client.disconnect();
    };
  }, [clinicId, handleWebSocketEvent, handleConnectionStatus]);

  return {
    areas,
    activeVisits,
    summary,
    alerts,
    isConnected,
    waitTimeHistory,
    clearResolvedAlerts: () =>
      setAlerts((prev) => prev.filter((a) => a.severity === "critical")),
  };
}
