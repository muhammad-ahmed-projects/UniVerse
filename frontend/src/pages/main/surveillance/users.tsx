import { ComponentCard } from "@/components/shared/component-card";
import { ConfirmDialog } from "@/components/shared/confirm-dialog";
import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "@/components/ui/toast-manager";
import {
  ResetPasswordDialog,
  UserFormDialog,
} from "@/components/users/user-dialogs";
import { useAuth } from "@/contexts";
import { ApiError, ROLE_LABELS, type User, usersApi } from "@/services";
import { useEffect, useState } from "react";
import { Navigate } from "react-router";

const HEADER_CELL =
  "px-5 py-3 text-start text-xs font-medium text-gray-500 dark:text-gray-400";

function RoleBadge({ role }: { role: User["role"] }) {
  const color =
    role === "admin" ? "primary" : role === "ai_service" ? "info" : "gray";
  return <Badge color={color}>{ROLE_LABELS[role]}</Badge>;
}

export default function UsersPage() {
  const { user: me } = useAuth();
  const [users, setUsers] = useState<User[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formFor, setFormFor] = useState<User | "new" | null>(null);
  const [resetFor, setResetFor] = useState<User | null>(null);
  const [pendingDelete, setPendingDelete] = useState<User | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const isAdmin = me?.role === "admin";

  const load = () => {
    usersApi
      .list()
      .then((list) => {
        setUsers(list);
        setError(null);
      })
      .catch((err) =>
        setError(
          err instanceof ApiError ? err.message : "Failed to load users",
        ),
      );
  };

  useEffect(() => {
    if (isAdmin) load();
  }, [isAdmin]);

  // Only admins manage users; the API refuses the same requests anyway.
  if (me && !isAdmin) return <Navigate to="/" replace />;

  const handleDelete = async () => {
    if (!pendingDelete) return;
    const target = pendingDelete;
    setIsDeleting(true);
    try {
      await usersApi.remove(target.id);
      setUsers((prev) => prev?.filter((u) => u.id !== target.id) ?? prev);
      setPendingDelete(null);
      toast.success("User deleted", target.username);
    } catch (err) {
      setPendingDelete(null);
      toast.error(
        "Couldn't delete user",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div>
      <PageMeta
        title="Users | UniVerse"
        description="Manage dashboard accounts"
      />
      <PageBreadcrumb pageTitle="Users" />

      <ComponentCard
        title="Users"
        description="Everyone who can sign in to the dashboard, and the detection scripts' service account. Admins manage cameras, people, settings and users; security operators watch cameras and review alerts and incidents."
      >
        <div className="mb-4 flex justify-end">
          <Button onClick={() => setFormFor("new")}>Add User</Button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-400">
            {error}
          </div>
        )}

        {users === null ? (
          !error && (
            <div className="flex justify-center py-12">
              <Spinner className="size-6" />
            </div>
          )
        ) : (
          <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-white/5">
            <div className="max-w-full overflow-x-auto">
              <Table>
                <TableHeader className="border-b border-gray-100 dark:border-white/5">
                  <TableRow>
                    {[
                      "Username",
                      "Email",
                      "Role",
                      "Status",
                      "Created",
                      "Action",
                    ].map((label) => (
                      <TableCell key={label} isHeader className={HEADER_CELL}>
                        {label}
                      </TableCell>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody className="divide-y divide-gray-100 dark:divide-white/5">
                  {users.map((u) => {
                    const isSelf = u.id === me?.id;
                    return (
                      <TableRow key={u.id}>
                        <TableCell className="px-5 py-4 text-sm font-medium text-gray-800 dark:text-white/90">
                          {u.username}
                          {isSelf && (
                            <span className="ms-2 text-xs font-normal text-gray-400">
                              (you)
                            </span>
                          )}
                        </TableCell>
                        <TableCell className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400">
                          {u.email ?? "—"}
                        </TableCell>
                        <TableCell className="px-5 py-4">
                          <RoleBadge role={u.role} />
                        </TableCell>
                        <TableCell className="px-5 py-4">
                          <Badge color={u.is_active ? "success" : "gray"}>
                            {u.is_active ? "active" : "inactive"}
                          </Badge>
                        </TableCell>
                        <TableCell className="px-5 py-4 text-sm text-gray-500 dark:text-gray-400">
                          {new Date(u.created_at).toLocaleDateString()}
                        </TableCell>
                        <TableCell className="px-5 py-4">
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setFormFor(u)}
                            >
                              Edit
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => setResetFor(u)}
                            >
                              Reset password
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={isSelf}
                              title={
                                isSelf
                                  ? "You can't delete your own account"
                                  : undefined
                              }
                              onClick={() => setPendingDelete(u)}
                            >
                              Delete
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
      </ComponentCard>

      {/* key: a fresh form per user, prefilled from that user */}
      <UserFormDialog
        key={`user-form-${formFor === null ? "closed" : formFor === "new" ? "new" : formFor.id}`}
        user={formFor}
        isSelf={formFor !== null && formFor !== "new" && formFor.id === me?.id}
        onOpenChange={(open) => {
          if (!open) setFormFor(null);
        }}
        onSaved={() => load()}
      />

      <ResetPasswordDialog
        key={`reset-${resetFor?.id ?? "closed"}`}
        user={resetFor}
        onOpenChange={(open) => {
          if (!open) setResetFor(null);
        }}
      />

      <ConfirmDialog
        open={pendingDelete !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null);
        }}
        title="Delete user?"
        description={
          <>
            <span className="font-medium text-gray-800 dark:text-white/90">
              {pendingDelete?.username}
            </span>{" "}
            won't be able to sign in any more. This can't be undone.
            {pendingDelete?.role === "ai_service" &&
              " The detection scripts use this account; monitoring stops working until they get another one."}{" "}
            Accounts that reviewed incidents can't be deleted; deactivate them
            instead.
          </>
        }
        confirmLabel="Delete user"
        destructive
        isConfirming={isDeleting}
        onConfirm={() => void handleDelete()}
      />
    </div>
  );
}
