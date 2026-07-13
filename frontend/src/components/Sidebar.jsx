import { useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { Heart, ChevronLeft, PanelLeftClose, PanelLeft } from "lucide-react";
import { NAV_GROUPS } from "@/config/modules";
import { cn } from "@/lib/utils";

export function Sidebar({ collapsed, setCollapsed }) {
  const location = useLocation();

  return (
    <aside
      data-testid="sidebar"
      className={cn(
        "hidden md:flex flex-col shrink-0 bg-sidebar text-sidebar-foreground border-r border-white/5 transition-[width] duration-300 ease-in-out",
        collapsed ? "w-[68px]" : "w-64"
      )}
    >
      <div className="flex items-center gap-2.5 h-16 px-4 border-b border-white/5 shrink-0">
        <div className="grid place-items-center h-9 w-9 rounded-lg gradient-brand shrink-0">
          <Heart className="h-5 w-5 text-white" fill="currentColor" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="font-display font-extrabold text-[15px] leading-none tracking-tight">Earn2Love</p>
            <p className="text-[10px] uppercase tracking-[0.18em] text-white/40 mt-1">Admin Console</p>
          </div>
        )}
      </div>

      <nav className="flex-1 overflow-y-auto py-3 px-2.5 space-y-4">
        {NAV_GROUPS.map((grp) => (
          <div key={grp.group}>
            {!collapsed && (
              <p className="px-2.5 mb-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/30">
                {grp.group}
              </p>
            )}
            <div className="space-y-0.5">
              {grp.items.map((item) => {
                const Icon = item.icon;
                const active = item.to === "/"
                  ? location.pathname === "/"
                  : location.pathname.startsWith(item.to);
                return (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    data-testid={`nav-${item.key}`}
                    title={collapsed ? item.label : undefined}
                    className={cn(
                      "group relative flex items-center gap-3 rounded-md px-2.5 py-2 text-[13px] font-medium transition-colors duration-150",
                      active
                        ? "bg-white/[0.06] text-white"
                        : "text-white/55 hover:text-white hover:bg-white/[0.04]"
                    )}
                  >
                    {active && (
                      <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-[3px] rounded-r-full gradient-brand" />
                    )}
                    <Icon className={cn("h-[18px] w-[18px] shrink-0", active && "text-pink-400")} />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      <button
        data-testid="sidebar-collapse-btn"
        onClick={() => setCollapsed(!collapsed)}
        className="flex items-center gap-2 h-11 px-4 border-t border-white/5 text-white/50 hover:text-white text-xs transition-colors"
      >
        {collapsed ? <PanelLeft className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        {!collapsed && <span>Collapse</span>}
      </button>
    </aside>
  );
}
