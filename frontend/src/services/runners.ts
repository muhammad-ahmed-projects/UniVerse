import { apiClient } from "./api-client";

/** AI scripts the dashboard can start for a camera. */
export type AnalysisScript =
  "roi_loitering" | "tamper_detection" | "face_recognition" | "camera_health";

export interface RunnerScript {
  name: AnalysisScript;
  pid: number;
  running: boolean;
  exit_code: number | null;
  /** Stopped from the dashboard; false + an exit code means it died on its own. */
  stopped_by_user: boolean;
  started_at: string;
}

export type RunnerState = "running" | "stopped" | "failed" | "never";

export function runnerState(runner: CameraRunner | undefined): RunnerState {
  if (!runner || runner.scripts.length === 0) return "never";
  if (runner.running) return "running";
  const failed = runner.scripts.some(
    (s) => !s.stopped_by_user && s.exit_code !== null && s.exit_code !== 0,
  );
  return failed ? "failed" : "stopped";
}

export interface CameraRunner {
  camera_id: number;
  running: boolean;
  /** A local USB webcam: only one analysis can use it at a time. */
  is_webcam: boolean;
  scripts: RunnerScript[];
  /** Last lines the scripts printed, oldest first. */
  log: string[];
}

export const ANALYSES: {
  script: AnalysisScript;
  label: string;
  description: string;
}[] = [
  {
    script: "roi_loitering",
    label: "People, restricted area & loitering",
    description:
      "Detects and tracks people; alerts when someone enters the restricted zone or stays too long.",
  },
  {
    script: "face_recognition",
    label: "Face recognition",
    description:
      "Names registered people, updates their 'last seen', alerts on unknown faces.",
  },
  {
    script: "tamper_detection",
    label: "Tamper detection",
    description: "Alerts when the camera is covered, moved or out of focus.",
  },
  {
    script: "camera_health",
    label: "Camera health only",
    description:
      "Watches whether the feed is up and alerts when it goes offline; no detection.",
  },
];

export const analysisLabel = (script: string) =>
  ANALYSES.find((a) => a.script === script)?.label ?? script;

export const runnersApi = {
  list: () => apiClient.get<CameraRunner[]>("/camera-runners"),
  get: (cameraId: number) =>
    apiClient.get<CameraRunner>(`/cameras/${cameraId}/runner`),
  start: (cameraId: number, scripts: AnalysisScript[]) =>
    apiClient.post<CameraRunner>(`/cameras/${cameraId}/runner`, { scripts }),
  stop: (cameraId: number) =>
    apiClient.delete<CameraRunner>(`/cameras/${cameraId}/runner`),
};
