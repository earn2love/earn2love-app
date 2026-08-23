import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { useAuth } from "@/context/AuthContext";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Bot, Search, Loader2, Send, Gamepad2, ArrowLeft, Sparkles, ChevronRight,
  MessageSquare, Swords, Trophy, X, Plus,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const AVATAR = ["from-pink-500/30 to-rose-500/20 text-pink-500", "from-sky-500/30 to-indigo-500/20 text-sky-500",
  "from-emerald-500/30 to-teal-500/20 text-emerald-500", "from-violet-500/30 to-fuchsia-500/20 text-violet-500",
  "from-amber-500/30 to-orange-500/20 text-amber-500"];
const avatarCls = (id) => AVATAR[(id || "").split("").reduce((a, c) => a + c.charCodeAt(0), 0) % AVATAR.length];

export default function PlayChat() {
  const [chars, setChars] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(null);
  const [tab, setTab] = useState("chat");

  useEffect(() => {
    api.get("/ai/characters").then(({ data }) => setChars((data.items || []).filter((c) => c.enabled !== false)))
      .catch((e) => toast.error(formatApiError(e.response?.data?.detail || e)))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return chars.filter((c) => !q || `${c.displayName} ${c.profession} ${c.city} ${c.country}`.toLowerCase().includes(q));
  }, [chars, query]);

  if (selected) {
    return (
      <div data-testid="play-chat-page">
        <Topbar title="Play & Chat" subtitle="Talk to a character, then challenge them to a game — all in one place" />
        <div className="p-6 max-w-3xl mx-auto space-y-4">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" data-testid="pc-back" onClick={() => setSelected(null)}><ArrowLeft className="h-4 w-4 mr-1" />All characters</Button>
            <div className={cn("grid place-items-center h-11 w-11 rounded-full bg-gradient-to-br font-bold shrink-0", avatarCls(selected.characterId))}>{(selected.displayName || "?")[0]}</div>
            <div className="min-w-0">
              <p className="font-semibold leading-tight">{selected.displayName}</p>
              <p className="text-[11px] text-muted-foreground truncate">{selected.profession} · {selected.city}, {selected.country}</p>
            </div>
            <div className="ml-auto flex rounded-lg border border-border p-0.5">
              <button data-testid="pc-tab-chat" onClick={() => setTab("chat")} className={cn("px-3 py-1.5 rounded-md text-sm flex items-center gap-1.5", tab === "chat" ? "gradient-brand text-white" : "text-muted-foreground")}><MessageSquare className="h-3.5 w-3.5" />Chat</button>
              <button data-testid="pc-tab-play" onClick={() => setTab("play")} className={cn("px-3 py-1.5 rounded-md text-sm flex items-center gap-1.5", tab === "play" ? "gradient-brand text-white" : "text-muted-foreground")}><Gamepad2 className="h-3.5 w-3.5" />Play</button>
            </div>
          </div>
          {tab === "chat"
            ? <ChatPanel character={selected} onChallenge={() => setTab("play")} />
            : <PlayPanel character={selected} roster={chars} />}
        </div>
      </div>
    );
  }

  return (
    <div data-testid="play-chat-page">
      <Topbar title="Play & Chat" subtitle="Talk to a character, then challenge them to a game — all in one place" />
      <div className="p-6 space-y-5">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input data-testid="pc-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Find a character to chat & play with…" className="pl-9 h-10" />
        </div>
        {loading ? <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {filtered.map((c) => (
                <button key={c.characterId} data-testid={`pc-char-${c.characterId}`} onClick={() => { setSelected(c); setTab("chat"); }}
                  className="text-left rounded-xl border border-border bg-card p-4 flex items-center gap-3 hover:border-pink-500/50 hover:bg-pink-500/5 transition-colors">
                  <div className={cn("grid place-items-center h-12 w-12 rounded-full bg-gradient-to-br text-lg font-bold shrink-0", avatarCls(c.characterId))}>{(c.displayName || "?")[0]}</div>
                  <div className="min-w-0">
                    <p className="font-semibold truncate">{c.displayName}</p>
                    <p className="text-[11px] text-muted-foreground truncate">{c.profession}</p>
                    <p className="text-[11px] text-muted-foreground truncate">{c.city}, {c.country}</p>
                  </div>
                </button>
              ))}
            </div>
          )}
      </div>
    </div>
  );
}

