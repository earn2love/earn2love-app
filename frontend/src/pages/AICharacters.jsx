import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { useAuth } from "@/context/AuthContext";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  Bot, Search, Loader2, FlaskConical, Pencil, BarChart3, Sparkles, Send, RotateCcw,
  ShieldCheck, Repeat, Languages, Brain, Gauge, MessagesSquare, CheckCircle2, XCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const LANGS = [
  { code: "", label: "Auto-detect" }, { code: "english", label: "English" },
  { code: "telugu-english", label: "Telugu-English" }, { code: "hindi-english", label: "Hindi-English" },
  { code: "tamil-english", label: "Tamil-English" }, { code: "telugu", label: "Telugu" }, { code: "hindi", label: "Hindi" },
];
const REL_STATES = ["", "new", "familiar", "comfortable", "established"];
const AVATAR = { ref_ananya: "from-pink-500/30 to-rose-500/20 text-pink-500", ref_marcus: "from-sky-500/30 to-indigo-500/20 text-sky-500", ref_sora: "from-emerald-500/30 to-teal-500/20 text-emerald-500" };

export default function AICharacters() {
  const { admin } = useAuth();
  const canEdit = admin?.role === "super_admin" || admin?.permissions === "*" || (Array.isArray(admin?.permissions) && admin.permissions.includes("ai-characters"));
  const [chars, setChars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [lab, setLab] = useState(null);
  const [editing, setEditing] = useState(null);
  const [stored, setStored] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try { const { data } = await api.get("/ai/characters"); setChars(data.items || []); setStored(data.storedAvailable); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return chars.filter((c) => !q || `${c.displayName} ${c.profession} ${(c.personalityTraits || []).join(" ")} ${c.city}`.toLowerCase().includes(q));
  }, [chars, query]);

  return (
    <div data-testid="ai-characters-page">
      <Topbar title="AI Characters" subtitle="Advanced AI Character Engine — profiles, world facts & the Character Lab" />
      <div className="p-6 space-y-5">
        {!stored && (
          <div className="flex items-center gap-2 rounded-lg border border-sky-500/30 bg-sky-500/10 text-sky-500 px-4 py-2.5 text-sm" data-testid="ai-reference-banner">
            <Sparkles className="h-4 w-4" /> Showing the <b className="mx-1">3 reference characters</b>. Stored production characters appear once Firebase is connected. The Character Lab works now.
          </div>
        )}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input data-testid="ai-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search characters…" className="pl-9 h-10" />
          </div>
          {canEdit && <Button data-testid="ai-new" onClick={() => setEditing({ _new: true, displayName: "", isAi: true, age: 25, country: "", profession: "", languages: ["English"], personalityTraits: [], replyLengthPreference: "short", emojiStyle: "sparing", humorStyle: "light", curiosityLevel: 0.5, confidenceLevel: 0.5, warmthLevel: 0.5, playfulnessLevel: 0.5, directnessLevel: 0.5, romanceLevel: 0.1, tierAccess: ["casual", "friendship", "love"], enabled: true })} className="gradient-brand text-white border-0"><Bot className="h-4 w-4 mr-1.5" />New Character</Button>}
        </div>

        {loading ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {filtered.map((c) => (
              <div key={c.characterId} data-testid={`ai-card-${c.characterId}`} className="rounded-xl border border-border bg-card p-5 flex flex-col gap-3">
                <div className="flex items-start gap-3">
                  <div className={cn("grid place-items-center h-12 w-12 rounded-full bg-gradient-to-br text-lg font-bold shrink-0", AVATAR[c.characterId] || "from-violet-500/30 to-fuchsia-500/20 text-violet-500")}>{(c.displayName || "?")[0]}</div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <p className="font-semibold truncate">{c.displayName}</p>
                      <span className="text-[9px] px-1.5 py-0.5 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-500 shrink-0">AI</span>
                    </div>
                    <p className="text-[11px] text-muted-foreground truncate">{c.profession}</p>
                    <p className="text-[11px] text-muted-foreground truncate">{c.city}{c.city && c.country ? ", " : ""}{c.country} · {c.age}</p>
                  </div>
                </div>
                <div className="flex flex-wrap gap-1">
                  {(c.personalityTraits || []).slice(0, 3).map((t) => <span key={t} className="text-[10px] px-2 py-0.5 rounded-full border border-border text-muted-foreground">{t}</span>)}
                </div>
                <div className="flex flex-wrap gap-1 text-[10px] text-muted-foreground">
                  <span className="inline-flex items-center gap-1"><Languages className="h-3 w-3" />{(c.languages || []).join(", ")}</span>
                </div>
                <div className="grid grid-cols-3 gap-1.5 text-[10px]">
                  <LevelBar label="Warm" v={c.warmthLevel} /><LevelBar label="Playful" v={c.playfulnessLevel} /><LevelBar label="Direct" v={c.directnessLevel} />
                </div>
                <div className="flex items-center gap-1 pt-2 border-t border-border">
                  <Button size="sm" data-testid={`ai-lab-${c.characterId}`} onClick={() => setLab(c)} className="gradient-brand text-white border-0 flex-1"><FlaskConical className="h-4 w-4 mr-1.5" />Lab</Button>
                  {canEdit && <Button size="sm" variant="outline" data-testid={`ai-edit-${c.characterId}`} onClick={() => setEditing(c)}><Pencil className="h-4 w-4" /></Button>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
      {lab && <CharacterLab character={lab} onClose={() => setLab(null)} />}
      {editing && <CharacterEditor character={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />}
    </div>
  );
}

const LevelBar = ({ label, v }) => (
  <div><div className="flex justify-between"><span>{label}</span><span>{Math.round((v || 0) * 100)}</span></div>
    <div className="h-1 rounded-full bg-muted overflow-hidden mt-0.5"><div className="h-full bg-pink-500" style={{ width: `${(v || 0) * 100}%` }} /></div></div>
);

/* ------------------------------ AI Character Lab (sandbox) ------------------------------ */
function CharacterLab({ character, onClose }) {
  const [sid, setSid] = useState(null);
  const [msgs, setMsgs] = useState([]);        // {role, text, meta?}
  const [input, setInput] = useState("");
  const [lang, setLang] = useState("");
  const [rel, setRel] = useState("");
  const [fixtures, setFixtures] = useState("");
  const [starting, setStarting] = useState(true);
  const [sending, setSending] = useState(false);
  const [selected, setSelected] = useState(null);
  const endRef = useRef(null);

  const start = useCallback(async () => {
    setStarting(true); setMsgs([]); setSelected(null);
    try {
      const { data } = await api.post("/ai/lab/start", { characterId: character.characterId, memoryFixtures: fixtures.split("\n").map((s) => s.trim()).filter(Boolean) });
      setSid(data.sessionId);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setStarting(false);
  }, [character.characterId, fixtures]);
  useEffect(() => { start(); /* eslint-disable-next-line */ }, [character.characterId]);
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  const send = async () => {
    const text = input.trim(); if (!text || !sid) return;
    setInput(""); setMsgs((m) => [...m, { role: "user", text }]); setSending(true);
    try {
      const { data } = await api.post("/ai/lab/chat", { sessionId: sid, message: text, language: lang || undefined, relationshipState: rel || undefined });
      setMsgs((m) => [...m, { role: "character", text: data.responseText, meta: data }]);
    } catch (e) {
      setMsgs((m) => [...m, { role: "error", text: formatApiError(e.response?.data?.detail || e) }]);
    }
    setSending(false);
  };

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-4xl h-[88vh] p-0 overflow-hidden" data-testid="character-lab">
        <div className="grid grid-cols-1 md:grid-cols-[1fr_320px] h-full">
          {/* Chat */}
          <div className="flex flex-col min-h-0 border-r border-border">
            <div className="px-5 py-3 border-b border-border flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-pink-500" />
              <div><p className="font-semibold text-sm">Character Lab · {character.displayName}</p>
                <p className="text-[11px] text-muted-foreground">Sandbox — nothing here is saved to production</p></div>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {starting ? <div className="flex justify-center py-10"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
                : msgs.length === 0 ? <p className="text-center text-sm text-muted-foreground py-10">Say hi, try a mixed-language message, plant a memory, or ask a tricky question.</p>
                : msgs.map((m, i) => (
                  <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                    <button onClick={() => m.meta && setSelected(m.meta)} className={cn("max-w-[80%] rounded-2xl px-3.5 py-2 text-sm text-left", m.role === "user" ? "bg-pink-500 text-white" : m.role === "error" ? "bg-rose-500/10 text-rose-500 border border-rose-500/30" : "bg-muted", m.meta && "cursor-pointer hover:ring-2 hover:ring-pink-500/40")} data-testid={m.role === "character" ? `lab-reply-${i}` : undefined}>
                      {m.text}
                      {m.meta && <span className="block mt-1 text-[10px] opacity-60">{m.meta.responseLanguage} · {m.meta.usage?.latencyMs}ms · tap for diagnostics</span>}
                    </button>
                  </div>
                ))}
              <div ref={endRef} />
            </div>
            <div className="p-3 border-t border-border flex gap-2">
              <Input data-testid="lab-input" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder="Type a message…" disabled={sending || !sid} />
              <Button data-testid="lab-send" onClick={send} disabled={sending || !input.trim() || !sid} className="gradient-brand text-white border-0">{sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}</Button>
            </div>
          </div>
          {/* Controls + diagnostics */}
          <div className="flex flex-col min-h-0 overflow-y-auto p-4 space-y-4">
            <DialogHeader className="p-0"><DialogTitle className="text-sm">Sandbox controls</DialogTitle></DialogHeader>
            <div><Label className="text-xs">Language</Label>
              <Select value={lang} onValueChange={setLang}><SelectTrigger data-testid="lab-lang" className="h-9"><SelectValue /></SelectTrigger>
                <SelectContent>{LANGS.map((l) => <SelectItem key={l.code} value={l.code}>{l.label}</SelectItem>)}</SelectContent></Select></div>
            <div><Label className="text-xs">Relationship state</Label>
              <Select value={rel} onValueChange={setRel}><SelectTrigger data-testid="lab-rel" className="h-9"><SelectValue placeholder="Auto (from turns)" /></SelectTrigger>
                <SelectContent>{REL_STATES.map((r) => <SelectItem key={r} value={r}>{r || "Auto (from turns)"}</SelectItem>)}</SelectContent></Select></div>
            <div><Label className="text-xs">Memory fixtures (one per line)</Label>
              <Textarea rows={3} value={fixtures} onChange={(e) => setFixtures(e.target.value)} placeholder="e.g. My dream is to visit Japan." className="text-xs" data-testid="lab-fixtures" />
              <Button size="sm" variant="outline" className="w-full mt-2" onClick={start} data-testid="lab-restart"><RotateCcw className="h-3.5 w-3.5 mr-1.5" />Restart session</Button></div>

            <div className="border-t border-border pt-3">
              <p className="text-xs font-semibold mb-2 flex items-center gap-1.5"><Gauge className="h-3.5 w-3.5" />Diagnostics</p>
              {!selected ? <p className="text-[11px] text-muted-foreground">Tap a reply to inspect its diagnostics.</p>
                : (
                  <div className="space-y-2 text-[11px]" data-testid="lab-diagnostics">
                    <Diag icon={Languages} label="Detected" value={selected.detectedLanguage} />
                    <Diag icon={Languages} label="Response lang" value={selected.responseLanguage} />
                    <Diag icon={MessagesSquare} label="Mode" value={selected.conversationMode} />
                    <Diag icon={Brain} label="Relationship" value={selected.relationshipState} />
                    <Diag icon={Brain} label="Memory used" value={(selected.memoryIdsUsed || []).length + " item(s)"} />
                    <div className="flex gap-2 pt-1">
                      <Pass ok={selected.quality?.consistencyPassed} icon={ShieldCheck} label="Consistency" />
                      <Pass ok={selected.quality?.repetitionPassed} icon={Repeat} label="No-repeat" />
                      <Pass ok={selected.quality?.safetyPassed} icon={ShieldCheck} label="Safety" />
                    </div>
                    <Diag icon={Gauge} label="Latency" value={`${selected.usage?.latencyMs}ms · ${selected.usage?.attempts} attempt(s)`} />
                    <Diag icon={Bot} label="Model" value={`${selected.usage?.provider}/${selected.usage?.model}`} />
                    {selected.plan && <details className="mt-1"><summary className="cursor-pointer text-muted-foreground">Response plan</summary><pre className="whitespace-pre-wrap break-words text-[10px] mt-1 bg-muted/40 p-2 rounded">{JSON.stringify(selected.plan, null, 1)}</pre></details>}
                  </div>
                )}
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
const Diag = ({ icon: Icon, label, value }) => (<div className="flex items-center justify-between gap-2"><span className="text-muted-foreground flex items-center gap-1"><Icon className="h-3 w-3" />{label}</span><span className="font-medium text-right truncate">{value}</span></div>);
const Pass = ({ ok, icon: Icon, label }) => (<span className={cn("inline-flex items-center gap-1 px-1.5 py-0.5 rounded border text-[10px]", ok ? "border-emerald-500/30 text-emerald-500 bg-emerald-500/10" : "border-rose-500/30 text-rose-500 bg-rose-500/10")}>{ok ? <CheckCircle2 className="h-3 w-3" /> : <XCircle className="h-3 w-3" />}{label}</span>);

/* ------------------------------ Editor ------------------------------ */
const LEVELS = [["warmthLevel", "Warmth"], ["playfulnessLevel", "Playfulness"], ["directnessLevel", "Directness"], ["confidenceLevel", "Confidence"], ["curiosityLevel", "Curiosity"], ["romanceLevel", "Romance"]];
function CharacterEditor({ character, onClose, onSaved }) {
  const [f, setF] = useState({ ...character });
  const [saving, setSaving] = useState(false);
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));
  const save = async () => {
    if (!f.displayName?.trim()) { toast.error("Name is required"); return; }
    setSaving(true);
    try {
      if (f._new) await api.post("/ai/characters", f);
      else await api.put(`/ai/characters/${f.characterId}`, f);
      toast.success("Character saved");
      onSaved();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setSaving(false);
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-xl max-h-[92vh] overflow-y-auto" data-testid="ai-editor">
        <DialogHeader><DialogTitle>{f._new ? "New AI Character" : `Edit — ${f.displayName}`}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div><Label>Display name</Label><Input data-testid="ai-name" value={f.displayName || ""} onChange={(e) => set("displayName", e.target.value)} /></div>
            <div><Label>Age (18+)</Label><Input type="number" value={f.age || 18} onChange={(e) => set("age", Number(e.target.value))} /></div>
            <div><Label>City</Label><Input value={f.city || ""} onChange={(e) => set("city", e.target.value)} /></div>
            <div><Label>Country</Label><Input value={f.country || ""} onChange={(e) => set("country", e.target.value)} /></div>
            <div className="col-span-2"><Label>Profession</Label><Input value={f.profession || ""} onChange={(e) => set("profession", e.target.value)} /></div>
            <div className="col-span-2"><Label>Languages (comma-separated)</Label><Input value={(f.languages || []).join(", ")} onChange={(e) => set("languages", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))} /></div>
            <div className="col-span-2"><Label>Personality traits (comma-separated)</Label><Input value={(f.personalityTraits || []).join(", ")} onChange={(e) => set("personalityTraits", e.target.value.split(",").map((s) => s.trim()).filter(Boolean))} /></div>
            <div><Label>Reply length</Label>
              <Select value={f.replyLengthPreference} onValueChange={(v) => set("replyLengthPreference", v)}><SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{["very_short", "short", "medium", "long"].map((x) => <SelectItem key={x} value={x}>{x}</SelectItem>)}</SelectContent></Select></div>
            <div><Label>Emoji style</Label>
              <Select value={f.emojiStyle} onValueChange={(v) => set("emojiStyle", v)}><SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{["none", "sparing", "frequent"].map((x) => <SelectItem key={x} value={x}>{x}</SelectItem>)}</SelectContent></Select></div>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            {LEVELS.map(([k, lbl]) => (
              <div key={k}><div className="flex justify-between text-xs"><Label>{lbl}</Label><span>{Math.round((f[k] || 0) * 100)}</span></div>
                <input type="range" min="0" max="1" step="0.05" value={f[k] || 0} onChange={(e) => set(k, Number(e.target.value))} className="w-full accent-pink-500" data-testid={`ai-level-${k}`} /></div>
            ))}
          </div>
          <div className="col-span-2"><Label>Communication style</Label><Textarea rows={2} value={f.communicationStyle || ""} onChange={(e) => set("communicationStyle", e.target.value)} /></div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button data-testid="ai-save" onClick={save} disabled={saving} className="gradient-brand text-white border-0">{saving && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />}Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
