import { useCallback, useEffect, useState } from "react";
import { Loader2, Phone, Save } from "lucide-react";
import { toast } from "sonner";

import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { useAuth } from "@/context/AuthContext";

export default function CallConfig() {
  const { admin } = useAuth();
  const [cfg, setCfg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const canEdit = admin?.role === "super_admin";

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/call-config");
      setCfg(data);
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail || error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const updateType = (type, field, value) => {
    setCfg((current) => ({
      ...current,
      [type]: {
        ...current[type],
        [field]: value,
      },
    }));
  };

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put("/call-config", cfg);
      setCfg(data);
      toast.success("Call pricing is now live");
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail || error));
    } finally {
      setSaving(false);
    }
  };

  if (loading || !cfg) {
    return (
      <div>
        <Topbar title="Call Configuration" subtitle="Live call pricing and billing rules" />
        <div className="grid place-items-center py-24">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      </div>
    );
  }

  return (
    <div data-testid="call-config-page">
      <Topbar
        title="Call Configuration"
        subtitle="Controls the live mobile audio and video call engine"
      />

      <div className="p-6 space-y-5 max-w-5xl">
        <div className="flex items-center justify-between rounded-xl border border-border bg-card p-4">
          <div>
            <p className="font-semibold">Global calls</p>
            <p className="text-sm text-muted-foreground">
              Disable to immediately prevent new audio and video calls.
            </p>
          </div>
          <Switch
            checked={cfg.enabled}
            disabled={!canEdit}
            onCheckedChange={(enabled) =>
              setCfg((current) => ({ ...current, enabled }))
            }
          />
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          {["audio", "video"].map((type) => (
            <div
              key={type}
              className="rounded-xl border border-border bg-card p-5 space-y-4"
            >
              <div className="flex items-center justify-between">
                <h3 className="capitalize font-semibold flex items-center gap-2">
                  <Phone className="h-4 w-4 text-pink-500" />
                  {type} calls
                </h3>
                <Switch
                  checked={cfg[type].enabled !== false}
                  disabled={!canEdit}
                  onCheckedChange={(enabled) =>
                    updateType(type, "enabled", enabled)
                  }
                />
              </div>

              <div>
                <Label>Caller pays per minute (Silver)</Label>
                <Input
                  type="number"
                  min="1"
                  disabled={!canEdit}
                  value={cfg[type].callerPerMinute}
                  onChange={(event) =>
                    updateType(
                      type,
                      "callerPerMinute",
                      Number(event.target.value),
                    )
                  }
                />
              </div>

              <div>
                <Label>Receiver reward percentage</Label>
                <Input
                  type="number"
                  min="0"
                  max="100"
                  disabled={!canEdit}
                  value={cfg[type].receiverRewardPercent}
                  onChange={(event) =>
                    updateType(
                      type,
                      "receiverRewardPercent",
                      Number(event.target.value),
                    )
                  }
                />
              </div>
            </div>
          ))}
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <Label>Billing increment (seconds)</Label>
            <Input
              type="number"
              min="1"
              max="3600"
              disabled={!canEdit}
              value={cfg.billingIncrementSeconds}
              onChange={(event) =>
                setCfg((current) => ({
                  ...current,
                  billingIncrementSeconds: Number(event.target.value),
                }))
              }
            />
          </div>

          <div>
            <Label>Minimum billable duration (seconds)</Label>
            <Input
              type="number"
              min="0"
              max="3600"
              disabled={!canEdit}
              value={cfg.minimumBillableSeconds}
              onChange={(event) =>
                setCfg((current) => ({
                  ...current,
                  minimumBillableSeconds: Number(event.target.value),
                }))
              }
            />
          </div>
        </div>

        <div className="flex justify-end">
          <Button onClick={save} disabled={!canEdit || saving}>
            {saving
              ? <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              : <Save className="h-4 w-4 mr-2" />}
            Save Call Configuration
          </Button>
        </div>
      </div>
    </div>
  );
}
