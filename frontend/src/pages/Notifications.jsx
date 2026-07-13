import { useEffect, useState, useCallback } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { DataTable } from "@/components/DataTable";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogTrigger,
} from "@/components/ui/dialog";
import { Send } from "lucide-react";
import { toast } from "sonner";

const TYPES = ["Account warning", "Account frozen", "Verification request", "Verification approved",
  "Withdrawal update", "Subscription update", "Payment update", "Promotion", "System announcement"];
const CHANNELS = ["In-app", "Email", "Push", "SMS"];
const AUDIENCES = ["All users", "UK users", "India users", "Love tier", "Friendship tier", "Unverified"];

const columns = [
  { key: "id", label: "ID", mono: true },
  { key: "title", label: "Title" },
  { key: "type", label: "Type" },
  { key: "channel", label: "Channel", badge: true },
  { key: "audience", label: "Audience" },
  { key: "sent_count", label: "Sent", mono: true },
  { key: "open_rate", label: "Open %" },
  { key: "status", label: "Status", badge: true },
];
const filters = [
  { key: "status", label: "Status", options: ["Sent", "Scheduled", "Draft", "Failed"] },
  { key: "channel", label: "Channel", options: CHANNELS },
];

export default function Notifications() {
  const { can } = useAuth();
  const canSend = can("notifications");
  const [rows, setRows] = useState([]);
  const [meta, setMeta] = useState({ total: 0, page: 1, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [flt, setFlt] = useState({});
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ title: "", type: TYPES[0], channel: "In-app", audience: "All users", body: "", send_mode: "now" });

  useEffect(() => { const t = setTimeout(() => setDebounced(search), 350); return () => clearTimeout(t); }, [search]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/resources/notifications", { params: { page, page_size: 15, search: debounced, ...flt } });
      setRows(data.items); setMeta({ total: data.total, page: data.page, pages: data.pages });
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setLoading(false); }
  }, [page, debounced, flt]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const submit = async (mode) => {
    try {
      await api.post("/notifications", { ...form, send_mode: mode });
      toast.success(mode === "now" ? "Notification sent" : mode === "schedule" ? "Notification scheduled" : "Draft saved");
      setOpen(false); setForm({ title: "", type: TYPES[0], channel: "In-app", audience: "All users", body: "", send_mode: "now" });
      fetchData();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  return (
    <>
      <Topbar title="Notifications" subtitle="Compose and track campaigns across channels" />
      <main className="flex-1 overflow-y-auto p-5 md:p-8 space-y-4">
        <div className="flex justify-end">
          {canSend && (
            <Dialog open={open} onOpenChange={setOpen}>
              <DialogTrigger asChild><Button data-testid="compose-btn" className="gradient-brand text-white border-0 gap-2"><Send className="h-4 w-4" /> Compose</Button></DialogTrigger>
              <DialogContent data-testid="compose-dialog" className="max-w-lg">
                <DialogHeader><DialogTitle>Compose Notification</DialogTitle></DialogHeader>
                <div className="space-y-3">
                  <div><Label>Title</Label><Input data-testid="notif-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Weekend bonus is live!" /></div>
                  <div className="grid grid-cols-2 gap-3">
                    <div><Label>Type</Label>
                      <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: v })}>
                        <SelectTrigger data-testid="notif-type"><SelectValue /></SelectTrigger>
                        <SelectContent>{TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                    <div><Label>Channel</Label>
                      <Select value={form.channel} onValueChange={(v) => setForm({ ...form, channel: v })}>
                        <SelectTrigger data-testid="notif-channel"><SelectValue /></SelectTrigger>
                        <SelectContent>{CHANNELS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div><Label>Audience</Label>
                    <Select value={form.audience} onValueChange={(v) => setForm({ ...form, audience: v })}>
                      <SelectTrigger data-testid="notif-audience"><SelectValue /></SelectTrigger>
                      <SelectContent>{AUDIENCES.map((a) => <SelectItem key={a} value={a}>{a}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                  <div><Label>Message</Label><Textarea data-testid="notif-body" rows={3} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} placeholder="Notification body…" /></div>
                </div>
                <DialogFooter className="gap-2">
                  <Button variant="outline" data-testid="notif-draft" onClick={() => submit("draft")} disabled={!form.title.trim()}>Save draft</Button>
                  <Button variant="outline" data-testid="notif-schedule" onClick={() => submit("schedule")} disabled={!form.title.trim()}>Schedule</Button>
                  <Button data-testid="notif-send" className="gradient-brand text-white border-0" onClick={() => submit("now")} disabled={!form.title.trim()}>Send now</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>
        <DataTable
          columns={columns} rows={rows} loading={loading} total={meta.total} page={meta.page} pages={meta.pages}
          onPage={setPage} search={search} onSearch={setSearch}
          filters={filters} filterValues={flt} onFilter={(k, v) => { setFlt((f) => ({ ...f, [k]: v })); setPage(1); }}
          exportName="notifications"
        />
      </main>
    </>
  );
}
