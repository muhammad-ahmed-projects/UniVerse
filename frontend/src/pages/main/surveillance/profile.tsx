import { ComponentCard } from "@/components/shared/component-card";
import { PageBreadcrumb } from "@/components/shared/page-breadcrumb";
import { PageMeta } from "@/components/shared/page-meta";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "@/components/ui/toast-manager";
import { PasswordChecklist } from "@/components/users/password-checklist";
import { useAuth } from "@/contexts";
import {
  ApiError,
  isStrongPassword,
  ROLE_DESCRIPTIONS,
  ROLE_LABELS,
  changeOwnPassword,
} from "@/services";
import { useState } from "react";

function Detail({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <div className="mt-1 text-sm font-medium text-gray-800 dark:text-white/90">
        {value}
      </div>
    </div>
  );
}

export default function ProfilePage() {
  const { user } = useAuth();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const mismatch = confirm.length > 0 && confirm !== next;

  const save = async () => {
    setIsSaving(true);
    try {
      await changeOwnPassword(current, next);
      setCurrent("");
      setNext("");
      setConfirm("");
      toast.success(
        "Password changed",
        "Your other signed-in sessions were signed out.",
      );
    } catch (err) {
      toast.error(
        "Couldn't change password",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div>
      <PageMeta title="Profile | UniVerse" description="Your account" />
      <PageBreadcrumb pageTitle="Profile" />

      <div className="grid gap-6 xl:grid-cols-2">
        <ComponentCard title="Account">
          {user && (
            <div className="grid gap-5 sm:grid-cols-2">
              <Detail label="Username" value={user.username} />
              <Detail label="Email" value={user.email ?? "—"} />
              <Detail
                label="Role"
                value={
                  <>
                    <Badge color={user.role === "admin" ? "primary" : "gray"}>
                      {ROLE_LABELS[user.role]}
                    </Badge>
                    <p className="mt-1 text-xs font-normal text-gray-500 dark:text-gray-400">
                      {ROLE_DESCRIPTIONS[user.role]}
                    </p>
                  </>
                }
              />
              <Detail
                label="Member since"
                value={new Date(user.created_at).toLocaleDateString()}
              />
            </div>
          )}
          <p className="mt-6 text-xs text-gray-400">
            Only an admin can change your username, email or role (Users page).
          </p>
        </ComponentCard>

        <ComponentCard
          title="Change password"
          description="Choose a strong password. Every other place you're signed in is signed out."
        >
          <form
            className="max-w-sm space-y-4"
            onSubmit={(e) => {
              e.preventDefault();
              void save();
            }}
          >
            <Field>
              <FieldLabel>Current password</FieldLabel>
              <Input
                type="password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                autoComplete="current-password"
                maxLength={72}
              />
            </Field>
            <Field>
              <FieldLabel>New password</FieldLabel>
              <Input
                type="password"
                value={next}
                onChange={(e) => setNext(e.target.value)}
                autoComplete="new-password"
                maxLength={72}
              />
              <PasswordChecklist password={next} />
            </Field>
            <Field>
              <FieldLabel>Confirm new password</FieldLabel>
              <Input
                type="password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                autoComplete="new-password"
                maxLength={72}
                aria-invalid={mismatch || undefined}
              />
              {mismatch && (
                <p className="text-xs text-red-500">Passwords don't match.</p>
              )}
            </Field>
            <Button
              type="submit"
              disabled={
                isSaving ||
                !current ||
                !isStrongPassword(next) ||
                next !== confirm
              }
            >
              {isSaving ? <Spinner /> : "Change password"}
            </Button>
          </form>
        </ComponentCard>
      </div>
    </div>
  );
}
