import { PageMeta } from "@/components/shared/page-meta";
import { Button } from "@/components/ui/button";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/contexts";
import { ApiError, requestPasswordReset } from "@/services";
import { useState } from "react";
import { Link, Navigate } from "react-router";
import { RequestSent } from "../account-request/page";
import SignInHeader from "../sign-in/header";

/** Public "Forgot password?": no email server, so an admin sets the new password. */
export default function ForgotPasswordPage() {
  const { user, isLoading } = useAuth();
  const [username, setUsername] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (isLoading) return null;
  if (user) return <Navigate to="/" replace />;

  const submit = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      setSent((await requestPasswordReset(username.trim())).detail);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Couldn't send the request",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex w-full flex-1 flex-col lg:w-1/2">
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center">
        <PageMeta
          title="Forgot Password | UniVerse"
          description="Ask an admin to reset your UniVerse password"
        />
        <SignInHeader
          title="Forgot password?"
          description="Enter your username. An admin will set a new password for you and tell you what it is."
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
                placeholder="Enter your username"
                autoComplete="username"
                maxLength={50}
              />
            </Field>
            <Button
              type="submit"
              size="lg"
              className="w-full"
              disabled={!username.trim() || isSubmitting}
            >
              {isSubmitting ? "Sending..." : "Ask for a new password"}
            </Button>
            <p className="text-center text-sm text-gray-500 dark:text-gray-400">
              Remembered it?{" "}
              <Link to="/signin" className="text-brand-500 hover:underline">
                Sign in
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  );
}
