import { Badge } from "@/components/ui/badge";
import { Field } from "@/components/ui/field";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupInput,
} from "@/components/ui/input-group";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/contexts";
import { useTranslations } from "@/i18n";
import { SearchIcon } from "@/icons";
import {
  alertsApi,
  camerasApi,
  incidentsApi,
  peopleApi,
  type Alert,
  type Camera,
  type Incident,
  type Person,
} from "@/services";
import { cn } from "@/utils";
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router";

interface Result {
  group: string;
  label: string;
  detail?: string;
  to: string;
}

const PAGES: {
  label: string;
  to: string;
  keywords: string;
  adminOnly?: boolean;
}[] = [
  { label: "Dashboard", to: "/", keywords: "home overview summary" },
  { label: "Live View", to: "/live", keywords: "video stream feed watch" },
  {
    label: "Cameras",
    to: "/cameras",
    keywords: "camera monitoring start stop",
  },
  { label: "Alerts", to: "/surveillance-alerts", keywords: "events evidence" },
  { label: "Incidents", to: "/incidents", keywords: "acknowledge resolve" },
  {
    label: "Registered People",
    to: "/people",
    keywords: "faces register person",
  },
  {
    label: "Settings",
    to: "/settings",
    keywords: "thresholds roi loitering tamper face",
  },
  {
    label: "Users",
    to: "/users",
    keywords: "accounts roles password",
    adminOnly: true,
  },
  { label: "My profile", to: "/profile", keywords: "account password change" },
];
const MAX_PER_GROUP = 5;

interface SearchData {
  cameras: Camera[];
  people: Person[];
  alerts: Alert[];
  incidents: Incident[];
}

const matches = (
  query: string,
  ...fields: (string | number | null | undefined)[]
) =>
  fields.some(
    (f) =>
      f !== null && f !== undefined && String(f).toLowerCase().includes(query),
  );

/** Header search: pages, cameras, people, recent alerts and incidents. Data
 * is fetched when the box is first focused, then searched in the browser. */
