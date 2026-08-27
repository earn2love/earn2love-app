import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import {
  CommandDialog, CommandInput, CommandList, CommandEmpty, CommandGroup, CommandItem,
} from "@/components/ui/command";
import { NAV_GROUPS } from "@/config/modules";
import { User, ShieldAlert, LifeBuoy, CornerDownLeft } from "lucide-react";

const TYPE_ICON = { User, Report: ShieldAlert, Ticket: LifeBuoy };

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const [results, setResults] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    const down = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    const openEvt = () => setOpen(true);
    document.addEventListener("keydown", down);
    window.addEventListener("open-command", openEvt);
    return () => { document.removeEventListener("keydown", down); window.removeEventListener("open-command", openEvt); };
  }, []);

  useEffect(() => {
    if (!q || q.length < 2) { setResults([]); return; }
    const t = setTimeout(async () => {
      try { const { data } = await api.get("/search", { params: { q } }); setResults(data.results); }
      catch { setResults([]); }
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  const go = useCallback((to) => { setOpen(false); setQ(""); navigate(to); }, [navigate]);

  const navItems = NAV_GROUPS.flatMap((g) => g.items);

  return (
    <CommandDialog open={open} onOpenChange={setOpen}>
      <CommandInput placeholder="Search users, reports, tickets — or jump to a page…" value={q} onValueChange={setQ} data-testid="command-input" />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>
        {results.length > 0 && (
          <CommandGroup heading="Search results">
            {results.map((r) => {
              const Icon = TYPE_ICON[r.type] || User;
              return (
                <CommandItem key={`${r.type}-${r.id}`} value={`${r.type} ${r.id} ${r.title}`} onSelect={() => go(r.route)} data-testid={`cmd-result-${r.id}`}>
                  <Icon className="h-4 w-4 mr-2 text-muted-foreground" />
                  <div className="flex flex-col">
                    <span className="text-sm">{r.title}</span>
                    <span className="text-[11px] text-muted-foreground">{r.type} · {r.subtitle}</span>
                  </div>
                  <CornerDownLeft className="h-3 w-3 ml-auto text-muted-foreground opacity-0 group-aria-selected:opacity-100" />
                </CommandItem>
              );
            })}
          </CommandGroup>
        )}
        <CommandGroup heading="Navigate">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <CommandItem key={item.to} value={`go ${item.label}`} onSelect={() => go(item.to)} data-testid={`cmd-nav-${item.key}`}>
                <Icon className="h-4 w-4 mr-2 text-muted-foreground" />
                {item.label}
              </CommandItem>
            );
          })}
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
}
