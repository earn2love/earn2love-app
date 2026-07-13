import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { StatusBadge } from "@/components/StatusBadge";
import { ActionDialog } from "@/components/ActionDialog";
import { useAuth } from "@/context/AuthContext";
import { fmtDate, fmtDateTime } from "@/lib/format";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { ArrowLeft, ShieldAlert, UserCog } from "lucide-react";
import { toast } from "sonner";

function Field({ label, children }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground mb-1">{label}</p>
      <div className="text-sm font-medium">{children}</div>
    </div>
  );
}

export default function ReportDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { can } = useAuth();
  const [data, setData] = useState(null);
  const [dialog, setDialog] = useState(null);
  const canSafety = can("reports");
  const canUsers = can("users");

  const load = () => api.get(`/reports/${id}/detail`).then((r) => setData(r.data)).catch((e) => toast.error(formatApiError(e.response?.data?.detail)));
  useEffect(() => { load(); }, [id]);

  const run = async (reason) => {
    const { kind, action } = dialog;
    try {
      if (kind === "report") await api.post(`/resources/reports/${id}/action`, { action: action.key, reason });
      else await api.post(`/users/${data.user.id}/action`, { action: action.key, reason });
      toast.success(`${action.label} done`);
      setDialog(null); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); setDialog(null); }
  };

  if (!data) return (<><Topbar title="Report" /><main className="flex-1 grid place-items-center text-muted-foreground">Loading…</main></>);
  const { report, user, previous_reports = [], notes = [], audit = [] } = data;

  const reportActions = [
    { key: "assign", label: "Assign to me" },
    { key: "escalate", label: "Escalate" },
    { key: "resolve", label: "Resolve" },
    { key: "reject", label: "Reject", danger: true },
  ];
  const userActions = [
    { key: "freeze", label: "Freeze user", danger: true },
    { key: "ban", label: "Ban user", danger: true },
    { key: "request-verification", label: "Request verification" },
    { key: "reset-liveness", label: "Request liveness" },
  ];

  return (
    <>
      <Topbar title={`Report ${report.id}`} subtitle={`${report.category} · ${report.priority} priority`} />
      <main className="flex-1 overflow-y-auto p-5 md:p-8 space-y-5">
        <button onClick={() => navigate("/m/reports")} data-testid="back-to-reports" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to reports
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Main */}
          <div className="lg:col-span-2 space-y-5">
            <div className="rounded-lg border border-border bg-card p-6">
              <div className="flex items-center gap-2 mb-5">
                <ShieldAlert className="h-5 w-5 text-rose-500" />
                <h3 className="font-display font-semibold">Case Details</h3>
                <div className="ml-auto flex gap-2"><StatusBadge value={report.priority} /><StatusBadge value={report.status} /></div>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-5">
                <Field label="Report ID"><span className="font-mono text-xs">{report.id}</span></Field>
                <Field label="Category">{report.category}</Field>
                <Field label="Country">{report.country}</Field>
                <Field label="Reporter">{report.reporter}</Field>
                <Field label="Reported User">{report.reported_user}</Field>
                <Field label="Assigned">{report.assigned_admin}</Field>
                <Field label="Created">{fmtDate(report.created_date)}</Field>
              </div>
              <div className="mt-5 rounded-md border border-dashed border-border p-4 text-sm text-muted-foreground">
                Evidence: message references, uploaded files and call references would appear here.
                <span className="italic"> (Demo — no live evidence attached.)</span>
              </div>
            </div>

            {canSafety && (
              <div className="rounded-lg border border-border bg-card p-5">
                <h3 className="font-display font-semibold text-sm mb-3">Case Actions</h3>
                <div className="flex flex-wrap gap-2">
                  {reportActions.map((a) => (
                    <Button key={a.key} data-testid={`report-action-${a.key}`} size="sm"
                      variant={a.danger ? "destructive" : "outline"} onClick={() => setDialog({ kind: "report", action: a })}>
                      {a.label}
                    </Button>
                  ))}
                </div>
                {canUsers && user && (
                  <>
                    <div className="flex items-center gap-2 mt-5 mb-2 text-sm font-medium"><UserCog className="h-4 w-4" /> Actions on reported user</div>
                    <div className="flex flex-wrap gap-2">
                      {userActions.map((a) => (
                        <Button key={a.key} data-testid={`report-user-action-${a.key}`} size="sm"
                          variant={a.danger ? "destructive" : "outline"} onClick={() => setDialog({ kind: "user", action: a })}>
                          {a.label}
                        </Button>
                      ))}
                    </div>
                  </>
                )}
              </div>
            )}

            <div className="rounded-lg border border-border bg-card p-5">
              <h3 className="font-display font-semibold text-sm mb-3">Previous Reports ({previous_reports.length})</h3>
              {previous_reports.length === 0 ? <p className="text-sm text-muted-foreground py-4">No previous reports against this user.</p> : (
                <div className="space-y-2">
                  {previous_reports.map((p) => (
                    <div key={p.id} className="flex items-center justify-between text-sm border-b border-border/60 pb-2">
                      <span className="font-mono text-xs">{p.id}</span>
                      <span className="text-muted-foreground">{p.category}</span>
                      <StatusBadge value={p.status} />
                      <span className="text-xs text-muted-foreground">{fmtDate(p.created_date)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-lg border border-border bg-card p-5">
              <h3 className="font-display font-semibold text-sm mb-3">Case Audit Trail</h3>
              {audit.length === 0 ? <p className="text-sm text-muted-foreground py-4">No actions recorded yet.</p> : (
                <div className="space-y-2">
                  {audit.map((a) => (
                    <div key={a.id} className="flex items-center gap-3 text-sm border-b border-border/60 pb-2">
                      <StatusBadge value={a.result} />
                      <span className="font-medium">{a.action}</span>
                      <span className="text-muted-foreground">by {a.admin}</span>
                      <span className="ml-auto text-xs text-muted-foreground">{fmtDateTime(a.timestamp)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Reported user sidebar */}
          <div className="space-y-5">
            {user ? (
              <div className="rounded-lg border border-border bg-card p-5">
                <div className="flex items-center gap-3 mb-4">
                  <Avatar className="h-14 w-14"><AvatarImage src={user.photo} /><AvatarFallback>{user.name?.slice(0, 2)}</AvatarFallback></Avatar>
                  <div>
                    <button onClick={() => navigate(`/users/${user.id}`)} className="font-display font-semibold hover:text-primary text-left">{user.name}</button>
                    <p className="text-xs text-muted-foreground font-mono">{user.id}</p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <Field label="Status"><StatusBadge value={user.account_status} /></Field>
                  <Field label="Tier"><StatusBadge value={user.tier} /></Field>
                  <Field label="Verified"><StatusBadge value={user.verification_status} /></Field>
                  <Field label="Risk">{user.risk_level}</Field>
                  <Field label="Reports"><span className={user.reports_count >= 3 ? "text-rose-500" : ""}>{user.reports_count}</span></Field>
                  <Field label="Country">{user.country}</Field>
                </div>
                <Button variant="outline" size="sm" className="w-full mt-4" onClick={() => navigate(`/users/${user.id}`)}>View full profile</Button>
              </div>
            ) : <div className="rounded-lg border border-border bg-card p-5 text-sm text-muted-foreground">Reported user record unavailable.</div>}

            <div className="rounded-lg border border-border bg-card p-5">
              <h3 className="font-display font-semibold text-sm mb-3">Internal Notes</h3>
              {notes.length === 0 ? <p className="text-sm text-muted-foreground">No notes.</p> : notes.map((n) => (
                <div key={n.id} className="text-sm border-b border-border/60 pb-2 mb-2">
                  <div className="flex justify-between"><span className="font-medium">{n.admin}</span><span className="text-xs text-muted-foreground">{fmtDate(n.created_at)}</span></div>
                  <p className="text-muted-foreground">{n.text}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      {dialog && (
        <ActionDialog open={!!dialog} onOpenChange={(o) => !o && setDialog(null)}
          title={`${dialog.action.label}?`} description="This will be recorded in the audit log."
          danger={dialog.action.danger} requireReason={dialog.action.danger}
          confirmLabel={dialog.action.label} onConfirm={run} />
      )}
    </>
  );
}
