import { useEffect, useState, useCallback } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Loader2, Save, Plus, Trash2, Coins, Phone, ArrowLeftRight, CreditCard, SlidersHorizontal } from "lucide-react";
import { toast } from "sonner";

const REGIONS = ["UK", "IN"];

export default function AppConfig() {
  const [cfg, setCfg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { const { data } = await api.get("/app-config"); setCfg(data); }
    catch (e) { toast.error(formatApiError(e)); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put("/app-config", cfg);
      setCfg(data);
      toast.success("App configuration saved — live for the app");
    } catch (e) { toast.error(formatApiError(e)); }
    setSaving(false);
  };

  // helpers
  const setArr = (key, idx, field, val) =>
    setCfg((c) => ({ ...c, [key]: c[key].map((r, i) => (i === idx ? { ...r, [field]: val } : r)) }));
  const addRow = (key, tmpl) => setCfg((c) => ({ ...c, [key]: [...(c[key] || []), tmpl] }));
  const delRow = (key, idx) => setCfg((c) => ({ ...c, [key]: c[key].filter((_, i) => i !== idx) }));
  const setNested = (path, val) =>
    setCfg((c) => {
      const next = structuredClone(c);
      let o = next; for (let i = 0; i < path.length - 1; i++) o = o[path[i]];
      o[path[path.length - 1]] = val; return next;
    });

  if (loading || !cfg) {
    return (<div><Topbar title="App Configuration" subtitle="Live coin, pricing, call & conversion settings" />
      <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div></div>);
  }

  const num = (v) => (v === "" ? "" : Number(v));

  return (
    <div data-testid="app-config-page">
      <Topbar title="App Configuration" subtitle="Single source of truth for the Earn2Love mobile app" />
      <div className="p-6 space-y-5">
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Edits here are the live source of truth. Last updated by {cfg.updatedBy || "—"}.
          </p>
          <Button onClick={save} disabled={saving} data-testid="app-config-save">
            {saving ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Save className="h-4 w-4 mr-1.5" />} Save Changes
          </Button>
        </div>

        <Tabs defaultValue="coins">
          <TabsList className="flex-wrap h-auto">
            <TabsTrigger value="coins" data-testid="tab-coins"><Coins className="h-4 w-4 mr-1.5" />Coin Packages</TabsTrigger>
            <TabsTrigger value="plans" data-testid="tab-plans"><CreditCard className="h-4 w-4 mr-1.5" />Membership Plans</TabsTrigger>
            <TabsTrigger value="calls" data-testid="tab-calls"><Phone className="h-4 w-4 mr-1.5" />Call Rates</TabsTrigger>
            <TabsTrigger value="conv" data-testid="tab-conv"><ArrowLeftRight className="h-4 w-4 mr-1.5" />Conversions</TabsTrigger>
            <TabsTrigger value="settings" data-testid="tab-settings"><SlidersHorizontal className="h-4 w-4 mr-1.5" />Settings</TabsTrigger>
          </TabsList>

          {/* Coin packages */}
          <TabsContent value="coins" className="mt-4">
            <div className="rounded-xl border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
                  <tr><th className="text-left p-3">ID</th><th className="text-left p-3">Label</th><th className="p-3">Region</th><th className="p-3">Price (minor)</th><th className="p-3">Currency</th><th className="p-3">Silver</th><th></th></tr>
                </thead>
                <tbody>
                  {cfg.coinPackages?.map((p, i) => (
                    <tr key={i} className="border-t border-border">
                      <td className="p-2"><Input value={p.id} onChange={(e) => setArr("coinPackages", i, "id", e.target.value)} className="h-9" /></td>
                      <td className="p-2"><Input value={p.label} onChange={(e) => setArr("coinPackages", i, "label", e.target.value)} className="h-9 min-w-[150px]" /></td>
                      <td className="p-2"><select value={p.region} onChange={(e) => setArr("coinPackages", i, "region", e.target.value)} className="h-9 rounded-md border border-border bg-background px-2">{REGIONS.map((r) => <option key={r}>{r}</option>)}</select></td>
                      <td className="p-2"><Input type="number" value={p.priceMinor} onChange={(e) => setArr("coinPackages", i, "priceMinor", num(e.target.value))} className="h-9 w-28" /></td>
                      <td className="p-2"><Input value={p.currency} onChange={(e) => setArr("coinPackages", i, "currency", e.target.value)} className="h-9 w-20" /></td>
                      <td className="p-2"><Input type="number" value={p.silver} onChange={(e) => setArr("coinPackages", i, "silver", num(e.target.value))} className="h-9 w-24" /></td>
                      <td className="p-2"><Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-red-500" onClick={() => delRow("coinPackages", i)}><Trash2 className="h-4 w-4" /></Button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Button size="sm" variant="outline" className="mt-3" data-testid="add-coin-package"
              onClick={() => addRow("coinPackages", { id: "new_pack", region: "UK", label: "New Pack", priceMinor: 199, currency: "gbp", silver: 100 })}>
              <Plus className="h-4 w-4 mr-1.5" /> Add Package
            </Button>
          </TabsContent>

          {/* Membership plans */}
          <TabsContent value="plans" className="mt-4">
            <div className="rounded-xl border border-border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
                  <tr><th className="text-left p-3">ID</th><th className="text-left p-3">Label</th><th className="p-3">Tier</th><th className="p-3">Region</th><th className="p-3">Price (minor)</th><th className="p-3">Currency</th><th></th></tr>
                </thead>
                <tbody>
                  {cfg.membershipPlans?.map((p, i) => (
                    <tr key={i} className="border-t border-border">
                      <td className="p-2"><Input value={p.id} onChange={(e) => setArr("membershipPlans", i, "id", e.target.value)} className="h-9" /></td>
                      <td className="p-2"><Input value={p.label} onChange={(e) => setArr("membershipPlans", i, "label", e.target.value)} className="h-9 min-w-[150px]" /></td>
                      <td className="p-2"><select value={p.tier} onChange={(e) => setArr("membershipPlans", i, "tier", e.target.value)} className="h-9 rounded-md border border-border bg-background px-2"><option value="casual">casual</option><option value="friendship">friendship</option><option value="love">love</option></select></td>
                      <td className="p-2"><select value={p.region} onChange={(e) => setArr("membershipPlans", i, "region", e.target.value)} className="h-9 rounded-md border border-border bg-background px-2">{REGIONS.map((r) => <option key={r}>{r}</option>)}</select></td>
                      <td className="p-2"><Input type="number" value={p.priceMinor} onChange={(e) => setArr("membershipPlans", i, "priceMinor", num(e.target.value))} className="h-9 w-28" /></td>
                      <td className="p-2"><Input value={p.currency} onChange={(e) => setArr("membershipPlans", i, "currency", e.target.value)} className="h-9 w-20" /></td>
                      <td className="p-2"><Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-red-500" onClick={() => delRow("membershipPlans", i)}><Trash2 className="h-4 w-4" /></Button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Button size="sm" variant="outline" className="mt-3"
              onClick={() => addRow("membershipPlans", { id: "new_plan", tier: "friendship", region: "UK", label: "New Plan", priceMinor: 499, currency: "gbp" })}>
              <Plus className="h-4 w-4 mr-1.5" /> Add Plan
            </Button>
          </TabsContent>

          {/* Call rates */}
          <TabsContent value="calls" className="mt-4">
            <div className="grid sm:grid-cols-2 gap-4 max-w-2xl">
              {["audio", "video"].map((t) => (
                <div key={t} className="rounded-xl border border-border p-5 space-y-4">
                  <h3 className="font-semibold capitalize flex items-center gap-2"><Phone className="h-4 w-4 text-pink-500" /> {t} call (Silver / minute)</h3>
                  <div><Label>Caller pays / min</Label><Input type="number" data-testid={`call-${t}-caller`} value={cfg.callCosts[t].callerPerMin} onChange={(e) => setNested(["callCosts", t, "callerPerMin"], num(e.target.value))} className="h-9" /></div>
                  <div><Label>Receiver earns / min</Label><Input type="number" value={cfg.callCosts[t].receiverPerMin} onChange={(e) => setNested(["callCosts", t, "receiverPerMin"], num(e.target.value))} className="h-9" /></div>
                </div>
              ))}
            </div>
          </TabsContent>

          {/* Conversions + withdrawal */}
          <TabsContent value="conv" className="mt-4">
            <div className="grid sm:grid-cols-2 gap-4 max-w-3xl">
              {REGIONS.map((r) => (
                <div key={r} className="rounded-xl border border-border p-5 space-y-4">
                  <h3 className="font-semibold flex items-center gap-2"><ArrowLeftRight className="h-4 w-4 text-pink-500" /> {r === "UK" ? "United Kingdom" : "India"}</h3>
                  <div><Label>Silver → Gold ratio</Label><Input type="number" step="0.0001" value={cfg.conversionRates[r].silverToGold} onChange={(e) => setNested(["conversionRates", r, "silverToGold"], num(e.target.value))} className="h-9" /></div>
                  <div><Label>Gold → Diamond ratio</Label><Input type="number" step="0.0001" value={cfg.conversionRates[r].goldToDiamond} onChange={(e) => setNested(["conversionRates", r, "goldToDiamond"], num(e.target.value))} className="h-9" /></div>
                  <div><Label>1 Diamond = (cash)</Label><Input type="number" step="0.0001" value={cfg.conversionRates[r].diamondCashUnit} onChange={(e) => setNested(["conversionRates", r, "diamondCashUnit"], num(e.target.value))} className="h-9" /></div>
                  <div><Label>Minimum withdrawal ({cfg.withdrawalMin[r].currency})</Label><Input type="number" data-testid={`withdraw-min-${r}`} value={cfg.withdrawalMin[r].min} onChange={(e) => setNested(["withdrawalMin", r, "min"], num(e.target.value))} className="h-9" /></div>
                </div>
              ))}
            </div>
          </TabsContent>

          {/* Settings list */}
          <TabsContent value="settings" className="mt-4">
            <div className="space-y-2 max-w-3xl">
              {cfg.settings?.map((s, i) => (
                <div key={i} className="flex items-center gap-3 rounded-lg border border-border p-3">
                  <div className="flex-1">
                    <p className="text-sm font-medium">{s.label}</p>
                    <p className="text-[11px] text-muted-foreground font-mono">{s.key}</p>
                  </div>
                  {s.type === "bool" ? (
                    <Switch checked={!!s.value} onCheckedChange={(v) => setArr("settings", i, "value", v)} data-testid={`setting-${s.key}`} />
                  ) : (
                    <Input type={s.type === "number" ? "number" : "text"} value={s.value}
                      onChange={(e) => setArr("settings", i, "value", s.type === "number" ? num(e.target.value) : e.target.value)}
                      className="h-9 w-48" data-testid={`setting-${s.key}`} />
                  )}
                </div>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
