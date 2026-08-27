import { useEffect, useMemo, useState, useCallback } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter, DialogTrigger } from "@/components/ui/dialog";
import {
  Send, Bell, Loader2, Smartphone, Mail, LayoutList, Users, Globe, Crown, ShieldAlert, Search, CheckCircle2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const CHANNEL_META = {
  in_app: { label: "In-app", icon: LayoutList },
  push: { label: "Push", icon: Smartphone },
  email: { label: "Email", icon: Mail },
};
const TYPE_LABELS = {
  system_alert: "System alert", promotion: "Promotion", account: "Account", verification: "Verification",
  payment: "Payment", subscription: "Subscription", withdrawal: "Withdrawal", general: "General",
};
const AUDIENCE_META = {
  all: { label: "All users", icon: Users },
  country: { label: "By country", icon: Globe },
  tier: { label: "By tier", icon: Crown },
  unverified: { label: "Unverified users", icon: ShieldAlert },
};
const STATUS_CLS = {
  Sent: "text-emerald-500 border-emerald-500/30 bg-emerald-500/10",
  Sending: "text-sky-500 border-sky-500/30 bg-sky-500/10",
  Scheduled: "text-violet-500 border-violet-500/30 bg-violet-500/10",
  Draft: "text-muted-foreground border-border bg-muted/40",
};
const COUNTRIES = ["UK", "IN"];
const TIERS = ["casual", "friendship", "love"];

const EMPTY = { title: "", body: "", type: "system_alert", channels: ["in_app"], audience: { mode: "all", country: "UK", tier: "love" } };

function timeAgo(iso) {
  if (!iso) return "";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return new Date(iso).toLocaleDateString();
}

export default function Notifications() {
  const { can } = useAuth();
  const canSend = can("notifications");
  const [meta, setMeta] = useState({ types: [], emailEnabled: false });
  const [campaigns, setCampaigns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [preview, setPreview] = useState(null);
  const [sending, setSending] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [c, m] = await Promise.all([
        api.get("/notifications/campaigns"),
        api.get("/notifications/meta"),
      ]);
      setCampaigns(c.data.items || []);
      setMeta(m.data);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  // live audience preview (debounced)
  useEffect(() => {
    if (!open) return;
    const t = setTimeout(async () => {
      try { const { data } = await api.post("/notifications/audience-preview", { audience: form.audience }); setPreview(data); }
      catch { setPreview(null); }
    }, 400);
    return () => clearTimeout(t);
  }, [open, form.audience]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return campaigns.filter((c) => !q || `${c.title} ${c.body} ${c.type}`.toLowerCase().includes(q));
  }, [campaigns, query]);

  const toggleChannel = (ch) => setForm((f) => ({
    ...f, channels: f.channels.includes(ch) ? f.channels.filter((c) => c !== ch) : [...f.channels, ch],
  }));

  const submit = async (sendMode) => {
    if (!form.title.trim()) { toast.error("Title is required"); return; }
    if (form.channels.length === 0) { toast.error("Select at least one channel"); return; }
    setSending(true);
    try {
      const { data } = await api.post("/notifications/send", { ...form, sendMode });
      const d = data.delivery || {};
      if (sendMode === "now") {
        const parts = [];
        if (d.inAppWritten != null) parts.push(`${d.inAppWritten} in-app`);
        if (d.push) parts.push(`${d.push.sent} push`);
        if (d.email) parts.push(d.email.enabled ? `${d.email.sent} email` : `email queued`);
        toast.success(`Sent to ${d.recipients ?? 0} users${parts.length ? ` · ${parts.join(", ")}` : ""}`);
      } else {
        toast.success(sendMode === "schedule" ? "Campaign scheduled" : "Draft saved");
      }
      setOpen(false); setForm(EMPTY); setPreview(null); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setSending(false);
  };

  return (
    <div data-testid="notifications-page">
      <Topbar title="Notifications" subtitle="Send real FCM push, in-app & email campaigns to app users" />
      <div className="p-6 space-y-5">
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input data-testid="notif-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search campaigns…" className="pl-9 h-10" />
          </div>
          {canSend && (
            <Dialog open={open} onOpenChange={(o) => { setOpen(o); if (!o) { setForm(EMPTY); setPreview(null); } }}>
              <DialogTrigger asChild>
                <Button data-testid="compose-btn" className="gradient-brand text-white border-0 gap-2"><Send className="h-4 w-4" />Compose</Button>
              </DialogTrigger>
              <DialogContent data-testid="compose-dialog" className="max-w-lg max-h-[92vh] overflow-y-auto">
                <DialogHeader>
                  <DialogTitle>Compose Notification</DialogTitle>
                  <DialogDescription>Target an audience and deliver via in-app, push and email.</DialogDescription>
                </DialogHeader>
                <div className="space-y-4">
                  <div><Label>Title</Label><Input data-testid="notif-title" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="Weekend bonus is live!" /></div>
                  <div><Label>Message</Label><Textarea data-testid="notif-body" rows={3} value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} placeholder="Notification body…" /></div>
                  <div><Label>Type</Label>
                    <Select value={form.type} onValueChange={(v) => setForm({ ...form, type: v })}>
                      <SelectTrigger data-testid="notif-type"><SelectValue /></SelectTrigger>
                      <SelectContent>{(meta.types || []).map((t) => <SelectItem key={t} value={t}>{TYPE_LABELS[t] || t}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Channels</Label>
                    <div className="grid grid-cols-3 gap-2 mt-1.5">
                      {["in_app", "push", "email"].map((ch) => {
                        const Icon = CHANNEL_META[ch].icon;
                        const on = form.channels.includes(ch);
                        const disabled = ch === "email" && !meta.emailEnabled;
                        return (
                          <button key={ch} type="button" data-testid={`notif-channel-${ch}`} disabled={disabled}
                            onClick={() => toggleChannel(ch)}
                            className={cn("flex flex-col items-center gap-1 rounded-lg border py-2.5 text-xs font-medium transition-colors",
                              on ? "border-pink-500/50 bg-pink-500/10 text-pink-500" : "border-border text-muted-foreground hover:text-foreground",
                              disabled && "opacity-40 cursor-not-allowed")}>
                            <Icon className="h-4 w-4" />{CHANNEL_META[ch].label}
                          </button>
                        );
                      })}
                    </div>
                    {!meta.emailEnabled && (
                      <p data-testid="email-disabled-note" className="text-[11px] text-amber-500 mt-1.5 flex items-center gap-1">
                        <Mail className="h-3 w-3" />Email is inactive — add a Resend API key to enable delivery.
                      </p>
                    )}
                  </div>

                  <div>
                    <Label>Audience</Label>
                    <Select value={form.audience.mode} onValueChange={(v) => setForm({ ...form, audience: { ...form.audience, mode: v } })}>
                      <SelectTrigger data-testid="notif-audience"><SelectValue /></SelectTrigger>
                      <SelectContent>{Object.entries(AUDIENCE_META).map(([k, m]) => <SelectItem key={k} value={k}>{m.label}</SelectItem>)}</SelectContent>
                    </Select>
                    {form.audience.mode === "country" && (
                      <Select value={form.audience.country} onValueChange={(v) => setForm({ ...form, audience: { ...form.audience, country: v } })}>
                        <SelectTrigger className="mt-2" data-testid="notif-country"><SelectValue /></SelectTrigger>
                        <SelectContent>{COUNTRIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                      </Select>
                    )}
                    {form.audience.mode === "tier" && (
                      <Select value={form.audience.tier} onValueChange={(v) => setForm({ ...form, audience: { ...form.audience, tier: v } })}>
                        <SelectTrigger className="mt-2" data-testid="notif-tier"><SelectValue /></SelectTrigger>
                        <SelectContent>{TIERS.map((t) => <SelectItem key={t} value={t} className="capitalize">{t}</SelectItem>)}</SelectContent>
                      </Select>
                    )}
                  </div>

                  <div data-testid="audience-preview" className="rounded-lg border border-border bg-muted/30 px-3.5 py-2.5 text-sm flex items-center gap-4">
                    {preview ? (
                      <>
                        <span className="flex items-center gap-1.5 font-semibold"><Users className="h-4 w-4 text-pink-500" />{preview.recipients} users</span>
                        <span className="text-muted-foreground flex items-center gap-1"><Smartphone className="h-3.5 w-3.5" />{preview.withPushToken} push</span>
                        <span className="text-muted-foreground flex items-center gap-1"><Mail className="h-3.5 w-3.5" />{preview.withEmail} email</span>
                      </>
                    ) : <span className="text-muted-foreground flex items-center gap-1.5"><Loader2 className="h-3.5 w-3.5 animate-spin" />Estimating audience…</span>}
                  </div>
                </div>
                <DialogFooter className="gap-2">
                  <Button variant="outline" data-testid="notif-draft" onClick={() => submit("draft")} disabled={sending}>Save draft</Button>
                  <Button data-testid="notif-send" className="gradient-brand text-white border-0" onClick={() => submit("now")} disabled={sending}>
                    {sending ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Send className="h-4 w-4 mr-1.5" />}Send now
                  </Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>

        {loading ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center py-24 text-muted-foreground"><Bell className="h-10 w-10 mb-3 opacity-40" /><p className="text-sm">No campaigns yet. Compose your first notification.</p></div>
        ) : (
          <div className="space-y-3">
            {filtered.map((c) => {
              const A = AUDIENCE_META[c.audience?.mode] || AUDIENCE_META.all;
              const d = c.delivery || {};
              return (
                <div key={c.id} data-testid={`campaign-${c.id}`} className="rounded-xl border border-border bg-card p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="font-semibold truncate">{c.title}</p>
                        <span className={cn("text-[10px] px-2 py-0.5 rounded-full border", STATUS_CLS[c.status] || STATUS_CLS.Draft)}>{c.status}</span>
                      </div>
                      <p className="text-sm text-muted-foreground line-clamp-2 mt-0.5">{c.body}</p>
                    </div>
                    <span className="text-[11px] text-muted-foreground shrink-0">{timeAgo(c.sentAt || c.createdAt)}</span>
                  </div>
                  <div className="flex flex-wrap items-center gap-3 mt-3 text-[11px] text-muted-foreground">
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-border"><A.icon className="h-3 w-3" />{A.label}{c.audience?.mode === "country" ? `: ${c.audience.country}` : c.audience?.mode === "tier" ? `: ${c.audience.tier}` : ""}</span>
                    {(c.channels || []).map((ch) => {
                      const M = CHANNEL_META[ch]; if (!M) return null; const Icon = M.icon;
                      return <span key={ch} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border border-border"><Icon className="h-3 w-3" />{M.label}</span>;
                    })}
                    <span className="uppercase tracking-wide">{TYPE_LABELS[c.type] || c.type}</span>
                    {c.status === "Sent" && (
                      <span className="inline-flex items-center gap-2 ml-auto text-foreground/70">
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                        {d.recipients ?? 0} recipients
                        {d.inAppWritten != null && ` · ${d.inAppWritten} in-app`}
                        {d.push && ` · ${d.push.sent}/${d.push.tokens} push`}
                        {d.email && (d.email.enabled ? ` · ${d.email.sent} email` : ` · email queued`)}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
