import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { StatusBadge } from "@/components/StatusBadge";
import { useAuth } from "@/context/AuthContext";
import { fmtDateTime, fmtNum } from "@/lib/format";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ArrowLeft } from "lucide-react";
import { toast } from "sonner";

function Field({ label, children }) {
  return (
    <div>
      <p className="text-[10px] uppercase tracking-[0.14em] text-muted-foreground mb-1">{label}</p>
      <div className="text-sm font-medium break-words">{children ?? "—"}</div>
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
      toast.success("Note added"); setNote(""); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  if (!user) return (<><Topbar title="User Profile" /><main className="flex-1 grid place-items-center text-muted-foreground">Loading…</main></>);

  const silver = user.silverBalance ?? user.silverCoins ?? 0;
  const gold = user.goldBalance ?? user.goldCoins ?? 0;
  const diamond = user.diamondBalance ?? user.diamondCoins ?? 0;
  const status = user.banned ? "Banned" : user.frozen ? "Frozen" : (user.accountStatus || "Active");

  return (
    <>
      <Topbar title="User Profile" subtitle={user.id} />
      <main className="flex-1 overflow-y-auto p-5 md:p-8 space-y-5">
        <button onClick={() => navigate("/users")} data-testid="back-to-users" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to users
        </button>

        <div className="rounded-lg border border-border bg-card p-6">
          <div className="flex flex-col sm:flex-row sm:items-center gap-5">
            <Avatar className="h-20 w-20 border-2 border-border">
              <AvatarImage src={user.photoUrl || user.profilePhoto || user.photoURL} alt={user.displayName} />
              <AvatarFallback>{(user.displayName || user.name || user.email || "U").slice(0, 2).toUpperCase()}</AvatarFallback>
            </Avatar>
            <div className="flex-1">
              <div className="flex items-center gap-2.5 flex-wrap">
                <h2 className="font-display text-2xl font-bold tracking-tight">{user.displayName || user.name || "Unnamed"}</h2>
                {(user.isOnline || user.online) && <span className="inline-flex items-center gap-1.5 text-xs text-emerald-600"><span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />Online</span>}
              </div>
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                <StatusBadge value={status} />
                {user.tier && <StatusBadge value={user.tier} />}
                {user.subscriptionStatus && <StatusBadge value={user.subscriptionStatus} />}
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div><p className="font-display text-xl font-bold text-slate-400">{fmtNum(silver)}</p><p className="text-[10px] uppercase tracking-wide text-muted-foreground">Silver</p></div>
              <div><p className="font-display text-xl font-bold text-amber-500">{fmtNum(gold)}</p><p className="text-[10px] uppercase tracking-wide text-muted-foreground">Gold</p></div>
              <div><p className="font-display text-xl font-bold text-sky-500">{fmtNum(diamond)}</p><p className="text-[10px] uppercase tracking-wide text-muted-foreground">Diamond</p></div>
            </div>
          </div>
        </div>

        <Tabs defaultValue="overview">
          <TabsList className="flex flex-wrap h-auto">
            {["overview", "wallet", "payments", "withdrawals", "reports", "notes", "audit"].map((t) => (
              <TabsTrigger key={t} value={t} data-testid={`tab-${t}`} className="capitalize">{t}</TabsTrigger>
            ))}
          </TabsList>

          <TabsContent value="overview" className="mt-4">
            <div className="rounded-lg border border-border bg-card p-6 grid grid-cols-2 md:grid-cols-4 gap-5">
              <Field label="User UID"><span className="font-mono text-xs">{user.id}</span></Field>
              <Field label="Email"><span className="text-xs">{user.email}</span></Field>
              <Field label="Phone"><span className="text-xs">{user.phoneNumber}</span></Field>
              <Field label="Gender">{user.gender}</Field>
              <Field label="Country">{user.country}</Field>
              <Field label="Currency">{user.currencyCode} {user.currencySymbol}</Field>
              <Field label="Tier">{user.tier}</Field>
              <Field label="Sub tier">{user.subTier}</Field>
              <Field label="Selected vibe">{user.selectedVibe}</Field>
              <Field label="Login type">{user.loginType}</Field>
              <Field label="Joined">{fmtDateTime(user.createdAt)}</Field>
              <Field label="Last seen">{fmtDateTime(user.lastSeenAt)}</Field>
            </div>
          </TabsContent>

          <TabsContent value="wallet" className="mt-4">
            <MiniTable empty="No wallet transactions" rows={related.transactions} columns={[
              { key: "type", label: "Type", render: (r) => <StatusBadge value={r.type} /> },
              { key: "title", label: "Title" },
              { key: "fromCoin", label: "From" },
              { key: "toCoin", label: "To" },
              { key: "toAmount", label: "Amount", render: (r) => <span className="font-mono">{r.toAmount ?? r.fromAmount ?? "—"}</span> },
              { key: "createdAt", label: "Date", render: (r) => fmtDateTime(r.createdAt) },
            ]} />
          </TabsContent>

          <TabsContent value="payments" className="mt-4">
            <MiniTable empty="No top-up payments" rows={related.payments} columns={[
              { key: "title", label: "Title" },
              { key: "toCoin", label: "Coin" },
              { key: "toAmount", label: "Amount", render: (r) => <span className="font-mono">{r.toAmount}</span> },
              { key: "status", label: "Status", render: (r) => <StatusBadge value={r.status} /> },
              { key: "createdAt", label: "Date", render: (r) => fmtDateTime(r.createdAt) },
            ]} />
          </TabsContent>

          <TabsContent value="withdrawals" className="mt-4">
            <MiniTable empty="No withdrawals" rows={related.withdrawals} columns={[
              { key: "fromAmount", label: "Diamonds", render: (r) => <span className="font-mono">{r.fromAmount}</span> },
              { key: "toAmount", label: "Cash", render: (r) => <span className="font-mono">{r.currencySymbol || ""}{r.toAmount}</span> },
              { key: "country", label: "Country" },
              { key: "status", label: "Status", render: (r) => <StatusBadge value={r.status || "requested"} /> },
              { key: "createdAt", label: "Requested", render: (r) => fmtDateTime(r.createdAt) },
            ]} />
          </TabsContent>

          <TabsContent value="reports" className="mt-4">
            <MiniTable empty="No reports against this user" rows={related.reports} columns={[
              { key: "id", label: "Report", render: (r) => <span className="font-mono text-xs">{r.id}</span> },
              { key: "reporterUid", label: "Reporter", render: (r) => <span className="font-mono text-xs">{r.reporterUid}</span> },
              { key: "issue", label: "Issue", render: (r) => r.issue || r.reason || "—" },
              { key: "status", label: "Status", render: (r) => <StatusBadge value={r.status} /> },
              { key: "createdAt", label: "Date", render: (r) => fmtDateTime(r.createdAt) },
            ]} />
          </TabsContent>

          <TabsContent value="notes" className="mt-4 space-y-4">
            {can("users") && (
              <div className="rounded-lg border border-border bg-card p-4 space-y-3">
                <Textarea data-testid="note-input" placeholder="Add an internal note about this user…" value={note} onChange={(e) => setNote(e.target.value)} rows={3} />
                <Button data-testid="add-note-btn" onClick={addNote} disabled={!note.trim()} className="gradient-brand text-white border-0">Add note</Button>
              </div>
            )}
            {(related.notes || []).length === 0 && <p className="text-sm text-muted-foreground text-center py-6">No notes yet</p>}
            {(related.notes || []).map((n) => (
              <div key={n.id} className="rounded-lg border border-border bg-card p-4">
                <div className="flex items-center justify-between mb-1">
                  <p className="text-sm font-medium">{n.admin}</p>
                  <p className="text-xs text-muted-foreground">{fmtDateTime(n.createdAt)}</p>
                </div>
                <p className="text-sm text-muted-foreground">{n.text}</p>
              </div>
            ))}
          </TabsContent>

          <TabsContent value="audit" className="mt-4">
            <MiniTable empty="No audit history for this user" rows={related.audit} columns={[
              { key: "action", label: "Action" },
              { key: "adminEmail", label: "Admin" },
              { key: "adminRole", label: "Role" },
              { key: "reason", label: "Reason" },
              { key: "timestamp", label: "Time", render: (r) => fmtDateTime(r.timestamp) },
            ]} />
          </TabsContent>
        </Tabs>
      </main>
    </>
  );
}
