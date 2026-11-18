import ProtectedRoute from "@/components/auth/protected-route";
import AppLayout from "@/components/layout/app-layout";
import { Error404Page } from "@/pages/main/pages";
import AlertsPage from "@/pages/main/surveillance/alerts";
import CamerasPage from "@/pages/main/surveillance/cameras";
import IncidentsPage from "@/pages/main/surveillance/incidents";
import LiveViewPage from "@/pages/main/surveillance/live";
import OverviewPage from "@/pages/main/surveillance/overview";
import PeoplePage from "@/pages/main/surveillance/people";
import ProfilePage from "@/pages/main/surveillance/profile";
import SettingsPage from "@/pages/main/surveillance/settings";
import UsersPage from "@/pages/main/surveillance/users";
import {
  AccountRequestPage,
  AuthLayout,
  ForgotPasswordPage,
  SignInPage,
} from "@/pages/others/auth";
import "flatpickr/dist/flatpickr.css";
import { Route, Routes } from "react-router";

export default function App() {
  return (
    <Routes>
      {/* Dashboard Layout */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<OverviewPage />} />
          <Route path="/live" element={<LiveViewPage />} />
          <Route path="/cameras" element={<CamerasPage />} />
          <Route path="/surveillance-alerts" element={<AlertsPage />} />
          <Route path="/incidents" element={<IncidentsPage />} />
          <Route path="/people" element={<PeoplePage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/users" element={<UsersPage />} />
          <Route path="/profile" element={<ProfilePage />} />
        </Route>
      </Route>

      {/* Auth Layout */}
      <Route element={<AuthLayout />}>
        <Route path="/signin" element={<SignInPage />} />
        <Route path="/signup" element={<AccountRequestPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      </Route>

      {/* Full-width / Error / Status Pages */}
      <Route path="/error-404" element={<Error404Page />} />

      {/* Fallback Route */}
      <Route path="*" element={<Error404Page />} />
    </Routes>
  );
}
