import { useEffect, useRef } from "react";
import { getStoredToken } from "@/services";

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";

export type SocketMessage =
  | { type: "alert"; id: number; camera_id: number; alert_type: string; priority: string; message: string; triggered_at: string }
  | { type: "camera_status"; camera_id: number; status: string }
  | { type: "incident_update"; id: number; status: string };

/** Connects to /ws/alerts and calls onMessage for every broadcast received.
 * Reconnects with a fixed delay if the connection drops (e.g. backend restart).
 */
export function useAlertsSocket(onMessage: (msg: SocketMessage) => void) {
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    const token = getStoredToken();
    if (!token) return;

    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
    let closedByEffectCleanup = false;

    function connect() {
      socket = new WebSocket(`${WS_BASE_URL}/ws/alerts?token=${token}`);
      socket.onmessage = (event) => {
        try {
          onMessageRef.current(JSON.parse(event.data));
        } catch {
          // ignore malformed payloads
        }
      };
      socket.onclose = () => {
        if (!closedByEffectCleanup) {
          reconnectTimer = setTimeout(connect, 3000);
        }
      };
    }

    connect();

    return () => {
      closedByEffectCleanup = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);
}
