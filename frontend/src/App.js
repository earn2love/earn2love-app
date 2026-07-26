import "@/App.css";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { ThemeProvider } from "next-themes";
import { AuthProvider } from "@/context/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { Layout } from "@/components/Layout";
import { Toaster } from "@/components/ui/sonner";

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
import Analytics from "@/pages/Analytics";
import Settings from "@/pages/Settings";
import Roles from "@/pages/Roles";
import Countries from "@/pages/Countries";

function App() {
  return (
    <ThemeProvider attribute="class" defaultTheme="dark" enableSystem={false}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/analytics" element={<Analytics />} />
              <Route path="/users" element={<Users />} />
              <Route path="/users/:id" element={<UserDetail />} />
              <Route path="/reports/:id" element={<ReportDetail />} />
              <Route path="/tickets/:id" element={<TicketDetail />} />
              <Route path="/verification/:kind/:id" element={<VerificationDetail />} />
              <Route path="/notifications" element={<Notifications />} />
              <Route path="/documents" element={<Documents />} />
              <Route path="/m/:key" element={<ModulePage />} />
              <Route path="/countries" element={<Countries />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/roles" element={<Roles />} />
            </Route>
          </Routes>
        </BrowserRouter>
        <Toaster position="top-right" richColors closeButton />
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