export function GlobalSearch() {
  const t = useTranslations("header");
  const navigate = useNavigate();
  const { user } = useAuth();
  const inputRef = useRef<HTMLInputElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [data, setData] = useState<SearchData | null>(null);
  const [loading, setLoading] = useState(false);
  const isMac =
    typeof navigator !== "undefined" && /Mac/i.test(navigator.platform);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        inputRef.current?.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, []);

  const loadData = () => {
    if (data || loading) return;
    setLoading(true);
    // Each source fails independently: a failed list just isn't searched.
    void Promise.all([
      camerasApi.list().catch(() => []),
      peopleApi.list().catch(() => []),
      alertsApi.list({ limit: 200 }).catch(() => []),
      incidentsApi.list().catch(() => []),
    ]).then(([cameras, people, alerts, incidents]) => {
      setData({ cameras, people, alerts, incidents });
      setLoading(false);
    });
  };

  const results = useMemo<Result[]>(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];
    const out: Result[] = [];
    const add = (items: Result[]) => out.push(...items.slice(0, MAX_PER_GROUP));

    add(
      PAGES.filter(
        (p) =>
          (!p.adminOnly || user?.role === "admin") &&
          matches(q, p.label, p.keywords),
      ).map((p) => ({ group: "Pages", label: p.label, to: p.to })),
    );
    if (data) {
      add(
        data.cameras
          .filter((c) => matches(q, c.name, c.location, `#${c.id}`))
          .map((c) => ({
            group: "Cameras",
            label: c.name,
            detail: `${c.status}${c.location ? ` · ${c.location}` : ""}`,
            to: `/cameras?camera=${c.id}`,
          })),
      );
      add(
        data.people
          .filter((p) => matches(q, p.name, p.notes))
          .map((p) => ({
            group: "People",
            label: p.name,
            detail: `${p.face_count} face photo${p.face_count === 1 ? "" : "s"}`,
            to: `/people?person=${p.id}`,
          })),
      );
      add(
        data.alerts
          .filter((a) => matches(q, a.alert_type, a.message))
          .map((a) => ({
            group: "Alerts",
            label: a.alert_type,
            detail: `camera #${a.camera_id} · ${new Date(a.triggered_at).toLocaleString()}`,
            to: `/surveillance-alerts?alert=${a.id}`,
          })),
      );
      add(
        data.incidents
          .filter((i) => matches(q, i.title, i.description, `#${i.id}`))
          .map((i) => ({
            group: "Incidents",
            label: `#${i.id} ${i.title}`,
            detail: i.status,
            to: `/incidents?incident=${i.id}`,
          })),
      );
    }
    return out;
  }, [query, data, user?.role]);

  const close = () => {
    setOpen(false);
    setActive(0);
  };

  const go = (result: Result) => {
    void navigate(result.to);
    setQuery("");
    close();
    inputRef.current?.blur();
    setData(null); // refetch next time, so new alerts/cameras show up
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Escape") {
      close();
      inputRef.current?.blur();
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      setActive((i) => Math.min(i + 1, Math.max(results.length - 1, 0)));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (event.key === "Enter" && results[active]) {
      event.preventDefault();
      go(results[active]);
    }
  };

  const showPanel = open && query.trim().length > 0;

  return (
    <div className="relative">
      <form onSubmit={(e) => e.preventDefault()} role="search">
        <Field className="xl:w-107.5">
          <InputGroup className="border-gray-200 bg-transparent dark:border-gray-800 dark:bg-white/3">
            <InputGroupAddon align="inline-start">
              <SearchIcon className="size-5 text-gray-500 dark:text-gray-400" />
            </InputGroupAddon>
            <InputGroupInput
              ref={inputRef}
              type="text"
              value={query}
              placeholder={t("searchPlaceholder")}
              aria-label="Search"
              aria-expanded={showPanel}
              aria-controls="global-search-results"
              autoComplete="off"
              onFocus={() => {
                if (closeTimer.current) clearTimeout(closeTimer.current);
                setOpen(true);
                loadData();
              }}
              // Delay so a click on a result lands before the panel closes;
              // refocusing cancels it.
              onBlur={() => {
                closeTimer.current = setTimeout(close, 150);
              }}
              onChange={(e) => {
                setQuery(e.target.value);
                setActive(0);
                setOpen(true);
              }}
              onKeyDown={onKeyDown}
              className="text-gray-800 placeholder:text-gray-400 dark:text-white/90 dark:placeholder:text-white/30"
            />
            <InputGroupAddon align="inline-end">
              <Badge
                variant="light"
                color="gray"
                size="sm"
                className="gap-0.5 rounded-lg border border-gray-200 bg-gray-50 px-1.75 py-[4.5px] text-xs tracking-[-0.2px] text-gray-500 shadow-none dark:border-gray-800 dark:bg-white/3 dark:text-gray-400"
              >
                <span>{isMac ? "⌘" : "Ctrl"}</span>
                <span>K</span>
              </Badge>
            </InputGroupAddon>
          </InputGroup>
        </Field>
      </form>

      {showPanel && (
        <div
          id="global-search-results"
          role="listbox"
          className="absolute start-0 top-full z-60 mt-2 max-h-[70vh] w-full overflow-y-auto rounded-xl border border-gray-200 bg-white p-2 shadow-theme-lg dark:border-gray-800 dark:bg-gray-900"
        >
          {results.length === 0 ? (
            <p className="flex items-center gap-2 px-3 py-4 text-sm text-gray-500 dark:text-gray-400">
              {loading ? (
                <>
                  <Spinner className="size-4" /> Searching...
                </>
              ) : (
                `No results for "${query.trim()}"`
              )}
            </p>
          ) : (
            results.map((r, i) => (
              <div key={`${r.group}-${r.to}`}>
                {(i === 0 || results[i - 1].group !== r.group) && (
                  <p className="px-3 pt-2 pb-1 text-xs font-medium text-gray-400 uppercase">
                    {r.group}
                  </p>
                )}
                <button
                  type="button"
                  role="option"
                  aria-selected={i === active}
                  onMouseDown={(e) => e.preventDefault()}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => go(r)}
                  className={cn(
                    "flex w-full items-baseline justify-between gap-3 rounded-lg px-3 py-2 text-start text-sm",
                    i === active
                      ? "bg-brand-50 text-brand-600 dark:bg-brand-500/15 dark:text-brand-400"
                      : "text-gray-700 dark:text-gray-300",
                  )}
                >
                  <span className="truncate">{r.label}</span>
                  {r.detail && (
                    <span className="shrink-0 text-xs text-gray-400">
                      {r.detail}
                    </span>
                  )}
                </button>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
