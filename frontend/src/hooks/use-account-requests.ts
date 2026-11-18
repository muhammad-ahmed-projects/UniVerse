import { useCallback, useEffect, useState } from "react";
import { toast } from "@/components/ui/toast-manager";
import { type AccountRequestCounts, usersApi } from "@/services";
import { useAlertsSocket } from "./use-alerts-socket";

const POLL_MS = 60_000;

/** Fire after approving/rejecting/resetting so the sidebar badge updates at once. */
export const ACCOUNT_REQUESTS_CHANGED = "universe:account-requests-changed";

export function notifyAccountRequestsChanged(): void {
  window.dispatchEvent(new Event(ACCOUNT_REQUESTS_CHANGED));
}

/** For admins: how many account requests and forgot-password requests are
 * waiting. Updates live (account_request WebSocket message, with a toast)
 * and once a minute. Returns zeros for everyone else without calling the API. */
export function useAccountRequests(enabled: boolean): AccountRequestCounts & {
  refresh: () => void;
} {
  const [counts, setCounts] = useState<AccountRequestCounts>({
    signups: 0,
    password_resets: 0,
  });

  const refresh = useCallback(() => {
    if (!enabled) return;
    usersApi
      .requests()
      .then(setCounts)
      .catch(() => undefined);
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;
    refresh();
    const timer = setInterval(refresh, POLL_MS);
    window.addEventListener(ACCOUNT_REQUESTS_CHANGED, refresh);
    return () => {
      clearInterval(timer);
      window.removeEventListener(ACCOUNT_REQUESTS_CHANGED, refresh);
    };
  }, [enabled, refresh]);

  useAlertsSocket((msg) => {
    if (!enabled || msg.type !== "account_request") return;
    refresh();
    toast.info(
      msg.kind === "signup"
        ? "New account request"
        : "Password reset requested",
      "Review it on the Users page.",
    );
  });

  return enabled
    ? { ...counts, refresh }
    : { signups: 0, password_resets: 0, refresh };
}
