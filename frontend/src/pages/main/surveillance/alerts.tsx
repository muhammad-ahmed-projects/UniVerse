import { ComponentCard } from "@/components/shared/component-card";
import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { EvidenceThumbnails } from "@/components/surveillance/evidence-gallery";
import { ReviewStatsCard } from "@/components/surveillance/review-stats-card";
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
import {
  type Alert,
  ApiError,
  type ReviewStatus,
  alertTypeLabel,
  alertsApi,
  incidentsApi,
} from "@/services";
import { useEffect, useState } from "react";

const HEADER_CELL =
  "px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400";

function PriorityBadge({ priority }: { priority: string }) {
  if (priority === "high") return <Badge color="error">high</Badge>;
  if (priority === "low") return <Badge color="gray">low</Badge>;
  return <Badge color="warning">medium</Badge>;
}

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const highlight = useHighlight("alert", alerts !== null);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

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

  const patch = (id: number, changes: Partial<Alert>) =>
    setAlerts(
      (prev) =>
        prev?.map((a) => (a.id === id ? { ...a, ...changes } : a)) ?? prev,
    );

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
          review_status: null,
          reviewed_by: null,
          reviewed_at: null,
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
    } else if (msg.type === "alert_review") {
      patch(msg.alert_id, { review_status: msg.review_status });
    } else if (msg.type === "incident_update") {
      // Another operator may have promoted an alert; refresh link state.
      load();
    }
  });

  const promoteToIncident = async (alert: Alert) => {
    setBusyId(alert.id);
    try {
      const incident = await incidentsApi.create({
        camera_id: alert.camera_id,
        title: `${alertTypeLabel(alert.alert_type)} on camera ${alert.camera_id}`,
        description: alert.message,
        priority: alert.priority,
        source_alert_id: alert.id,
      });
      patch(alert.id, { incident_id: incident.id, review_status: "confirmed" });
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
      setBusyId(null);
    }
  };

  const review = async (alert: Alert, verdict: ReviewStatus | null) => {
    setBusyId(alert.id);
    try {
      const updated = await alertsApi.review(alert.id, verdict);
      patch(alert.id, updated);
      if (verdict === "false_alarm") toast.info("Marked as false alarm");
    } catch (err) {
      toast.error(
        "Couldn't save the review",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-6">
      <PageMeta
        title="Alerts | UniVerse"
        description="Live security alerts from the detection scripts"
      />
      <PageBreadcrumb pageTitle="Alerts" />

      <ComponentCard
        title="Detection accuracy"
        description="From your reviews below: mark each alert as real or a false alarm. Promoting an alert to an incident counts as real."
      >
        <ReviewStatsCard />
      </ComponentCard>

      <ComponentCard
        title="Alerts"
        description="Raw events from the detection scripts, live. Review each one: a real event can become an Incident; a false alarm is recorded so the false-alarm rate can be measured."
      >
        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-400">
            {error}
          </div>
        )}

        {alerts === null ? (
          !error && (
            <div className="flex justify-center py-12">
              <Spinner className="size-6" />
            </div>
          )
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
                    {[
                      "Time",
                      "Camera",
                      "Type",
                      "Priority",
                      "Message",
                      "Evidence",
                      "Review",
                      "Action",
                    ].map((label) => (
                      <TableCell key={label} isHeader className={HEADER_CELL}>
                        {label}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody className="divide-y divide-gray-100 dark:divide-white/5">
                  {alerts.map((alert) => {
                    const busy = busyId === alert.id;
                    return (
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
                          {alertTypeLabel(alert.alert_type)}
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
                            title={`${alertTypeLabel(alert.alert_type)} · camera #${alert.camera_id}`}
                          />
                        </TableCell>
                        <TableCell className="px-5 py-4">
                          {alert.review_status === null ? (
                            <div className="flex gap-1.5">
                              <Button
                                size="xs"
                                variant="outline"
                                disabled={busy}
                                onClick={() => void review(alert, "confirmed")}
                              >
                                Real
                              </Button>
                              <Button
                                size="xs"
                                variant="outline"
                                disabled={busy}
                                onClick={() =>
                                  void review(alert, "false_alarm")
                                }
                              >
                                False alarm
                              </Button>
                            </div>
                          ) : (
                            <div className="flex items-center gap-1.5">
                              <Badge
                                color={
                                  alert.review_status === "confirmed"
                                    ? "success"
                                    : "gray"
                                }
                              >
                                {alert.review_status === "confirmed"
                                  ? "real"
                                  : "false alarm"}
                              </Badge>
                              {alert.incident_id === null && (
                                <button
                                  type="button"
                                  disabled={busy}
                                  onClick={() => void review(alert, null)}
                                  className="text-xs text-gray-400 hover:text-gray-700 hover:underline dark:hover:text-white"
                                >
                                  undo
                                </button>
                              )}
                            </div>
                          )}
                        </TableCell>
                        <TableCell className="px-5 py-4">
                          {alert.incident_id ? (
                            <Badge color="info">incident created</Badge>
                          ) : alert.review_status === "false_alarm" ? (
                            <span className="text-xs text-gray-400">—</span>
                          ) : (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={busy}
                              onClick={() => void promoteToIncident(alert)}
                            >
                              {busy ? <Spinner /> : "Create Incident"}
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </ComponentCard>
    </div>
  );
}
