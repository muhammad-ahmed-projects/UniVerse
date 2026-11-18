import { ComponentCard } from "@/components/shared/component-card";
import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { LiveCameraTile } from "@/components/surveillance/live-camera-tile";
import {
  MonitoringDialog,
  RunnerStateBadge,
} from "@/components/surveillance/monitoring-dialog";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/contexts";
import { useAlertsSocket } from "@/hooks/use-alerts-socket";
import { useRunners } from "@/hooks/use-runners";
import { ApiError, type Camera, camerasApi } from "@/services";
import { useEffect, useState } from "react";

export default function LiveViewPage() {
  const { user } = useAuth();
  const [cameras, setCameras] = useState<Camera[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openCameraId, setOpenCameraId] = useState<number | null>(null);
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
    if (msg.type === "camera_status") load();
  });

  const openCamera = cameras?.find((c) => c.id === openCameraId) ?? null;

  return (
    <div>
      <PageMeta
        title="Live View | UniVerse"
        description="Live, annotated feeds from every camera"
      />
      <PageBreadcrumb pageTitle="Live View" />

      <ComponentCard
        title="Live View"
        description="Every camera's feed as its detection script sees it: boxes, track IDs, recognized names and the restricted zone. Click a camera to start or stop monitoring and see what its scripts are doing."
      >
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
            No cameras registered yet. Add one from the Cameras page.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 2xl:grid-cols-3">
            {cameras.map((camera) => (
              <LiveCameraTile
                key={camera.id}
                camera={camera}
                onOpen={() => setOpenCameraId(camera.id)}
                badge={<RunnerStateBadge runner={runners.get(camera.id)} />}
              />
            ))}
          </div>
        )}
      </ComponentCard>

      <MonitoringDialog
        key={`monitor-${openCameraId ?? "closed"}`}
        camera={openCamera}
        runner={openCameraId === null ? undefined : runners.get(openCameraId)}
        canControl={user?.role === "admin"}
        onOpenChange={(open) => {
          if (!open) setOpenCameraId(null);
        }}
        onChanged={() => {
          refreshRunners();
          load();
        }}
      />
    </div>
  );
}
