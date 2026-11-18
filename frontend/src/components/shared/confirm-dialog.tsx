import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Spinner } from "@/components/ui/spinner";
import type { ReactNode } from "react";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: ReactNode;
  description?: ReactNode;
  confirmLabel?: string;
  destructive?: boolean;
  isConfirming?: boolean;
  onConfirm: () => void;
}

/** In-app replacement for `window.confirm`, styled like every other dialog. */
export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  destructive = false,
  isConfirming = false,
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        // Don't let the dialog close mid-request.
        if (!isConfirming) onOpenChange(next);
      }}
    >
      <DialogContent
        showCloseButton={false}
        className="max-w-[calc(100%-2rem)] sm:max-w-md"
      >
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>
        <DialogFooter>
          <DialogClose
            disabled={isConfirming}
            render={<Button variant="outline">Cancel</Button>}
          />
          <Button
            variant={destructive ? "destructive" : "default"}
            disabled={isConfirming}
            onClick={onConfirm}
          >
            {isConfirming ? <Spinner /> : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
