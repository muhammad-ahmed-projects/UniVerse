import { Toast } from "@base-ui/react/toast";
import type { ReactNode } from "react";

export type ToastType = "success" | "error" | "info";

/**
 * One app-wide toast manager, so any module (pages, hooks, services) can
 * raise a toast without needing React context: `toast.success("Saved")`.
 * Rendered by `<Toaster />` (components/ui/toast.tsx), mounted once in main.tsx.
 */
export const toastManager = Toast.createToastManager();

function add(type: ToastType, title: ReactNode, description?: ReactNode) {
  return toastManager.add({
    type,
    title,
    description,
    // Errors stay longer so the operator has time to read them.
    timeout: type === "error" ? 8000 : 4000,
    priority: type === "error" ? "high" : "low",
  });
}

export const toast = {
  success: (title: ReactNode, description?: ReactNode) =>
    add("success", title, description),
  error: (title: ReactNode, description?: ReactNode) =>
    add("error", title, description),
  info: (title: ReactNode, description?: ReactNode) =>
    add("info", title, description),
};
