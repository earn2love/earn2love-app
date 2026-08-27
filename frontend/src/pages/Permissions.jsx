import { useEffect, useMemo, useState, useCallback } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { ShieldCheck, Loader2, Save, Lock, Eye, Pencil } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const MODULE_LABELS = {
  users: "User Management", reports: "Reports & Safety", moderation: "Content Moderation",
  verification: "Verification", identity: "Identity Verification", subscriptions: "Subscriptions",
  payments: "Payments", wallets: "Wallet & Transactions", transactions: "Transactions",
  conversions: "Coin Conversions", withdrawals: "Withdrawals", calls: "Audio & Video Calls",
  tasks: "Tasks & Offerwall", "friend-requests": "Friend Requests", chats: "Chats & Messages",
  notifications: "Notifications", support: "User Support", documents: "Documents",
  "app-config": "App Configuration", employees: "Employees", permissions: "Permissions",
};

export default function Permissions() {
  const { admin } = useAuth();
  const isSuper = admin?.role === "super_admin";
  const [matrix, setMatrix] = useState(null);
  const [roles, setRoles] = useState([]);
  const [modules, setModules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/role-permissions");
      setMatrix(data.matrix); setRoles(data.roles || []); setModules(data.modules || []);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const toggle = (role, module, perm) => {
    if (!isSuper || role === "super_admin") return;
    setMatrix((m) => ({
      ...m,
      [role]: { ...m[role], [module]: { ...(m[role]?.[module] || {}), [perm]: !(m[role]?.[module]?.[perm]) } },
    }));
    setDirty(true);
  };

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put("/role-permissions", { matrix });
      setMatrix(data.matrix); setDirty(false); toast.success("Permissions matrix saved");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setSaving(false);
  };

  const summary = useMemo(() => {
    if (!matrix) return {};
    const out = {};
    for (const r of roles) {
      const mods = matrix[r] || {};
      out[r] = Object.values(mods).filter((p) => p?.view).length;
    }
    return out;
  }, [matrix, roles]);

  return (
    <div data-testid="permissions-page">
      <Topbar title="Permissions Matrix" subtitle="Control what each admin role can view and edit across modules" />
      <div className="p-6 space-y-5">
        {!isSuper && (
          <div data-testid="perm-readonly-banner" className="flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 text-amber-500 px-4 py-2.5 text-sm">
            <Lock className="h-4 w-4" /> Read-only — only a <b className="mx-1">super_admin</b> can edit the permissions matrix.
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : matrix ? (
          <Tabs defaultValue={roles[0]} className="space-y-4">
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <TabsList className="flex-wrap h-auto">
                {roles.map((r) => (
                  <TabsTrigger key={r} value={r} data-testid={`perm-role-tab-${r}`} className="gap-1.5">
                    <ShieldCheck className="h-3.5 w-3.5" />
                    <span className="capitalize">{r.replace(/_/g, " ")}</span>
                    <span className="ml-1 text-[10px] rounded-full bg-muted px-1.5 tabular-nums">{summary[r] || 0}</span>
                  </TabsTrigger>
                ))}
              </TabsList>
              {isSuper && (
                <Button onClick={save} disabled={!dirty || saving} data-testid="perm-save-btn" className="gradient-brand text-white border-0">
                  {saving ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Save className="h-4 w-4 mr-1.5" />}Save changes
                </Button>
              )}
            </div>

            {roles.map((role) => (
              <TabsContent key={role} value={role} className="mt-0">
                {role === "super_admin" && (
                  <div className="mb-3 flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-500 px-4 py-2.5 text-sm">
                    <ShieldCheck className="h-4 w-4" /> Super admin has full, unrestricted access to every module (locked).
                  </div>
                )}
                <div className="rounded-xl border border-border overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
                      <tr>
                        <th className="text-left p-3 font-semibold">Module</th>
                        <th className="p-3 font-semibold w-28"><span className="inline-flex items-center gap-1 justify-center"><Eye className="h-3.5 w-3.5" />View</span></th>
                        <th className="p-3 font-semibold w-28"><span className="inline-flex items-center gap-1 justify-center"><Pencil className="h-3.5 w-3.5" />Edit</span></th>
                      </tr>
                    </thead>
                    <tbody>
                      {modules.map((mod) => {
                        const cell = matrix[role]?.[mod] || {};
                        const locked = !isSuper || role === "super_admin";
                        return (
                          <tr key={mod} data-testid={`perm-row-${role}-${mod}`} className="border-t border-border hover:bg-muted/30">
                            <td className="p-3 font-medium">{MODULE_LABELS[mod] || mod}</td>
                            <td className="p-3 text-center">
                              <Switch data-testid={`perm-${role}-${mod}-view`} checked={!!cell.view} disabled={locked}
                                onCheckedChange={() => toggle(role, mod, "view")} className={cn(locked && "opacity-60")} />
                            </td>
                            <td className="p-3 text-center">
                              <Switch data-testid={`perm-${role}-${mod}-edit`} checked={!!cell.edit} disabled={locked}
                                onCheckedChange={() => toggle(role, mod, "edit")} className={cn(locked && "opacity-60")} />
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </TabsContent>
            ))}
          </Tabs>
        ) : (
          <p className="text-sm text-muted-foreground py-24 text-center">Could not load permissions matrix.</p>
        )}
      </div>
    </div>
  );
}
