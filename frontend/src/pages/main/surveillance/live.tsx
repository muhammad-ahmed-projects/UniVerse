import { ComponentCard } from "@/components/shared/component-card";
import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { LiveCameraTile } from "@/components/surveillance/live-camera-tile";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { useAlertsSocket } from "@/hooks/use-alerts-socket";
import { ApiError, type Camera, camerasApi } from "@/services";
import { useEffect, useState } from "react";

export default function LiveViewPage() {
  const [cameras, setCameras] = useState<Camera[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openCameraId, setOpenCameraId] = useState<number | null>(null);

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
        description="Live, AI-annotated feeds from every camera"
      />
      <PageBreadcrumb pageTitle="Live View" />

      <ComponentCard
        title="Live View"
        description="Every camera's feed as its AI script sees it: boxes, track IDs, recognized names and the restricted zone. A feed appears while a script runs for that camera with --camera-id. Click a camera to enlarge it."
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
              />
            ))}
          </div>
        )}
      </ComponentCard>

      <Dialog
        open={openCamera !== null}
        onOpenChange={(open) => {
          if (!open) setOpenCameraId(null);
        }}
      >
        <DialogContent className="max-w-[calc(100%-2rem)] sm:max-w-5xl">
          <DialogHeader>
            <DialogTitle>{openCamera?.name}</DialogTitle>
          </DialogHeader>
          {openCamera && <LiveCameraTile camera={openCamera} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}
