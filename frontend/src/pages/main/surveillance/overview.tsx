import { ComponentCard } from "@/components/shared/component-card";
import { PageMeta } from "@/components/shared/page-meta";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { useAlertsSocket } from "@/hooks/use-alerts-socket";
import {
  ApiError,
  type Alert,
  type DashboardSummary,
  alertsApi,
  dashboardApi,
} from "@/services";
import { CameraIcon, OctagonAlertIcon, PieChartIcon, UsersIcon } from "@/icons";
import { useEffect, useState } from "react";
import { Link } from "react-router";

const RECENT_ALERTS = 5;

function StatCard({
  icon,
  label,
  value,
  hint,
  to,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  hint?: string;
  to: string;
}) {
  return (
    <Link
      to={to}
      className="flex items-center gap-4 rounded-2xl border border-gray-200 bg-white p-5 transition-colors hover:border-brand-300 dark:border-white/5 dark:bg-white/3"
    >
      <div className="flex size-12 shrink-0 items-center justify-center rounded-xl bg-brand-50 text-brand-500 dark:bg-brand-500/15 dark:text-brand-400">
        {icon}
      </div>
      <div>
        <p className="text-sm text-gray-500 dark:text-gray-400">{label}</p>
        <p className="text-title-sm font-semibold text-gray-800 dark:text-white/90">
          {value}
        </p>
        {hint && (
          <p className="text-xs text-gray-400 dark:text-gray-500">{hint}</p>
        )}
      </div>
    </Link>
  );
}

function priorityColor(
  priority: Alert["priority"],
): "error" | "gray" | "warning" {
  if (priority === "high") return "error";
  if (priority === "low") return "gray";
  return "warning";
}

export default function OverviewPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recentAlerts, setRecentAlerts] = useState<Alert[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    Promise.all([
      dashboardApi.summary(),
      alertsApi.list({ limit: RECENT_ALERTS }),
    ])
      .then(([summaryData, alertList]) => {
        setSummary(summaryData);
        setRecentAlerts(alertList);
        setError(null);
      })
      .catch((err: unknown) =>
        setError(
          err instanceof ApiError
            ? err.message
            : "Failed to load dashboard data",
        ),
      );
  };

  useEffect(load, []);

  useAlertsSocket(() => load());

  const isLoading = summary === null || recentAlerts === null;

  return (
    <div>
      <PageMeta
        title="Dashboard | UniVerse"
        description="Surveillance overview: camera status, alerts, incidents"
      />
      <h2 className="mb-6 text-title-lg font-semibold text-gray-800 dark:text-white/90">
        Overview
      </h2>

      {error && (
        <div className="mb-6 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-400">
          {error}
        </div>
      )}

      {isLoading && !error && (
        <div className="flex justify-center py-12">
          <Spinner className="size-6" />
        </div>
      )}

      {summary && recentAlerts && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon={<CameraIcon className="size-6" />}
              label="Cameras online"
              value={`${summary.cameras_online} / ${summary.cameras_total}`}
              to="/cameras"
            />
            <StatCard
              icon={<PieChartIcon className="size-6" />}
              label="Total alerts"
              value={summary.alerts_total}
              hint={`${summary.alerts_unreviewed} awaiting review`}
              to="/surveillance-alerts"
            />
            <StatCard
              icon={<OctagonAlertIcon className="size-6" />}
              label="Open incidents"
              value={summary.incidents_open}
              to="/incidents"
            />
            <StatCard
              icon={<UsersIcon className="size-6" />}
              label="Registered people"
              value={summary.people_registered}
              to="/people"
            />
          </div>

          <ComponentCard title="Recent Alerts">
            {recentAlerts.length === 0 ? (
              <p className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">
                No alerts yet.
              </p>
            ) : (
              <ul className="divide-y divide-gray-100 dark:divide-white/5">
                {recentAlerts.map((alert) => (
                  <li
                    key={alert.id}
                    className="flex items-center justify-between gap-3 py-3 text-sm"
                  >
                    <div>
                      <span className="font-medium text-gray-800 dark:text-white/90">
                        {alert.alert_type}
                      </span>
                      <span className="ml-2 text-gray-500 dark:text-gray-400">
                        camera #{alert.camera_id} — {alert.message}
                      </span>
                      <span className="ml-2 text-xs text-gray-400">
                        {new Date(alert.triggered_at).toLocaleString()}
                      </span>
                    </div>
                    <Badge color={priorityColor(alert.priority)}>
                      {alert.priority}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </ComponentCard>
        </div>
      )}
    </div>
  );
}
