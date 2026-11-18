import { type ToastType, toastManager } from "@/components/ui/toast-manager";
import { AlertIcon, CheckCircleIcon, InfoIcon, XIcon } from "@/icons";
import { cn } from "@/utils";
import { Toast } from "@base-ui/react/toast";

const ICONS: Record<ToastType, typeof InfoIcon> = {
  success: CheckCircleIcon,
  error: AlertIcon,
  info: InfoIcon,
};

const ICON_COLORS: Record<ToastType, string> = {
  success: "text-green-500",
  error: "text-red-500",
  info: "text-brand-500",
};

const ACCENTS: Record<ToastType, string> = {
  success: "border-s-green-500",
  error: "border-s-red-500",
  info: "border-s-brand-500",
};

function asToastType(value: string | undefined): ToastType {
  return value === "success" || value === "error" ? value : "info";
}

function ToastList() {
  const { toasts } = Toast.useToastManager();
  return toasts.map((t) => {
    const type = asToastType(t.type);
    const Icon = ICONS[type];
    return (
      <Toast.Root
        key={t.id}
        toast={t}
        swipeDirection="right"
        data-slot="toast"
        className={cn(
          "pointer-events-auto flex w-full items-start gap-3 rounded-xl border border-s-4 border-gray-200 bg-white p-4 shadow-theme-lg transition-all duration-200 dark:border-gray-800 dark:bg-[#1E2635]",
          "data-ending-style:translate-x-4 data-ending-style:opacity-0 data-starting-style:translate-y-2 data-starting-style:opacity-0",
          ACCENTS[type],
        )}
      >
        <Icon className={cn("mt-0.5 size-5 shrink-0", ICON_COLORS[type])} />
        <div className="min-w-0 flex-1">
          <Toast.Title className="text-sm font-semibold text-gray-800 dark:text-white/90" />
          <Toast.Description className="mt-0.5 text-sm break-words text-gray-500 dark:text-gray-400" />
        </div>
        <Toast.Close
          aria-label="Dismiss"
          className="-m-1 rounded-md p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-800 dark:hover:text-white"
        >
          <XIcon className="size-4" />
        </Toast.Close>
      </Toast.Root>
    );
  });
}

/** Mount once near the app root; renders every toast raised via `toast.*`. */
export function Toaster() {
  return (
    <Toast.Provider toastManager={toastManager} limit={4}>
      <Toast.Portal>
        <Toast.Viewport className="pointer-events-none fixed end-4 bottom-4 z-200 flex w-[min(380px,calc(100vw-2rem))] flex-col-reverse gap-2">
          <ToastList />
        </Toast.Viewport>
      </Toast.Portal>
    </Toast.Provider>
  );
}
