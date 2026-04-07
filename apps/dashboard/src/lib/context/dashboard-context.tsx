"use client";

import { createContext, useContext, useState, ReactNode } from "react";

interface DashboardContextValue {
  isConnected: boolean;
  setIsConnected: (v: boolean) => void;
  alertCount: number;
  setAlertCount: (v: number) => void;
}

const DashboardContext = createContext<DashboardContextValue>({
  isConnected: false,
  setIsConnected: () => {},
  alertCount: 0,
  setAlertCount: () => {},
});

export function DashboardProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [isConnected, setIsConnected] = useState(false);
  const [alertCount, setAlertCount] = useState(0);

  return (
    <DashboardContext.Provider
      value={{ isConnected, setIsConnected, alertCount, setAlertCount }}
    >
      {children}
    </DashboardContext.Provider>
  );
}

export function useDashboardContext() {
  return useContext(DashboardContext);
}
