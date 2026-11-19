import { ComponentCard } from "@/components/shared/component-card";
import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useAuth } from "@/contexts";
import {
  AUDIT_ACTION_LABELS,
  AUDIT_CATEGORIES,
  ApiError,
  type AuditEntry,
  type AuditPage,
  auditApi,
} from "@/services";
import { useEffect, useState } from "react";
import { Navigate } from "react-router";

const PAGE_SIZE = 50;
const ALL = "all";
const HEADER_CELL =
  "px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400";

const show = (value: unknown): string =>
  typeof value === "object" && value !== null
    ? JSON.stringify(value)
    : String(value);

function describe(entry: AuditEntry): string {
  const d = entry.details ?? {};
  const parts: string[] = [];
  for (const key of ["username", "name", "title", "role", "verdict", "type"]) {
    if (d[key] !== undefined) parts.push(`${key}: ${show(d[key])}`);
  }
  if (Array.isArray(d.scripts)) parts.push(`analyses: ${d.scripts.join(", ")}`);
  if (Array.isArray(d.fields)) parts.push(`changed: ${d.fields.join(", ")}`);
  if (d.changes && typeof d.changes === "object")
    parts.push(
      `changed: ${Object.entries(d.changes as Record<string, unknown>)
        .map(([k, v]) => `${k}=${show(v)}`)
        .join(", ")}`,
    );
  if (d.matched === false) parts.push("no such account");
  if (entry.target_type && entry.target_id !== null)
    parts.push(`${entry.target_type} #${entry.target_id}`);
  return parts.join(" · ") || "—";
}

/** Admin-only, read-only record of who did what (proposal: audit logs). */
export default function AuditLogPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [category, setCategory] = useState(ALL);
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<AuditPage | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Search after typing pauses, not on every key.
  useEffect(() => {
    const t = setTimeout(() => {
      setQuery(search.trim());
      setOffset(0);
    }, 350);
    return () => clearTimeout(t);
  }, [search]);

  useEffect(() => {
    if (!isAdmin) return;
    let cancelled = false;
    auditApi
      .list({
        category: category === ALL ? undefined : category,
        q: query || undefined,
        limit: PAGE_SIZE,
        offset,
      })
      .then((p) => {
        if (cancelled) return;
        setPage(p);
        setError(null);
      })
      .catch((err) => {
        if (!cancelled)
          setError(
            err instanceof ApiError
              ? err.message
              : "Failed to load the audit log",
          );
      });
    return () => {
      cancelled = true;
    };
  }, [isAdmin, category, query, offset]);

  if (user && !isAdmin) return <Navigate to="/" replace />;

  const from = page && page.total > 0 ? offset + 1 : 0;
  const to = page ? offset + page.items.length : 0;

  return (
    <div>
      <PageMeta
        title="Audit Log | UniVerse"
        description="Who did what, and when"
      />
      <PageBreadcrumb pageTitle="Audit Log" />

      <ComponentCard
        title="Audit Log"
        description="Every sign-in, account change, camera and settings change, monitoring start/stop, face-data access and incident action, newest first. Entries can't be edited or deleted."
      >
        <div className="mb-4 flex flex-col gap-3 sm:flex-row">
          <div className="sm:w-64">
            <Select
              value={category}
              onValueChange={(v) => {
                setCategory(v ?? ALL);
                setOffset(0);
              }}
            >
              <SelectTrigger aria-label="Category">
                <SelectValue>
                  {(v: string) =>
                    v === ALL
                      ? "All activity"
                      : (AUDIT_CATEGORIES.find((c) => c.value === v)?.label ??
                        v)
                  }
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL}>All activity</SelectItem>
                {AUDIT_CATEGORIES.map((c) => (
                  <SelectItem key={c.value} value={c.value}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by username or action"
            aria-label="Search audit log"
            className="sm:max-w-xs"
            maxLength={50}
          />
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-400">
            {error}
          </div>
        )}

        {page === null ? (
          !error && (
            <div className="flex justify-center py-12">
              <Spinner className="size-6" />
            </div>
          )
        ) : page.items.length === 0 ? (
          <p className="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
            Nothing recorded for this filter.
          </p>
        ) : (
          <>
            <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-white/5">
              <div className="max-w-full overflow-x-auto">
                <Table>
                  <TableHeader className="border-b border-gray-100 dark:border-white/5">
                    <TableRow>
                      {["Time", "User", "Action", "Details", "IP address"].map(
                        (h) => (
                          <TableCell key={h} isHeader className={HEADER_CELL}>
                            {h}
                          </TableCell>
                        ),
                      )}
                    </TableRow>
                  </TableHeader>
                  <TableBody className="divide-y divide-gray-100 dark:divide-white/5">
                    {page.items.map((entry) => (
                      <TableRow key={entry.id}>
                        <TableCell className="px-5 py-3 text-sm whitespace-nowrap text-gray-500 dark:text-gray-400">
                          {new Date(entry.created_at).toLocaleString()}
                        </TableCell>
                        <TableCell className="px-5 py-3 text-sm text-gray-800 dark:text-white/90">
                          {entry.actor_username ?? "—"}
                          {entry.actor_id === null && entry.actor_username && (
                            <span className="ms-1 text-xs text-gray-400">
                              (not signed in)
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="px-5 py-3 text-sm">
                          {entry.action === "auth.login_failed" ? (
                            <Badge color="error">Failed sign-in</Badge>
                          ) : (
                            <span className="text-gray-800 dark:text-white/90">
                              {AUDIT_ACTION_LABELS[entry.action] ??
                                entry.action}
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="px-5 py-3 text-sm text-gray-500 dark:text-gray-400">
                          {describe(entry)}
                        </TableCell>
                        <TableCell className="font-mono px-5 py-3 text-xs text-gray-400">
                          {entry.ip_address ?? "—"}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
            <div className="mt-4 flex items-center justify-between text-sm text-gray-500 dark:text-gray-400">
              <span>
                {from}-{to} of {page.total}
              </span>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={offset === 0}
                  onClick={() => setOffset(Math.max(offset - PAGE_SIZE, 0))}
                >
                  Newer
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={to >= page.total}
                  onClick={() => setOffset(offset + PAGE_SIZE)}
                >
                  Older
                </Button>
              </div>
            </div>
          </>
        )}
      </ComponentCard>
    </div>
  );
}
