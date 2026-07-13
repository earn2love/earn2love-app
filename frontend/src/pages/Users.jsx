import { useEffect, useState, useCallback } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { DataTable } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { ActionDialog } from "@/components/ActionDialog";
import { useAuth } from "@/context/AuthContext";
import { fmtDate } from "@/lib/format";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { toast } from "sonner";

const USER_ACTIONS = [
  { key: "freeze", label: "Freeze account" },
  { key: "unfreeze", label: "Unfreeze account" },
  { key: "ban", label: "Ban account", danger: true },
  { key: "unban", label: "Unban account" },
  { key: "force-logout", label: "Force logout" },
  { key: "request-verification", label: "Request verification" },
  { key: "reset-liveness", label: "Reset liveness" },
  { key: "reset-reports", label: "Reset reports counter" },
  { key: "freeze-wallet", label: "Freeze wallet", danger: true },
  { key: "unfreeze-wallet", label: "Unfreeze wallet" },
];

export default function Users() {
  const navigate = useNavigate();
  const { can } = useAuth();
  const [searchParams] = useSearchParams();
  const canWrite = can("users");

  const [rows, setRows] = useState([]);
  const [meta, setMeta] = useState({ total: 0, page: 1, pages: 1 });
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [debounced, setDebounced] = useState("");
  const [filters, setFilters] = useState(() => {
    const online = searchParams.get("online");
    return online ? { online } : {};
  });
  const [dialog, setDialog] = useState(null);

  useEffect(() => { const t = setTimeout(() => setDebounced(search), 350); return () => clearTimeout(t); }, [search]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/resources/users", { params: { page, page_size: 15, search: debounced, ...filters } });
      setRows(data.items);
      setMeta({ total: data.total, page: data.page, pages: data.pages });
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setLoading(false); }
  }, [page, debounced, filters]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const onFilter = (k, v) => { setFilters((f) => ({ ...f, [k]: v })); setPage(1); };

  const runAction = async (reason) => {
    const { row, action } = dialog;
    try {
      await api.post(`/users/${row.id}/action`, { action: action.key, reason });
      toast.success(`${action.label} · ${row.name}`);
      setDialog(null); fetchData();
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); setDialog(null); }
  };

  const columns = [
    {
      key: "name", label: "User",
      render: (r) => (
        <div className="flex items-center gap-2.5">
          <Avatar className="h-8 w-8">
            <AvatarImage src={r.photo} alt={r.name} />
            <AvatarFallback className="text-[10px]">{r.name?.slice(0, 2).toUpperCase()}</AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <p className="font-medium truncate flex items-center gap-1.5">
              {r.online && <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 shrink-0" title="Online" />}
              {r.name}
            </p>
            <p className="text-[11px] text-muted-foreground truncate font-mono">{r.id}</p>
          </div>
        </div>
      ),
    },
    { key: "age", label: "Age" },
    { key: "gender", label: "Gender" },
    { key: "country", label: "Country" },
    { key: "tier", label: "Tier", badge: true },
    { key: "account_status", label: "Status", badge: true },
    { key: "verification_status", label: "Verified", badge: true },
    { key: "reports_count", label: "Reports", render: (r) => <span className={`font-mono text-xs ${r.reports_count >= 3 ? "text-rose-500 font-semibold" : ""}`}>{r.reports_count}</span> },
    { key: "join_date", label: "Joined", type: "date" },
  ];

  const filterConfig = [
    { key: "account_status", label: "Status", options: ["Active", "Frozen", "Banned", "Under Review"] },
    { key: "tier", label: "Tier", options: ["Casual", "Friendship", "Love"] },
    { key: "verification_status", label: "Verification", options: ["Verified", "Unverified", "Pending", "Needs Review"] },
    { key: "country", label: "Country", options: ["United Kingdom", "India"] },
    { key: "gender", label: "Gender", options: ["Male", "Female", "Other", "Prefer not to say"] },
    { key: "online", label: "Presence", options: ["true", "false"] },
  ];

  return (
    <>
      <Topbar title="User Management" subtitle="Search, review and take action on platform users" />
      <main className="flex-1 overflow-y-auto p-5 md:p-8 space-y-4">
        <DataTable
          columns={columns}
          rows={rows}
          loading={loading}
          total={meta.total}
          page={meta.page}
          pages={meta.pages}
          onPage={setPage}
          search={search}
          onSearch={setSearch}
          filters={filterConfig}
          filterValues={filters}
          onFilter={onFilter}
          actions={canWrite ? USER_ACTIONS : []}
          onAction={(row, action) => setDialog({ row, action })}
          onRowClick={(row) => navigate(`/users/${row.id}`)}
          exportName="users"
        />
      </main>

      {dialog && (
        <ActionDialog
          open={!!dialog}
          onOpenChange={(o) => !o && setDialog(null)}
          title={`${dialog.action.label}?`}
          description={`Apply "${dialog.action.label}" to ${dialog.row.name}. Recorded in the audit log.`}
          danger={dialog.action.danger}
          requireReason={dialog.action.danger}
          confirmLabel={dialog.action.label}
          onConfirm={runAction}
        />
      )}
    </>
  );
}
