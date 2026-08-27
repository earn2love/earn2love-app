import { useState } from "react";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";

export function ActionDialog({ open, onOpenChange, title, description, danger, requireReason, onConfirm, confirmLabel = "Confirm" }) {
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);

  const handle = async () => {
    setBusy(true);
    await onConfirm(reason);
    setBusy(false);
    setReason("");
  };

  return (
    <AlertDialog open={open} onOpenChange={(o) => { if (!o) setReason(""); onOpenChange(o); }}>
      <AlertDialogContent data-testid="action-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        <div className="space-y-2">
          <Label className="text-xs uppercase tracking-wide text-muted-foreground">
            Reason {requireReason && <span className="text-rose-500">*</span>}
          </Label>
          <Textarea
            data-testid="action-reason-input"
            placeholder="Add a reason for the audit log…"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
          />
        </div>
        <AlertDialogFooter>
          <AlertDialogCancel data-testid="action-cancel">Cancel</AlertDialogCancel>
          <AlertDialogAction
            data-testid="action-confirm"
            disabled={busy || (requireReason && !reason.trim())}
            onClick={(e) => { e.preventDefault(); handle(); }}
            className={cn(danger && "bg-rose-600 hover:bg-rose-700 focus:ring-rose-600")}
          >
            {busy ? "Working…" : confirmLabel}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
