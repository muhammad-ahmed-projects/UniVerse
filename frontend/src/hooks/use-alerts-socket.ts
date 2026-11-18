import { useEffect, useRef } from "react";
import { type AlertImage, getCurrentUser, getStoredToken } from "@/services";

export const WS_BASE_URL =
  import.meta.env.VITE_WS_BASE_URL ?? "ws://127.0.0.1:8000";
// Exponential backoff: 1s, 2s, 4s ... capped at 30s, reset on a successful open.
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

export type SocketMessage =
  | {
      type: "alert";
      id: number;
      camera_id: number;
      alert_type: string;
      priority: string;
      message: string;
      triggered_at: string;
    }
  | { type: "camera_status"; camera_id: number; status: string }
  | { type: "incident_update"; id: number; status: string }
  | {
      type: "alert_image";
      alert_id: number;
      incident_id: number | null;
      image: AlertImage;
    }
  | {
      type: "person_seen";
      person_id: number;
      camera_id: number;
      similarity: number;
      seen_at: string;
    };

type Listener = (msg: SocketMessage) => void;

// One shared connection per browser tab, opened when the first component
// subscribes and closed when the last one unsubscribes.
const listeners = new Set<Listener>();
let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let failedAttempts = 0;

function connect(): void {
  const token = getStoredToken();
  if (!token || listeners.size === 0) return;

  const ws = new WebSocket(
    `${WS_BASE_URL}/ws/alerts?token=${encodeURIComponent(token)}`,
  );
  socket = ws;
  ws.onmessage = (event: MessageEvent<string>) => {
    let msg: SocketMessage;
    try {
      msg = JSON.parse(event.data) as SocketMessage;
    } catch {
      return; // ignore malformed payloads
    }
    listeners.forEach((listener) => listener(msg));
  };
  ws.onopen = () => {
    failedAttempts = 0;
  };
  ws.onclose = () => {
    // Ignore closes of sockets that were intentionally closed or already replaced.
    if (socket !== ws) return;
    socket = null;
    if (listeners.size === 0 || reconnectTimer !== null) return;

    // A rejected token looks the same as a network drop from here (the server
    // refuses the handshake). Re-checking the session over HTTP lets the API
    // client's 401 handling log the user out, which unmounts every subscriber
    // and stops the reconnect loop.
    getCurrentUser().catch(() => undefined);

    const delay = Math.min(
      RECONNECT_BASE_MS * 2 ** failedAttempts,
      RECONNECT_MAX_MS,
    );
    failedAttempts += 1;
    reconnectTimer = setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, delay);
  };
}

function subscribe(listener: Listener): () => void {
  listeners.add(listener);
  if (!socket && reconnectTimer === null) connect();

  return () => {
    listeners.delete(listener);
    if (listeners.size === 0) {
      if (reconnectTimer !== null) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      socket?.close();
      socket = null;
    }
  };
}

/** Calls onMessage for every /ws/alerts broadcast while the component is mounted.
 * All subscribers in a tab share one WebSocket, which reconnects after a drop
 * (e.g. backend restart).
 */
export function useAlertsSocket(onMessage: Listener): void {
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  });

  useEffect(() => subscribe((msg) => onMessageRef.current(msg)), []);
}
