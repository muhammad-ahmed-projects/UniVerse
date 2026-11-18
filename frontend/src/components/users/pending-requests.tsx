import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "@/components/ui/toast-manager";
import { notifyAccountRequestsChanged } from "@/hooks/use-account-requests";
import { ApiError, type User, type UserRole, usersApi } from "@/services";
import { timeAgo } from "@/utils";
import { useState } from "react";
import { RoleSelect } from "./user-dialogs";

function PendingRow({
  user,
  onChanged,
}: {
  user: User;
  onChanged: () => void;
}) {
  const [role, setRole] = useState<UserRole>("security_operator");
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [confirmReject, setConfirmReject] = useState(false);

  const approve = async () => {
    setBusy("approve");
    try {
      await usersApi.approve(user.id, role);
      toast.success("Account approved", `${user.username} can sign in now.`);
      notifyAccountRequestsChanged();
      onChanged();
    } catch (err) {
      toast.error(
        "Couldn't approve",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setBusy(null);
    }
  };

  const reject = async () => {
    setBusy("reject");
    try {
      await usersApi.remove(user.id);
      toast.success("Request rejected", user.username);
      setConfirmReject(false);
      notifyAccountRequestsChanged();
      onChanged();
    } catch (err) {
      toast.error(
        "Couldn't reject",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setBusy(null);
    }
  };

  return (
    <div
      id={`request-${user.id}`}
      className="grid gap-4 rounded-xl border border-gray-200 p-4 sm:grid-cols-[1fr_16rem_auto] sm:items-start dark:border-gray-800"
    >
      <div>
        <p className="text-sm font-medium text-gray-800 dark:text-white/90">
          {user.username}
        </p>
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {user.email ?? "No email given"} · asked {timeAgo(user.created_at)}
        </p>
      </div>
      <RoleSelect value={role} onChange={setRole} />
      <div className="flex gap-2 sm:pt-6">
        <Button
          size="sm"
          disabled={busy !== null}
          onClick={() => void approve()}
        >
          {busy === "approve" ? <Spinner /> : "Approve"}
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={busy !== null}
          onClick={() => setConfirmReject(true)}
        >
          Reject
        </Button>
      </div>
      <ConfirmDialog
        open={confirmReject}
        onOpenChange={setConfirmReject}
        title="Reject this request?"
        description={`${user.username}'s request is deleted. They can ask again later.`}
        confirmLabel="Reject"
        destructive
        isConfirming={busy === "reject"}
        onConfirm={() => void reject()}
      />
    </div>
  );
}

/** Account requests from the sign-in page, waiting for an admin. */
export function PendingRequests({
  users,
  onChanged,
}: {
  users: User[];
  onChanged: () => void;
}) {
  return (
    <div className="space-y-3">
      {users.map((u) => (
        <PendingRow key={u.id} user={u} onChanged={onChanged} />
      ))}
    </div>
  );
}
