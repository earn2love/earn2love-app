import { useEffect, useState } from "react";
import {
  BriefcaseBusiness,
  CalendarDays,
  ClipboardCheck,
  FileText,
  ReceiptText,
  UserRound,
} from "lucide-react";

import api from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { useAuth } from "@/context/AuthContext";

export default function PortalDashboard({ portal }) {
  const { admin } = useAuth();
  const [profile, setProfile] = useState(null);

  useEffect(() => {
    api.get("/me/profile")
      .then(({ data }) => setProfile(data.profile || null))
      .catch(() => setProfile(null));
  }, []);

  const isHr = portal === "hr";

  const cards = isHr
    ? [
        ["Employees", "Team records and onboarding", BriefcaseBusiness],
        ["Attendance", "Review attendance records", CalendarDays],
        ["Leave", "Approve and track leave", ClipboardCheck],
        ["Payroll", "Payroll and payslip operations", ReceiptText],
      ]
    : [
        ["My Profile", "Personal and employment details", UserRound],
        ["Attendance", "My attendance history", CalendarDays],
        ["Leave", "My leave requests", ClipboardCheck],
        ["Payslips", "My payroll documents", ReceiptText],
        ["Documents", "Contracts and internal documents", FileText],
      ];

  return (
    <div>
      <Topbar
        title={isHr ? "HR Portal" : "Employee Portal"}
        subtitle={`Welcome ${profile?.firstName || admin?.name || ""}`}
      />

      <div className="p-6 space-y-6">
        <div className="rounded-2xl border border-border bg-card p-6">
          <p className="text-sm text-muted-foreground">
            Signed in as
          </p>
          <h2 className="mt-1 text-xl font-bold">
            {profile
              ? `${profile.firstName || ""} ${profile.lastName || ""}`.trim()
              : admin?.name}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {profile?.designation || admin?.role?.replaceAll("_", " ")}
          </p>
        </div>

        <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-4">
          {cards.map(([title, subtitle, Icon]) => (
            <div
              key={title}
              className="rounded-xl border border-border bg-card p-5"
            >
              <Icon className="h-5 w-5 text-pink-500" />
              <h3 className="mt-3 font-semibold">{title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                {subtitle}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
