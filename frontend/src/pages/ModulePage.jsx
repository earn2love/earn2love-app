import { useEffect, useMemo, useState, useCallback } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { MODULES } from "@/config/modules";
import { Topbar } from "@/components/Topbar";
import { DataTable } from "@/components/DataTable";
import { ActionDialog } from "@/components/ActionDialog";
import { useAuth } from "@/context/AuthContext";
import { AlertTriangle } from "lucide-react";
import { toast } from "sonner";

export default function ModulePage() {
  const { key } = useParams();
  const config = MODULES[key];
  const { can } = useAuth();
  const [searchParams] = useSearchParams();

  const [rows, setRows] = useState([]);
  const [meta, setMeta] = useState({ total: 0, page: 1, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [filters, setFilters] = useState({});
  const [dialog, setDialog] = useState(null); // { row, action }

  const canWrite = config ? can(config.endpoint) : false;

  useEffect(() => {
    // reset state on module change
    setPage(1); setSearch(""); setDebounced(""); setFilters({});
  }, [key]);

  useEffect(() => {
    const t = setTimeout(() => setDebounced(search), 350);
    return () => clearTimeout(t);
  }, [search]);

  const fetchData = useCallback(async () => {
    if (!config) return;
    setLoading(true);
    try {
      const params = { page, page_size: 15, search: debounced, ...filters };
      const { data } = await api.get(`/resources/${config.endpoint}`, { params });
      setRows(data.items);
      setMeta({ total: data.total, page: data.page, pages: data.pages });
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  }, [config, page, debounced, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onFilter = (fkey, val) => { setFilters((f) => ({ ...f, [fkey]: val })); setPage(1); };

  const runAction = async (reason) => {
    const { row, action } = dialog;
    try {
      await api.post(`/resources/${config.endpoint}/${row.id}/action`, { action: action.key, reason });
      toast.success(`${action.label} · ${row.id}`);
      setDialog(null);
      fetchData();
    } catch (e) {
      toast.error(formatApiError(e.response?.data?.detail));
      setDialog(null);
    }
  };

  const actions = useMemo(() => (canWrite ? config?.actions || [] : []), [canWrite, config]);

  if (!config) {
    return (
      <>
        <Topbar title="Not found" />
        <main className="flex-1 grid place-items-center text-muted-foreground">Unknown module: {key}</main>
      </>
    );
  }

  return (
    <>
      <Topbar title={config.title} subtitle={config.subtitle} />
      <main className="flex-1 overflow-y-auto p-5 md:p-8 space-y-4">
        {config.notice && (
          <div className="flex items-start gap-2.5 rounded-lg border border-amber-500/25 bg-amber-500/10 px-4 py-3 text-sm text-amber-700 dark:text-amber-400">
            <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
            <p>{config.notice}</p>
          </div>
        )}
        {!canWrite && config.actions?.length > 0 && (
          <p className="text-xs text-muted-foreground">
            Your role has read-only access to this module — actions are disabled.
          </p>
        )}
        <DataTable
          columns={config.columns}
          rows={rows}
          loading={loading}
          total={meta.total}
          page={meta.page}
          pages={meta.pages}
          onPage={setPage}
          search={search}
          onSearch={setSearch}
          filters={config.filters}
          filterValues={filters}
          onFilter={onFilter}
          actions={actions}
          onAction={(row, action) => setDialog({ row, action })}
          exportName={config.endpoint}
        />
      </main>

      {dialog && (
        <ActionDialog
          open={!!dialog}
          onOpenChange={(o) => !o && setDialog(null)}
          title={`${dialog.action.label}?`}
          description={`Apply "${dialog.action.label}" to ${dialog.row.id}. This will be recorded in the audit log.`}
          danger={dialog.action.danger}
          requireReason={dialog.action.danger}
          confirmLabel={dialog.action.label}
          onConfirm={runAction}
        />
      )}
    </>
  );
}
