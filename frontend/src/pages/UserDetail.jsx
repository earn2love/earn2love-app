import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { StatusBadge } from "@/components/StatusBadge";
import { useAuth } from "@/context/AuthContext";
import { fmtDate, fmtDateTime, fmtCurrency, fmtNum } from "@/lib/format";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ArrowLeft, Coins } from "lucide-react";
import { toast } from "sonner";

function Field({ label, children }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground mb-1">{label}</p>
      <div className="text-sm font-medium">{children}</div>
    </div>
  );
}

function MiniTable({ columns, rows, empty }) {
  if (!rows?.length) return <p className="text-sm text-muted-foreground py-8 text-center">{empty}</p>;
  return (
    <div className="overflow-x-auto rounded-lg border border-border">
      <table className="w-full text-sm">
        <thead><tr className="border-b border-border text-[11px] uppercase tracking-wider text-muted-foreground">
          {columns.map((c) => <th key={c.key} className="text-left px-4 py-2.5 font-semibold">{c.label}</th>)}
        </tr></thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.id || i} className="border-b border-border/60">
              {columns.map((c) => <td key={c.key} className="px-4 py-2.5">{c.render ? c.render(r) : (r[c.key] ?? "—")}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function UserDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { can } = useAuth();
  const [user, setUser] = useState(null);
  const [related, setRelated] = useState({});
  const [note, setNote] = useState("");

  const load = async () => {
    try {
      const [u, rel] = await Promise.all([
        api.get(`/resources/users/${id}`),
        api.get(`/users/${id}/related`),
      ]);
      setUser(u.data); setRelated(rel.data);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  useEffect(() => { load(); }, [id]);

  const addNote = async () => {
    if (!note.trim()) return;
    try {
      await api.post(`/users/${id}/note`, { action: "note", reason: note });
      toast.success("Note added");
      setNote(""); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  if (!user) {
    return (<><Topbar title="User Profile" /><main className="flex-1 grid place-items-center text-muted-foreground">Loading…</main></>);
  }

  const sym = user.currency_symbol || "";

  return (
    <>
      <Topbar title="User Profile" subtitle={user.id} />
      <main className="flex-1 overflow-y-auto p-5 md:p-8 space-y-5">
        <button onClick={() => navigate("/users")} data-testid="back-to-users" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to users
        </button>

        {/* Header card */}
        <div className="rounded-lg border border-border bg-card p-6">
          <div className="flex flex-col sm:flex-row sm:items-center gap-5">
            <Avatar className="h-20 w-20 border-2 border-border">
              <AvatarImage src={user.photo} alt={user.name} />
              <AvatarFallback>{user.name?.slice(0, 2).toUpperCase()}</AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <div className="flex items-center gap-2.5 flex-wrap">
                <h2 className="font-display text-2xl font-bold tracking-tight">{user.name}</h2>
                {user.online && <span className="inline-flex items-center gap-1.5 text-xs text-emerald-600"><span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />Online</span>}
              </div>
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                <StatusBadge value={user.account_status} />
                <StatusBadge value={user.tier} />
                <StatusBadge value={user.verification_status} />
                <span className="text-xs text-muted-foreground">Risk: <span className="font-medium text-foreground">{user.risk_level}</span></span>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div><p className="font-display text-xl font-bold text-slate-400">{fmtNum(user.wallet_silver)}</p><p className="text-[10px] uppercase tracking-wide text-muted-foreground">Silver</p></div>
              <div><p className="font-display text-xl font-bold text-amber-500">{fmtNum(user.wallet_gold)}</p><p className="text-[10px] uppercase tracking-wide text-muted-foreground">Gold</p></div>
              <div><p className="font-display text-xl font-bold text-sky-500">{fmtNum(user.wallet_diamond)}</p><p className="text-[10px] uppercase tracking-wide text-muted-foreground">Diamond</p></div>
            </div>
          </div>
        </div>

        <Tabs defaultValue="overview">
          <TabsList className="flex flex-wrap h-auto">
            {["overview", "wallet", "payments", "withdrawals", "reports", "calls", "notes", "audit"].map((t) => (
              <TabsTrigger key={t} value={t} data-testid={`tab-${t}`} className="capitalize">{t}</TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="overview" className="mt-4">
            <div className="rounded-lg border border-border bg-card p-6 grid grid-cols-2 md:grid-cols-4 gap-5">
              <Field label="User ID"><span className="font-mono text-xs">{user.id}</span></Field>
              <Field label="Age">{user.age}</Field>
              <Field label="Gender">{user.gender}</Field>
              <Field label="Country">{user.country}</Field>
              <Field label="Email"><span className="text-xs">{user.email}</span></Field>
              <Field label="Phone"><span className="text-xs">{user.phone}</span></Field>
              <Field label="Joined">{fmtDate(user.join_date)}</Field>
              <Field label="Last seen">{fmtDate(user.last_seen)}</Field>
              <Field label="Reports"><span className={user.reports_count >= 3 ? "text-rose-500" : ""}>{user.reports_count}</span></Field>
              <Field label="Wallet frozen">{user.wallet_frozen ? "Yes" : "No"}</Field>
              <Field label="Lifetime revenue">{fmtCurrency(user.lifetime_revenue, user.currency)}</Field>
              <Field label="Lifetime earnings">{fmtCurrency(user.lifetime_earnings, user.currency)}</Field>
            </div>
          </TabsContent>

          <TabsContent value="wallet" className="mt-4">
            <MiniTable empty="No wallet transactions" rows={related.transactions} columns={[
              { key: "id", label: "Tx", render: (r) => <span className="font-mono text-xs">{r.id}</span> },
              { key: "coin_type", label: "Coin", render: (r) => <StatusBadge value={r.coin_type} /> },
              { key: "type", label: "Type" },
              { key: "amount", label: "Amount", render: (r) => <span className="font-mono">{r.amount}</span> },
              { key: "reason", label: "Reason" },
              { key: "status", label: "Status", render: (r) => <StatusBadge value={r.status} /> },
              { key: "date", label: "Date", render: (r) => fmtDate(r.date) },
            ]} />
          </TabsContent>

          <TabsContent value="payments" className="mt-4">
            <MiniTable empty="No payments" rows={related.payments} columns={[
              { key: "id", label: "Payment", render: (r) => <span className="font-mono text-xs">{r.id}</span> },
              { key: "gateway", label: "Gateway" },
              { key: "payment_type", label: "Type" },
              { key: "amount", label: "Amount", render: (r) => fmtCurrency(r.amount, r.currency) },
              { key: "status", label: "Status", render: (r) => <StatusBadge value={r.status} /> },
              { key: "created_date", label: "Date", render: (r) => fmtDate(r.created_date) },
            ]} />
          </TabsContent>

          <TabsContent value="withdrawals" className="mt-4">
            <MiniTable empty="No withdrawals" rows={related.withdrawals} columns={[
              { key: "id", label: "ID", render: (r) => <span className="font-mono text-xs">{r.id}</span> },
              { key: "diamond_amount", label: "Diamonds", render: (r) => <span className="font-mono">{r.diamond_amount}</span> },
              { key: "cash_amount", label: "Cash", render: (r) => fmtCurrency(r.cash_amount, r.currency) },
              { key: "payment_method", label: "Method" },
              { key: "status", label: "Status", render: (r) => <StatusBadge value={r.status} /> },
            ]} />
          </TabsContent>

          <TabsContent value="reports" className="mt-4">
            <MiniTable empty="No reports against this user" rows={related.reports} columns={[
              { key: "id", label: "Report", render: (r) => <span className="font-mono text-xs">{r.id}</span> },
              { key: "reporter", label: "Reporter" },
              { key: "category", label: "Category" },
              { key: "priority", label: "Priority", render: (r) => <StatusBadge value={r.priority} /> },
              { key: "status", label: "Status", render: (r) => <StatusBadge value={r.status} /> },
            ]} />
          </TabsContent>

          <TabsContent value="calls" className="mt-4">
            <MiniTable empty="No calls" rows={related.calls} columns={[
              { key: "id", label: "Call", render: (r) => <span className="font-mono text-xs">{r.id}</span> },
              { key: "call_type", label: "Type", render: (r) => <StatusBadge value={r.call_type} /> },
              { key: "duration", label: "Min" },
              { key: "silver_charged", label: "Charged", render: (r) => <span className="font-mono">{r.silver_charged}</span> },
              { key: "status", label: "Status", render: (r) => <StatusBadge value={r.status} /> },
            ]} />
          </TabsContent>

          <TabsContent value="notes" className="mt-4 space-y-4">
            {can("users") && (
              <div className="rounded-lg border border-border bg-card p-4 space-y-3">
                <Textarea data-testid="note-input" placeholder="Add an internal note about this user…" value={note} onChange={(e) => setNote(e.target.value)} rows={3} />
                <Button data-testid="add-note-btn" onClick={addNote} disabled={!note.trim()} className="gradient-brand text-white border-0">Add note</Button>
              </div>
            )}
            <div className="space-y-2">
              {(related.notes || []).length === 0 && <p className="text-sm text-muted-foreground text-center py-6">No notes yet</p>}
              {(related.notes || []).map((n) => (
                <div key={n.id} className="rounded-lg border border-border bg-card p-4">
                  <div className="flex items-center justify-between mb-1">
                    <p className="text-sm font-medium">{n.admin}</p>
                    <p className="text-xs text-muted-foreground">{fmtDateTime(n.created_at)}</p>
                  </div>
                  <p className="text-sm text-muted-foreground">{n.text}</p>
                </div>
              ))}
            </div>
          </TabsContent>

          <TabsContent value="audit" className="mt-4">
            <MiniTable empty="No audit history for this user" rows={related.audit} columns={[
              { key: "action", label: "Action" },
              { key: "admin", label: "Admin" },
              { key: "role", label: "Role" },
              { key: "reason", label: "Reason" },
              { key: "result", label: "Result", render: (r) => <StatusBadge value={r.result} /> },
              { key: "timestamp", label: "Time", render: (r) => fmtDateTime(r.timestamp) },
            ]} />
          </TabsContent>
        </Tabs>
      </main>
    </>
  );
}
