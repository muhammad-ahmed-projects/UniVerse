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
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Switch } from "@/components/ui/switch";
import { toast } from "@/components/ui/toast-manager";
import {
  ApiError,
  MIN_PASSWORD_LENGTH,
  ROLE_DESCRIPTIONS,
  ROLE_LABELS,
  type User,
  type UserRole,
  usersApi,
} from "@/services";
import { useState } from "react";

const ROLES = Object.keys(ROLE_LABELS) as UserRole[];

export function RoleSelect({
  value,
  onChange,
  disabled,
}: {
  value: UserRole;
  onChange: (role: UserRole) => void;
  disabled?: boolean;
}) {
  return (
    <Field>
      <FieldLabel>Role</FieldLabel>
      <Select
        value={value}
        onValueChange={(v) => v && onChange(v as UserRole)}
        disabled={disabled}
      >
        <SelectTrigger>
          <SelectValue>
            {(v: string) => ROLE_LABELS[v as UserRole] ?? v}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {ROLES.map((role) => (
            <SelectItem key={role} value={role}>
              {ROLE_LABELS[role]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <p className="text-xs text-gray-400">{ROLE_DESCRIPTIONS[value]}</p>
    </Field>
  );
}

/** Add a user (user = "new") or edit one. */
export function UserFormDialog({
  user,
  isSelf,
  onOpenChange,
  onSaved,
}: {
  user: User | "new" | null;
  isSelf: boolean;
  onOpenChange: (open: boolean) => void;
  onSaved: (user: User) => void;
}) {
  const editing = user !== null && user !== "new" ? user : null;
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState(editing?.email ?? "");
  const [role, setRole] = useState<UserRole>(
    editing?.role ?? "security_operator",
  );
  const [isActive, setIsActive] = useState(editing?.is_active ?? true);
  const [password, setPassword] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const canSave = editing
    ? true
    : username.trim().length >= 3 && password.length >= MIN_PASSWORD_LENGTH;

  const save = async () => {
    setIsSaving(true);
    try {
      let saved: User;
      if (editing) {
        // Send only what changed, so unchanged fields are never re-validated.
        const trimmed = email.trim();
        saved = await usersApi.update(editing.id, {
          ...(trimmed !== (editing.email ?? "")
            ? { email: trimmed || null }
            : {}),
          ...(role !== editing.role ? { role } : {}),
          ...(isActive !== editing.is_active ? { is_active: isActive } : {}),
        });
      } else {
        saved = await usersApi.create({
          username: username.trim(),
          email: email.trim() || undefined,
          password,
          role,
        });
      }
      toast.success(editing ? "User updated" : "User added", saved.username);
      onSaved(saved);
      onOpenChange(false);
    } catch (err) {
      toast.error(
        editing ? "Couldn't update user" : "Couldn't add user",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog
      open={user !== null}
      onOpenChange={(open) => {
        if (!isSaving) onOpenChange(open);
      }}
    >
      <DialogContent className="max-w-[calc(100%-2rem)] sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {editing ? `Edit ${editing.username}` : "Add User"}
          </DialogTitle>
          {isSelf && (
            <DialogDescription>
              You can't change your own role or deactivate yourself; another
              admin can.
            </DialogDescription>
          )}
        </DialogHeader>
        <div className="space-y-4">
          {!editing && (
            <Field>
              <FieldLabel>Username</FieldLabel>
              <Input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="e.g. aiman"
                autoComplete="off"
                maxLength={50}
              />
              <p className="text-xs text-gray-400">
                At least 3 characters: letters, numbers, . _ -
              </p>
            </Field>
          )}
          <Field>
            <FieldLabel>Email</FieldLabel>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Optional"
            />
          </Field>
          <RoleSelect value={role} onChange={setRole} disabled={isSelf} />
          {!editing && (
            <Field>
              <FieldLabel>Password</FieldLabel>
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                maxLength={72}
              />
              <p className="text-xs text-gray-400">
                At least {MIN_PASSWORD_LENGTH} characters. Share it with the
                person privately; they can change it on their Profile page.
              </p>
            </Field>
          )}
          {editing && (
            <Field orientation="horizontal">
              <Switch
                checked={isActive}
                onCheckedChange={setIsActive}
                disabled={isSelf}
              />
              <FieldLabel className="font-normal">
                Active (an inactive account can't sign in)
              </FieldLabel>
            </Field>
          )}
        </div>
        <DialogFooter>
          <DialogClose render={<Button variant="outline">Cancel</Button>} />
          <Button onClick={() => void save()} disabled={isSaving || !canSave}>
            {isSaving ? <Spinner /> : "Save"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/** Admin sets a new password for an account; its sessions are signed out. */
export function ResetPasswordDialog({
  user,
  onOpenChange,
  onDone,
}: {
  user: User | null;
  onOpenChange: (open: boolean) => void;
  onDone?: () => void;
}) {
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const mismatch = confirm.length > 0 && confirm !== password;

  const save = async () => {
    if (!user) return;
    setIsSaving(true);
    try {
      await usersApi.resetPassword(user.id, password);
      toast.success(
        "Password reset",
        user.password_reset_requested_at
          ? `Tell ${user.username} the new password; their request is closed.`
          : `${user.username} is signed out everywhere and must use the new password.`,
      );
      onDone?.();
      onOpenChange(false);
    } catch (err) {
      toast.error(
        "Couldn't reset password",
        err instanceof ApiError ? err.message : undefined,
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog
      open={user !== null}
      onOpenChange={(open) => {
        if (!isSaving) onOpenChange(open);
      }}
    >
      <DialogContent className="max-w-[calc(100%-2rem)] sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Reset password · {user?.username}</DialogTitle>
          <DialogDescription>
            {user?.role === "ai_service"
              ? "The detection scripts use this account: update UNIVERSE_API_PASSWORD in backend/.env too, then restart monitoring."
              : "All of this account's open sessions are signed out."}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <Field>
            <FieldLabel>New password</FieldLabel>
            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="new-password"
              maxLength={72}
            />
            <p className="text-xs text-gray-400">
              At least {MIN_PASSWORD_LENGTH} characters.
            </p>
          </Field>
          <Field>
            <FieldLabel>Repeat new password</FieldLabel>
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
        </div>
        <DialogFooter>
          <DialogClose render={<Button variant="outline">Cancel</Button>} />
          <Button
            onClick={() => void save()}
            disabled={
              isSaving ||
              password.length < MIN_PASSWORD_LENGTH ||
              confirm !== password
            }
          >
            {isSaving ? <Spinner /> : "Reset password"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
