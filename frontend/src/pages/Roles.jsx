import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { StatusBadge } from "@/components/StatusBadge";
import { useAuth } from "@/context/AuthContext";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import { UserCog, Check, X } from "lucide-react";
import { toast } from "sonner";

const ALL_MODULES = ["users", "reports", "moderation", "liveness", "identity", "payments", "withdrawals",
  "wallets", "conversions", "subscriptions", "chats", "friend-requests", "notifications", "support-tickets", "verification"];

export default function Roles() {
  const { admin } = useAuth();
  const [data, setData] = useState({ items: [], roles: [], permissions_map: {} });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ email: "", role: "moderator" });
  const canManage = admin?.role === "super_admin";

  const load = () => api.get("/admins").then((r) => setData(r.data)).catch((e) => toast.error(formatApiError(e.response?.data?.detail)));
  useEffect(() => { load(); }, []);

  const setRole = async () => {
    try {
      await api.post("/admins/set-role", form);
      toast.success(`Role '${form.role}' assigned to ${form.email}`);
      setOpen(false); setForm({ email: "", role: "moderator" }); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <>
      <Topbar title="Admin Roles" subtitle="Firebase custom-claim roles & permissions" />
      <main className="flex-1 overflow-y-auto p-5 md:p-8 space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="font-display font-semibold text-sm">Admin Accounts ({data.items.length})</h3>
          {canManage && (
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild>
                <Button data-testid="assign-role-btn" className="gradient-brand text-white border-0 gap-2"><UserCog className="h-4 w-4" /> Assign role</Button>
              </DialogTrigger>
              <DialogContent data-testid="assign-role-dialog">
                <DialogHeader>
                  <DialogTitle>Assign Admin Role</DialogTitle>
                  <DialogDescription>Grant a Firebase custom-claim role to an existing account by email. The user must sign in again for it to take effect.</DialogDescription>
                </DialogHeader>
                <div className="space-y-3">
                  <div><Label>Email</Label><Input data-testid="role-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="admin@earn2love.com" /></div>
                  <div><Label>Role</Label>
                    <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                      <SelectTrigger data-testid="role-select"><SelectValue /></SelectTrigger>
                      <SelectContent>{data.roles.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter><Button data-testid="submit-role-btn" onClick={setRole} disabled={!form.email.trim()} className="gradient-brand text-white border-0">Assign</Button></DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>

        <div className="rounded-lg border border-border bg-card overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="border-b border-border text-[11px] uppercase tracking-wider text-muted-foreground">
              <th className="text-left px-4 py-3 font-semibold">Admin</th>
              <th className="text-left px-4 py-3 font-semibold">Role</th>
              <th className="text-left px-4 py-3 font-semibold">Status</th>
              <th className="text-left px-4 py-3 font-semibold">UID</th>
            </tr></thead>
            <tbody>
              {data.items.length === 0 && (
                <tr><td colSpan={4} className="px-4 py-10 text-center text-muted-foreground text-sm">No admins with role claims yet.</td></tr>
              )}
              {data.items.map((a) => (
                <tr key={a.id} data-testid={`admin-row-${a.id}`} className="border-b border-border/60">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <Avatar className="h-8 w-8"><AvatarFallback className="text-[10px] gradient-brand text-white">{a.initials}</AvatarFallback></Avatar>
                      <div><p className="font-medium">{a.name}</p><p className="text-[11px] text-muted-foreground">{a.email}</p></div>
                    </div>
                  </td>
                  <td className="px-4 py-3"><span className="text-xs font-medium">{a.role}</span></td>
                  <td className="px-4 py-3"><StatusBadge value={a.status} /></td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{a.uid}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div>
          <h3 className="font-display font-semibold text-sm mb-3">Role Permission Matrix</h3>
          <div className="rounded-lg border border-border bg-card overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="border-b border-border">
                <th className="text-left px-3 py-2.5 font-semibold sticky left-0 bg-card">Module</th>
                {data.roles.map((r) => <th key={r} className="px-2 py-2.5 font-semibold text-center whitespace-nowrap">{r}</th>)}
              </tr></thead>
              <tbody>
                {ALL_MODULES.map((m) => (
                  <tr key={m} className="border-b border-border/60">
                    <td className="px-3 py-2 font-medium capitalize sticky left-0 bg-card">{m.replace("-", " ")}</td>
                    {data.roles.map((r) => {
                      const perms = data.permissions_map[r];
                      const has = perms === "*" || (Array.isArray(perms) && perms.includes(m));
                      return <td key={r} className="px-2 py-2 text-center">{has ? <Check className="h-3.5 w-3.5 text-emerald-500 mx-auto" /> : <X className="h-3.5 w-3.5 text-muted-foreground/30 mx-auto" />}</td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </main>
    </>
  );
}
