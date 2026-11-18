import { Badge } from "@/components/ui/badge";
import { useCameraFrame } from "@/hooks/use-camera-stream";
import { useNow } from "@/hooks/use-now";
import { VideoIcon } from "@/icons";
import type { Camera } from "@/services";
import { cn } from "@/utils";

// Scripts send ~5 frames/s (face recognition on a CPU can be ~1/s); after
// this long without one, the feed counts as stopped.
const STALE_AFTER_MS = 5000;

function StatusBadge({ status }: { status: Camera["status"] }) {
  if (status === "online") return <Badge color="success">online</Badge>;
  if (status === "offline") return <Badge color="error">offline</Badge>;
  return <Badge color="gray">unknown</Badge>;
}

/** One camera's live view: the annotated frames its AI script streams. */
export function LiveCameraTile({
  camera,
  onOpen,
  className,
}: {
  camera: Camera;
  onOpen?: () => void;
  className?: string;
}) {
  const frame = useCameraFrame(camera.id);
  const now = useNow(1000);
  const isLive = frame !== null && now - frame.receivedAt < STALE_AFTER_MS;
  const stalledFor =
    frame && !isLive ? Math.round((now - frame.receivedAt) / 1000) : null;

  const body = (
    <div className="relative aspect-video w-full overflow-hidden rounded-xl bg-gray-900">
      {frame && (
        <img
          src={frame.src}
          alt={`Live view of ${camera.name}`}
          className={cn(
            "size-full object-contain",
            !isLive && "opacity-40 grayscale",
          )}
        />
      )}

      {!frame && (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 px-6 text-center">
          <VideoIcon className="size-8 text-gray-500" />
          <p className="text-sm font-medium text-gray-300">No live feed</p>
          <p className="text-xs text-gray-500">
            Start a detection script for this camera with{" "}
            <code className="rounded bg-white/10 px-1 py-0.5 text-gray-300">
              --camera-id {camera.id}
            </code>
          </p>
        </div>
      )}

      {stalledFor !== null && (
        <div className="absolute inset-0 flex items-center justify-center">
          <p className="rounded-lg bg-black/70 px-3 py-1.5 text-sm text-gray-200">
            Feed stopped · last frame {stalledFor}s ago
          </p>
        </div>
      )}

      <div className="absolute start-3 top-3 flex items-center gap-2">
        {isLive && (
          <span className="flex items-center gap-1.5 rounded-md bg-red-600 px-2 py-0.5 text-xs font-semibold text-white">
            <span className="size-1.5 animate-pulse rounded-full bg-white" />
            LIVE
          </span>
        )}
      </div>
      <div className="absolute end-3 top-3">
        <StatusBadge status={camera.status} />
      </div>
    </div>
  );

  return (
    <div className={cn("space-y-2", className)}>
      {onOpen ? (
        <button
          type="button"
          onClick={onOpen}
          className="block w-full rounded-xl ring-brand-500 outline-none focus-visible:ring-2"
          aria-label={`Open ${camera.name} full size`}
        >
          {body}
        </button>
      ) : (
        body
      )}
      <div className="flex items-baseline justify-between gap-3 px-1">
        <p className="truncate text-sm font-medium text-gray-800 dark:text-white/90">
          {camera.name}
        </p>
        <p className="font-mono shrink-0 text-xs text-gray-400">
          ID {camera.id}
        </p>
      </div>
      {camera.location && (
        <p className="-mt-1.5 truncate px-1 text-xs text-gray-500 dark:text-gray-400">
          {camera.location}
        </p>
      )}
    </div>
  );
}
