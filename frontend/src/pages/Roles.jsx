import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { StatusBadge } from "@/components/StatusBadge";
import { useAuth } from "@/context/AuthContext";
import { fmtDateTime } from "@/lib/format";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { UserPlus, MoreHorizontal, Check, X } from "lucide-react";
import { toast } from "sonner";

export default function Roles() {
  const { admin } = useAuth();
  const [data, setData] = useState({ items: [], roles: [], permissions_map: {} });
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", role: "Support Admin", password: "" });
  const canManage = ["Owner", "Super Admin"].includes(admin?.role);

  const load = () => api.get("/admins").then((r) => setData(r.data)).catch(() => {});
  useEffect(() => { load(); }, []);

  const create = async () => {
    try {
      await api.post("/admins", form);
      toast.success("Admin created");
      setOpen(false); setForm({ name: "", email: "", role: "Support Admin", password: "" }); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const act = async (id, action, value) => {
    try {
      await api.post(`/admins/${id}/action`, { action, value });
      toast.success("Updated");
      load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const allModules = ["users", "reports", "moderation", "liveness", "identity", "payments", "withdrawals", "wallets", "conversions", "subscriptions", "chats", "calls", "countries", "notifications", "support-tickets", "settings"];

  return (
    <>
      <Topbar title="Admin Roles" subtitle="Manage admin accounts and role permissions" />
      <main className="flex-1 overflow-y-auto p-5 md:p-8 space-y-6">
        <div className="flex items-center justify-between">
          <h3 className="font-display font-semibold text-sm">Admin Accounts ({data.items.length})</h3>
          {canManage && (
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild>
                <Button data-testid="create-admin-btn" className="gradient-brand text-white border-0 gap-2"><UserPlus className="h-4 w-4" /> New Admin</Button>
              </DialogTrigger>
              <DialogContent data-testid="create-admin-dialog">
                <DialogHeader><DialogTitle>Create Admin Account</DialogTitle></DialogHeader>
                <div className="space-y-3">
                  <div><Label>Name</Label><Input data-testid="new-admin-name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
                  <div><Label>Email</Label><Input data-testid="new-admin-email" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
                  <div><Label>Role</Label>
                    <Select value={form.role} onValueChange={(v) => setForm({ ...form, role: v })}>
                      <SelectTrigger data-testid="new-admin-role"><SelectValue /></SelectTrigger>
                      <SelectContent>{data.roles.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div><Label>Password</Label><Input data-testid="new-admin-password" type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></div>
                </div>
                <DialogFooter><Button data-testid="submit-admin-btn" onClick={create} className="gradient-brand text-white border-0">Create</Button></DialogFooter>
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
              <th className="text-left px-4 py-3 font-semibold">Last Login</th>
              <th className="text-left px-4 py-3 font-semibold">Last IP</th>
              {canManage && <th className="w-12" />}
            </tr></thead>
            <tbody>
              {data.items.map((a) => (
                <tr key={a.id} data-testid={`admin-row-${a.id}`} className="border-b border-border/60">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2.5">
                      <Avatar className="h-8 w-8"><AvatarFallback className="text-[10px] gradient-brand text-white">{a.initials}</AvatarFallback></Avatar>
                      <div><p className="font-medium">{a.name}</p><p className="text-[11px] text-muted-foreground">{a.email}</p></div>
                    </div>
                  </td>
                  <td className="px-4 py-3"><StatusBadge value={a.role === "Owner" ? "Love" : "Friendship"} className="hidden" /><span className="text-xs font-medium">{a.role}</span></td>
                  <td className="px-4 py-3"><StatusBadge value={a.status} /></td>
                  <td className="px-4 py-3 text-muted-foreground text-xs">{a.last_login ? fmtDateTime(a.last_login) : "Never"}</td>
                  <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{a.last_ip || "—"}</td>
                  {canManage && (
                    <td className="px-4 py-3">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild><button data-testid={`admin-actions-${a.id}`} className="grid place-items-center h-7 w-7 rounded-md hover:bg-accent"><MoreHorizontal className="h-4 w-4" /></button></DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {a.status === "Active"
                            ? <DropdownMenuItem className="text-rose-600" onClick={() => act(a.id, "disable")}>Disable</DropdownMenuItem>
                            : <DropdownMenuItem onClick={() => act(a.id, "enable")}>Enable</DropdownMenuItem>}
                          {data.roles.filter((r) => r !== a.role).map((r) => (
                            <DropdownMenuItem key={r} onClick={() => act(a.id, "change-role", { role: r })}>Set role: {r}</DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Permission matrix */}
        <div>
          <h3 className="font-display font-semibold text-sm mb-3">Role Permission Matrix</h3>
          <div className="rounded-lg border border-border bg-card overflow-x-auto">
            <table className="w-full text-xs">
              <thead><tr className="border-b border-border">
                <th className="text-left px-3 py-2.5 font-semibold sticky left-0 bg-card">Module</th>
                {data.roles.map((r) => <th key={r} className="px-2 py-2.5 font-semibold text-center whitespace-nowrap">{r}</th>)}
              </tr></thead>
              <tbody>
                {allModules.map((m) => (
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
