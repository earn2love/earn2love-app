export function fmtDate(v) {
  if (!v) return "—";
  try {
    const d = new Date(v);
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  } catch { return v; }
}

export function fmtDateTime(v) {
  if (!v) return "—";
  try {
    const d = new Date(v);
    return d.toLocaleString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  } catch { return v; }
}

const SYM = { GBP: "£", INR: "₹", USD: "$", EUR: "€" };
export function fmtCurrency(amount, currency) {
  if (amount == null) return "—";
  const s = SYM[currency] || "";
  return `${s}${Number(amount).toLocaleString("en-GB", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function fmtNum(n) {
  if (n == null) return "—";
  return Number(n).toLocaleString("en-GB");
}

export function exportCsv(rows, columns, filename) {
  if (!rows?.length) return;
  const headers = columns.map((c) => c.label);
  const keys = columns.map((c) => c.key);
  const escape = (v) => {
    if (v == null) return "";
    const s = String(v).replace(/"/g, '""');
    return /[",\n]/.test(s) ? `"${s}"` : s;
  };
  const lines = [headers.join(",")];
  rows.forEach((r) => lines.push(keys.map((k) => escape(r[k])).join(",")));
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${filename}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
