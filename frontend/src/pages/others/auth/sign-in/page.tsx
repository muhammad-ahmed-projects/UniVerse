import { PageMeta } from "@/components/shared/page-meta";
import { useAuth } from "@/contexts";
import { Navigate, useLocation } from "react-router";
import SignIn from "./index";

export default function SignInPage() {
  const { user, isLoading } = useAuth();
  const location = useLocation();
  const redirectTo =
    (location.state as { from?: { pathname?: string } } | null)?.from
      ?.pathname ?? "/";

  if (isLoading) return null;
  if (user) return <Navigate to={redirectTo} replace />;

  return (
    <>
      <PageMeta
        title="Sign In | UniVerse"
        description="Sign in to the UniVerse surveillance dashboard"
      />
      <SignIn />
    </>
  );
}
