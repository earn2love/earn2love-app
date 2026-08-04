import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { LogOut, Menu, Search, Bell, UserCircle2 } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { roleCanSeeItem } from "@/lib/portal";
import { usePendingCounts } from "@/context/PendingCountsContext";
import { ThemeToggle } from "@/components/ThemeToggle";
import { NAV_GROUPS } from "@/config/modules";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function Topbar({ title, subtitle }) {
  const { admin, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { counts, total } = usePendingCounts();

  const PENDING_ITEMS = [
    { key: "reports", label: "Open reports", to: "/m/reports" },
    { key: "withdrawals", label: "Withdrawals to review", to: "/m/withdrawals" },
    { key: "liveness", label: "Liveness checks", to: "/m/liveness" },
    { key: "identity", label: "Identity checks", to: "/m/identity" },
    { key: "moderation", label: "Moderation queue", to: "/m/moderation" },
    { key: "support-tickets", label: "Open tickets", to: "/m/support-tickets" },
    { key: "conversions", label: "Conversions under review", to: "/m/conversions" },
    { key: "payments", label: "Disputed payments", to: "/m/payments" },
  ].filter((i) => (counts[i.key] || 0) > 0);

  const doLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <header
      data-testid="topbar"
      className="sticky top-0 z-30 flex items-center justify-between h-16 px-5 md:px-8 border-b border-border bg-background/70 backdrop-blur-xl"
    >
      <div className="flex items-center gap-2.5 min-w-0">
        <Sheet>
          <SheetTrigger asChild>
            <button data-testid="mobile-nav-trigger" className="md:hidden text-muted-foreground hover:text-foreground p-1">
              <Menu className="h-5 w-5" />
            </button>
          </SheetTrigger>
          <SheetContent side="left" className="w-72 p-0 bg-sidebar text-sidebar-foreground border-white/5">
            <div className="flex items-center gap-2.5 h-16 px-4 border-b border-white/5">
              <div className="grid place-items-center h-9 w-9 rounded-lg overflow-hidden bg-white/95 ring-1 ring-white/10">
                <img src="/earn2love-logo.png" alt="Earn2Love" className="h-full w-full object-cover" />
              </div>
              <p className="font-display font-extrabold tracking-tight">Earn2Love</p>
            </div>
            <nav className="overflow-y-auto py-3 px-2.5 space-y-3 h-[calc(100vh-4rem)]">
              {NAV_GROUPS.map((grp) => (
                <div key={grp.group}>
                  <p className="px-2.5 mb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/30">{grp.group}</p>
                  {grp.items.filter((item) => roleCanSeeItem(admin?.role, item)).map((item) => {
                    const Icon = item.icon;
                    const active = item.to === "/" ? location.pathname === "/" : location.pathname.startsWith(item.to);
                    return (
                      <NavLink key={item.to} to={item.to} data-testid={`mnav-${item.key}`}
                        className={`flex items-center gap-3 rounded-md px-2.5 py-2 text-[13px] font-medium ${active ? "bg-white/[0.06] text-white" : "text-white/55"}`}>
                        <Icon className={`h-[18px] w-[18px] ${active ? "text-pink-400" : ""}`} />
                        <span>{item.label}</span>
                      </NavLink>
                    );
                  })}
                </div>
              ))}
            </nav>
          </SheetContent>
        </Sheet>
        <div className="min-w-0">
          <h1 className="font-display font-bold text-lg md:text-xl tracking-tight truncate">{title}</h1>
          {subtitle && <p className="text-xs text-muted-foreground truncate hidden sm:block">{subtitle}</p>}
        </div>
      </div>

      <div className="flex items-center gap-1.5 md:gap-2.5">
        <button
          data-testid="command-trigger"
          onClick={() => window.dispatchEvent(new Event("open-command"))}
          className="hidden sm:flex items-center gap-2 h-9 pl-3 pr-2 rounded-full border border-border bg-card text-muted-foreground hover:text-foreground hover:border-primary/40 transition-colors text-xs"
        >
          <Search className="h-3.5 w-3.5" />
          <span>Search…</span>
          <kbd className="ml-1 rounded bg-muted px-1.5 py-0.5 text-[10px] font-mono">⌘K</kbd>
        </button>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button data-testid="notif-bell" className="relative grid place-items-center h-9 w-9 rounded-full text-muted-foreground hover:text-foreground hover:bg-accent transition-colors">
              <Bell className="h-[18px] w-[18px]" />
              {total > 0 && (
                <span data-testid="notif-bell-count" className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 grid place-items-center rounded-full bg-pink-500 text-white text-[9px] font-bold tabular-nums">
                  {total > 99 ? "99+" : total}
                </span>
              )}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-64">
            <DropdownMenuLabel className="flex items-center justify-between">
              <span>Pending items</span>
              <span className="text-xs text-muted-foreground font-normal">{total} total</span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            {PENDING_ITEMS.length === 0 ? (
              <div className="px-2 py-6 text-center text-sm text-muted-foreground">All caught up 🎉</div>
            ) : PENDING_ITEMS.map((i) => (
              <DropdownMenuItem key={i.key} data-testid={`notif-item-${i.key}`} onClick={() => navigate(i.to)} className="flex items-center justify-between">
                <span>{i.label}</span>
                <span className="min-w-[20px] h-5 px-1.5 grid place-items-center rounded-full bg-pink-500/15 text-pink-500 text-[11px] font-semibold">{counts[i.key]}</span>
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
        <ThemeToggle />
        <div className="h-6 w-px bg-border mx-0.5 hidden sm:block" />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button data-testid="admin-menu-trigger" className="flex items-center gap-2.5 rounded-full pl-1 pr-2.5 py-1 hover:bg-accent transition-colors">
              <span className="grid place-items-center h-8 w-8 rounded-full gradient-brand text-white text-xs font-semibold">
                {admin?.initials || "AD"}
              </span>
              <div className="text-left hidden md:block leading-tight">
                <p className="text-[13px] font-semibold">{admin?.name}</p>
                <p className="text-[11px] text-muted-foreground">{admin?.role}</p>
              </div>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>
              <p className="font-semibold">{admin?.name}</p>
              <p className="text-xs text-muted-foreground font-normal">{admin?.email}</p>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem disabled className="text-xs">
              Role: <span className="font-medium ml-1 text-foreground">{admin?.role}</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem data-testid="my-profile-btn" onClick={() => navigate("/profile")}>
              <UserCircle2 className="h-4 w-4 mr-2" /> My Profile
            </DropdownMenuItem>
            <DropdownMenuItem data-testid="logout-btn" onClick={doLogout} className="text-rose-600 focus:text-rose-600">
              <LogOut className="h-4 w-4 mr-2" /> Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
