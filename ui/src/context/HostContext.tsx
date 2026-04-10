import { createContext, useContext, useRef } from "react";
import type { ReactNode } from "react";

const HOSTS = ["localhost:8090", "localhost:8091", "localhost:8092"]

interface HostContextType {
  getNextHost: () => string;
}

const HostContext = createContext<HostContextType | undefined>(undefined);

export function HostProvider({ children }: { children: ReactNode }) {
  const indexRef = useRef(0);

  const getNextHost = () => {
    const host = HOSTS[indexRef.current];
    indexRef.current = (indexRef.current + 1) % HOSTS.length;
    return host;
  };

  return (
    <HostContext.Provider value={{ getNextHost }}>
      {children}
    </HostContext.Provider>
  );
}

export function useHost() {
  const context = useContext(HostContext);
  if (!context) {
    throw new Error("useHost must be used within HostProvider");
  }
  return context;
}
