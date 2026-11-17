import { ComponentCard } from "@/components/shared/component-card";
import { PageMeta } from "@/components/shared/page-meta";
import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import { useAlertsSocket } from "@/hooks/use-alerts-socket";
import {
  type Alert,
  type Camera,
  type Incident,
  type Person,
  alertsApi,
  camerasApi,
  incidentsApi,
  peopleApi,
} from "@/services";
import { CameraIcon, OctagonAlertIcon, PieChartIcon, UsersIcon } from "@/icons";
import { useEffect, useState } from "react";
import { Link } from "react-router";

function StatCard({
  icon,
  label,
  value,
  to,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
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
        <p className="text-title-sm font-semibold text-gray-800 dark:text-white/90">{value}</p>
      </div>
    </Link>
  );
}

export default function OverviewPage() {
  const [cameras, setCameras] = useState<Camera[] | null>(null);
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [incidents, setIncidents] = useState<Incident[] | null>(null);
  const [people, setPeople] = useState<Person[] | null>(null);

  const load = () => {
    camerasApi.list().then(setCameras).catch(() => setCameras([]));
    alertsApi.list().then(setAlerts).catch(() => setAlerts([]));
    incidentsApi.list().then(setIncidents).catch(() => setIncidents([]));
    peopleApi.list().then(setPeople).catch(() => setPeople([]));
  };

  useEffect(load, []);

  useAlertsSocket((msg) => {
    if (msg.type === "alert" || msg.type === "camera_status" || msg.type === "incident_update") {
      load();
    }
  });

  const isLoading = cameras === null || alerts === null || incidents === null || people === null;
  const onlineCount = cameras?.filter((c) => c.status === "online").length ?? 0;
  const openIncidents = incidents?.filter((i) => i.status !== "resolved").length ?? 0;
  const recentAlerts = alerts?.slice(0, 5) ?? [];

  return (
    <div>
      <PageMeta title="Dashboard | UniVerse" description="Surveillance overview: camera status, alerts, incidents" />
      <h2 className="text-title-lg mb-6 font-semibold text-gray-800 dark:text-white/90">
        Overview
      </h2>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <Spinner className="size-6" />
        </div>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard icon={<CameraIcon className="size-6" />} label="Cameras online" value={`${onlineCount} / ${cameras?.length ?? 0}`} to="/cameras" />
            <StatCard icon={<PieChartIcon className="size-6" />} label="Total alerts" value={alerts?.length ?? 0} to="/surveillance-alerts" />
            <StatCard icon={<OctagonAlertIcon className="size-6" />} label="Open incidents" value={openIncidents} to="/incidents" />
            <StatCard icon={<UsersIcon className="size-6" />} label="Registered people" value={people?.length ?? 0} to="/people" />
          </div>

          <ComponentCard title="Recent Alerts">
            {recentAlerts.length === 0 ? (
              <p className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">No alerts yet.</p>
            ) : (
              <ul className="divide-y divide-gray-100 dark:divide-white/5">
                {recentAlerts.map((alert) => (
                  <li key={alert.id} className="flex items-center justify-between py-3 text-sm">
                    <div>
                      <span className="font-medium text-gray-800 dark:text-white/90">{alert.alert_type}</span>
                      <span className="ml-2 text-gray-500 dark:text-gray-400">camera #{alert.camera_id} — {alert.message}</span>
                    </div>
                    <Badge color={alert.priority === "high" ? "error" : alert.priority === "low" ? "gray" : "warning"}>
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
