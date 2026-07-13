import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid,
  PieChart, Pie, Cell, Legend,
} from "recharts";
import { Users, HeartPulse, Banknote, ShieldAlert, BanknoteArrowDown, ScanFace, LifeBuoy } from "lucide-react";
import api from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { KpiCard } from "@/components/KpiCard";
import { StatusBadge } from "@/components/StatusBadge";
import { fmtDate, fmtNum } from "@/lib/format";

const DONUT_COLORS = ["#A855F7", "#EC4899", "#6D28D9", "#10B981", "#F59E0B", "#0EA5E9"];

function ChartCard({ title, children, className = "" }) {
  return (
    <div className={`rounded-lg border border-border bg-card p-5 ${className}`}>
      <h3 className="font-display font-semibold text-sm tracking-tight mb-4">{title}</h3>
      {children}
    </div>
  );
}

function Donut({ data }) {
  const total = data.reduce((s, d) => s + d.value, 0);
  return (
    <ResponsiveContainer width="100%" height={220}>
      <PieChart>
        <Pie data={data} dataKey="value" nameKey="name" innerRadius={55} outerRadius={80} paddingAngle={2} stroke="none">
          {data.map((_, i) => <Cell key={i} fill={DONUT_COLORS[i % DONUT_COLORS.length]} />)}
        </Pie>
        <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
        <Legend iconType="circle" iconSize={8} formatter={(v) => <span className="text-xs text-muted-foreground">{v}</span>} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export default function Dashboard() {
  const [data, setData] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.get("/dashboard").then((r) => setData(r.data)).catch(() => {});
  }, []);

  const k = data?.kpis || {};

  return (
    <>
      <Topbar title="Dashboard" subtitle="Live operational overview" />
      <main className="flex-1 overflow-y-auto p-5 md:p-8 space-y-6">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 text-xs text-emerald-600 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-2.5 py-1">
            <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" /> Live · Demo data
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
          <KpiCard testid="kpi-total-users" label="Total Users" value={fmtNum(k.total_users)} delta={12.4} icon={Users} accent="violet" onClick={() => navigate("/users")} />
          <KpiCard testid="kpi-active-users" label="Active Now" value={fmtNum(k.active_users)} delta={5.1} icon={HeartPulse} accent="emerald" onClick={() => navigate("/users?online=true")} />
          <KpiCard testid="kpi-revenue" label="Total Revenue" value={`£${fmtNum(Math.round(k.revenue || 0))}`} delta={8.7} icon={Banknote} accent="pink" onClick={() => navigate("/m/payments")} />
          <KpiCard testid="kpi-pending-reports" label="Pending Reports" value={fmtNum(k.pending_reports)} delta={-3.2} icon={ShieldAlert} accent="amber" onClick={() => navigate("/m/reports")} />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <KpiCard testid="kpi-pending-withdrawals" label="Pending Withdrawals" value={fmtNum(k.pending_withdrawals)} icon={BanknoteArrowDown} accent="sky" onClick={() => navigate("/m/withdrawals")} />
          <KpiCard testid="kpi-pending-verifs" label="Verifications Queue" value={fmtNum(k.pending_verifs)} icon={ScanFace} accent="violet" onClick={() => navigate("/m/liveness")} />
          <KpiCard testid="kpi-open-tickets" label="Open Tickets" value={fmtNum(k.open_tickets)} icon={LifeBuoy} accent="pink" onClick={() => navigate("/m/support-tickets")} />
        </div>

        {/* Trend + revenue donut */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <ChartCard title="Registrations & Active Users (14 days)" className="lg:col-span-2">
            <ResponsiveContainer width="100%" height={260}>
              <AreaChart data={data?.trend || []}>
                <defs>
                  <linearGradient id="gReg" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#A855F7" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#A855F7" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="gAct" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#EC4899" stopOpacity={0.4} />
                    <stop offset="100%" stopColor="#EC4899" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} vertical={false} />
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} width={30} />
                <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
                <Area type="monotone" dataKey="active" stroke="#EC4899" strokeWidth={2} fill="url(#gAct)" name="Active" />
                <Area type="monotone" dataKey="registrations" stroke="#A855F7" strokeWidth={2} fill="url(#gReg)" name="Registrations" />
              </AreaChart>
            </ResponsiveContainer>
          </ChartCard>
          <ChartCard title="Revenue by Source">
            <Donut data={data?.rev_by_source || []} />
          </ChartCard>
        </div>

        {/* Donuts row */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ChartCard title="Users by Gender"><Donut data={data?.by_gender || []} /></ChartCard>
          <ChartCard title="Users by Country"><Donut data={data?.by_country || []} /></ChartCard>
          <ChartCard title="Users by Tier"><Donut data={data?.by_tier || []} /></ChartCard>
        </div>

        {/* Recent tables */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          <div className="rounded-lg border border-border bg-card">
            <div className="flex items-center justify-between p-5 pb-3">
              <h3 className="font-display font-semibold text-sm">Recent Reports</h3>
              <button onClick={() => navigate("/m/reports")} className="text-xs text-primary hover:underline">View all</button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-y border-border text-[11px] uppercase tracking-wider text-muted-foreground">
                  <th className="text-left px-5 py-2 font-semibold">Reported</th>
                  <th className="text-left px-2 py-2 font-semibold">Category</th>
                  <th className="text-left px-2 py-2 font-semibold">Priority</th>
                  <th className="text-left px-2 py-2 font-semibold">Status</th>
                </tr></thead>
                <tbody>
                  {(data?.recent_reports || []).map((r) => (
                    <tr key={r.id} className="border-b border-border/60 hover:bg-accent/40 cursor-pointer" onClick={() => navigate("/m/reports")}>
                      <td className="px-5 py-2.5 truncate max-w-[140px]">{r.reported_user}</td>
                      <td className="px-2 py-2.5 text-muted-foreground">{r.category}</td>
                      <td className="px-2 py-2.5"><StatusBadge value={r.priority} /></td>
                      <td className="px-2 py-2.5"><StatusBadge value={r.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card">
            <div className="flex items-center justify-between p-5 pb-3">
              <h3 className="font-display font-semibold text-sm">Recent Verification Requests</h3>
              <button onClick={() => navigate("/m/identity")} className="text-xs text-primary hover:underline">View all</button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="border-y border-border text-[11px] uppercase tracking-wider text-muted-foreground">
                  <th className="text-left px-5 py-2 font-semibold">User</th>
                  <th className="text-left px-2 py-2 font-semibold">Type</th>
                  <th className="text-left px-2 py-2 font-semibold">Risk</th>
                  <th className="text-left px-2 py-2 font-semibold">Status</th>
                </tr></thead>
                <tbody>
                  {(data?.recent_verifications || []).map((r) => (
                    <tr key={r.id} className="border-b border-border/60 hover:bg-accent/40 cursor-pointer" onClick={() => navigate("/m/identity")}>
                      <td className="px-5 py-2.5 truncate max-w-[140px]">{r.user}</td>
                      <td className="px-2 py-2.5 text-muted-foreground">{r.verification_type}</td>
                      <td className="px-2 py-2.5 font-mono text-xs">{r.risk_score}</td>
                      <td className="px-2 py-2.5"><StatusBadge value={r.status} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>
    </>
  );
}
