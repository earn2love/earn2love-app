import { useEffect, useState, useCallback } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { useAuth } from "@/context/AuthContext";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Loader2, UserCircle2, ShieldCheck, Wallet, CalendarDays, Award, BadgeCheck, Mail, Phone, Building2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const KYC_META = {
  approved: "text-emerald-500 border-emerald-500/30 bg-emerald-500/10",
  pending: "text-amber-500 border-amber-500/30 bg-amber-500/10",
  rejected: "text-rose-500 border-rose-500/30 bg-rose-500/10",
  not_started: "text-muted-foreground border-border bg-muted/40",
};

export default function Profile() {
  const { admin } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ firstName: "", lastName: "", phone: "", department: "", designation: "" });

  const load = useCallback(async () => {
    setLoading(true);
    try { const { data } = await api.get("/me/profile"); setProfile(data.profile); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const createProfile = async () => {
    if (!form.firstName.trim()) { toast.error("First name is required"); return; }
    setCreating(true);
    try { const { data } = await api.post("/me/profile", form); setProfile(data); toast.success("Your HR profile has been created"); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setCreating(false);
  };

  return (
    <div data-testid="profile-page">
      <Topbar title="My Profile" subtitle="Your admin account and HR record" />
      <div className="p-6 max-w-5xl space-y-5">
        {/* Identity header card */}
        <div className="rounded-xl border border-border bg-card p-5 flex items-center gap-4">
          <div className="grid place-items-center h-16 w-16 rounded-full gradient-brand text-white text-xl font-bold shrink-0">
            {admin?.initials || "AD"}
          </div>
          <div className="min-w-0 flex-1">
            <p className="font-display font-bold text-lg truncate">{profile ? `${profile.firstName} ${profile.lastName}` : admin?.name}</p>
            <p className="text-sm text-muted-foreground truncate flex items-center gap-1.5"><Mail className="h-3.5 w-3.5" />{admin?.email}</p>
            <div className="flex items-center gap-2 mt-1.5">
              <span className="text-[11px] px-2 py-0.5 rounded-full border border-pink-500/30 bg-pink-500/10 text-pink-500 capitalize">{admin?.role?.replace(/_/g, " ")}</span>
              {profile?.employeeCode && <span className="text-[11px] px-2 py-0.5 rounded-full border border-border font-mono">{profile.employeeCode}</span>}
            </div>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : !profile ? (
          <div data-testid="profile-create" className="rounded-xl border border-border bg-card p-6 space-y-4">
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <UserCircle2 className="h-5 w-5" /> You don't have an HR record yet. Create one to track your KYC, badge, payslips and attendance.
            </div>
            <div className="grid grid-cols-2 gap-3 max-w-xl">
              <div><Label>First name</Label><Input data-testid="profile-firstName" value={form.firstName} onChange={(e) => setForm({ ...form, firstName: e.target.value })} /></div>
              <div><Label>Last name</Label><Input data-testid="profile-lastName" value={form.lastName} onChange={(e) => setForm({ ...form, lastName: e.target.value })} /></div>
              <div><Label>Phone</Label><Input value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
              <div><Label>Department</Label><Input value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} /></div>
              <div className="col-span-2"><Label>Designation</Label><Input value={form.designation} onChange={(e) => setForm({ ...form, designation: e.target.value })} /></div>
            </div>
            <Button onClick={createProfile} disabled={creating} data-testid="profile-create-btn" className="gradient-brand text-white border-0">
              {creating && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />}Create my HR profile
            </Button>
          </div>
        ) : (
          <Tabs defaultValue="overview" className="space-y-4">
            <TabsList className="flex-wrap h-auto">
              <TabsTrigger value="overview"><BadgeCheck className="h-4 w-4 mr-1" />Overview</TabsTrigger>
              <TabsTrigger value="kyc"><ShieldCheck className="h-4 w-4 mr-1" />KYC & Badge</TabsTrigger>
              <TabsTrigger value="payslips"><Wallet className="h-4 w-4 mr-1" />Payslips</TabsTrigger>
              <TabsTrigger value="attendance"><CalendarDays className="h-4 w-4 mr-1" />Attendance</TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="mt-0">
              <div className="grid sm:grid-cols-2 gap-3">
                <InfoRow icon={Building2} label="Department" value={profile.department} />
                <InfoRow icon={BadgeCheck} label="Designation" value={profile.designation} />
                <InfoRow icon={Phone} label="Phone" value={profile.phone} />
                <InfoRow icon={ShieldCheck} label="Status" value={profile.status} />
                <InfoRow icon={Award} label="Badge" value={profile.badge?.level ? `${profile.badge.level}${profile.badge.title ? ` · ${profile.badge.title}` : ""}` : "—"} />
                <InfoRow icon={CalendarDays} label="Joined" value={profile.joinDate ? new Date(profile.joinDate).toLocaleDateString() : (profile.createdAt ? new Date(profile.createdAt).toLocaleDateString() : "—")} />
              </div>
            </TabsContent>

            <TabsContent value="kyc" className="mt-0 space-y-4">
              <div className="rounded-xl border border-border bg-card p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase text-muted-foreground tracking-wide">KYC status</p>
                    <span className={cn("inline-block mt-1.5 text-xs px-2.5 py-1 rounded-full border capitalize", KYC_META[profile.kyc?.status || "not_started"])}>
                      {(profile.kyc?.status || "not_started").replace(/_/g, " ")}
                    </span>
                  </div>
                  {profile.kyc?.docUrl && <a href={profile.kyc.docUrl} target="_blank" rel="noreferrer" className="text-pink-500 text-sm underline">View document</a>}
                </div>
              </div>
              <div className="rounded-xl border border-border bg-card p-5 flex items-center gap-3">
                <Award className="h-6 w-6 text-amber-500" />
                <div>
                  <p className="font-semibold text-sm">{profile.badge?.level || "Member"}</p>
                  <p className="text-xs text-muted-foreground">{profile.badge?.title || "No badge title"}</p>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="payslips" className="mt-0">
              <RecordTable rows={profile.payslips} cols={[["month", "Month"], ["gross", "Gross"], ["net", "Net"], ["status", "Status"]]} empty="No payslips yet." />
            </TabsContent>
            <TabsContent value="attendance" className="mt-0">
              <RecordTable rows={profile.attendance} cols={[["date", "Date"], ["status", "Status"], ["hours", "Hours"]]} empty="No attendance records yet." />
            </TabsContent>
          </Tabs>
        )}
      </div>
    </div>
  );
}

function InfoRow({ icon: Icon, label, value }) {
  return (
    <div className="rounded-lg border border-border bg-card px-4 py-3 flex items-center gap-3">
      <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
      <div className="min-w-0">
        <p className="text-[11px] uppercase text-muted-foreground tracking-wide">{label}</p>
        <p className="text-sm font-medium truncate capitalize">{value || "—"}</p>
      </div>
    </div>
  );
}

function RecordTable({ rows, cols, empty }) {
  if (!rows?.length) return <p className="text-sm text-muted-foreground py-10 text-center">{empty}</p>;
  return (
    <div className="rounded-xl border border-border overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-xs uppercase text-muted-foreground"><tr>{cols.map(([, l]) => <th key={l} className="text-left p-3">{l}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => (<tr key={i} className="border-t border-border">{cols.map(([k]) => <td key={k} className="p-3 capitalize">{String(r[k] ?? "—")}</td>)}</tr>))}</tbody>
      </table>
    </div>
  );
}
