import { ComponentCard } from "@/components/shared/component-card";
import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { EvidenceThumbnails } from "@/components/surveillance/evidence-gallery";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "@/components/ui/toast-manager";
import { useAlertsSocket } from "@/hooks/use-alerts-socket";
import { HIGHLIGHT_ROW, useHighlight } from "@/hooks/use-highlight";
import { type Alert, ApiError, alertsApi, incidentsApi } from "@/services";
import { useEffect, useState } from "react";

function PriorityBadge({ priority }: { priority: string }) {
  if (priority === "high") return <Badge color="error">high</Badge>;
  if (priority === "low") return <Badge color="gray">low</Badge>;
  return <Badge color="warning">medium</Badge>;
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const highlight = useHighlight("alert", alerts !== null);
  const [error, setError] = useState<string | null>(null);
  const [promotingId, setPromotingId] = useState<number | null>(null);

  const load = () => {
    alertsApi
      .list()
      .then(setAlerts)
      .catch((err) =>
        setError(
          err instanceof ApiError ? err.message : "Failed to load alerts",
        ),
      );
  };

  useEffect(load, []);

  useAlertsSocket((msg) => {
    if (msg.type === "alert") {
      setAlerts((prev) => {
        const newAlert: Alert = {
          id: msg.id,
          camera_id: msg.camera_id,
          alert_type: msg.alert_type,
          priority: msg.priority as Alert["priority"],
          message: msg.message,
          extra_data: null,
          incident_id: null,
          triggered_at: msg.triggered_at,
          images: [], // evidence arrives right after, as alert_image messages
        };
        // Dedupe: a reconnect can race with the initial list load.
        if (prev?.some((a) => a.id === newAlert.id)) return prev;
        return prev ? [newAlert, ...prev] : [newAlert];
      });
    } else if (msg.type === "alert_image") {
      setAlerts(
        (prev) =>
          prev?.map((a) =>
            a.id === msg.alert_id &&
            !a.images.some((img) => img.id === msg.image.id)
              ? { ...a, images: [...a.images, msg.image] }
              : a,
          ) ?? prev,
      );
    } else if (msg.type === "incident_update") {
      // Another operator may have promoted an alert; refresh link state.
      load();
    }
  });

  const promoteToIncident = async (alert: Alert) => {
    setPromotingId(alert.id);
    try {
      const incident = await incidentsApi.create({
        camera_id: alert.camera_id,
        title: `${alert.alert_type} on camera ${alert.camera_id}`,
        description: alert.message,
        priority: alert.priority,
        source_alert_id: alert.id,
      });
      setAlerts(
        (prev) =>
          prev?.map((a) =>
            a.id === alert.id ? { ...a, incident_id: incident.id } : a,
          ) ?? prev,
      );
      toast.success(
        `Incident #${incident.id} created`,
        "Acknowledge and resolve it from the Incidents page.",
      );
    } catch (err) {
      toast.error(
        "Couldn't create incident",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setPromotingId(null);
    }
  };

  return (
    <div>
      <PageMeta
        title="Alerts | UniVerse"
        description="Live AI-generated security alerts"
      />
      <PageBreadcrumb pageTitle="Alerts" />

      <ComponentCard
        title="Alerts"
        description="Raw AI-generated events. New alerts appear here live. Review one and promote it to an Incident for the acknowledge/resolve workflow."
      >
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-400">
            {error}
          </div>
        )}

        {alerts === null ? (
          <div className="flex justify-center py-12">
            <Spinner className="size-6" />
          </div>
        ) : alerts.length === 0 ? (
          <p className="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
            No alerts yet.
          </p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-white/5">
            <div className="max-w-full overflow-x-auto">
              <Table>
                <TableHeader className="border-b border-gray-100 dark:border-white/5">
                  <TableRow>
                    <TableCell
                      isHeader
                      className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400"
                    >
                      Time
                    </TableCell>
                    <TableCell
                      isHeader
                      className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400"
                    >
                      Camera
                    </TableCell>
                    <TableCell
                      isHeader
                      className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400"
                    >
                      Type
                    </TableCell>
                    <TableCell
                      isHeader
                      className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400"
                    >
                      Priority
                    </TableCell>
                    <TableCell
                      isHeader
                      className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400"
                    >
                      Message
                    </TableCell>
                    <TableCell
                      isHeader
                      className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400"
                    >
                      Evidence
                    </TableCell>
                    <TableCell
                      isHeader
                      className="px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400"
                    >
                      Action
                    </TableCell>
                  </TableRow>
                </TableHeader>
                <TableBody className="divide-y divide-gray-100 dark:divide-white/5">
                  {alerts.map((alert) => (
                    <TableRow
                      key={alert.id}
                      id={`alert-${alert.id}`}
                      className={
                        highlight === alert.id ? HIGHLIGHT_ROW : undefined
                      }
                    >
                      <TableCell className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {new Date(alert.triggered_at).toLocaleString()}
                      </TableCell>
                      <TableCell className="px-5 py-4 text-sm text-gray-800 dark:text-white/90">
                        #{alert.camera_id}
                      </TableCell>
                      <TableCell className="px-5 py-4 text-sm text-gray-800 dark:text-white/90">
                        {alert.alert_type}
                      </TableCell>
                      <TableCell className="px-5 py-4">
                        <PriorityBadge priority={alert.priority} />
                      </TableCell>
                      <TableCell className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400">
                        {alert.message}
                      </TableCell>
                      <TableCell className="px-5 py-4">
                        <EvidenceThumbnails
                          images={alert.images}
                          title={`${alert.alert_type} · camera #${alert.camera_id}`}
                        />
                      </TableCell>
                      <TableCell className="px-5 py-4">
                        {alert.incident_id ? (
                          <Badge color="info">incident created</Badge>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={promotingId === alert.id}
                            onClick={() => promoteToIncident(alert)}
                          >
                            {promotingId === alert.id ? (
                              <Spinner />
                            ) : (
                              "Create Incident"
                            )}
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </ComponentCard>
    </div>
  );
}
