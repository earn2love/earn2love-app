import { useEffect, useMemo, useState, useCallback } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from "@/components/ui/dialog";
import {
  FileText, Download, Eye, Search, FolderOpen, Plus, Pencil, Trash2, Loader2, X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const STATUS = ["Published", "Draft", "Under Review", "Archived"];
const CATS = [
  "Legal & Compliance", "Operations & SOP", "Deployment & Technical",
  "Finance & Risk", "Internal Administration", "User Documentation", "Other",
];

// Branded, print-ready standalone HTML for viewing / downloading a document.
function buildDocHtml(d) {
  const today = new Date().toLocaleDateString();
  return `<!doctype html><html><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>${d.title}</title>
<style>
  :root{--pink:#e6007e;--purple:#7b2ff7;--gold:#d4a017;--ink:#1a1526;--muted:#6b6580;}
  *{box-sizing:border-box;}
  body{font-family:'Segoe UI',Helvetica,Arial,sans-serif;color:var(--ink);margin:0;background:#f4f2f8;}
  .page{max-width:820px;margin:24px auto;background:#fff;box-shadow:0 4px 24px rgba(80,40,120,.12);}
  header.doc{background:linear-gradient(120deg,var(--purple),var(--pink));color:#fff;padding:26px 40px;display:flex;align-items:center;gap:18px;}
  header.doc img{height:52px;width:52px;border-radius:12px;background:#fff;object-fit:cover;padding:2px;}
  header.doc .meta{flex:1;}
  header.doc h1{margin:0;font-size:22px;font-weight:700;}
  header.doc .sub{opacity:.9;font-size:12px;margin-top:4px;letter-spacing:.3px;}
  .ribbon{background:var(--gold);color:#3a2c00;font-size:11px;font-weight:700;padding:6px 40px;text-transform:uppercase;letter-spacing:1px;display:flex;justify-content:space-between;}
  .body{padding:34px 40px 10px;line-height:1.65;font-size:14px;}
  .body .lead{font-size:15px;color:var(--muted);border-left:3px solid var(--pink);padding-left:14px;margin-bottom:22px;}
  .body h2{color:var(--purple);font-size:16px;margin:26px 0 10px;border-bottom:1px solid #eee;padding-bottom:6px;}
  .body ul{margin:8px 0 8px 18px;} .body li{margin:5px 0;}
  .body table{width:100%;border-collapse:collapse;margin:12px 0;font-size:13px;}
  .body th{background:#f3eefc;color:var(--purple);text-align:left;padding:9px 11px;border:1px solid #e6dff5;}
  .body td{padding:9px 11px;border:1px solid #eee;vertical-align:top;}
  .body tr:nth-child(even) td{background:#faf8fe;}
  .figure{text-align:center;margin:18px 0;} .figure img{max-width:180px;border-radius:12px;}
  .figure figcaption{font-size:12px;color:var(--muted);margin-top:6px;}
  footer.doc{border-top:2px solid var(--pink);margin-top:26px;padding:16px 40px 30px;font-size:11px;color:var(--muted);display:flex;justify-content:space-between;flex-wrap:wrap;gap:8px;}
  @media print{body{background:#fff;} .page{box-shadow:none;margin:0;max-width:100%;} }
</style></head>
<body><div class="page">
  <header class="doc">
    <img src="/earn2love-logo.png" alt="Earn2Love"/>
    <div class="meta"><h1>${d.title}</h1>
      <div class="sub">Earn2Love · ${d.category} · ${d.code || ""}</div></div>
  </header>
  <div class="ribbon"><span>${d.status || "Document"}</span><span>Version ${d.version || "1.0"}</span></div>
  <div class="body">${d.contentHtml || ""}</div>
  <footer class="doc">
    <span>© ${new Date().getFullYear()} Earn2Love — Confidential. For internal &amp; authorised use only.</span>
    <span>${d.code || ""} · Generated ${today}</span>
  </footer>
</div></body></html>`;
}

function downloadDoc(d) {
  const w = window.open("", "_blank");
  if (!w) { toast.error("Allow pop-ups to download"); return; }
  w.document.write(buildDocHtml(d));
  w.document.close();
  w.focus();
  setTimeout(() => w.print(), 500);
}

const emptyDoc = { title: "", category: "Legal & Compliance", code: "", description: "", status: "Draft", version: "1.0", contentHtml: "<h2>Section</h2>\n<p>Write content…</p>" };

export default function Documents() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const [viewDoc, setViewDoc] = useState(null);
  const [editDoc, setEditDoc] = useState(null); // {id?, ...fields}
  const [saving, setSaving] = useState(false);
  const [confirmDel, setConfirmDel] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/documents");
      setItems(data.items || []);
    } catch (e) { toast.error(formatApiError(e)); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const categories = useMemo(() => ["All", ...CATS.filter((c) => items.some((d) => d.category === c))], [items]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((d) => {
      const mc = category === "All" || d.category === category;
      const mq = !q || `${d.title} ${d.code} ${d.description}`.toLowerCase().includes(q);
      return mc && mq;
    });
  }, [items, query, category]);

  const grouped = useMemo(() => {
    const g = {};
    filtered.forEach((d) => { (g[d.category] = g[d.category] || []).push(d); });
    return g;
  }, [filtered]);

  const openView = async (d) => {
    try { const { data } = await api.get(`/documents/${d.id}`); setViewDoc(data); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const save = async () => {
    setSaving(true);
    try {
      if (editDoc.id) await api.put(`/documents/${editDoc.id}`, editDoc);
      else await api.post("/documents", editDoc);
      toast.success("Document saved");
      setEditDoc(null);
      await load();
    } catch (e) { toast.error(formatApiError(e)); }
    setSaving(false);
  };

  const doDelete = async () => {
    try {
      await api.delete(`/documents/${confirmDel.id}`);
      toast.success("Document deleted");
      setConfirmDel(null);
      await load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="documents-page">
      <Topbar title="Documents" subtitle={`${items.length} managed documents · forms, policies, SOPs & guides`} />

      <div className="p-6 space-y-6">
        <div className="flex flex-col lg:flex-row lg:items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input data-testid="documents-search" value={query} onChange={(e) => setQuery(e.target.value)}
              placeholder="Search documents…" className="pl-9 h-10" />
          </div>
          <div className="flex flex-wrap gap-2 flex-1">
            {categories.map((c) => (
              <button key={c} data-testid={`documents-filter-${c.replace(/[^a-z]/gi, "-").toLowerCase()}`}
                onClick={() => setCategory(c)}
                className={cn("px-3 h-8 rounded-full text-xs font-medium border transition-colors",
                  category === c ? "bg-pink-500/15 text-pink-500 border-pink-500/30"
                    : "border-border text-muted-foreground hover:text-foreground")}>{c}</button>
            ))}
          </div>
          <Button data-testid="documents-add-btn" onClick={() => setEditDoc({ ...emptyDoc })} className="shrink-0">
            <Plus className="h-4 w-4 mr-1.5" /> New Document
          </Button>
        </div>

        {loading ? (
          <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
        ) : filtered.length === 0 ? (
          <div data-testid="documents-empty" className="flex flex-col items-center justify-center py-24 text-center text-muted-foreground">
            <FolderOpen className="h-10 w-10 mb-3 opacity-40" /><p className="text-sm">No documents found.</p>
          </div>
        ) : (
          Object.keys(grouped).map((cat) => (
            <div key={cat} className="space-y-3">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{cat} <span className="text-muted-foreground/60">({grouped[cat].length})</span></h3>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {grouped[cat].map((d) => (
                  <div key={d.id} data-testid={`document-card-${d.id}`}
                    className="group rounded-xl border border-border bg-card p-4 flex flex-col gap-3 hover:border-pink-500/30 transition-colors">
                    <div className="flex items-start gap-3">
                      <div className="grid place-items-center h-10 w-10 rounded-lg bg-pink-500/10 text-pink-500 shrink-0"><FileText className="h-5 w-5" /></div>
                      <div className="min-w-0 flex-1">
                        <p className="font-semibold text-sm leading-snug truncate" title={d.title}>{d.title}</p>
                        <p className="text-[11px] text-muted-foreground mt-0.5 font-mono">{d.code}</p>
                      </div>
                      <span className={cn("text-[10px] px-2 py-0.5 rounded-full border",
                        d.status === "Published" ? "text-emerald-500 border-emerald-500/30 bg-emerald-500/10"
                          : "text-amber-500 border-amber-500/30 bg-amber-500/10")}>{d.status}</span>
                    </div>
                    <div className="flex items-center gap-1.5 mt-auto">
                      <Button size="sm" variant="outline" className="flex-1 h-8" onClick={() => openView(d)} data-testid={`document-view-${d.id}`}><Eye className="h-3.5 w-3.5 mr-1" /> View</Button>
                      <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={async () => { try { const { data } = await api.get(`/documents/${d.id}`); setEditDoc(data); } catch (e) { toast.error(formatApiError(e)); } }} data-testid={`document-edit-${d.id}`}><Pencil className="h-3.5 w-3.5" /></Button>
                      <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => downloadDoc(d)} data-testid={`document-download-${d.id}`}><Download className="h-3.5 w-3.5" /></Button>
                      <Button size="sm" variant="ghost" className="h-8 w-8 p-0 text-red-500 hover:text-red-600" onClick={() => setConfirmDel(d)} data-testid={`document-delete-${d.id}`}><Trash2 className="h-3.5 w-3.5" /></Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Viewer */}
      <Dialog open={!!viewDoc} onOpenChange={(o) => !o && setViewDoc(null)}>
        <DialogContent className="max-w-4xl h-[90vh] p-0 overflow-hidden" data-testid="document-viewer">
          <div className="flex items-center justify-between px-4 py-2.5 border-b">
            <p className="text-sm font-medium truncate">{viewDoc?.title}</p>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" onClick={() => downloadDoc(viewDoc)}><Download className="h-4 w-4 mr-1.5" /> Download PDF</Button>
              <Button size="sm" variant="ghost" className="h-8 w-8 p-0" onClick={() => setViewDoc(null)}><X className="h-4 w-4" /></Button>
            </div>
          </div>
          {viewDoc && <iframe title="doc" srcDoc={buildDocHtml(viewDoc)} className="w-full h-full border-0 bg-white" />}
        </DialogContent>
      </Dialog>

      {/* Editor */}
      <Dialog open={!!editDoc} onOpenChange={(o) => !o && setEditDoc(null)}>
        <DialogContent className="max-w-5xl h-[92vh] flex flex-col" data-testid="document-editor">
          <DialogHeader>
            <DialogTitle>{editDoc?.id ? "Edit Document" : "New Document"}</DialogTitle>
            <DialogDescription>Content supports HTML — headings, lists, tables and images.</DialogDescription>
          </DialogHeader>
          {editDoc && (
            <div className="grid lg:grid-cols-2 gap-4 flex-1 min-h-0">
              <div className="space-y-3 overflow-auto pr-1">
                <div><Label>Title</Label><Input data-testid="editor-title" value={editDoc.title} onChange={(e) => setEditDoc({ ...editDoc, title: e.target.value })} /></div>
                <div className="grid grid-cols-2 gap-3">
                  <div><Label>Category</Label>
                    <Select value={editDoc.category} onValueChange={(v) => setEditDoc({ ...editDoc, category: v })}>
                      <SelectTrigger data-testid="editor-category"><SelectValue /></SelectTrigger>
                      <SelectContent>{CATS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                    </Select></div>
                  <div><Label>Status</Label>
                    <Select value={editDoc.status} onValueChange={(v) => setEditDoc({ ...editDoc, status: v })}>
                      <SelectTrigger data-testid="editor-status"><SelectValue /></SelectTrigger>
                      <SelectContent>{STATUS.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                    </Select></div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div><Label>Code</Label><Input value={editDoc.code || ""} onChange={(e) => setEditDoc({ ...editDoc, code: e.target.value })} placeholder="E2L-…" /></div>
                  <div><Label>Version</Label><Input value={editDoc.version || ""} onChange={(e) => setEditDoc({ ...editDoc, version: e.target.value })} /></div>
                </div>
                <div><Label>Description</Label><Input value={editDoc.description || ""} onChange={(e) => setEditDoc({ ...editDoc, description: e.target.value })} /></div>
                <div className="flex-1"><Label>Content (HTML)</Label>
                  <Textarea data-testid="editor-content" value={editDoc.contentHtml} onChange={(e) => setEditDoc({ ...editDoc, contentHtml: e.target.value })}
                    className="font-mono text-xs h-[38vh]" /></div>
              </div>
              <div className="min-h-0 flex flex-col">
                <Label className="mb-1">Live Preview</Label>
                <iframe title="preview" srcDoc={buildDocHtml(editDoc)} className="w-full flex-1 border rounded-lg bg-white" />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditDoc(null)}>Cancel</Button>
            <Button onClick={save} disabled={saving} data-testid="editor-save">
              {saving && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />} Save Document
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirm */}
      <Dialog open={!!confirmDel} onOpenChange={(o) => !o && setConfirmDel(null)}>
        <DialogContent className="max-w-md" data-testid="document-delete-confirm">
          <DialogHeader><DialogTitle>Delete document?</DialogTitle>
            <DialogDescription>“{confirmDel?.title}” will be permanently removed. This cannot be undone.</DialogDescription></DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmDel(null)}>Cancel</Button>
            <Button variant="destructive" onClick={doDelete} data-testid="confirm-delete-btn">Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
