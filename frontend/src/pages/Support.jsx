import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Bot, User, Headset, Send, CheckCircle2, Search, Loader2, MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const STATUS_META = {
  bot: { label: "AI handling", cls: "text-sky-500 border-sky-500/30 bg-sky-500/10" },
  escalated: { label: "Needs agent", cls: "text-amber-500 border-amber-500/30 bg-amber-500/10" },
  open: { label: "Agent replied", cls: "text-violet-500 border-violet-500/30 bg-violet-500/10" },
  resolved: { label: "Resolved", cls: "text-emerald-500 border-emerald-500/30 bg-emerald-500/10" },
};
const FILTERS = ["all", "escalated", "bot", "open", "resolved"];

function timeAgo(iso) {
  if (!iso) return "";
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}

export default function Support() {
  const [items, setItems] = useState([]);
  const [filter, setFilter] = useState("all");
  const [query, setQuery] = useState("");
  const [selId, setSelId] = useState(null);
  const [conv, setConv] = useState(null);
  const [reply, setReply] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const threadRef = useRef(null);

  const loadList = useCallback(async () => {
    try { const { data } = await api.get("/support/conversations"); setItems(data.items || []); }
    catch (e) { toast.error(formatApiError(e)); }
    setLoading(false);
  }, []);

  const loadConv = useCallback(async (id) => {
    if (!id) return;
    try { const { data } = await api.get(`/support/conversations/${id}`); setConv(data); }
    catch (e) { toast.error(formatApiError(e)); }
  }, []);

  useEffect(() => { loadList(); }, [loadList]);
  useEffect(() => {
    const t = setInterval(() => { loadList(); if (selId) loadConv(selId); }, 15000);
    return () => clearInterval(t);
  }, [loadList, loadConv, selId]);
  useEffect(() => { if (selId) loadConv(selId); }, [selId, loadConv]);
  useEffect(() => { if (threadRef.current) threadRef.current.scrollTop = threadRef.current.scrollHeight; }, [conv]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((c) =>
      (filter === "all" || c.status === filter) &&
      (!q || `${c.userName} ${c.lastMessage}`.toLowerCase().includes(q)));
  }, [items, filter, query]);

  const sendReply = async () => {
    if (!reply.trim() || !selId) return;
    setSending(true);
    try {
      const { data } = await api.post(`/support/conversations/${selId}/reply`, { text: reply });
      setConv(data); setReply(""); loadList();
    } catch (e) { toast.error(formatApiError(e)); }
    setSending(false);
  };

  const setStatus = async (status) => {
    try {
      const { data } = await api.post(`/support/conversations/${selId}/status`, { status });
      setConv(data); loadList();
      toast.success(status === "resolved" ? "Marked resolved" : "Reopened");
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="support-page">
      <Topbar title="User Support" subtitle="AI assistant handles first — escalations land here for your team" />
      <div className="p-6">
        <div className="grid lg:grid-cols-[360px_1fr] gap-4 h-[calc(100vh-160px)]">
          {/* List */}
          <div className="rounded-xl border border-border flex flex-col overflow-hidden">
            <div className="p-3 border-b border-border space-y-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input data-testid="support-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search users…" className="pl-9 h-9" />
              </div>
              <div className="flex flex-wrap gap-1.5">
                {FILTERS.map((f) => (
                  <button key={f} data-testid={`support-filter-${f}`} onClick={() => setFilter(f)}
                    className={cn("px-2.5 h-7 rounded-full text-[11px] font-medium border capitalize transition-colors",
                      filter === f ? "bg-pink-500/15 text-pink-500 border-pink-500/30" : "border-border text-muted-foreground hover:text-foreground")}>
                    {f === "all" ? "All" : STATUS_META[f]?.label || f}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex-1 overflow-auto">
              {loading ? (
                <div className="flex justify-center py-16"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
              ) : filtered.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-16 text-muted-foreground text-sm"><MessageSquare className="h-8 w-8 mb-2 opacity-40" />No conversations</div>
              ) : filtered.map((c) => (
                <button key={c.id} data-testid={`support-conv-${c.id}`} onClick={() => setSelId(c.id)}
                  className={cn("w-full text-left px-4 py-3 border-b border-border hover:bg-muted/40 transition-colors",
                    selId === c.id && "bg-muted/60")}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-medium text-sm truncate">{c.userName}</span>
                    <span className="text-[10px] text-muted-foreground shrink-0">{timeAgo(c.lastMessageAt)}</span>
                  </div>
                  <p className="text-xs text-muted-foreground truncate mt-0.5">{c.lastMessage}</p>
                  <span className={cn("inline-block mt-1.5 text-[10px] px-2 py-0.5 rounded-full border", STATUS_META[c.status]?.cls)}>
                    {STATUS_META[c.status]?.label || c.status}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {/* Thread */}
          <div className="rounded-xl border border-border flex flex-col overflow-hidden">
            {!conv ? (
              <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground">
                <Headset className="h-10 w-10 mb-3 opacity-40" /><p className="text-sm">Select a conversation</p>
              </div>
            ) : (
              <>
                <div className="px-4 py-3 border-b border-border flex items-center justify-between">
                  <div>
                    <p className="font-semibold text-sm">{conv.userName}</p>
                    <p className="text-[11px] text-muted-foreground">Category: {conv.category} · {conv.assignedTo ? `Assigned: ${conv.assignedTo}` : "Unassigned"}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={cn("text-[11px] px-2 py-0.5 rounded-full border", STATUS_META[conv.status]?.cls)}>{STATUS_META[conv.status]?.label}</span>
                    {conv.status !== "resolved"
                      ? <Button size="sm" variant="outline" onClick={() => setStatus("resolved")} data-testid="support-resolve"><CheckCircle2 className="h-4 w-4 mr-1.5" />Resolve</Button>
                      : <Button size="sm" variant="outline" onClick={() => setStatus("open")} data-testid="support-reopen">Reopen</Button>}
                  </div>
                </div>
                <div ref={threadRef} className="flex-1 overflow-auto p-4 space-y-3">
                  {(conv.messages || []).map((m, i) => {
                    const mine = m.sender === "agent";
                    const bot = m.sender === "bot";
                    return (
                      <div key={i} className={cn("flex gap-2 max-w-[80%]", mine ? "ml-auto flex-row-reverse" : "")}>
                        <div className={cn("grid place-items-center h-7 w-7 rounded-full shrink-0",
                          bot ? "bg-sky-500/15 text-sky-500" : mine ? "bg-pink-500/15 text-pink-500" : "bg-muted text-muted-foreground")}>
                          {bot ? <Bot className="h-4 w-4" /> : mine ? <Headset className="h-4 w-4" /> : <User className="h-4 w-4" />}
                        </div>
                        <div>
                          <div className={cn("rounded-2xl px-3.5 py-2 text-sm",
                            mine ? "bg-pink-500 text-white rounded-tr-sm" : bot ? "bg-sky-500/10 rounded-tl-sm" : "bg-muted rounded-tl-sm")}>
                            {m.text}
                          </div>
                          <p className="text-[10px] text-muted-foreground mt-0.5 px-1">
                            {bot ? "Aria (AI)" : mine ? (m.agentEmail || "Agent") : conv.userName} · {timeAgo(m.createdAt)}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="p-3 border-t border-border flex items-center gap-2">
                  <Input data-testid="support-reply-input" value={reply} onChange={(e) => setReply(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendReply()} placeholder="Reply as support agent…" className="h-10" />
                  <Button onClick={sendReply} disabled={sending || !reply.trim()} data-testid="support-send">
                    {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                  </Button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
