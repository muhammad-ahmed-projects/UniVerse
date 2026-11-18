import { useEffect } from "react";
import { useSearchParams } from "react-router";

/** The id in `?<param>=<id>` (set by the header search), or null. Once the
 * page's rows are rendered (`ready`), the row with id `${param}-${id}` is
 * scrolled into view. */
export function useHighlight(param: string, ready: boolean): number | null {
  const [params] = useSearchParams();
  const raw = params.get(param);
  const id = raw !== null && /^\d+$/.test(raw) ? Number(raw) : null;

  useEffect(() => {
    if (!ready || id === null) return;
    document
      .getElementById(`${param}-${id}`)
      ?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [param, id, ready]);

  return id;
}

/** Row styling for the highlighted search result. */
export const HIGHLIGHT_ROW = "bg-brand-50 dark:bg-brand-500/10";
