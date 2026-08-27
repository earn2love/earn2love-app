import { cn } from "@/lib/utils";

const GREEN = "bg-emerald-500/12 text-emerald-600 dark:text-emerald-400 border-emerald-500/20";
const AMBER = "bg-amber-500/12 text-amber-600 dark:text-amber-400 border-amber-500/20";
const RED = "bg-rose-500/12 text-rose-600 dark:text-rose-400 border-rose-500/20";
const VIOLET = "bg-violet-500/12 text-violet-600 dark:text-violet-400 border-violet-500/20";
const PINK = "bg-pink-500/12 text-pink-600 dark:text-pink-400 border-pink-500/20";
const BLUE = "bg-sky-500/12 text-sky-600 dark:text-sky-400 border-sky-500/20";
const GRAY = "bg-muted text-muted-foreground border-border";
const ORANGE = "bg-orange-500/12 text-orange-600 dark:text-orange-400 border-orange-500/20";

const MAP = {
  // success
  Active: GREEN, Approved: GREEN, Successful: GREEN, Completed: GREEN, Paid: GREEN,
  Resolved: GREEN, Verified: GREEN, Accepted: GREEN, Connected: GREEN, Sent: GREEN, Low: GREEN, Success: GREEN,
  // warning
  Pending: AMBER, "Under Review": AMBER, "Needs Review": AMBER, "Waiting for User": AMBER,
  Processing: AMBER, Investigating: AMBER, Assigned: AMBER, Trialing: AMBER, Draft: AMBER,
  Scheduled: AMBER, "Past Due": AMBER, Paused: AMBER, Medium: AMBER,
  // danger
  Banned: RED, Rejected: RED, Failed: RED, Disputed: RED, Blocked: RED, Frozen: RED,
  Disabled: RED, Critical: RED, Expired: RED, Cancelled: RED, Reversed: RED, Removed: RED,
  // accents
  Love: VIOLET, Escalated: VIOLET, Diamond: BLUE, Open: VIOLET,
  Friendship: PINK, Gold: AMBER, Video: PINK, "Partially Refunded": ORANGE, Refunded: ORANGE,
  High: ORANGE, Audio: BLUE, Push: VIOLET, Email: BLUE, "In-app": PINK, SMS: GRAY,
  Casual: GRAY, Silver: GRAY, Inactive: GRAY, "Not Submitted": GRAY, Unverified: GRAY,
  Missed: GRAY, Other: GRAY, Requested: GRAY, Closed: GRAY,
};

export function StatusBadge({ value, className }) {
  if (value == null || value === "") return <span className="text-muted-foreground">—</span>;
  const key = String(value);
  const norm = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const cls = MAP[key] || MAP[norm] || GRAY;
  return (
    <span
      className={cn("inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium whitespace-nowrap capitalize", cls, className)}
      data-testid={`badge-${key.toLowerCase().replace(/\s+/g, "-")}`}
    >
      {norm}
    </span>
  );
}
