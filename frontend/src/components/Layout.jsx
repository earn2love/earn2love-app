import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Sidebar } from "@/components/Sidebar";
import { CommandPalette } from "@/components/CommandPalette";
import { PendingCountsProvider } from "@/context/PendingCountsContext";

export function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <PendingCountsProvider>
      <div className="flex h-screen w-full overflow-hidden bg-background">
        <Sidebar collapsed={collapsed} setCollapsed={setCollapsed} />
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          <Outlet />
        </div>
        <CommandPalette />
      </div>
    </PendingCountsProvider>
  );
}
