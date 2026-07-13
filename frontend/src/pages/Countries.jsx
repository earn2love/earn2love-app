import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import { Globe, Plus, Pencil } from "lucide-react";
import { toast } from "sonner";

const NUM_FIELDS = [
  ["price_casual", "Casual price"], ["price_friendship", "Friendship price"], ["price_love", "Love price"],
  ["withdrawal_min", "Min withdrawal"], ["audio_rate", "Audio Silver/min"], ["video_rate", "Video Silver/min"], ["tax", "Tax %"],
];

export default function Countries() {
  const { admin } = useAuth();
  const [countries, setCountries] = useState([]);
  const [editing, setEditing] = useState(null);
  const [addOpen, setAddOpen] = useState(false);
  const [newC, setNewC] = useState({ name: "", code: "", dial_code: "", currency_code: "", currency_symbol: "" });
  const canEdit = ["Owner", "Super Admin", "Finance Admin"].includes(admin?.role);

  const load = () => api.get("/resources/countries", { params: { page_size: 100 } }).then((r) => setCountries(r.data.items)).catch(() => {});
  useEffect(() => { load(); }, []);

  const saveEdit = async () => {
    try {
      const body = { ...editing }; delete body._id;
      await api.put(`/countries/${editing.id}`, body);
      toast.success(`${editing.name} updated`); setEditing(null); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  const addCountry = async () => {
    try {
      await api.post("/countries", newC);
      toast.success("Country added"); setAddOpen(false);
      setNewC({ name: "", code: "", dial_code: "", currency_code: "", currency_symbol: "" }); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <>
      <Topbar title="Countries & Pricing" subtitle="Per-country pricing, currency, rates and rules" />
      <main className="flex-1 overflow-y-auto p-5 md:p-8 space-y-5">
        <div className="flex justify-end">
          {canEdit && (
            <Dialog open={addOpen} onOpenChange={setAddOpen}>
              <DialogTrigger asChild><Button data-testid="add-country-btn" className="gradient-brand text-white border-0 gap-2"><Plus className="h-4 w-4" /> Add Country</Button></DialogTrigger>
              <DialogContent>
                <DialogHeader><DialogTitle>Add Country</DialogTitle></DialogHeader>
                <div className="grid grid-cols-2 gap-3">
                  <div className="col-span-2"><Label>Name</Label><Input value={newC.name} onChange={(e) => setNewC({ ...newC, name: e.target.value })} /></div>
                  <div><Label>Code</Label><Input placeholder="US" value={newC.code} onChange={(e) => setNewC({ ...newC, code: e.target.value })} /></div>
                  <div><Label>Dial code</Label><Input placeholder="+1" value={newC.dial_code} onChange={(e) => setNewC({ ...newC, dial_code: e.target.value })} /></div>
                  <div><Label>Currency code</Label><Input placeholder="USD" value={newC.currency_code} onChange={(e) => setNewC({ ...newC, currency_code: e.target.value })} /></div>
                  <div><Label>Symbol</Label><Input placeholder="$" value={newC.currency_symbol} onChange={(e) => setNewC({ ...newC, currency_symbol: e.target.value })} /></div>
                </div>
                <DialogFooter><Button onClick={addCountry} className="gradient-brand text-white border-0">Add</Button></DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {countries.map((c) => (
            <div key={c.id} data-testid={`country-${c.id}`} className="rounded-lg border border-border bg-card p-5">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="grid place-items-center h-10 w-10 rounded-lg bg-accent"><Globe className="h-5 w-5 text-primary" /></div>
                  <div>
                    <p className="font-display font-semibold">{c.name} <span className="text-xs text-muted-foreground font-normal">({c.code})</span></p>
                    <p className="text-xs text-muted-foreground">{c.currency_code} · {c.currency_symbol} · {c.dial_code}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${c.enabled ? "bg-emerald-500/10 text-emerald-600" : "bg-muted text-muted-foreground"}`}>{c.enabled ? "Enabled" : "Disabled"}</span>
                  {canEdit && <button data-testid={`edit-country-${c.id}`} onClick={() => setEditing({ ...c })} className="grid place-items-center h-7 w-7 rounded-md hover:bg-accent"><Pencil className="h-3.5 w-3.5" /></button>}
                </div>
              </div>
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div><p className="text-[10px] uppercase text-muted-foreground">Friendship</p><p className="font-mono">{c.currency_symbol}{c.price_friendship}</p></div>
                <div><p className="text-[10px] uppercase text-muted-foreground">Love</p><p className="font-mono">{c.currency_symbol}{c.price_love}</p></div>
                <div><p className="text-[10px] uppercase text-muted-foreground">Min Withdrawal</p><p className="font-mono">{c.currency_symbol}{c.withdrawal_min?.toLocaleString()}</p></div>
                <div><p className="text-[10px] uppercase text-muted-foreground">Audio /min</p><p className="font-mono">{c.audio_rate} 🪙</p></div>
                <div><p className="text-[10px] uppercase text-muted-foreground">Video /min</p><p className="font-mono">{c.video_rate} 🪙</p></div>
                <div><p className="text-[10px] uppercase text-muted-foreground">Tax</p><p className="font-mono">{c.tax}%</p></div>
              </div>
            </div>
          ))}
        </div>
      </main>

      {editing && (
        <Dialog open={!!editing} onOpenChange={(o) => !o && setEditing(null)}>
          <DialogContent data-testid="edit-country-dialog">
            <DialogHeader><DialogTitle>Edit {editing.name}</DialogTitle></DialogHeader>
            <div className="grid grid-cols-2 gap-3">
              {NUM_FIELDS.map(([k, label]) => (
                <div key={k}><Label className="text-xs">{label}</Label>
                  <Input type="number" value={editing[k] ?? 0} onChange={(e) => setEditing({ ...editing, [k]: Number(e.target.value) })} /></div>
              ))}
              <div className="col-span-2 flex items-center justify-between pt-1">
                <Label>Enabled</Label>
                <Switch checked={editing.enabled} onCheckedChange={(v) => setEditing({ ...editing, enabled: v })} />
              </div>
            </div>
            <DialogFooter><Button data-testid="save-country-btn" onClick={saveEdit} className="gradient-brand text-white border-0">Save</Button></DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}
