import { PageMeta } from "@/components/shared/page-meta";
import { Button } from "@/components/ui/button";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/contexts";
import { CheckCircleIcon } from "@/icons";
import { ApiError, MIN_PASSWORD_LENGTH, requestAccount } from "@/services";
import { useState } from "react";
import { Link, Navigate } from "react-router";
import SignInHeader from "../sign-in/header";

const USERNAME_PATTERN = /^[A-Za-z0-9_.-]{3,50}$/;

function Shell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex w-full flex-1 flex-col lg:w-1/2">
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center">
        {children}
      </div>
    </div>
  );
}

export function RequestSent({ message }: { message: string }) {
  return (
    <div className="space-y-5">
      <div className="flex gap-3 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700 dark:bg-green-500/10 dark:text-green-400">
        <CheckCircleIcon className="size-5 shrink-0" />
        <p>{message}</p>
      </div>
      <Link
        to="/signin"
        className="block text-sm font-medium text-brand-500 hover:underline"
      >
        Back to sign in
      </Link>
    </div>
  );
}

/** Public "Create account": the account waits for an admin's approval. */
export default function AccountRequestPage() {
  const { user, isLoading } = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isLoading) return null;
  if (user) return <Navigate to="/" replace />;

  const usernameInvalid =
    username.length > 0 && !USERNAME_PATTERN.test(username);
  const mismatch = confirm.length > 0 && confirm !== password;
  const canSubmit =
    USERNAME_PATTERN.test(username) &&
    password.length >= MIN_PASSWORD_LENGTH &&
    password === confirm;

  const submit = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      const { detail } = await requestAccount({
        username: username.trim(),
        email: email.trim() || undefined,
        password,
      });
      setSent(detail);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Couldn't send the request",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Shell>
      <PageMeta
        title="Create Account | UniVerse"
        description="Request a UniVerse dashboard account"
      />
      <SignInHeader
        title="Create account"
        description="Ask for access to the UniVerse dashboard. An admin reviews every request and chooses your role before you can sign in."
      />
      {sent ? (
        <RequestSent message={sent} />
      ) : (
        <form
          className="space-y-5"
          noValidate
          onSubmit={(e) => {
            e.preventDefault();
            void submit();
          }}
        >
          {error && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-600 dark:bg-red-500/10 dark:text-red-400">
              {error}
            </div>
          )}
          <Field>
            <FieldLabel>
              Username <span className="text-red-500">*</span>
            </FieldLabel>
            <Input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. aiman"
              autoComplete="username"
              maxLength={50}
              aria-invalid={usernameInvalid || undefined}
            />
            <p
              className={
                usernameInvalid
                  ? "text-xs text-red-500"
                  : "text-xs text-gray-400"
              }
            >
              3-50 characters: letters, numbers, . _ -
            </p>
          </Field>
          <Field>
            <FieldLabel>Email</FieldLabel>
            <Input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Optional, so the admin can reach you"
              autoComplete="email"
            />
          </Field>
          <Field>
            <FieldLabel>
              Password <span className="text-red-500">*</span>
            </FieldLabel>
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
            <FieldLabel>
              Repeat password <span className="text-red-500">*</span>
            </FieldLabel>
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
            size="lg"
            className="w-full"
            disabled={!canSubmit || isSubmitting}
          >
            {isSubmitting ? "Sending..." : "Request account"}
          </Button>
          <p className="text-center text-sm text-gray-500 dark:text-gray-400">
            Already have an account?{" "}
            <Link to="/signin" className="text-brand-500 hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      )}
    </Shell>
  );
}
