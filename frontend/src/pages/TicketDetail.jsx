import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { StatusBadge } from "@/components/StatusBadge";
import { useAuth } from "@/context/AuthContext";
import { fmtDateTime } from "@/lib/format";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ArrowLeft, Lock, Send } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

export default function TicketDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { can } = useAuth();
  const [data, setData] = useState(null);
  const [text, setText] = useState("");
  const [visibility, setVisibility] = useState("user");
  const [busy, setBusy] = useState(false);
  const canReply = can("support-tickets");

  const load = () => api.get(`/support-tickets/${id}/detail`).then((r) => setData(r.data)).catch((e) => toast.error(formatApiError(e.response?.data?.detail)));
  useEffect(() => { load(); }, [id]);

  const send = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try {
      await api.post(`/support-tickets/${id}/reply`, { text, visibility });
      setText(""); await load();
      toast.success(visibility === "user" ? "Reply sent to user" : "Internal note added");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setBusy(false); }
  };

  const act = async (action) => {
    try { await api.post(`/resources/support-tickets/${id}/action`, { action }); load(); toast.success("Updated"); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
  };

  if (!data) return (<><Topbar title="Ticket" /><main className="flex-1 grid place-items-center text-muted-foreground">Loading…</main></>);
  const { ticket, messages } = data;

  return (
    <>
      <Topbar title={`Ticket ${ticket.id}`} subtitle={ticket.subject} />
      <main className="flex-1 overflow-y-auto p-5 md:p-8 space-y-5">
        <button onClick={() => navigate("/m/support-tickets")} data-testid="back-to-tickets" className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to tickets
        </button>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 space-y-4">
            {/* Thread */}
            <div className="rounded-lg border border-border bg-card p-5 space-y-4">
              <h3 className="font-display font-semibold text-sm">Conversation</h3>
              {messages.length === 0 && <p className="text-sm text-muted-foreground py-4">No messages yet.</p>}
              {messages.map((m) => {
                const isUser = m.role === "User";
                return (
                  <div key={m.id} data-testid={`ticket-msg-${m.id}`} className={cn("flex gap-3", !isUser && "flex-row-reverse")}>
                    <Avatar className="h-8 w-8 shrink-0"><AvatarFallback className={cn("text-[10px]", !isUser && "gradient-brand text-white")}>{m.author?.slice(0, 2).toUpperCase()}</AvatarFallback></Avatar>
                    <div className={cn("max-w-[80%] rounded-lg border p-3", isUser ? "bg-accent/40 border-border" : "bg-primary/5 border-primary/20",
                      m.visibility === "internal" && "bg-amber-500/10 border-amber-500/25")}>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-semibold">{m.author}</span>
                        {m.visibility === "internal" && <span className="inline-flex items-center gap-1 text-[10px] text-amber-600"><Lock className="h-3 w-3" /> Internal</span>}
                        <span className="text-[10px] text-muted-foreground ml-auto">{fmtDateTime(m.created_at)}</span>
                      </div>
                      <p className="text-sm">{m.text}</p>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Reply box */}
            {canReply ? (
              <div className="rounded-lg border border-border bg-card p-4 space-y-3">
                <div className="flex gap-2">
                  <button data-testid="reply-mode-user" onClick={() => setVisibility("user")} className={cn("text-xs px-3 py-1.5 rounded-full border", visibility === "user" ? "border-primary text-primary bg-primary/10" : "border-border text-muted-foreground")}>Reply to user</button>
                  <button data-testid="reply-mode-internal" onClick={() => setVisibility("internal")} className={cn("text-xs px-3 py-1.5 rounded-full border", visibility === "internal" ? "border-amber-500 text-amber-600 bg-amber-500/10" : "border-border text-muted-foreground")}>Internal note</button>
                </div>
                <Textarea data-testid="ticket-reply-input" value={text} onChange={(e) => setText(e.target.value)} rows={3}
                  placeholder={visibility === "user" ? "Write a reply visible to the user…" : "Write an internal-only note…"} />
                <div className="flex justify-end">
                  <Button data-testid="ticket-send-btn" onClick={send} disabled={busy || !text.trim()} className="gradient-brand text-white border-0 gap-2">
                    <Send className="h-4 w-4" /> {busy ? "Sending…" : "Send"}
                  </Button>
                </div>
              </div>
            ) : <p className="text-xs text-muted-foreground">Your role has read-only access to tickets.</p>}
          </div>

          {/* Ticket info */}
          <div className="space-y-4">
            <div className="rounded-lg border border-border bg-card p-5 space-y-3">
              <h3 className="font-display font-semibold text-sm">Ticket Info</h3>
              <div className="flex justify-between text-sm"><span className="text-muted-foreground">Status</span><StatusBadge value={ticket.status} /></div>
              <div className="flex justify-between text-sm"><span className="text-muted-foreground">Priority</span><StatusBadge value={ticket.priority} /></div>
              <div className="flex justify-between text-sm"><span className="text-muted-foreground">Category</span><span className="font-medium">{ticket.category}</span></div>
              <div className="flex justify-between text-sm"><span className="text-muted-foreground">User</span><span className="font-medium">{ticket.user}</span></div>
              <div className="flex justify-between text-sm"><span className="text-muted-foreground">Assigned</span><span className="font-medium">{ticket.assigned_admin}</span></div>
              <div className="flex justify-between text-sm"><span className="text-muted-foreground">Updated</span><span className="text-xs">{fmtDateTime(ticket.last_updated)}</span></div>
            </div>
            {canReply && (
              <div className="rounded-lg border border-border bg-card p-5 space-y-2">
                <h3 className="font-display font-semibold text-sm mb-1">Quick Actions</h3>
                <Button variant="outline" size="sm" className="w-full" data-testid="ticket-assign" onClick={() => act("assign")}>Assign to me</Button>
                <Button variant="outline" size="sm" className="w-full" data-testid="ticket-resolve" onClick={() => act("resolve")}>Mark resolved</Button>
                <Button variant="outline" size="sm" className="w-full" data-testid="ticket-close" onClick={() => act("close")}>Close ticket</Button>
              </div>
            )}
          </div>
        </div>
      </main>
    </>
  );
}
