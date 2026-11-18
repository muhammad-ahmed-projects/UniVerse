import { useEffect, useState } from "react";

/** Current time (ms), refreshed every `intervalMs` -- for "x seconds ago"
 * labels and spotting a live feed that stopped sending frames. */
export function useNow(intervalMs = 1000): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(timer);
  }, [intervalMs]);
  return now;
}
