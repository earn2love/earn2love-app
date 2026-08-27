import { useEffect, useState } from "react";
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell,
} from "recharts";
import api from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { KpiCard } from "@/components/KpiCard";
import { Users, Phone, Clock, Banknote, ShieldX, BadgeCheck } from "lucide-react";
import { fmtNum } from "@/lib/format";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

const RANGES = [{ v: "7", l: "Last 7 days" }, { v: "30", l: "Last 30 days" }, { v: "90", l: "Last 90 days" }, { v: "365", l: "This year" }];

export default function Analytics() {
  const [range, setRange] = useState("30");
  const [data, setData] = useState(null);

  useEffect(() => { api.get("/analytics", { params: { range } }).then((r) => setData(r.data)).catch(() => {}); }, [range]);
  const s = data?.summary || {};

  return (
    <>
      <Topbar title="Platform Analytics" subtitle="Growth, revenue and platform health metrics" />
      <main className="flex-1 overflow-y-auto p-5 md:p-8 space-y-6">
        <div className="flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground border border-border rounded-full px-2.5 py-1"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" /> Live data</span>
          <Select value={range} onValueChange={setRange}>
            <SelectTrigger data-testid="analytics-range" className="h-9 w-[160px] bg-card"><SelectValue /></SelectTrigger>
            <SelectContent>{RANGES.map((r) => <SelectItem key={r.v} value={r.v}>{r.l}</SelectItem>)}</SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          <KpiCard label="Total Users" value={fmtNum(s.total_users)} icon={Users} accent="violet" />
          <KpiCard label="Total Calls" value={fmtNum(s.total_calls)} icon={Phone} accent="pink" />
          <KpiCard label="Call Minutes" value={fmtNum(s.total_minutes)} icon={Clock} accent="sky" />
          <KpiCard label="Revenue" value={`£${fmtNum(Math.round(s.revenue || 0))}`} icon={Banknote} accent="emerald" />
          <KpiCard label="Ban Rate" value={`${s.ban_rate || 0}%`} icon={ShieldX} accent="amber" />
          <KpiCard label="Verified" value={`${s.verification_rate || 0}%`} icon={BadgeCheck} accent="emerald" />
        </div>

        <div className="rounded-lg border border-border bg-card p-5">
          <h3 className="font-display font-semibold text-sm mb-4">User Growth</h3>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={data?.growth || []}>
              <defs>
                <linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#A855F7" stopOpacity={0.5} />
                  <stop offset="100%" stopColor="#A855F7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} interval="preserveStartEnd" />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} width={40} />
              <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} />
              <Area type="monotone" dataKey="users" stroke="#A855F7" strokeWidth={2.5} fill="url(#ag)" name="Cumulative users" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="rounded-lg border border-border bg-card p-5">
          <h3 className="font-display font-semibold text-sm mb-4">Revenue by Country</h3>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data?.country_comparison || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} vertical={false} />
              <XAxis dataKey="name" tick={{ fontSize: 12, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} width={50} />
              <Tooltip contentStyle={{ background: "hsl(var(--popover))", border: "1px solid hsl(var(--border))", borderRadius: 8, fontSize: 12 }} cursor={{ fill: "hsl(var(--accent))" }} />
              <Bar dataKey="revenue" radius={[6, 6, 0, 0]} name="Revenue">
                {(data?.country_comparison || []).map((_, i) => <Cell key={i} fill={i % 2 ? "#EC4899" : "#A855F7"} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </main>
    </>
  );
}
