import { useEffect, useMemo, useState, useCallback } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Users, Plus, Search, Loader2, Trash2, ShieldCheck, FileText, CalendarDays, Wallet, Award, BadgeCheck } from "lucide-react";
import { cn } from "@/lib/utils";
import { toast } from "sonner";

const ROLES = ["super_admin", "moderator", "support_agent", "finance_admin", "verification_agent"];
const STATUSES = ["active", "on_leave", "terminated"];
const KYC = ["not_started", "pending", "approved", "rejected"];

export default function Employees() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [edit, setEdit] = useState(null);
  const [saving, setSaving] = useState(false);
  const [del, setDel] = useState(null);
  // sub-record forms
  const [pay, setPay] = useState({ month: "", gross: "", net: "", currency: "gbp", status: "paid" });
  const [att, setAtt] = useState({ date: "", status: "present", hours: "8" });
  const [doc, setDoc] = useState({ name: "", type: "document", url: "" });

  const load = useCallback(async () => {
    setLoading(true);
    try { const { data } = await api.get("/employees"); setItems(data.items || []); }
    catch (e) { toast.error(formatApiError(e)); }
    setLoading(false);
  }, []);
  useEffect(() => { load(); }, [load]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items.filter((e) => !q || `${e.firstName} ${e.lastName} ${e.employeeCode} ${e.email}`.toLowerCase().includes(q));
  }, [items, query]);

  const openNew = () => setEdit({ firstName: "", lastName: "", email: "", phone: "", role: "support_agent", department: "", designation: "", status: "active", kyc: { status: "not_started", documents: [] }, badge: { level: "Member", title: "" }, payslips: [], attendance: [], documents: [] });
  const openEdit = async (id) => { try { const { data } = await api.get(`/employees/${id}`); setEdit(data); } catch (e) { toast.error(formatApiError(e)); } };

  const save = async () => {
    setSaving(true);
    try {
      if (edit.id) await api.put(`/employees/${edit.id}`, edit);
      else await api.post("/employees", edit);
      toast.success("Employee saved"); setEdit(null); await load();
    } catch (e) { toast.error(formatApiError(e)); }
    setSaving(false);
  };
  const doDelete = async () => { try { await api.delete(`/employees/${del.id}`); toast.success("Employee removed"); setDel(null); await load(); } catch (e) { toast.error(formatApiError(e)); } };

  const addSub = async (kind, payload, reset) => {
    try { const { data } = await api.post(`/employees/${edit.id}/${kind}`, payload); setEdit(data); reset(); toast.success("Added"); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const set = (f, v) => setEdit((e) => ({ ...e, [f]: v }));

  return (
    <div data-testid="employees-page">
      <Topbar title="Employees" subtitle="Team records, KYC, contracts, badges, payslips & attendance" />
      <div className="p-6 space-y-5">
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input data-testid="employees-search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search employees…" className="pl-9 h-10" />
          </div>
          <Button onClick={openNew} data-testid="employee-add-btn"><Plus className="h-4 w-4 mr-1.5" />Add Employee</Button>
        </div>

        {loading ? <div className="flex justify-center py-24"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
          : filtered.length === 0 ? <div className="flex flex-col items-center py-24 text-muted-foreground"><Users className="h-10 w-10 mb-3 opacity-40" /><p className="text-sm">No employees yet.</p></div>
          : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {filtered.map((e) => (
                <div key={e.id} data-testid={`employee-card-${e.id}`} className="rounded-xl border border-border bg-card p-4 hover:border-pink-500/30 transition-colors cursor-pointer" onClick={() => openEdit(e.id)}>
                  <div className="flex items-center gap-3">
                    <div className="grid place-items-center h-11 w-11 rounded-full bg-gradient-to-br from-pink-500 to-violet-500 text-white font-semibold">{(e.firstName?.[0] || "") + (e.lastName?.[0] || "")}</div>
                    <div className="min-w-0 flex-1">
                      <p className="font-semibold text-sm truncate">{e.firstName} {e.lastName}</p>
                      <p className="text-[11px] text-muted-foreground font-mono">{e.employeeCode} · {e.role}</p>
                    </div>
                    <span className={cn("text-[10px] px-2 py-0.5 rounded-full border", e.status === "active" ? "text-emerald-500 border-emerald-500/30 bg-emerald-500/10" : "text-amber-500 border-amber-500/30 bg-amber-500/10")}>{e.status}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-2">{e.designation || "—"}{e.department ? ` · ${e.department}` : ""}</p>
                  <div className="flex gap-3 mt-3 text-[11px] text-muted-foreground">
                    <span className="flex items-center gap-1"><Wallet className="h-3 w-3" />{e.counts?.payslips || 0}</span>
                    <span className="flex items-center gap-1"><CalendarDays className="h-3 w-3" />{e.counts?.attendance || 0}</span>
                    <span className="flex items-center gap-1"><FileText className="h-3 w-3" />{e.counts?.documents || 0}</span>
                    {e.badge?.level && <span className="flex items-center gap-1 ml-auto text-amber-500"><Award className="h-3 w-3" />{e.badge.level}</span>}
                  </div>
                </div>
              ))}
            </div>
          )}
      </div>

      {/* Editor */}
      <Dialog open={!!edit} onOpenChange={(o) => !o && setEdit(null)}>
        <DialogContent className="max-w-3xl h-[92vh] flex flex-col" data-testid="employee-editor">
          <DialogHeader><DialogTitle>{edit?.id ? `${edit.firstName} ${edit.lastName} (${edit.employeeCode})` : "New Employee"}</DialogTitle></DialogHeader>
          {edit && (
            <Tabs defaultValue="details" className="flex-1 min-h-0 flex flex-col">
              <TabsList className="flex-wrap h-auto">
                <TabsTrigger value="details"><BadgeCheck className="h-4 w-4 mr-1" />Details</TabsTrigger>
                <TabsTrigger value="kyc"><ShieldCheck className="h-4 w-4 mr-1" />KYC & Badge</TabsTrigger>
                <TabsTrigger value="payslips" disabled={!edit.id}><Wallet className="h-4 w-4 mr-1" />Payslips</TabsTrigger>
                <TabsTrigger value="attendance" disabled={!edit.id}><CalendarDays className="h-4 w-4 mr-1" />Attendance</TabsTrigger>
                <TabsTrigger value="documents" disabled={!edit.id}><FileText className="h-4 w-4 mr-1" />Documents</TabsTrigger>
              </TabsList>
              <div className="flex-1 overflow-auto mt-3 pr-1">
                <TabsContent value="details" className="space-y-3 mt-0">
                  <div className="grid grid-cols-2 gap-3">
                    <div><Label>First name</Label><Input data-testid="emp-firstName" value={edit.firstName} onChange={(e) => set("firstName", e.target.value)} /></div>
                    <div><Label>Last name</Label><Input data-testid="emp-lastName" value={edit.lastName} onChange={(e) => set("lastName", e.target.value)} /></div>
                    <div><Label>Email</Label><Input value={edit.email || ""} onChange={(e) => set("email", e.target.value)} /></div>
                    <div><Label>Phone</Label><Input value={edit.phone || ""} onChange={(e) => set("phone", e.target.value)} /></div>
                    <div><Label>Role</Label><Select value={edit.role} onValueChange={(v) => set("role", v)}><SelectTrigger data-testid="emp-role"><SelectValue /></SelectTrigger><SelectContent>{ROLES.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}</SelectContent></Select></div>
                    <div><Label>Status</Label><Select value={edit.status} onValueChange={(v) => set("status", v)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent></Select></div>
                    <div><Label>Department</Label><Input value={edit.department || ""} onChange={(e) => set("department", e.target.value)} /></div>
                    <div><Label>Designation</Label><Input value={edit.designation || ""} onChange={(e) => set("designation", e.target.value)} /></div>
                  </div>
                </TabsContent>
                <TabsContent value="kyc" className="space-y-4 mt-0">
                  <div className="grid grid-cols-2 gap-3">
                    <div><Label>KYC status</Label><Select value={edit.kyc?.status || "not_started"} onValueChange={(v) => set("kyc", { ...edit.kyc, status: v })}><SelectTrigger data-testid="emp-kyc"><SelectValue /></SelectTrigger><SelectContent>{KYC.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent></Select></div>
                    <div><Label>KYC document URL</Label><Input value={edit.kyc?.docUrl || ""} onChange={(e) => set("kyc", { ...edit.kyc, docUrl: e.target.value })} placeholder="https://…" /></div>
                    <div><Label>Badge level</Label><Input value={edit.badge?.level || ""} onChange={(e) => set("badge", { ...edit.badge, level: e.target.value })} /></div>
                    <div><Label>Badge title</Label><Input value={edit.badge?.title || ""} onChange={(e) => set("badge", { ...edit.badge, title: e.target.value })} /></div>
                  </div>
                  <div><Label>Contract note / URL</Label><Input value={edit.contractUrl || ""} onChange={(e) => set("contractUrl", e.target.value)} placeholder="Contract document link" /></div>
                </TabsContent>
                <TabsContent value="payslips" className="mt-0 space-y-3">
                  <div className="flex flex-wrap gap-2 items-end">
                    <div><Label className="text-xs">Month</Label><Input className="h-9 w-32" value={pay.month} onChange={(e) => setPay({ ...pay, month: e.target.value })} placeholder="2026-07" /></div>
                    <div><Label className="text-xs">Gross</Label><Input className="h-9 w-24" type="number" value={pay.gross} onChange={(e) => setPay({ ...pay, gross: e.target.value })} /></div>
                    <div><Label className="text-xs">Net</Label><Input className="h-9 w-24" type="number" value={pay.net} onChange={(e) => setPay({ ...pay, net: e.target.value })} /></div>
                    <Button size="sm" data-testid="add-payslip" onClick={() => addSub("payslips", pay, () => setPay({ month: "", gross: "", net: "", currency: "gbp", status: "paid" }))}><Plus className="h-4 w-4" /></Button>
                  </div>
                  <RecordTable rows={edit.payslips} cols={[["month", "Month"], ["gross", "Gross"], ["net", "Net"], ["status", "Status"]]} />
                </TabsContent>
                <TabsContent value="attendance" className="mt-0 space-y-3">
                  <div className="flex flex-wrap gap-2 items-end">
                    <div><Label className="text-xs">Date</Label><Input className="h-9 w-40" type="date" value={att.date} onChange={(e) => setAtt({ ...att, date: e.target.value })} /></div>
                    <div><Label className="text-xs">Status</Label><Select value={att.status} onValueChange={(v) => setAtt({ ...att, status: v })}><SelectTrigger className="h-9 w-32"><SelectValue /></SelectTrigger><SelectContent><SelectItem value="present">present</SelectItem><SelectItem value="absent">absent</SelectItem><SelectItem value="leave">leave</SelectItem></SelectContent></Select></div>
                    <div><Label className="text-xs">Hours</Label><Input className="h-9 w-20" type="number" value={att.hours} onChange={(e) => setAtt({ ...att, hours: e.target.value })} /></div>
                    <Button size="sm" data-testid="add-attendance" onClick={() => addSub("attendance", att, () => setAtt({ date: "", status: "present", hours: "8" }))}><Plus className="h-4 w-4" /></Button>
                  </div>
                  <RecordTable rows={edit.attendance} cols={[["date", "Date"], ["status", "Status"], ["hours", "Hours"]]} />
                </TabsContent>
                <TabsContent value="documents" className="mt-0 space-y-3">
                  <div className="flex flex-wrap gap-2 items-end">
                    <div><Label className="text-xs">Name</Label><Input className="h-9 w-40" value={doc.name} onChange={(e) => setDoc({ ...doc, name: e.target.value })} /></div>
                    <div><Label className="text-xs">Type</Label><Input className="h-9 w-32" value={doc.type} onChange={(e) => setDoc({ ...doc, type: e.target.value })} /></div>
                    <div><Label className="text-xs">URL</Label><Input className="h-9 w-52" value={doc.url} onChange={(e) => setDoc({ ...doc, url: e.target.value })} placeholder="https://…" /></div>
                    <Button size="sm" data-testid="add-document" onClick={() => addSub("documents", doc, () => setDoc({ name: "", type: "document", url: "" }))}><Plus className="h-4 w-4" /></Button>
                  </div>
                  <RecordTable rows={edit.documents} cols={[["name", "Name"], ["type", "Type"], ["url", "Link"]]} isLink />
                </TabsContent>
              </div>
            </Tabs>
          )}
          <DialogFooter className="gap-2">
            {edit?.id && <Button variant="destructive" className="mr-auto" onClick={() => setDel(edit)}><Trash2 className="h-4 w-4 mr-1.5" />Delete</Button>}
            <Button variant="outline" onClick={() => setEdit(null)}>Cancel</Button>
            <Button onClick={save} disabled={saving} data-testid="employee-save">{saving && <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />}Save</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!del} onOpenChange={(o) => !o && setDel(null)}>
        <DialogContent className="max-w-md"><DialogHeader><DialogTitle>Remove employee?</DialogTitle></DialogHeader>
          <p className="text-sm text-muted-foreground">{del?.firstName} {del?.lastName} will be permanently removed.</p>
          <DialogFooter><Button variant="outline" onClick={() => setDel(null)}>Cancel</Button><Button variant="destructive" onClick={doDelete}>Delete</Button></DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function RecordTable({ rows, cols, isLink }) {
  if (!rows?.length) return <p className="text-xs text-muted-foreground py-4">No records yet.</p>;
  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50 text-xs uppercase text-muted-foreground"><tr>{cols.map(([, l]) => <th key={l} className="text-left p-2.5">{l}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => (<tr key={i} className="border-t border-border">{cols.map(([k]) => <td key={k} className="p-2.5">{isLink && k === "url" && r[k] ? <a href={r[k]} target="_blank" rel="noreferrer" className="text-pink-500 underline">open</a> : String(r[k] ?? "—")}</td>)}</tr>))}</tbody>
      </table>
    </div>
  );
}
