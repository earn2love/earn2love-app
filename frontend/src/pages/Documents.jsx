import { useMemo, useState } from "react";
import { Topbar } from "@/components/Topbar";
import { DOCUMENTS, DOCUMENT_CATEGORIES } from "@/config/documents";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { FileText, Download, Eye, Search, FolderOpen } from "lucide-react";
import { cn } from "@/lib/utils";

export default function Documents() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");

  const categories = useMemo(
    () => ["All", ...DOCUMENT_CATEGORIES.filter((c) => DOCUMENTS.some((d) => d.category === c))],
    []
  );

  const docs = useMemo(() => {
    const q = query.trim().toLowerCase();
    return DOCUMENTS.filter((d) => {
      const matchCat = category === "All" || d.category === category;
      const matchQ = !q || `${d.title} ${d.description} ${d.filename}`.toLowerCase().includes(q);
      return matchCat && matchQ;
    });
  }, [query, category]);

  return (
    <div data-testid="documents-page">
      <Topbar title="Documents" subtitle="Downloadable forms, policies and files" />

      <div className="p-6 space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              data-testid="documents-search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search documents…"
              className="pl-9 h-10"
            />
          </div>
          <div className="flex flex-wrap gap-2">
            {categories.map((c) => (
              <button
                key={c}
                data-testid={`documents-filter-${c.toLowerCase()}`}
                onClick={() => setCategory(c)}
                className={cn(
                  "px-3 h-8 rounded-full text-xs font-medium border transition-colors",
                  category === c
                    ? "bg-pink-500/15 text-pink-500 border-pink-500/30"
                    : "border-border text-muted-foreground hover:text-foreground"
                )}
              >
                {c}
              </button>
            ))}
          </div>
        </div>

        {docs.length === 0 ? (
          <div
            data-testid="documents-empty"
            className="flex flex-col items-center justify-center py-24 text-center text-muted-foreground"
          >
            <FolderOpen className="h-10 w-10 mb-3 opacity-40" />
            <p className="text-sm">No documents found.</p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {docs.map((d) => (
              <div
                key={d.id}
                data-testid={`document-card-${d.id}`}
                className="group rounded-xl border border-border bg-card p-5 flex flex-col gap-4 hover:border-pink-500/30 transition-colors"
              >
                <div className="flex items-start gap-3">
                  <div className="grid place-items-center h-11 w-11 rounded-lg bg-pink-500/10 text-pink-500 shrink-0">
                    <FileText className="h-5 w-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="font-semibold text-sm leading-snug truncate" title={d.title}>{d.title}</p>
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{d.description}</p>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                  <span className="px-2 py-0.5 rounded bg-muted font-medium">{d.type}</span>
                  <span>{d.size}</span>
                  {d.updated && <span>· Updated {d.updated}</span>}
                </div>

                <div className="flex items-center gap-2 mt-auto">
                  <Button asChild size="sm" className="flex-1" data-testid={`document-download-${d.id}`}>
                    <a href={d.file} download={d.filename}>
                      <Download className="h-4 w-4 mr-1.5" /> Download
                    </a>
                  </Button>
                  <Button asChild size="sm" variant="outline" data-testid={`document-view-${d.id}`}>
                    <a href={d.file} target="_blank" rel="noopener noreferrer" aria-label="Preview">
                      <Eye className="h-4 w-4" />
                    </a>
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
