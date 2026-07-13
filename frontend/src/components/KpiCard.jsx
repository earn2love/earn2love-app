import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown } from "lucide-react";

export function KpiCard({ label, value, delta, icon: Icon, accent = "violet", onClick, testid }) {
  const accents = {
    violet: "text-violet-500 bg-violet-500/10",
    pink: "text-pink-500 bg-pink-500/10",
    emerald: "text-emerald-500 bg-emerald-500/10",
    amber: "text-amber-500 bg-amber-500/10",
    sky: "text-sky-500 bg-sky-500/10",
  };
  const up = delta != null && delta >= 0;
  return (
    <button
      data-testid={testid}
      onClick={onClick}
      className={cn(
        "group text-left rounded-lg border border-border bg-card p-5 transition-all duration-200",
        onClick && "hover:-translate-y-[2px] hover:border-primary/40 cursor-pointer"
      )}
    >
      <div className="flex items-start justify-between">
        <p className="text-[11px] uppercase tracking-[0.14em] font-medium text-muted-foreground">{label}</p>
        {Icon && (
          <span className={cn("grid place-items-center h-8 w-8 rounded-md", accents[accent])}>
            <Icon className="h-4 w-4" />
          </span>
        )}
      </div>
      <p className="font-display text-3xl font-extrabold tracking-tight mt-3 tabular-nums">{value}</p>
      {delta != null && (
        <div className="flex items-center gap-1 mt-2">
          <span className={cn("inline-flex items-center gap-0.5 text-xs font-medium rounded-full px-1.5 py-0.5",
            up ? "text-emerald-600 bg-emerald-500/10" : "text-rose-600 bg-rose-500/10")}>
            {up ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {Math.abs(delta)}%
          </span>
          <span className="text-[11px] text-muted-foreground">vs last period</span>
        </div>
      )}
    </button>
  );
}
