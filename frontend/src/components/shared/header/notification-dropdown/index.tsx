import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useAlertsSocket } from "@/hooks/use-alerts-socket";
import { type Alert, alertsApi } from "@/services";
import { BellIcon, XIcon } from "@/icons";
import { cn } from "@/utils";
import { Fragment, useEffect, useState } from "react";
import { Link } from "react-router";

function priorityColor(priority: string): "error" | "warning" | "gray" {
  if (priority === "high") return "error";
  if (priority === "low") return "gray";
  return "warning";
}

export default function NotificationDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const [notifying, setNotifying] = useState(false);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loadFailed, setLoadFailed] = useState(false);

  useEffect(() => {
    alertsApi
      .list({ limit: 5 })
      .then(setAlerts)
      .catch(() => setLoadFailed(true));
  }, []);

  useAlertsSocket((msg) => {
    if (msg.type === "alert") {
      setNotifying(true);
      setAlerts((prev) =>
        [
          {
            id: msg.id,
            camera_id: msg.camera_id,
            alert_type: msg.alert_type,
            priority: msg.priority as Alert["priority"],
            message: msg.message,
            evidence_path: null,
            extra_data: null,
            incident_id: null,
            triggered_at: msg.triggered_at,
          },
          ...prev,
        ].slice(0, 5),
      );
    }
  });

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open);
    if (open) setNotifying(false);
  };

  return (
    <DropdownMenu open={isOpen} onOpenChange={handleOpenChange}>
      <DropdownMenuTrigger
        render={
          <Button
            variant="outline"
            size="icon-lg"
            className="relative"
            aria-label="Toggle notifications"
          >
            <span
              className={cn(
                "absolute inset-e-0 -top-0.5 z-10 h-2 w-2 translate-x-1/2 rounded-full bg-orange-400 rtl:-inset-e-1.5",
                !notifying ? "hidden" : "flex",
              )}
            >
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-orange-400 opacity-75" />
            </span>
            <BellIcon className="size-auto!" />
          </Button>
        }
      />

      <DropdownMenuContent
        align="end"
        sideOffset={12}
        className="w-87.5 overflow-hidden p-3 sm:w-90.25 dark:bg-[#1E2635]"
      >
        <div className="flex items-center justify-between pb-3">
          <h5 className="text-title-sm font-semibold text-gray-800 dark:text-gray-200">
            Alerts
          </h5>
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => setIsOpen(false)}
            aria-label="Close notifications"
          >
            <XIcon className="size-5" />
          </Button>
        </div>

        <DropdownMenuSeparator className="my-0" />

        <ScrollArea scrollbars="vertical" className="h-96">
          <div className="flex flex-col pe-2">
            {alerts.length === 0 ? (
              <p className="py-6 text-center text-sm text-gray-500 dark:text-gray-400">
                {loadFailed ? "Couldn't load alerts." : "No alerts yet."}
              </p>
            ) : (
              alerts.map((alert) => (
                <Fragment key={alert.id}>
                  <DropdownMenuItem className="flex items-start justify-between gap-3 rounded-lg p-3 hover:bg-gray-100 dark:hover:bg-white/5">
                    <span className="block flex-1 text-start text-sm text-gray-600 dark:text-gray-300">
                      <span className="font-medium text-gray-800 dark:text-white/90">
                        {alert.alert_type}
                      </span>{" "}
                      on camera #{alert.camera_id} — {alert.message}
                    </span>
                    <Badge color={priorityColor(alert.priority)} size="sm">
                      {alert.priority}
                    </Badge>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator className="my-0.5 bg-gray-100 last-of-type:hidden dark:bg-gray-700" />
                </Fragment>
              ))
            )}
          </div>
        </ScrollArea>

        <Button
          variant="outline"
          size="default"
          nativeButton={false}
          render={<Link to="/surveillance-alerts" />}
          className="mt-3 w-full"
          onClick={() => setIsOpen(false)}
        >
          View All Alerts
        </Button>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
