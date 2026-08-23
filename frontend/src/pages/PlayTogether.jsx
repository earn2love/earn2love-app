import { useEffect, useMemo, useState, useCallback } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { useAuth } from "@/context/AuthContext";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import {
  Gamepad2, Search, Loader2, Star, Copy, Archive, Play, Pencil, ListChecks, BarChart3,
  Plus, Trash2, RotateCcw, ChevronRight, Sparkles, Circle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const MECHANIC_LABEL = { choice: "Choice", trivia: "Trivia", prompt: "Prompt", guess: "Guess", coop: "Co-op" };
const MECHANIC_CLS = {
  choice: "text-sky-500 border-sky-500/30 bg-sky-500/10",
  trivia: "text-violet-500 border-violet-500/30 bg-violet-500/10",
  prompt: "text-emerald-500 border-emerald-500/30 bg-emerald-500/10",
  guess: "text-amber-500 border-amber-500/30 bg-amber-500/10",
  coop: "text-pink-500 border-pink-500/30 bg-pink-500/10",
};
const CATEGORIES = ["Conversation & Connection", "Fun & Personality", "Knowledge & Thinking", "Word & Language", "Cooperative & Relationship"];
const DIFFICULTIES = ["easy", "medium", "hard"];
const TIERS = ["casual", "friendship", "love"];

export default function PlayTogether() {
  const { admin } = useAuth();
  const canEdit = admin?.role === "super_admin" || (Array.isArray(admin?.permissions) && admin.permissions.includes("games")) || admin?.permissions === "*";
  const [games, setGames] = useState([]);
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("all");
  const [status, setStatus] = useState("all");
  const [editing, setEditing] = useState(null);
  const [contentGame, setContentGame] = useState(null);
  const [previewGame, setPreviewGame] = useState(null);
  const [statsGame, setStatsGame] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [g, o] = await Promise.all([
        api.get("/games", { params: { search: "", category: "all", status: "all" } }),
        api.get("/games/overview"),
      ]);
      setGames(g.data.items || []); setOverview(o.data);
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return games.filter((g) =>
      (category === "all" || g.category === category) &&
      (status === "all" || (status === "enabled" ? (g.enabled && !g.archived) : status === "disabled" ? (!g.enabled && !g.archived) : g.archived)) &&
      (!q || `${g.name} ${g.shortDescription} ${g.gameType} ${g.category}`.toLowerCase().includes(q)));
  }, [games, query, category, status]);

  const patch = async (gid, body, msg) => {
    try { await api.put(`/games/${gid}`, body); if (msg) toast.success(msg); await load(); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
  };
  const duplicate = async (gid) => { try { await api.post(`/games/${gid}/duplicate`); toast.success("Game duplicated (disabled)"); await load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); } };
  const archive = async (g) => { try { await api.put(`/games/${g.gameId}`, { archived: !g.archived, enabled: g.archived ? g.enabled : false }); toast.success(g.archived ? "Restored" : "Archived"); await load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); } };
  const seed = async () => { setBusy(true); try { const { data } = await api.post("/games/seed"); toast.success(`Seeded ${data.games.seeded} games · ${data.content.seeded ?? 0} content`); await load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); } setBusy(false); };

  return (
    <div data-testid="play-together-page">
      <Topbar title="Play Together — Games" subtitle="Manage the reusable game platform: configure, preview, and publish" />
      <div className="p-6 space-y-5">
        {/* Overview */}
        {overview && (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <Stat label="Total games" value={overview.totalGames} />
            <Stat label="Enabled" value={overview.enabled} accent="emerald" />
            <Stat label="Disabled" value={overview.disabled} accent="amber" />
            <Stat label="Archived" value={overview.archived} />
            <Stat label="Featured" value={overview.featured} accent="pink" />
            <Stat label="Mechanics" value={(overview.mechanics || []).length} accent="violet" />
          </div>
        )}

        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative flex-1 min-w-[220px] max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input data-testid="games-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search games…" className="pl-9 h-10" />
          </div>
          <Select value={category} onValueChange={setCategory}>
            <SelectTrigger className="w-56" data-testid="games-category"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="all">All categories</SelectItem>{CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
          </Select>
          <Select value={status} onValueChange={setStatus}>
            <SelectTrigger className="w-40" data-testid="games-status"><SelectValue /></SelectTrigger>
            <SelectContent><SelectItem value="all">All statuses</SelectItem><SelectItem value="enabled">Enabled</SelectItem><SelectItem value="disabled">Disabled</SelectItem><SelectItem value="archived">Archived</SelectItem></SelectContent>
          </Select>
          {canEdit && <Button variant="outline" onClick={seed} disabled={busy} data-testid="games-seed">{busy ? <Loader2 className="h-4 w-4 mr-1.5 animate-spin" /> : <Sparkles className="h-4 w-4 mr-1.5" />}Seed catalog</Button>}
          {canEdit && <Button onClick={() => setEditing({ _new: true, name: "", gameType: "choice", category: CATEGORIES[0], difficulty: "medium", tierAccess: [...TIERS], enabled: true, supportsAI: true, supportsUserVsUser: true, estimatedMinutes: 5, minPlayers: 2, maxPlayers: 2, shortDescription: "", instructions: "", configuration: { rounds: 6, timerSeconds: 45, contentKey: "" } })} data-testid="game-new" className="gradient-brand text-white border-0"><Plus className="h-4 w-4 mr-1.5" />New Game</Button>}
        </div>

        {/* Grid */}
        {loading ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center py-24 text-muted-foreground"><Gamepad2 className="h-10 w-10 mb-3 opacity-40" /><p className="text-sm">No games match. Try seeding the catalog.</p></div>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {filtered.map((g) => (
              <div key={g.gameId} data-testid={`game-card-${g.gameId}`} className={cn("rounded-xl border bg-card p-4 flex flex-col gap-3 transition-colors", g.archived ? "opacity-60 border-border" : "border-border hover:border-pink-500/30")}>
                <div className="flex items-start gap-3">
                  <div className="grid place-items-center h-10 w-10 rounded-lg bg-gradient-to-br from-pink-500/20 to-violet-500/20 text-pink-500 shrink-0"><Gamepad2 className="h-5 w-5" /></div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <p className="font-semibold text-sm truncate">{g.name}</p>
                      {g.featured && <Star className="h-3.5 w-3.5 text-amber-500 fill-amber-500 shrink-0" />}
                    </div>
                    <p className="text-[11px] text-muted-foreground truncate">{g.category}</p>
                  </div>
                  {canEdit && (
                    <Switch data-testid={`game-toggle-${g.gameId}`} checked={!!g.enabled} disabled={g.archived}
                      onCheckedChange={(v) => patch(g.gameId, { enabled: v }, v ? "Enabled" : "Disabled")} />
                  )}
                </div>
                <p className="text-xs text-muted-foreground line-clamp-2 flex-1">{g.shortDescription}</p>
                <div className="flex flex-wrap gap-1.5 text-[10px]">
                  <span className={cn("px-2 py-0.5 rounded-full border", MECHANIC_CLS[g.gameType])}>{MECHANIC_LABEL[g.gameType] || g.gameType}</span>
                  <span className="px-2 py-0.5 rounded-full border border-border text-muted-foreground capitalize">{g.difficulty}</span>
                  <span className="px-2 py-0.5 rounded-full border border-border text-muted-foreground">{g.estimatedMinutes}m</span>
                  <span className="px-2 py-0.5 rounded-full border border-border text-muted-foreground">{(g.tierAccess || []).length === 3 ? "All tiers" : (g.tierAccess || []).join("/")}</span>
                </div>
                <div className="flex items-center gap-1 pt-1 border-t border-border">
                  <IconBtn testid={`game-preview-${g.gameId}`} title="Preview" onClick={() => setPreviewGame(g)}><Play className="h-4 w-4" /></IconBtn>
                  {canEdit && <IconBtn testid={`game-edit-${g.gameId}`} title="Edit" onClick={() => setEditing(g)}><Pencil className="h-4 w-4" /></IconBtn>}
                  <IconBtn testid={`game-content-${g.gameId}`} title="Content" onClick={() => setContentGame(g)}><ListChecks className="h-4 w-4" /></IconBtn>
                  <IconBtn testid={`game-stats-${g.gameId}`} title="Stats" onClick={() => setStatsGame(g)}><BarChart3 className="h-4 w-4" /></IconBtn>
                  {canEdit && <IconBtn testid={`game-feature-${g.gameId}`} title={g.featured ? "Unfeature" : "Feature"} onClick={() => patch(g.gameId, { featured: !g.featured }, g.featured ? "Unfeatured" : "Featured")}><Star className={cn("h-4 w-4", g.featured && "fill-amber-500 text-amber-500")} /></IconBtn>}
                  {canEdit && <IconBtn testid={`game-duplicate-${g.gameId}`} title="Duplicate" onClick={() => duplicate(g.gameId)}><Copy className="h-4 w-4" /></IconBtn>}
                  {canEdit && <IconBtn testid={`game-archive-${g.gameId}`} title={g.archived ? "Restore" : "Archive"} onClick={() => archive(g)}>{g.archived ? <RotateCcw className="h-4 w-4" /> : <Archive className="h-4 w-4" />}</IconBtn>}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {editing && <GameEditor game={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />}
      {contentGame && <ContentManager game={contentGame} canEdit={canEdit} onClose={() => setContentGame(null)} />}
      {previewGame && <GamePreview game={previewGame} onClose={() => setPreviewGame(null)} />}
      {statsGame && <GameStats game={statsGame} onClose={() => setStatsGame(null)} />}
    </div>
  );
}

const Stat = ({ label, value, accent }) => (
  <div className="rounded-xl border border-border bg-card px-4 py-3">
    <p className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</p>
    <p className={cn("text-2xl font-bold mt-0.5", accent === "emerald" && "text-emerald-500", accent === "amber" && "text-amber-500", accent === "pink" && "text-pink-500", accent === "violet" && "text-violet-500")}>{value}</p>
  </div>
);
const IconBtn = ({ children, title, onClick, testid }) => (
  <button data-testid={testid} title={title} onClick={onClick} className="grid place-items-center h-8 w-8 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">{children}</button>
);

/* ------------------------------ Editor ------------------------------ */
function GameEditor({ game, onClose, onSaved }) {
  const [f, setF] = useState({ ...game });
  const [saving, setSaving] = useState(false);
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));
  const setCfg = (k, v) => setF((p) => ({ ...p, configuration: { ...p.configuration, [k]: v } }));
  const toggleTier = (t) => setF((p) => ({ ...p, tierAccess: (p.tierAccess || []).includes(t) ? p.tierAccess.filter((x) => x !== t) : [...(p.tierAccess || []), t] }));
  const save = async () => {
    if (!f.name?.trim()) { toast.error("Name is required"); return; }
    setSaving(true);
    try {
      if (f._new) await api.post("/games", f);
      else await api.put(`/games/${f.gameId}`, f);
      toast.success("Game saved");
      onSaved();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
    setSaving(false);
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl max-h-[92vh] overflow-y-auto" data-testid="game-editor">
        <DialogHeader><DialogTitle>{f._new ? "New Game" : `Edit — ${f.name}`}</DialogTitle></DialogHeader>
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="col-span-2"><Label>Title</Label><Input data-testid="edit-name" value={f.name || ""} onChange={(e) => set("name", e.target.value)} /></div>
            <div className="col-span-2"><Label>Short description</Label><Input value={f.shortDescription || ""} onChange={(e) => set("shortDescription", e.target.value)} /></div>
            <div className="col-span-2"><Label>Full description</Label><Textarea rows={2} value={f.fullDescription || ""} onChange={(e) => set("fullDescription", e.target.value)} /></div>
            <div className="col-span-2"><Label>Instructions</Label><Textarea rows={2} value={f.instructions || ""} onChange={(e) => set("instructions", e.target.value)} /></div>
            <div><Label>Mechanic (gameType)</Label>
              <Select value={f.gameType} onValueChange={(v) => set("gameType", v)}>
                <SelectTrigger data-testid="edit-mechanic"><SelectValue /></SelectTrigger>
                <SelectContent>{Object.keys(MECHANIC_LABEL).map((m) => <SelectItem key={m} value={m}>{MECHANIC_LABEL[m]}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div><Label>Category</Label>
              <Select value={f.category} onValueChange={(v) => set("category", v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div><Label>Difficulty</Label>
              <Select value={f.difficulty} onValueChange={(v) => set("difficulty", v)}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>{DIFFICULTIES.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div><Label>Est. minutes</Label><Input type="number" value={f.estimatedMinutes || 0} onChange={(e) => set("estimatedMinutes", Number(e.target.value))} /></div>
            <div><Label>Rounds</Label><Input type="number" value={f.configuration?.rounds || 6} onChange={(e) => setCfg("rounds", Number(e.target.value))} /></div>
            <div><Label>Timer (seconds)</Label><Input type="number" value={f.configuration?.timerSeconds || 45} onChange={(e) => setCfg("timerSeconds", Number(e.target.value))} /></div>
            <div><Label>Content key</Label><Input value={f.configuration?.contentKey || ""} onChange={(e) => setCfg("contentKey", e.target.value)} placeholder="e.g. would_you_rather" /></div>
            <div><Label>Min players</Label><Input type="number" value={f.minPlayers || 2} onChange={(e) => set("minPlayers", Number(e.target.value))} /></div>
            <div><Label>Max players</Label><Input type="number" value={f.maxPlayers || 2} onChange={(e) => set("maxPlayers", Number(e.target.value))} /></div>
            <div><Label>Age rating</Label><Input value={f.ageRating || "18+"} onChange={(e) => set("ageRating", e.target.value)} /></div>
          </div>
          <div>
            <Label>Tier access</Label>
            <div className="flex gap-2 mt-1.5">
              {TIERS.map((t) => (
                <button key={t} type="button" data-testid={`edit-tier-${t}`} onClick={() => toggleTier(t)}
                  className={cn("px-3 h-8 rounded-full text-xs font-medium border capitalize transition-colors", (f.tierAccess || []).includes(t) ? "border-pink-500/50 bg-pink-500/10 text-pink-500" : "border-border text-muted-foreground")}>{t}</button>
              ))}
            </div>
          </div>
          <div className="flex flex-wrap gap-5 pt-1">
            <label className="flex items-center gap-2 text-sm"><Switch checked={!!f.supportsAI} onCheckedChange={(v) => set("supportsAI", v)} data-testid="edit-ai" />AI player support</label>
            <label className="flex items-center gap-2 text-sm"><Switch checked={!!f.supportsUserVsUser} onCheckedChange={(v) => set("supportsUserVsUser", v)} />User vs user</label>
            <label className="flex items-center gap-2 text-sm"><Switch checked={!!f.enabled} onCheckedChange={(v) => set("enabled", v)} />Enabled</label>
            <label className="flex items-center gap-2 text-sm"><Switch checked={!!f.featured} onCheckedChange={(v) => set("featured", v)} />Featured</label>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={save} disabled={saving} data-testid="game-save" className="gradient-brand text-white border-0">{saving && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />}Save</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------ Content Manager ------------------------------ */
function ContentManager({ game, canEdit, onClose }) {
  const [items, setItems] = useState(null);
  const [edit, setEdit] = useState(null);
  const load = useCallback(async () => {
    try { const { data } = await api.get("/games-content", { params: { gameId: game.gameId } }); setItems(data.items || []); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); setItems([]); }
  }, [game.gameId]);
  useEffect(() => { load(); }, [load]);

  const toggle = async (c) => { try { await api.put(`/games-content/${c.id}`, { enabled: !c.enabled }); load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); } };
  const del = async (c) => { try { await api.delete(`/games-content/${c.id}`); toast.success("Removed"); load(); } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); } };
  const saveNew = async (prompt) => {
    try {
      await api.post("/games-content", { contentKey: game.configuration?.contentKey, gameId: game.gameId, mechanic: game.gameType, language: "en", enabled: true, data: { prompt } });
      toast.success("Content added"); setEdit(null); load();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
  };

  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-2xl max-h-[92vh] overflow-y-auto" data-testid="content-manager">
        <DialogHeader><DialogTitle>Content — {game.name}</DialogTitle></DialogHeader>
        {canEdit && (
          <div className="flex gap-2">
            <Input placeholder="New prompt / question text…" value={edit || ""} onChange={(e) => setEdit(e.target.value)} data-testid="content-new-input" />
            <Button disabled={!edit?.trim()} onClick={() => saveNew(edit.trim())} data-testid="content-add"><Plus className="h-4 w-4" /></Button>
          </div>
        )}
        <div className="space-y-2">
          {items === null ? <div className="flex justify-center py-10"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
            : items.length === 0 ? <p className="text-sm text-muted-foreground py-10 text-center">No content yet. Seed the catalog or add items above.</p>
            : items.map((c) => (
              <div key={c.id} className="flex items-center gap-3 rounded-lg border border-border p-2.5 text-sm">
                <span className={cn("h-2 w-2 rounded-full shrink-0", c.enabled ? "bg-emerald-500" : "bg-muted-foreground/40")} />
                <span className="flex-1 min-w-0 truncate">{c.data?.prompt || JSON.stringify(c.data).slice(0, 80)}</span>
                {c.data?.correct && <span className="text-[10px] text-emerald-500 border border-emerald-500/30 rounded px-1.5">has answer</span>}
                {canEdit && <Switch checked={!!c.enabled} onCheckedChange={() => toggle(c)} />}
                {canEdit && <button onClick={() => del(c)} className="text-muted-foreground hover:text-rose-500"><Trash2 className="h-4 w-4" /></button>}
              </div>
            ))}
        </div>
        <p className="text-[11px] text-muted-foreground">{items?.length || 0} items · content key <code className="font-mono">{game.configuration?.contentKey}</code></p>
      </DialogContent>
    </Dialog>
  );
}

/* ------------------------------ Playable Sandbox Preview ------------------------------ */
function GamePreview({ game, onClose }) {
  const [state, setState] = useState(null);
  const [sid, setSid] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [opponent, setOpponent] = useState("human");
  const [aiChars, setAiChars] = useState([]);
  const supportsAI = game.supportsAI !== false;

  useEffect(() => {
    if (!supportsAI) return;
    api.get("/ai/characters").then(({ data }) => setAiChars((data.items || []).filter((c) => c.enabled !== false)))
      .catch(() => {});
  }, [supportsAI]);

  const aiName = useMemo(() => {
    const m = {};
    aiChars.forEach((c) => { m[c.characterId] = c.displayName; });
    return m;
  }, [aiChars]);

  const label = useCallback((pid) => {
    if (pid === "preview_p1") return "You";
    if (pid === "preview_p2") return "Player 2";
    return aiName[pid] ? `${aiName[pid]} (AI)` : "AI";
  }, [aiName]);

  const start = useCallback(async () => {
    setLoading(true); setErr("");
    try {
      const body = opponent !== "human" ? { aiCharacterId: opponent } : {};
      const { data } = await api.post(`/games/${game.gameId}/preview/start`, body);
      setSid(data.sessionId); setState(data);
    }
    catch (e) { setErr(formatApiError(e.response?.data?.detail || e)); }
    setLoading(false);
  }, [game.gameId, opponent]);
  useEffect(() => { start(); }, [start]);

  const act = async (pid, action) => {
    try { const { data } = await api.post(`/games/preview/${sid}/act`, { playerId: pid, action }); setState(data); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
  };
  const advance = async () => {
    try { const { data } = await api.post(`/games/preview/${sid}/advance`); setState(data); }
    catch (e) { toast.error(formatApiError(e.response?.data?.detail || e)); }
  };

  const pub = state;
  const players = opponent !== "human" ? ["preview_p1"] : ["preview_p1", "preview_p2"];
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md max-h-[92vh] overflow-y-auto" data-testid="game-preview">
        <DialogHeader><DialogTitle className="flex items-center gap-2"><Play className="h-4 w-4 text-pink-500" />Preview — {game.name}</DialogTitle></DialogHeader>
        <p className="text-[11px] text-amber-500 -mt-2">Sandboxed simulation · no real sessions, scores or analytics are affected.</p>
        {supportsAI && (
          <div className="flex items-center gap-2" data-testid="preview-opponent-row">
            <Label className="text-xs shrink-0">Opponent</Label>
            <Select value={opponent} onValueChange={setOpponent}>
              <SelectTrigger className="h-8 text-xs" data-testid="preview-opponent-select"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="human" data-testid="preview-opponent-human">Player 2 (human)</SelectItem>
                {aiChars.map((c) => (
                  <SelectItem key={c.characterId} value={c.characterId} data-testid={`preview-opponent-${c.characterId}`}>
                    🤖 {c.displayName} · {c.city}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        )}
        {loading ? <div className="flex justify-center py-16"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          : err ? <div className="py-10 text-center text-sm text-rose-500">{err}</div>
          : pub && (
            <div className="mx-auto w-full max-w-[340px] rounded-2xl border-2 border-border bg-background p-4 space-y-3">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Round {pub.round}/{pub.totalRounds}</span>
                <span className="capitalize px-2 py-0.5 rounded-full border border-border">{pub.phase}</span>
              </div>
              <div className="h-1.5 rounded-full bg-muted overflow-hidden"><div className="h-full gradient-brand" style={{ width: `${(pub.round / pub.totalRounds) * 100}%` }} /></div>

              {pub.status === "completed" ? (
                <div className="text-center py-6 space-y-2">
                  <Sparkles className="h-8 w-8 mx-auto text-pink-500" />
                  <p className="font-semibold">Game complete!</p>
                  <p className="text-sm text-muted-foreground">{pub.result?.type === "scored" ? (pub.result.draw ? "It's a draw" : `Winner: ${(pub.result.winners || []).map(label).join(", ")}`) : "Nicely done together."}</p>
                  <ScoreRow scores={pub.scores} label={label} />
                  <Button onClick={start} data-testid="preview-restart" variant="outline" className="mt-2"><RotateCcw className="h-4 w-4 mr-1.5" />Play again</Button>
                </div>
              ) : (
                <>
                  {pub.prompt && <div className="rounded-xl bg-card border border-border p-3 text-center font-medium">{pub.prompt.prompt}</div>}
                  {pub.setter && <p className="text-[11px] text-center text-muted-foreground">Setter: {label(pub.setter)} · {pub.subphase}</p>}
                  {pub.turn && <p className="text-[11px] text-center text-muted-foreground">Turn: {label(pub.turn)}</p>}

                  {pub.phase === "reveal" ? (
                    <div className="space-y-2">
                      <RevealView pub={pub} />
                      <Button onClick={advance} data-testid="preview-advance" className="w-full gradient-brand text-white border-0">Next round<ChevronRight className="h-4 w-4 ml-1" /></Button>
                    </div>
                  ) : (
                    players.map((pid) => {
                      const acts = pub.actionsByPlayer?.[pid] || [];
                      if (acts.length === 0) return <p key={pid} className="text-[11px] text-center text-muted-foreground/70">{label(pid)} — waiting…</p>;
                      return <PlayerControls key={pid} pid={pid} action={acts[0]} prompt={pub.prompt} onAct={act} />;
                    })
                  )}
                  {opponent !== "human" && <p className="text-[10px] text-center text-pink-500/80" data-testid="preview-ai-note">{label(opponent)} is thinking &amp; playing automatically</p>}
                  <ScoreRow scores={pub.scores} label={label} />
                </>
              )}
            </div>
          )}
      </DialogContent>
    </Dialog>
  );
}

function PlayerControls({ pid, action, prompt, onAct }) {
  const [text, setText] = useState("");
  const [stmts, setStmts] = useState(["", "", ""]);
  const [lie, setLie] = useState(null);
  const name = pid === "preview_p1" ? "Player 1" : "Player 2";
  const t = action.type;
  return (
    <div className="rounded-lg border border-border p-2.5 space-y-2" data-testid={`preview-controls-${pid}`}>
      <p className="text-[11px] font-semibold text-muted-foreground">{name}</p>
      {(t === "answer" || t === "guess" || t === "set_secret") && action.options && Array.isArray(action.options) && (
        <div className="grid gap-1.5">
          {action.options.map((o) => {
            const label = prompt?.options?.find((x) => x.key === o)?.label ?? (typeof o === "number" ? `Statement ${o + 1}` : o);
            return <button key={String(o)} data-testid={`preview-opt-${pid}-${o}`} onClick={() => onAct(pid, { type: t, value: o, actionId: `${pid}-${Date.now()}-${o}` })} className="w-full text-left px-3 py-2 rounded-lg border border-border hover:border-pink-500/50 hover:bg-pink-500/5 text-sm transition-colors">{label}</button>;
          })}
        </div>
      )}
      {t === "set_secret" && action.statements && (
        <div className="space-y-1.5">
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex items-center gap-2">
              <button data-testid={`preview-lie-${pid}-${i}`} onClick={() => setLie(i)} className={cn("h-4 w-4 rounded-full border shrink-0", lie === i ? "bg-rose-500 border-rose-500" : "border-muted-foreground")} title="Mark as lie" />
              <Input className="h-8" placeholder={`Statement ${i + 1}${lie === i ? " (lie)" : ""}`} value={stmts[i]} onChange={(e) => setStmts((s) => s.map((v, j) => j === i ? e.target.value : v))} />
            </div>
          ))}
          <Button size="sm" className="w-full" data-testid={`preview-set-secret-${pid}`} disabled={stmts.some((s) => !s.trim()) || lie === null} onClick={() => onAct(pid, { type: "set_secret", statements: stmts, lieIndex: lie, actionId: `${pid}-${Date.now()}` })}>Set statements</Button>
        </div>
      )}
      {(t === "respond" || t === "contribute") && !action.options && (
        <div className="flex gap-2">
          <Input className="h-8" data-testid={`preview-text-${pid}`} value={text} onChange={(e) => setText(e.target.value)} placeholder="Type response…" />
          <Button size="sm" data-testid={`preview-send-${pid}`} disabled={!text.trim()} onClick={() => { onAct(pid, { type: t, value: text, actionId: `${pid}-${Date.now()}` }); setText(""); }}>Send</Button>
        </div>
      )}
      {t === "contribute" && action.options && (
        <div className="grid gap-1.5">
          {action.options.map((o) => {
            const label = prompt?.options?.find((x) => x.key === o)?.label ?? o;
            return <button key={o} data-testid={`preview-opt-${pid}-${o}`} onClick={() => onAct(pid, { type: "contribute", value: o, actionId: `${pid}-${Date.now()}-${o}` })} className="w-full text-left px-3 py-2 rounded-lg border border-border hover:border-pink-500/50 text-sm">{label}</button>;
          })}
        </div>
      )}
    </div>
  );
}

const ScoreRow = ({ scores, label }) => (
  <div className="flex items-center justify-center gap-4 text-xs pt-1 border-t border-border">
    {Object.entries(scores || {}).map(([p, s]) => (
      <span key={p} className="flex items-center gap-1"><Circle className="h-2 w-2 fill-pink-500 text-pink-500" />{label ? label(p) : p}: <b>{s}</b></span>
    ))}
  </div>
);
const RevealView = ({ pub }) => {
  const r = pub.revealed;
  if (!r) return null;
  return <div className="rounded-lg bg-muted/40 border border-border p-2.5 text-xs space-y-1">
    <p className="font-semibold text-muted-foreground">Revealed</p>
    <pre className="whitespace-pre-wrap break-words text-[11px]">{JSON.stringify(r, null, 1)}</pre>
  </div>;
};

/* ------------------------------ Stats ------------------------------ */
function GameStats({ game, onClose }) {
  const [s, setS] = useState(null);
  useEffect(() => { (async () => { try { const { data } = await api.get(`/games/${game.gameId}/stats`); setS(data); } catch { setS({ hasData: false }); } })(); }, [game.gameId]);
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md" data-testid="game-stats">
        <DialogHeader><DialogTitle>Usage — {game.name}</DialogTitle></DialogHeader>
        {!s ? <div className="flex justify-center py-10"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
          : !s.hasData ? <div className="py-10 text-center text-sm text-muted-foreground"><BarChart3 className="h-8 w-8 mx-auto mb-2 opacity-40" />No gameplay yet — real stats will appear once users start playing.</div>
          : (
            <div className="grid grid-cols-2 gap-3">
              <Stat label="Opened" value={s.sessionsOpened} />
              <Stat label="Started" value={s.sessionsStarted} />
              <Stat label="Completed" value={s.completed} accent="emerald" />
              <Stat label="Abandoned" value={s.abandoned} accent="amber" />
              <Stat label="Completion %" value={s.completionRate ?? "—"} accent="emerald" />
              <Stat label="Avg duration" value={s.avgSessionSeconds ? `${Math.round(s.avgSessionSeconds)}s` : "—"} />
            </div>
          )}
      </DialogContent>
    </Dialog>
  );
}