/* ------------------------------ Persistent Chat ------------------------------ */
function ChatPanel({ character, onChallenge }) {
  const [turns, setTurns] = useState([]);
  const [rel, setRel] = useState(null);
  const [text, setText] = useState("");
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const scroller = useRef(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/ai/chat/${character.characterId}/history`);
      setTurns(data.turns || []); setRel(data.relationship?.state || "new");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setLoading(false);
  }, [character.characterId]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { scroller.current?.scrollTo(0, scroller.current.scrollHeight); }, [turns, loading]);

  const send = async () => {
    const msg = text.trim();
    if (!msg || sending) return;
    setText(""); setSending(true);
    const idx = turns.length;
    setTurns((t) => [...t, { sender: "user", text: msg, index: idx }]);
    try {
      const { data } = await api.post("/ai/chat", { characterId: character.characterId, message: msg });
      setTurns((t) => [...t, { sender: "character", text: data.responseText, index: idx + 1, cooldown: data.cooldown }]);
      if (data.relationshipState) setRel(data.relationshipState);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setSending(false);
  };

  return (
    <div className="rounded-2xl border border-border bg-card overflow-hidden" data-testid="pc-chat-panel">
      <div className="flex items-center justify-between px-4 py-2 border-b border-border bg-muted/30">
        <span className="text-[11px] text-muted-foreground">Relationship: <b className="text-foreground capitalize" data-testid="pc-relationship">{rel || "new"}</b> · memory persists across sessions</span>
        <Button size="sm" variant="outline" data-testid="pc-challenge" onClick={onChallenge}><Swords className="h-3.5 w-3.5 mr-1.5" />Challenge to a game</Button>
      </div>
      <div ref={scroller} className="h-[420px] overflow-y-auto p-4 space-y-3" data-testid="pc-messages">
        {loading ? <div className="flex justify-center py-16"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
          : turns.length === 0 ? <p className="text-center text-sm text-muted-foreground py-16">Say hi to {character.displayName} 👋</p>
            : turns.map((t, i) => (
              <div key={i} className={cn("flex", t.sender === "user" ? "justify-end" : "justify-start")}>
                <div data-testid={`pc-msg-${t.sender}`} className={cn("max-w-[78%] rounded-2xl px-3.5 py-2 text-sm whitespace-pre-wrap break-words",
                  t.sender === "user" ? "gradient-brand text-white rounded-br-sm"
                    : t.cooldown ? "bg-amber-500/10 border border-amber-500/30 text-amber-700 rounded-bl-sm"
                      : "bg-muted rounded-bl-sm")}>{t.text}</div>
              </div>
            ))}
        {sending && <div className="flex justify-start"><div className="bg-muted rounded-2xl rounded-bl-sm px-3.5 py-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" /></div></div>}
      </div>
      <div className="flex items-center gap-2 p-3 border-t border-border">
        <Input data-testid="pc-input" value={text} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send()} placeholder={`Message ${character.displayName}…`} className="h-10" disabled={sending} />
        <Button data-testid="pc-send" onClick={send} disabled={!text.trim() || sending} className="gradient-brand text-white border-0 h-10 w-10 p-0"><Send className="h-4 w-4" /></Button>
      </div>
    </div>
  );
}

/* ------------------------------ Game setup + run ------------------------------ */
function PlayPanel({ character, roster }) {
  const [games, setGames] = useState([]);
  const [gameId, setGameId] = useState("");
  const [extraAIs, setExtraAIs] = useState([]); // additional opponents (multi-AI room)
  const [session, setSession] = useState(null);
  const [starting, setStarting] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/games").then(({ data }) => {
      const list = (data.items || data || []).filter((g) => g.supportsAI !== false && g.enabled && !g.archived);
      setGames(list); if (list[0]) setGameId(list[0].gameId);
    }).catch((e) => toast.error(formatApiError(e.response?.data?.detail || e))).finally(() => setLoading(false));
  }, []);

  const game = games.find((g) => g.gameId === gameId);
  const maxExtra = Math.max(0, (game?.maxPlayers || 2) - 2); // seats beyond you + main character
  const rosterOptions = roster.filter((c) => c.characterId !== character.characterId && !extraAIs.includes(c.characterId));

  const start = async () => {
    setStarting(true);
    try {
      const aiIds = [character.characterId, ...extraAIs];
      const { data } = await api.post("/play/sessions", { gameId, aiCharacterIds: aiIds });
      setSession(data);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setStarting(false);
  };

  if (session) return <GameRunner session={session} setSession={setSession} character={character} roster={roster} onExit={() => setSession(null)} />;

  return (
    <div className="rounded-2xl border border-border bg-card p-5 space-y-4" data-testid="pc-play-panel">
      {loading ? <div className="flex justify-center py-12"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div> : (
        <>
          <div className="space-y-1.5">
            <label className="text-xs text-muted-foreground">Choose a game to play against {character.displayName}</label>
            <Select value={gameId} onValueChange={(v) => { setGameId(v); setExtraAIs([]); }}>
              <SelectTrigger className="h-10" data-testid="pc-game-select"><SelectValue placeholder="Pick a game" /></SelectTrigger>
              <SelectContent className="max-h-80">
                {games.map((g) => <SelectItem key={g.gameId} value={g.gameId} data-testid={`pc-game-${g.gameId}`}>{g.name} · <span className="capitalize text-muted-foreground">{g.gameType}</span></SelectItem>)}
              </SelectContent>
            </Select>
            {game && <p className="text-[11px] text-muted-foreground">{game.shortDescription}</p>}
          </div>

          {maxExtra > 0 && (
            <div className="space-y-2" data-testid="pc-multiai">
              <label className="text-xs text-muted-foreground">Group game — add more AI opponents (up to {maxExtra})</label>
              <div className="flex flex-wrap gap-1.5">
                {extraAIs.map((id) => {
                  const c = roster.find((r) => r.characterId === id);
                  return <span key={id} data-testid={`pc-extra-${id}`} className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full border border-pink-500/30 bg-pink-500/10 text-pink-600">{c?.displayName || id}<button onClick={() => setExtraAIs((a) => a.filter((x) => x !== id))}><X className="h-3 w-3" /></button></span>;
                })}
                {extraAIs.length < maxExtra && (
                  <Select value="" onValueChange={(v) => v && setExtraAIs((a) => [...a, v])}>
                    <SelectTrigger className="h-8 w-[190px] text-xs" data-testid="pc-add-ai"><span className="flex items-center gap-1 text-muted-foreground"><Plus className="h-3 w-3" />Add opponent</span></SelectTrigger>
                    <SelectContent className="max-h-72">
                      {rosterOptions.map((c) => <SelectItem key={c.characterId} value={c.characterId}>{c.displayName} · {c.city}</SelectItem>)}
                    </SelectContent>
                  </Select>
                )}
              </div>
            </div>
          )}

          <Button data-testid="pc-start-game" onClick={start} disabled={!gameId || starting} className="w-full gradient-brand text-white border-0">
            {starting ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Swords className="h-4 w-4 mr-2" />}
            Start game{extraAIs.length ? ` (you + ${1 + extraAIs.length} AI)` : ` vs ${character.displayName}`}
          </Button>
        </>
      )}
    </div>
  );
}

function GameRunner({ session, setSession, character, roster, onExit }) {
  const { admin } = useAuth();
  const [busy, setBusy] = useState(false);
  const pub = session;
  const myId = admin?.uid;
  const stateRef = useRef(session);
  stateRef.current = session;

  // release the authoritative session if the user leaves mid-game (no orphan ACTIVE sessions)
  useEffect(() => () => {
    const s = stateRef.current;
    if (s?.sessionId && s.status !== "completed") {
      api.post(`/play/sessions/${s.sessionId}/abandon`, {}).catch(() => {});
    }
  }, []);

  const label = useCallback((id) => {
    if (id === myId) return "You";
    const c = roster.find((r) => r.characterId === id) || (id === character.characterId ? character : null);
    return c ? c.displayName : id;
  }, [myId, roster, character]);

  const act = async (action) => {
    setBusy(true);
    try { const { data } = await api.post(`/play/sessions/${pub.sessionId}/act`, { action, expectedRevision: pub.revision }); setSession(data); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setBusy(false);
  };
  const advance = async () => {
    setBusy(true);
    try { const { data } = await api.post(`/play/sessions/${pub.sessionId}/advance`, {}); setSession(data); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setBusy(false);
  };
  const leave = async () => {
    if (pub.sessionId && pub.status !== "completed") {
      try { await api.post(`/play/sessions/${pub.sessionId}/abandon`, {}); } catch (e) { /* ignore */ }
    }
    onExit();
  };

  const myActions = pub.yourActions || [];
  return (
    <div className="rounded-2xl border-2 border-border bg-card p-5 space-y-3" data-testid="pc-game-runner">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span>Round {pub.round}/{pub.totalRounds}</span>
        <div className="flex items-center gap-2">
          <span className="capitalize px-2 py-0.5 rounded-full border border-border">{pub.phase}</span>
          {pub.status !== "completed" && <button data-testid="pc-leave" onClick={leave} className="text-rose-500 hover:text-rose-600 flex items-center gap-1"><X className="h-3.5 w-3.5" />Leave</button>}
        </div>
      </div>
      <div className="h-1.5 rounded-full bg-muted overflow-hidden"><div className="h-full gradient-brand" style={{ width: `${(pub.round / pub.totalRounds) * 100}%` }} /></div>

      {pub.status === "completed" ? (
        <div className="text-center py-6 space-y-2" data-testid="pc-game-complete">
          <Trophy className="h-8 w-8 mx-auto text-amber-500" />
          <p className="font-semibold">Game complete!</p>
          <p className="text-sm text-muted-foreground">{pub.result?.type === "scored" ? (pub.result.draw ? "It's a draw!" : `Winner: ${(pub.result.winners || []).map(label).join(", ")}`) : "Nicely done together."}</p>
          <ScoreRow scores={pub.scores} label={label} />
          <div className="flex items-center justify-center gap-2 pt-2">
            <Button variant="outline" size="sm" data-testid="pc-game-exit" onClick={onExit}>Back to setup</Button>
          </div>
        </div>
      ) : (
        <>
          {pub.prompt && <div className="rounded-xl bg-background border border-border p-3 text-center font-medium">{pub.prompt.prompt}</div>}
          {pub.setter && <p className="text-[11px] text-center text-muted-foreground">Setter: {label(pub.setter)} · {pub.subphase}</p>}
          {pub.turn && <p className="text-[11px] text-center text-muted-foreground">Turn: {label(pub.turn)}</p>}

          {pub.phase === "reveal" ? (
            <div className="space-y-2">
              <RevealView pub={pub} label={label} />
              <Button onClick={advance} disabled={busy} data-testid="pc-advance" className="w-full gradient-brand text-white border-0">Next round<ChevronRight className="h-4 w-4 ml-1" /></Button>
            </div>
          ) : myActions.length > 0 ? (
            <MyControls action={myActions[0]} prompt={pub.prompt} onAct={act} busy={busy} />
          ) : (
            <p className="text-[11px] text-center text-muted-foreground/70" data-testid="pc-waiting">{busy ? "Opponents are playing…" : "Waiting for opponents…"}</p>
          )}
          <ScoreRow scores={pub.scores} label={label} />
        </>
      )}
    </div>
  );
}

function MyControls({ action, prompt, onAct, busy }) {
  const [text, setText] = useState("");
  const [stmts, setStmts] = useState(["", "", ""]);
  const [lie, setLie] = useState(null);
  const t = action.type;
  const aid = () => `me-${Date.now()}`;
  const opts = prompt?.options || [];

  if (t === "answer" || t === "guess") {
    const list = action.options || opts.map((o) => o.key) || [];
    return (
      <div className="space-y-1.5" data-testid="pc-controls-choice">
        {list.map((o) => {
          const label = opts.find((x) => x.key === o)?.label ?? String(o);
          return <button key={String(o)} data-testid={`pc-opt-${o}`} disabled={busy} onClick={() => onAct({ type: t, value: o, actionId: aid() })}
            className="w-full text-left px-3 py-2 rounded-lg border border-border hover:border-pink-500/50 hover:bg-pink-500/5 text-sm transition-colors disabled:opacity-50">{label}</button>;
        })}
      </div>
    );
  }
  if (t === "set_secret" && action.statements) {
    return (
      <div className="space-y-1.5" data-testid="pc-controls-statements">
        {stmts.map((s, i) => (
          <div key={i} className="flex items-center gap-2">
            <button data-testid={`pc-lie-${i}`} onClick={() => setLie(i)} className={cn("h-4 w-4 rounded-full border shrink-0", lie === i ? "bg-rose-500 border-rose-500" : "border-muted-foreground")} title="Mark as the lie" />
            <Input className="h-8" value={s} onChange={(e) => setStmts((a) => a.map((x, j) => j === i ? e.target.value : x))} placeholder={`Statement ${i + 1}`} />
          </div>
        ))}
        <Button size="sm" className="w-full" data-testid="pc-set-secret" disabled={busy || stmts.some((s) => !s.trim()) || lie === null} onClick={() => onAct({ type: "set_secret", statements: stmts, lieIndex: lie, actionId: aid() })}>Submit statements</Button>
      </div>
    );
  }
  if (t === "respond" || (t === "contribute" && !opts.length) || (t === "set_secret" && !opts.length)) {
    return (
      <div className="flex items-center gap-2" data-testid="pc-controls-text">
        <Input className="h-9" data-testid="pc-text" value={text} onChange={(e) => setText(e.target.value)} placeholder="Type your response…" />
        <Button size="sm" data-testid="pc-text-send" disabled={busy || !text.trim()} onClick={() => { onAct({ type: t, value: text, actionId: aid() }); setText(""); }}>Send</Button>
      </div>
    );
  }
  // contribute with options
  const list = action.options || opts.map((o) => o.key) || [];
  return (
    <div className="space-y-1.5" data-testid="pc-controls-contribute">
      {list.map((o) => {
        const label = opts.find((x) => x.key === o)?.label ?? String(o);
        return <button key={o} data-testid={`pc-opt-${o}`} disabled={busy} onClick={() => onAct({ type: "contribute", value: o, actionId: aid() })}
          className="w-full text-left px-3 py-2 rounded-lg border border-border hover:border-pink-500/50 text-sm disabled:opacity-50">{label}</button>;
      })}
    </div>
  );
}

const ScoreRow = ({ scores, label }) => (
  <div className="flex flex-wrap items-center justify-center gap-3 text-xs pt-2 border-t border-border" data-testid="pc-scores">
    {Object.entries(scores || {}).map(([p, s]) => (
      <span key={p} className="flex items-center gap-1"><Sparkles className="h-3 w-3 text-pink-500" />{label ? label(p) : p}: <b>{s}</b></span>
    ))}
  </div>
);

const RevealView = ({ pub, label }) => {
  const r = pub.revealed;
  if (!r || typeof r !== "object") return null;
  const fmt = (v) => Array.isArray(v) ? v.join(", ") : (v && typeof v === "object" ? Object.entries(v).map(([k, x]) => `${label ? label(k) : k}: ${x}`).join(" · ") : String(v));
  return (
    <div className="rounded-lg bg-muted/40 border border-border p-3 text-xs space-y-1" data-testid="pc-reveal">
      <p className="font-semibold text-muted-foreground mb-1">Round reveal</p>
      {Object.entries(r).map(([k, v]) => (
        <div key={k} className="flex gap-2">
          <span className="text-muted-foreground capitalize shrink-0">{label ? label(k) : k.replace(/_/g, " ")}:</span>
          <span className="break-words">{fmt(v)}</span>
        </div>
      ))}
    </div>
  );
};
