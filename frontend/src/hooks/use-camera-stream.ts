import { useEffect, useState } from "react";
import { getCurrentUser, getStoredToken } from "@/services";
import { WS_BASE_URL } from "./use-alerts-socket";

// Same backoff as the alerts socket: 1s, 2s, 4s ... capped at 30s.
const RECONNECT_BASE_MS = 1000;
const RECONNECT_MAX_MS = 30000;

type FrameListener = (frame: Blob) => void;

// One /ws/stream connection per tab carries every camera the page shows
// (one MJPEG <img> per camera would hit the browser's ~6 connections per
// host limit and starve the dashboard's API calls). Each binary message is
// a 4-byte big-endian camera id followed by the JPEG.
const frameListeners = new Map<number, Set<FrameListener>>();
let socket: WebSocket | null = null;
let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
let failedAttempts = 0;

function sendSubscriptions(): void {
  if (socket?.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ subscribe: [...frameListeners.keys()] }));
  }
}

function connect(): void {
  const token = getStoredToken();
  if (!token || frameListeners.size === 0) return;

  const ws = new WebSocket(
    `${WS_BASE_URL}/ws/stream?token=${encodeURIComponent(token)}`,
  );
  ws.binaryType = "arraybuffer";
  socket = ws;
  ws.onopen = () => {
    failedAttempts = 0;
    sendSubscriptions();
  };
  ws.onmessage = (event: MessageEvent<ArrayBuffer | string>) => {
    if (typeof event.data === "string" || event.data.byteLength < 5) return;
    const cameraId = new DataView(event.data).getUint32(0);
    const listeners = frameListeners.get(cameraId);
    if (!listeners) return;
    const frame = new Blob([event.data.slice(4)], { type: "image/jpeg" });
    listeners.forEach((listener) => listener(frame));
  };
  ws.onclose = () => {
    if (socket !== ws) return;
    socket = null;
    if (frameListeners.size === 0 || reconnectTimer !== null) return;
    // As in use-alerts-socket: a rejected token looks like a network drop,
    // so re-check the session (a 401 logs the user out and unmounts us).
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

function subscribeFrames(cameraId: number, listener: FrameListener) {
  let listeners = frameListeners.get(cameraId);
  const isNewCamera = !listeners;
  if (!listeners) {
    listeners = new Set();
    frameListeners.set(cameraId, listeners);
  }
  listeners.add(listener);
  if (!socket && reconnectTimer === null) connect();
  else if (isNewCamera) sendSubscriptions();

  return () => {
    listeners.delete(listener);
    if (listeners.size > 0) return;
    frameListeners.delete(cameraId);
    if (frameListeners.size > 0) {
      sendSubscriptions();
      return;
    }
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer);
      reconnectTimer = null;
    }
    socket?.close();
    socket = null;
  };
}

export interface CameraFrame {
  /** Object URL of the latest JPEG, valid while the component is mounted. */
  src: string;
  /** Date.now() when it arrived; compare with the clock to spot a stalled feed. */
  receivedAt: number;
}

/** The latest live-view frame of one camera, or null until one arrives. */
export function useCameraFrame(cameraId: number): CameraFrame | null {
  const [frame, setFrame] = useState<CameraFrame | null>(null);

  useEffect(() => {
    let currentUrl: string | null = null;
    const unsubscribe = subscribeFrames(cameraId, (blob) => {
      const url = URL.createObjectURL(blob);
      // The <img> keeps the decoded previous frame until the new one loads,
      // so the old URL can be released right away.
      if (currentUrl) URL.revokeObjectURL(currentUrl);
      currentUrl = url;
      setFrame({ src: url, receivedAt: Date.now() });
    });
    return () => {
      unsubscribe();
      if (currentUrl) URL.revokeObjectURL(currentUrl);
    };
  }, [cameraId]);

  return frame;
}
