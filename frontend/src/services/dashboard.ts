import { apiClient } from "./api-client";

export interface DashboardSummary {
  cameras_total: number;
  cameras_online: number;
  alerts_total: number;
  alerts_unreviewed: number;
  incidents_open: number;
  people_registered: number;
}

export const dashboardApi = {
  summary: () => apiClient.get<DashboardSummary>("/dashboard/summary"),
};
