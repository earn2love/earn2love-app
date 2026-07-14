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
import { ArrowLeft, ScanFace, IdCard, Lock, ShieldCheck, ShieldX } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

function Field({ label, children }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground mb-1">{label}</p>
      <div className="text-sm font-medium">{children}</div>
    </div>
  );
}

function DocPanel({ label, allowed }) {
  return (
    <div className={cn("relative rounded-lg border border-border overflow-hidden aspect-[3/2] grid place-items-center",
      allowed ? "bg-accent/40" : "bg-muted")}>
      {allowed ? (
        <div className="flex flex-col items-center gap-1.5 text-muted-foreground">
          <IdCard className="h-8 w-8 opacity-50" />
          <p className="text-xs">{label}</p>
          <p className="text-[10px] italic">Demo — document redacted</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-1.5 text-muted-foreground">
          <Lock className="h-6 w-6" />
          <p className="text-xs">{label}</p>
          <p className="text-[10px]">Restricted</p>
        </div>
      )}
    </div>
  );
}

export default function VerificationDetail() {
  const { kind, id } = useParams();
  const navigate = useNavigate();
  const { can } = useAuth();
  const [data, setData] = useState(null);
  const [dialog, setDialog] = useState(null);
  const canWrite = can(kind);

  const load = () => api.get(`/verification/${kind}/${id}/detail`).then((r) => setData(r.data)).catch((e) => toast.error(formatApiError(e.response?.data?.detail)));
  useEffect(() => { load(); }, [kind, id]);

  const run = async (reason) => {
    const { action } = dialog;
    try {
      await api.post(`/resources/${kind}/${id}/action`, { action: action.key, reason });
      toast.success(`${action.label} done`);
      setDialog(null); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); setDialog(null); }
  };

  if (!data) return (<><Topbar title="Verification" /><main className="flex-1 grid place-items-center text-muted-foreground">Loading…</main></>);
  const { item, user, history = { liveness: [], identity: [] }, audit = [], can_view_documents } = data;
  const isLiveness = kind === "liveness";

  const actions = isLiveness
    ? [{ key: "approve", label: "Approve" }, { key: "reject", label: "Reject", danger: true }, { key: "under-review", label: "Needs review" }, { key: "escalate", label: "Escalate" }]
    : [{ key: "approve", label: "Approve" }, { key: "reject", label: "Reject", danger: true }, { key: "under-review", label: "Needs review" }];

  const docs = isLiveness ? ["Liveness selfie", "Liveness video frame"] : ["Document front", "Document back", "Selfie"];

  return (
    <>
      <Topbar title={`${isLiveness ? "Liveness" : "Identity"} · ${item.id}`} subtitle={user ? user.name : ""} />
      <main className="flex-1 overflow-y-auto p-5 md:p-8 space-y-5">
        <button onClick={() => navigate(isLiveness ? "/m/liveness" : "/m/identity")} data-testid="back-to-verif" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to queue
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 space-y-5">
            {/* Documents */}
            <div className="rounded-lg border border-border bg-card p-6">
              <div className="flex items-center gap-2 mb-4">
                {isLiveness ? <ScanFace className="h-5 w-5 text-violet-500" /> : <IdCard className="h-5 w-5 text-violet-500" />}
                <h3 className="font-display font-semibold">Submitted Evidence</h3>
                <div className="ml-auto"><StatusBadge value={item.status} /></div>
              </div>
              {!can_view_documents && (
                <div className="flex items-center gap-2 rounded-md border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-700 dark:text-amber-400 mb-4">
                  <Lock className="h-3.5 w-3.5" /> Your role cannot view sensitive documents — panels are locked.
                </div>
              )}
              <div className={cn("grid gap-4", docs.length === 3 ? "grid-cols-3" : "grid-cols-2")}>
                {docs.map((d) => <DocPanel key={d} label={d} allowed={can_view_documents} />)}
              </div>
            </div>

            {/* Checks */}
            <div className="rounded-lg border border-border bg-card p-6">
              <h3 className="font-display font-semibold text-sm mb-4">Verification Checks</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {isLiveness ? (
                  <>
                    <Field label="Confidence"><span className={item.confidence_score >= 0.7 ? "text-emerald-600" : "text-amber-600"}>{item.confidence_score}</span></Field>
                    <Field label="Fraud flags"><span className={item.fraud_flags > 0 ? "text-rose-500" : ""}>{item.fraud_flags}</span></Field>
                    <Field label="Trigger">{item.trigger_reason}</Field>
                    <Field label="Device IP"><span className="font-mono text-xs">{item.device_ip}</span></Field>
                    <Field label="Country">{item.country}</Field>
                    <Field label="Submitted">{fmtDate(item.submitted_date)}</Field>
                  </>
                ) : (
                  <>
                    <Field label="Document">{item.verification_type}</Field>
                    <Field label="Risk score"><span className={item.risk_score > 60 ? "text-rose-500" : "text-emerald-600"}>{item.risk_score}</span></Field>
                    <Field label="Country">{item.country}</Field>
                    <Field label="Name match">{item.name_match ? <span className="text-emerald-600 inline-flex items-center gap-1"><ShieldCheck className="h-3.5 w-3.5" />Match</span> : <span className="text-rose-500 inline-flex items-center gap-1"><ShieldX className="h-3.5 w-3.5" />Mismatch</span>}</Field>
                    <Field label="DOB match">{item.dob_match ? <span className="text-emerald-600 inline-flex items-center gap-1"><ShieldCheck className="h-3.5 w-3.5" />Match</span> : <span className="text-rose-500 inline-flex items-center gap-1"><ShieldX className="h-3.5 w-3.5" />Mismatch</span>}</Field>
                    <Field label="Submitted">{fmtDate(item.submitted_date)}</Field>
                  </>
                )}
              </div>
            </div>

            {canWrite && (
              <div className="rounded-lg border border-border bg-card p-5">
                <h3 className="font-display font-semibold text-sm mb-3">Decision</h3>
                <div className="flex flex-wrap gap-2">
                  {actions.map((a) => (
                    <Button key={a.key} data-testid={`verif-action-${a.key}`} size="sm"
                      variant={a.danger ? "destructive" : "outline"} onClick={() => setDialog({ action: a })}>
                      {a.label}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            <div className="rounded-lg border border-border bg-card p-5">
              <h3 className="font-display font-semibold text-sm mb-3">Audit Trail</h3>
              {audit.length === 0 ? <p className="text-sm text-muted-foreground py-3">No actions recorded yet.</p> : audit.map((a) => (
                <div key={a.id} className="flex items-center gap-3 text-sm border-b border-border/60 pb-2 mb-2">
                  <StatusBadge value={a.result} />
                  <span className="font-medium">{a.action}</span>
                  <span className="text-muted-foreground">by {a.admin}</span>
                  <span className="ml-auto text-xs text-muted-foreground">{fmtDateTime(a.timestamp)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* User + history */}
          <div className="space-y-5">
            {user && (
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
                  <Field label="Verified"><StatusBadge value={user.verification_status} /></Field>
                  <Field label="Risk">{user.risk_level}</Field>
                  <Field label="Country">{user.country}</Field>
                </div>
                <Button variant="outline" size="sm" className="w-full mt-4" onClick={() => navigate(`/users/${user.id}`)}>View full profile</Button>
              </div>
            )}
            <div className="rounded-lg border border-border bg-card p-5">
              <h3 className="font-display font-semibold text-sm mb-3">Verification History</h3>
              {[...history.liveness.map((h) => ({ ...h, t: "Liveness" })), ...history.identity.map((h) => ({ ...h, t: "Identity" }))]
                .filter((h) => h.id !== item.id).length === 0 ? (
                <p className="text-sm text-muted-foreground">No other verification records.</p>
              ) : (
                [...history.liveness.map((h) => ({ ...h, t: "Liveness" })), ...history.identity.map((h) => ({ ...h, t: "Identity" }))]
                  .filter((h) => h.id !== item.id).map((h) => (
                    <div key={h.id} className="flex items-center justify-between text-sm border-b border-border/60 pb-2 mb-2">
                      <span className="text-xs text-muted-foreground">{h.t}</span>
                      <span className="font-mono text-xs">{h.id}</span>
                      <StatusBadge value={h.status} />
                    </div>
                  ))
              )}
            </div>
          </div>
        </div>
      </main>

      {dialog && (
        <ActionDialog open={!!dialog} onOpenChange={(o) => !o && setDialog(null)}
          title={`${dialog.action.label}?`} description="This decision will be recorded in the audit log."
          danger={dialog.action.danger} requireReason={dialog.action.danger}
          confirmLabel={dialog.action.label} onConfirm={run} />
      )}
    </>
  );
}
