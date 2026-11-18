import { ComponentCard } from "@/components/shared/component-card";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { CameraFormDialog } from "@/components/surveillance/camera-form-dialog";
import {
  MonitoringDialog,
  RunnerStateBadge,
} from "@/components/surveillance/monitoring-dialog";
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
import { useAuth } from "@/contexts";
import { useAlertsSocket } from "@/hooks/use-alerts-socket";
import { HIGHLIGHT_ROW, useHighlight } from "@/hooks/use-highlight";
import { useRunners } from "@/hooks/use-runners";
import {
  ApiError,
  type Camera,
  type CameraStatus,
  analysisLabel,
  camerasApi,
} from "@/services";
import { useEffect, useState } from "react";

const HEADER_CELL =
  "px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400";

function StatusBadge({ status }: { status: CameraStatus }) {
  if (status === "online") return <Badge color="success">online</Badge>;
  if (status === "offline") return <Badge color="error">offline</Badge>;
  return <Badge color="gray">unknown</Badge>;
}

export default function CamerasPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [cameras, setCameras] = useState<Camera[] | null>(null);
  const highlight = useHighlight("camera", cameras !== null);
  const [error, setError] = useState<string | null>(null);
  const [formFor, setFormFor] = useState<Camera | "new" | null>(null);
  const [monitorId, setMonitorId] = useState<number | null>(null);
  const [pendingDelete, setPendingDelete] = useState<Camera | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const { runners, refresh: refreshRunners } = useRunners();

  const load = () => {
    camerasApi
      .list()
      .then((list) => {
        setCameras(list);
        setError(null);
      })
      .catch((err) =>
        setError(
          err instanceof ApiError ? err.message : "Failed to load cameras",
        ),
      );
  };

  useEffect(load, []);

  useAlertsSocket((msg) => {
    // Reload rather than patch, so last_seen_at updates along with status.
    if (msg.type === "camera_status") load();
  });

  const handleDelete = async () => {
    if (!pendingDelete) return;
    const camera = pendingDelete;
    setIsDeleting(true);
    try {
      await camerasApi.remove(camera.id);
      setCameras((prev) => prev?.filter((c) => c.id !== camera.id) ?? prev);
      setPendingDelete(null);
      refreshRunners();
      toast.success("Camera deleted", camera.name);
    } catch (err) {
      toast.error(
        "Couldn't delete camera",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setIsDeleting(false);
    }
  };

  const monitorCamera = cameras?.find((c) => c.id === monitorId) ?? null;

  return (
    <div>
      <PageMeta
        title="Cameras | UniVerse"
        description="Camera status and management"
      />
      <PageBreadcrumb pageTitle="Cameras" />

      <ComponentCard
        title="Cameras"
        description="Every registered camera, its live status, and what's monitoring it. Open Monitoring to start or stop a camera's detection and watch its output."
      >
        <div className="mb-4 flex justify-end">
          {isAdmin && (
            <Button onClick={() => setFormFor("new")}>Add Camera</Button>
          )}
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-400">
            {error}
          </div>
        )}

        {cameras === null ? (
          !error && (
            <div className="flex justify-center py-12">
              <Spinner className="size-6" />
            </div>
          )
        ) : cameras.length === 0 ? (
          <p className="py-12 text-center text-sm text-gray-500 dark:text-gray-400">
            No cameras registered yet.
          </p>
        ) : (
          <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-white/5">
            <div className="max-w-full overflow-x-auto">
              <Table>
                <TableHeader className="border-b border-gray-100 dark:border-white/5">
                  <TableRow>
                    {[
                      "ID",
                      "Name",
                      "Location",
                      "Source",
                      "Status",
                      "Monitoring",
                      "Last seen",
                      "Action",
                    ].map((label) => (
                      <TableCell key={label} isHeader className={HEADER_CELL}>
                        {label}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody className="divide-y divide-gray-100 dark:divide-white/5">
                  {cameras.map((camera) => {
                    const runner = runners.get(camera.id);
                    const active = runner?.running
                      ? runner.scripts.filter((s) => s.running)
                      : [];
                    return (
                      <TableRow
                        key={camera.id}
                        id={`camera-${camera.id}`}
                        className={
                          highlight === camera.id ? HIGHLIGHT_ROW : undefined
                        }
                      >
                        {/* Detection scripts take this as --camera-id. */}
                        <TableCell className="font-mono px-5 py-4 text-sm text-gray-500 dark:text-gray-400">
                          {camera.id}
                        </TableCell>
                        <TableCell className="px-5 py-4 text-sm font-medium text-gray-800 dark:text-white/90">
                          {camera.name}
                        </TableCell>
                        <TableCell className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400">
                          {camera.location ?? "—"}
                        </TableCell>
                        <TableCell className="max-w-56 truncate px-5 py-4 text-sm text-gray-500 dark:text-gray-400">
                          {camera.stream_source}
                        </TableCell>
                        <TableCell className="px-5 py-4">
                          <StatusBadge status={camera.status} />
                        </TableCell>
                        <TableCell className="px-5 py-4">
                          <RunnerStateBadge runner={runner} />
                          {active.length > 0 && (
                            <span className="mt-1 block text-xs text-gray-500 dark:text-gray-400">
                              {active
                                .map((s) => analysisLabel(s.name))
                                .join(", ")}
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400">
                          {camera.last_seen_at
                            ? new Date(camera.last_seen_at).toLocaleString()
                            : "—"}
                        </TableCell>
                        <TableCell className="px-5 py-4">
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant={runner?.running ? "outline" : "default"}
                              onClick={() => setMonitorId(camera.id)}
                            >
                              Monitoring
                            </Button>
                            {isAdmin && (
                              <>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => setFormFor(camera)}
                                >
                                  Edit
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => setPendingDelete(camera)}
                                >
                                  Delete
                                </Button>
                              </>
                            )}
                          </div>
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

      {/* key: a fresh form per camera, prefilled from that camera */}
      <CameraFormDialog
        key={`form-${formFor === null ? "closed" : formFor === "new" ? "new" : formFor.id}`}
        camera={formFor}
        onOpenChange={(open) => {
          if (!open) setFormFor(null);
        }}
        onSaved={() => load()}
      />

      <MonitoringDialog
        key={`monitor-${monitorId ?? "closed"}`}
        camera={monitorCamera}
        runner={monitorId === null ? undefined : runners.get(monitorId)}
        canControl={isAdmin}
        onOpenChange={(open) => {
          if (!open) setMonitorId(null);
        }}
        onChanged={() => {
          refreshRunners();
          load();
        }}
      />

      <ConfirmDialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null);
        }}
        title="Delete camera?"
        description={
          <>
            <span className="font-medium text-gray-800 dark:text-white/90">
              {pendingDelete?.name}
            </span>{" "}
            will be deleted together with all its alerts, incidents, evidence
            photos and settings. Its monitoring is stopped. This can't be
            undone.
          </>
        }
        confirmLabel="Delete camera"
        destructive
        isConfirming={isDeleting}
        onConfirm={() => void handleDelete()}
      />
    </div>
  );
}
