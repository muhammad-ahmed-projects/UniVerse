import { apiClient } from "./api-client";

export interface CameraSettings {
  camera_id: number;
  roi_x1: number;
  roi_y1: number;
  roi_x2: number;
  roi_y2: number;
  loiter_seconds: number;
  tamper_motion_threshold: number;
  tamper_covered_brightness_ratio: number;
  tamper_covered_sharpness_ratio: number;
  tamper_defocus_sharpness_ratio: number;
}

export type CameraSettingsInput = Omit<CameraSettings, "camera_id">;

export const cameraSettingsApi = {
  get: (cameraId: number) =>
    apiClient.get<CameraSettings>(`/cameras/${cameraId}/settings`),
  update: (cameraId: number, input: CameraSettingsInput) =>
    apiClient.put<CameraSettings>(`/cameras/${cameraId}/settings`, input),
};
