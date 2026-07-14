import { createContext, useContext, useEffect, useState, useCallback } from "react";
import api from "@/lib/api";

const PendingCountsContext = createContext({ counts: {}, total: 0, refresh: () => {} });

export function PendingCountsProvider({ children }) {
  const [counts, setCounts] = useState({});
  const [total, setTotal] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const { data } = await api.get("/pending-counts");
      setCounts(data.counts || {});
      setTotal(data.total || 0);
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 30000);
    return () => clearInterval(t);
  }, [refresh]);

  return (
    <PendingCountsContext.Provider value={{ counts, total, refresh }}>
      {children}
    </PendingCountsContext.Provider>
  );
}

export const usePendingCounts = () => useContext(PendingCountsContext);
