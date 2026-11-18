import { useCallback, useEffect, useState } from "react";
import { type CameraRunner, runnersApi } from "@/services";
import { useAlertsSocket } from "./use-alerts-socket";

/** Monitoring state of every camera, keyed by camera id. Refreshes when a
 * camera_runner message arrives (start/stop/crash) and every few seconds,
 * so script logs and exits show up without a page reload. */
export function useRunners(pollMs = 3000): {
  runners: Map<number, CameraRunner>;
  refresh: () => void;
} {
  const [runners, setRunners] = useState<Map<number, CameraRunner>>(
    () => new Map(),
  );

  const refresh = useCallback(() => {
    runnersApi
      .list()
      .then((list) => setRunners(new Map(list.map((r) => [r.camera_id, r]))))
      .catch(() => undefined); // keep the last known state; the next poll retries
  }, []);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, pollMs);
    return () => clearInterval(timer);
  }, [refresh, pollMs]);

  useAlertsSocket((msg) => {
    if (msg.type === "camera_runner") refresh();
  });

  return { runners, refresh };
}
