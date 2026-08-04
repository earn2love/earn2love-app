import "@/App.css";

import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";
import { ThemeProvider } from "next-themes";

import { AuthProvider, useAuth } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Layout } from "@/components/Layout";
import { Toaster } from "@/components/ui/sonner";
import { homeForRole } from "@/lib/portal";

import Login from "@/pages/Login";
import Dashboard from "@/pages/Dashboard";
import Users from "@/pages/Users";
import UserDetail from "@/pages/UserDetail";
import ModulePage from "@/pages/ModulePage";
import ReportDetail from "@/pages/ReportDetail";
import TicketDetail from "@/pages/TicketDetail";
import VerificationDetail from "@/pages/VerificationDetail";
import Notifications from "@/pages/Notifications";
import Documents from "@/pages/Documents";
import AppConfig from "@/pages/AppConfig";
import CallConfig from "@/pages/CallConfig";
import Games from "@/pages/Games";
import AiProfiles from "@/pages/AiProfiles";
import PortalDashboard from "@/pages/PortalDashboard";
import Support from "@/pages/Support";
import Employees from "@/pages/Employees";
import Permissions from "@/pages/Permissions";
import Profile from "@/pages/Profile";
import Analytics from "@/pages/Analytics";
import Settings from "@/pages/Settings";
import Roles from "@/pages/Roles";
import Countries from "@/pages/Countries";

const ADMIN_ROLES = [
  "super_admin",
  "moderator",
  "support_agent",
  "finance_admin",
  "verification_agent",
];

const HR_ROLES = [
  "hr_admin",
  "hr_manager",
  "payroll_admin",
];

function HomeRedirect() {
  const { admin } = useAuth();

  if (!admin) return <Navigate to="/login" replace />;

  return <Navigate to={homeForRole(admin.role)} replace />;
}

function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />

            <Route
              element={(
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              )}
            >
              <Route path="/" element={<HomeRedirect />} />

              <Route
                path="/admin"
                element={(
                  <ProtectedRoute roles={ADMIN_ROLES}>
                    <Dashboard />
                  </ProtectedRoute>
                )}
              />

              <Route
                path="/hr"
                element={(
                  <ProtectedRoute roles={HR_ROLES}>
                    <PortalDashboard portal="hr" />
                  </ProtectedRoute>
                )}
              />

              <Route
                path="/employee"
                element={(
                  <ProtectedRoute roles={["employee"]}>
                    <PortalDashboard portal="employee" />
                  </ProtectedRoute>
                )}
              />

              <Route
                path="/analytics"
                element={
                  <ProtectedRoute roles={ADMIN_ROLES}>
                    <Analytics />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/users"
                element={
                  <ProtectedRoute roles={ADMIN_ROLES}>
                    <Users />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/users/:id"
                element={
                  <ProtectedRoute roles={ADMIN_ROLES}>
                    <UserDetail />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/reports/:id"
                element={
                  <ProtectedRoute roles={["super_admin", "moderator"]}>
                    <ReportDetail />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/tickets/:id"
                element={
                  <ProtectedRoute roles={["super_admin", "support_agent"]}>
                    <TicketDetail />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/verification/:kind/:id"
                element={
                  <ProtectedRoute roles={["super_admin", "verification_agent"]}>
                    <VerificationDetail />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/notifications"
                element={
                  <ProtectedRoute roles={["super_admin", "support_agent"]}>
                    <Notifications />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/documents"
                element={<Documents />}
              />

              <Route
                path="/app-config"
                element={
                  <ProtectedRoute roles={["super_admin", "finance_admin"]}>
                    <AppConfig />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/call-config"
                element={(
                  <ProtectedRoute roles={["super_admin", "finance_admin"]}>
                    <CallConfig />
                  </ProtectedRoute>
                )}
              />

              <Route
                path="/games"
                element={(
                  <ProtectedRoute roles={["super_admin"]}>
                    <Games />
                  </ProtectedRoute>
                )}
              />

              <Route
                path="/ai-profiles"
                element={(
                  <ProtectedRoute roles={["super_admin"]}>
                    <AiProfiles />
                  </ProtectedRoute>
                )}
              />

              <Route
                path="/support"
                element={
                  <ProtectedRoute roles={["super_admin", "moderator", "support_agent"]}>
                    <Support />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/employees"
                element={
                  <ProtectedRoute roles={["super_admin", "hr_admin", "hr_manager", "payroll_admin"]}>
                    <Employees />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/permissions"
                element={
                  <ProtectedRoute roles={["super_admin"]}>
                    <Permissions />
                  </ProtectedRoute>
                }
              />

              <Route path="/profile" element={<Profile />} />

              <Route
                path="/m/:key"
                element={
                  <ProtectedRoute roles={ADMIN_ROLES}>
                    <ModulePage />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/countries"
                element={
                  <ProtectedRoute roles={["super_admin", "finance_admin"]}>
                    <Countries />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/settings"
                element={
                  <ProtectedRoute roles={["super_admin"]}>
                    <Settings />
                  </ProtectedRoute>
                }
              />

              <Route
                path="/roles"
                element={
                  <ProtectedRoute roles={["super_admin"]}>
                    <Roles />
                  </ProtectedRoute>
                }
              />

              <Route path="*" element={<HomeRedirect />} />
            </Route>
          </Routes>
        </BrowserRouter>

        <Toaster position="top-right" richColors closeButton />
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
