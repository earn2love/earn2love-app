import { Search, Download, MoreHorizontal, ChevronLeft, ChevronRight, Inbox } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import { fmtDate, fmtDateTime, fmtCurrency, exportCsv } from "@/lib/format";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

function renderCell(row, col) {
  if (col.render) return col.render(row);
  const v = row[col.key];
  if (col.badge) return <StatusBadge value={v} />;
  if (col.type === "date") return <span className="text-muted-foreground">{fmtDate(v)}</span>;
  if (col.type === "datetime") return <span className="text-muted-foreground">{fmtDateTime(v)}</span>;
  if (col.type === "currency") return <span className="font-mono tabular-nums">{fmtCurrency(v, row.currency)}</span>;
  if (col.type === "bool")
    return v ? <StatusBadge value="Yes" className="bg-rose-500/12 text-rose-500 border-rose-500/20" /> : <span className="text-muted-foreground text-xs">No</span>;
  if (v == null || v === "") return <span className="text-muted-foreground">—</span>;
  return <span className={cn(col.mono && "font-mono text-[12.5px] tabular-nums", "truncate")}>{String(v)}</span>;
}

export function DataTable({
  columns, rows, loading, total, page, pages, onPage,
  search, onSearch, filters = [], filterValues = {}, onFilter,
  actions = [], onAction, onRowClick, exportName = "export", rightSlot,
  selectable = false, selected = [], onSelectChange, bulkActions = [], onBulkAction,
}) {
  const hasActions = actions && actions.length > 0;
  const allSelected = selectable && rows.length > 0 && rows.every((r) => selected.includes(r.id));
  const toggleAll = () => {
    if (!onSelectChange) return;
    onSelectChange(allSelected ? [] : rows.map((r) => r.id));
  };
  const toggleOne = (id) => {
    if (!onSelectChange) return;
    onSelectChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  };

  return (
    <div className="rounded-lg border border-border bg-card">
      {/* Bulk action bar */}
      {selectable && selected.length > 0 && (
        <div className="flex items-center gap-3 px-4 py-2.5 border-b border-border bg-accent/40" data-testid="bulk-bar">
          <span className="text-sm font-medium">{selected.length} selected</span>
          <div className="flex items-center gap-1.5">
            {bulkActions.map((a) => (
              <Button key={a.key} data-testid={`bulk-${a.key}`} size="sm" variant={a.danger ? "destructive" : "outline"}
                className="h-8" onClick={() => onBulkAction(a)}>
                {a.label}
              </Button>
            ))}
          </div>
          <button className="ml-auto text-xs text-muted-foreground hover:text-foreground" onClick={() => onSelectChange([])}>Clear</button>
        </div>
      )}
      {/* Toolbar */}
      <div className="flex flex-col lg:flex-row lg:items-center gap-3 p-3.5 border-b border-border">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            data-testid="table-search"
            value={search}
            onChange={(e) => onSearch(e.target.value)}
            placeholder="Search…"
            className="pl-9 h-9 bg-background"
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {filters.map((f) => (
            <Select key={f.key} value={filterValues[f.key] || "All"} onValueChange={(val) => onFilter(f.key, val)}>
              <SelectTrigger data-testid={`filter-${f.key}`} className="h-9 w-auto min-w-[130px] bg-background text-xs">
                <SelectValue placeholder={f.label} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="All">All {f.label}</SelectItem>
                {f.options.map((o) => (
                  <SelectItem key={o} value={o}>{o}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          ))}
          {rightSlot}
          <Button
            data-testid="export-csv-btn"
            variant="outline"
            size="sm"
            className="h-9 gap-1.5"
            onClick={() => exportCsv(rows, columns, exportName)}
          >
            <Download className="h-4 w-4" /> Export
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              {selectable && (
                <th className="px-4 py-3 w-10">
                  <Checkbox checked={allSelected} onCheckedChange={toggleAll} data-testid="select-all" aria-label="Select all" />
                </th>
              )}
              {columns.map((c) => (
                <th key={c.key} className="text-left font-semibold text-[11px] uppercase tracking-wider text-muted-foreground px-4 py-3 whitespace-nowrap">
                  {c.label}
                </th>
              ))}
              {hasActions && <th className="px-4 py-3 w-12" />}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              Array.from({ length: 8 }).map((_, i) => (
                <tr key={i} className="border-b border-border/60">
                  {selectable && <td className="px-4 py-3" />}
                  {columns.map((c) => (
                    <td key={c.key} className="px-4 py-3"><Skeleton className="h-4 w-20" /></td>
                  ))}
                  {hasActions && <td className="px-4 py-3" />}
                </tr>
              ))
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length + (hasActions ? 1 : 0) + (selectable ? 1 : 0)} className="px-4 py-16 text-center">
                  <div className="flex flex-col items-center gap-2 text-muted-foreground">
                    <Inbox className="h-8 w-8 opacity-40" />
                    <p className="text-sm">No records found</p>
                  </div>
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr
                  key={row.id}
                  data-testid={`row-${row.id}`}
                  onClick={() => onRowClick?.(row)}
                  className={cn(
                    "border-b border-border/60 transition-colors",
                    (onRowClick) && "cursor-pointer hover:bg-accent/40",
                    selected.includes(row.id) && "bg-accent/30"
                  )}
                >
                  {selectable && (
                    <td className="px-4 py-2.5" onClick={(e) => e.stopPropagation()}>
                      <Checkbox checked={selected.includes(row.id)} onCheckedChange={() => toggleOne(row.id)} data-testid={`select-${row.id}`} />
                    </td>
                  )}
                  {columns.map((c) => (
                    <td key={c.key} className="px-4 py-2.5 max-w-[220px]">{renderCell(row, c)}</td>
                  ))}
                  {hasActions && (
                    <td className="px-4 py-2.5" onClick={(e) => e.stopPropagation()}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <button data-testid={`row-actions-${row.id}`} className="grid place-items-center h-7 w-7 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors">
                            <MoreHorizontal className="h-4 w-4" />
                          </button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-44">
                          {actions.map((a) => (
                            <DropdownMenuItem
                              key={a.key}
                              data-testid={`action-${a.key}-${row.id}`}
                              onClick={() => onAction(row, a)}
                              className={cn(a.danger && "text-rose-600 focus:text-rose-600")}
                            >
                              {a.label}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  )}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between px-4 py-3 border-t border-border">
        <p className="text-xs text-muted-foreground">
          {total != null ? <><span className="font-medium text-foreground">{total.toLocaleString()}</span> records</> : null}
        </p>
        <div className="flex items-center gap-2">
          <span className="text-xs text-muted-foreground">Page {page} of {pages}</span>
          <Button data-testid="page-prev" variant="outline" size="icon" className="h-8 w-8" disabled={page <= 1} onClick={() => onPage(page - 1)}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button data-testid="page-next" variant="outline" size="icon" className="h-8 w-8" disabled={page >= pages} onClick={() => onPage(page + 1)}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
