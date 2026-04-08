import {
  createContext,
  useContext,
  useEffect,
  useRef,
  useState,
  ReactNode,
} from "react";
import { useHost } from "./HostContext";
import { useAuth } from "./AuthContext";
import type { Notification } from "../types";

const RECONNECT_BASE_DELAY_MILLISECONDS = 1_000;
const MAX_RECONNECT_ATTEMPTS = 5;

type ConnectionState = "connected" | "disconnected" | "error";

type Listener = (message: Notification) => void;

interface WebSocketContextType {
  notifications: any[];
  status: ConnectionState;
  subscribe: (fn: Listener) => (() => void);
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export function WebSocketProvider({ children }: { children: ReactNode }) {
  const { getNextHost } = useHost();
  const { user } = useAuth();
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const lastErrorTimeRef = useRef<number>(0);

  const [notifications, setNotifications] = useState<any[]>([]);
  const seenMessageIds = useRef<Set<string>>(new Set());
  const [status, setStatus] = useState<ConnectionState>("disconnected");

  const listeners = useRef<Set<Listener>>(new Set());
  const subscribe = (fn: Listener) => {
    listeners.current.add(fn);
    return () => listeners.current.delete(fn);
  };

  useEffect(() => {
    if (!user) {
      wsRef.current?.close();
      wsRef.current = null;
      setStatus("disconnected");
      return;
    }

    const connect = () => {
      const host = getNextHost();
      const url = `ws://${host}/ws?token=${user.token}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        setStatus("connected");
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as Notification;
          if (!data?.message_id || seenMessageIds.current.has(data.message_id)) {
		    return;
		  }

          seenMessageIds.current.add(data.message_id);
          setNotifications((prev) => [...prev, data]);
          listeners.current.forEach(fn => fn(data));
        } catch (e) {
          console.error(`Failed to parse notification: ${e}`)
        }
      };

      ws.onclose = () => {
        setStatus("disconnected");

        const now = Date.now();
        if (now - lastErrorTimeRef.current < 5000) {
          setStatus("error");
          return;
        }
        lastErrorTimeRef.current = now;

        if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttemptsRef.current += 1;
          const delay = RECONNECT_BASE_DELAY_MILLISECONDS * reconnectAttemptsRef.current;
          setTimeout(connect, delay);
        } else {
          setStatus("error");
        }
      };

      ws.onerror = () => {
        setStatus("disconnected");
      };
    };

    connect();

    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [user, getNextHost]);

  return (
    <WebSocketContext.Provider value={{ notifications, status, subscribe }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket() {
  const ctx = useContext(WebSocketContext);
  if (!ctx) {
    throw new Error("useWebSocket must be used within provider");
  }
  return ctx;
}
