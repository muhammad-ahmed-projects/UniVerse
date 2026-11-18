import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "@/components/ui/toast-manager";
import { useNow } from "@/hooks/use-now";
import {
  ANALYSES,
  type AnalysisScript,
  ApiError,
  type Camera,
  type CameraRunner,
  analysisLabel,
  runnerState,
  runnersApi,
} from "@/services";
import { cn, timeAgo } from "@/utils";
import { useEffect, useRef, useState } from "react";
import { LiveCameraTile } from "./live-camera-tile";

const LOG_POLL_MS = 1500;

export function RunnerStateBadge({ runner }: { runner?: CameraRunner }) {
  const state = runnerState(runner);
  if (state === "running") return <Badge color="success">running</Badge>;
  if (state === "failed")
    return <Badge color="error">stopped with error</Badge>;
  return <Badge color="gray">not running</Badge>;
}

function defaultSelection(
  isWebcam: boolean,
  previous?: CameraRunner,
): AnalysisScript[] {
  const last = previous?.scripts.map((s) => s.name) ?? [];
  if (last.length > 0 && (!isWebcam || last.length === 1)) return last;
  return isWebcam ? ["roi_loitering"] : ["roi_loitering", "camera_health"];
}

/** Start/stop a camera's AI analyses and watch what they're doing. */
export function MonitoringDialog({
  camera,
  runner: initialRunner,
  canControl,
  onOpenChange,
  onChanged,
}: {
  camera: Camera | null;
  runner?: CameraRunner;
  canControl: boolean;
  onOpenChange: (open: boolean) => void;
  onChanged: () => void;
}) {
  const [runner, setRunner] = useState<CameraRunner | undefined>(initialRunner);
  const [selected, setSelected] = useState<AnalysisScript[]>([]);
  const [busy, setBusy] = useState<"start" | "stop" | null>(null);
  const logRef = useRef<HTMLPreElement>(null);
  const now = useNow(5000);
  const cameraId = camera?.id ?? null;
  const isWebcam =
    runner?.is_webcam ?? /^\d+$/.test(camera?.stream_source ?? "");

  // Fresh state (and the default selection) each time the dialog opens.
  useEffect(() => {
    if (cameraId === null) return;
    let cancelled = false;
    const poll = () =>
      runnersApi
        .get(cameraId)
        .then((r) => {
          if (!cancelled) setRunner(r);
        })
        .catch(() => undefined);
    void runnersApi
      .get(cameraId)
      .then((r) => {
        if (cancelled) return;
        setRunner(r);
        setSelected(defaultSelection(r.is_webcam, r));
      })
      .catch(() => undefined);
    const timer = setInterval(() => void poll(), LOG_POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [cameraId]);

  // Keep the newest log line in view.
  const logLength = runner?.log.length ?? 0;
  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [logLength]);

  const toggle = (script: AnalysisScript) => {
    setSelected((prev) => {
      if (isWebcam) return [script]; // one program per webcam
      return prev.includes(script)
        ? prev.filter((s) => s !== script)
        : [...prev, script];
    });
  };

  const start = async () => {
    if (!camera) return;
    setBusy("start");
    try {
      setRunner(await runnersApi.start(camera.id, selected));
      onChanged();
      toast.success(
        `Monitoring started on ${camera.name}`,
        "The camera goes online and its live view appears in a few seconds.",
      );
    } catch (err) {
      toast.error(
        "Couldn't start monitoring",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setBusy(null);
    }
  };

  const stop = async () => {
    if (!camera) return;
    setBusy("stop");
    try {
      setRunner(await runnersApi.stop(camera.id));
      onChanged();
      toast.success(`Monitoring stopped on ${camera.name}`);
    } catch (err) {
      toast.error(
        "Couldn't stop monitoring",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setBusy(null);
    }
  };

  const state = runnerState(runner);

  return (
    <Dialog
      open={camera !== null}
      onOpenChange={(open) => {
        if (!open && busy === null) onOpenChange(false);
      }}
    >
      <DialogContent className="max-h-[calc(100dvh-2rem)] max-w-[calc(100%-2rem)] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            Monitoring · {camera?.name}
            <RunnerStateBadge runner={runner} />
          </DialogTitle>
          <DialogDescription>
            {isWebcam
              ? "USB webcam: only one analysis can use it at a time."
              : "IP camera or video: several analyses can run together."}{" "}
            Analyses run as background AI scripts on the server.
          </DialogDescription>
        </DialogHeader>

        {camera && (
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-4">
              <LiveCameraTile camera={camera} />

              {state === "running" && runner ? (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-gray-800 dark:text-white/90">
                    Running now
                  </h4>
                  <ul className="space-y-1.5">
                    {runner.scripts.map((s) => (
                      <li
                        key={s.pid}
                        className="flex items-center justify-between gap-3 text-sm"
                      >
                        <span className="text-gray-700 dark:text-gray-300">
                          {analysisLabel(s.name)}
                        </span>
                        {s.running ? (
                          <span className="shrink-0 text-xs text-gray-400">
                            since {timeAgo(s.started_at, now)}
                          </span>
                        ) : (
                          <Badge color="error">exited ({s.exit_code})</Badge>
                        )}
                      </li>
                    ))}
                  </ul>
                  {canControl && (
                    <Button
                      variant="destructive"
                      className="w-full"
                      disabled={busy !== null}
                      onClick={() => void stop()}
                    >
                      {busy === "stop" ? <Spinner /> : "Stop monitoring"}
                    </Button>
                  )}
                </div>
              ) : canControl ? (
                <div className="space-y-3">
                  <h4 className="text-sm font-medium text-gray-800 dark:text-white/90">
                    {isWebcam ? "Choose one analysis" : "Choose analyses"}
                  </h4>
                  <div className="space-y-2">
                    {ANALYSES.map((a) => {
                      const checked = selected.includes(a.script);
                      return (
                        <label
                          key={a.script}
                          className={cn(
                            "flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors",
                            checked
                              ? "border-brand-500 bg-brand-50 dark:bg-brand-500/10"
                              : "border-gray-200 hover:border-gray-300 dark:border-gray-800",
                          )}
                        >
                          <Checkbox
                            className="mt-0.5"
                            checked={checked}
                            onCheckedChange={() => toggle(a.script)}
                          />
                          <span>
                            <span className="block text-sm font-medium text-gray-800 dark:text-white/90">
                              {a.label}
                            </span>
                            <span className="block text-xs text-gray-500 dark:text-gray-400">
                              {a.description}
                            </span>
                          </span>
                        </label>
                      );
                    })}
                  </div>
                  <Button
                    className="w-full"
                    disabled={busy !== null || selected.length === 0}
                    onClick={() => void start()}
                  >
                    {busy === "start" ? <Spinner /> : "Start monitoring"}
                  </Button>
                </div>
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  Monitoring isn't running. An admin can start it.
                </p>
              )}
            </div>

            <div className="flex min-h-0 flex-col">
              <h4 className="mb-2 text-sm font-medium text-gray-800 dark:text-white/90">
                Script output
              </h4>
              <pre
                ref={logRef}
                className="font-mono h-80 overflow-auto rounded-xl bg-gray-900 p-3 text-xs leading-relaxed break-all whitespace-pre-wrap text-gray-200 lg:h-full lg:min-h-80"
              >
                {runner && runner.log.length > 0
                  ? runner.log.join("\n")
                  : "No output yet. Start monitoring to see what the AI scripts are doing."}
              </pre>
              {state === "failed" && (
                <p className="mt-2 text-xs text-red-600 dark:text-red-400">
                  A script stopped with an error; the last lines above usually
                  say why (for example, the camera couldn't be opened).
                </p>
              )}
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
