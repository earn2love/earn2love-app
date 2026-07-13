import { useEffect, useState } from "react";
import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { useAuth } from "@/context/AuthContext";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { Save } from "lucide-react";

const SECTION_TITLES = {
  general: "General", age_restriction: "Age Restriction", report_thresholds: "Report Thresholds & Auto-Freeze",
  calls: "Call Rates", tasks: "Tasks & Offerwall", advertisements: "Advertisement Rewards",
  coin_conversion: "Coin Conversion Rules", withdrawal_rules: "Withdrawal Rules",
  feature_flags: "Feature Flags", data_retention: "Data Retention",
};

function humanize(k) {
  return k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function Settings() {
  const { admin } = useAuth();
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const canEdit = ["Owner", "Super Admin"].includes(admin?.role);

  useEffect(() => { api.get("/settings").then((r) => setSettings(r.data)).catch(() => {}); }, []);

  const setField = (section, key, value) => {
    setSettings((s) => ({ ...s, [section]: { ...s[section], [key]: value } }));
  };

  const save = async () => {
    setSaving(true);
    try {
      const body = { ...settings }; delete body._id;
      await api.put("/settings", body);
      toast.success("Settings saved");
    } catch (e) { toast.error(formatApiError(e.response?.data?.detail)); }
    finally { setSaving(false); }
  };

  if (!settings) return (<><Topbar title="System Settings" /><main className="flex-1 grid place-items-center text-muted-foreground">Loading…</main></>);

  const sections = Object.keys(SECTION_TITLES).filter((k) => settings[k]);

  return (
    <>
      <Topbar title="System Settings" subtitle="Platform-wide configuration (all values configurable)" />
      <main className="flex-1 overflow-y-auto p-5 md:p-8 space-y-5">
        {!canEdit && <p className="text-xs text-muted-foreground">Only Owner / Super Admin can modify settings. Fields are read-only for your role.</p>}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {sections.map((section) => (
            <div key={section} className="rounded-lg border border-border bg-card p-5" data-testid={`settings-${section}`}>
              <h3 className="font-display font-semibold text-sm tracking-tight mb-4">{SECTION_TITLES[section]}</h3>
              <div className="space-y-3.5">
                {Object.entries(settings[section]).map(([key, val]) => {
                  if (Array.isArray(val)) {
                    return (
                      <div key={key} className="flex items-center justify-between gap-4">
                        <Label className="text-sm text-muted-foreground">{humanize(key)}</Label>
                        <Input disabled={!canEdit} className="max-w-[220px] h-9 bg-background text-sm"
                          value={val.join(", ")} onChange={(e) => setField(section, key, e.target.value.split(",").map((x) => x.trim()))} />
                      </div>
                    );
                  }
                  if (typeof val === "boolean") {
                    return (
                      <div key={key} className="flex items-center justify-between gap-4">
                        <Label className="text-sm text-muted-foreground">{humanize(key)}</Label>
                        <Switch disabled={!canEdit} checked={val} onCheckedChange={(v) => setField(section, key, v)} data-testid={`toggle-${section}-${key}`} />
                      </div>
                    );
                  }
                  return (
                    <div key={key} className="flex items-center justify-between gap-4">
                      <Label className="text-sm text-muted-foreground">{humanize(key)}</Label>
                      <Input disabled={!canEdit} type={typeof val === "number" ? "number" : "text"}
                        className="max-w-[200px] h-9 bg-background text-sm"
                        value={val}
                        onChange={(e) => setField(section, key, typeof val === "number" ? Number(e.target.value) : e.target.value)} />
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
        {canEdit && (
          <div className="sticky bottom-4 flex justify-end">
            <Button data-testid="save-settings-btn" onClick={save} disabled={saving} className="gradient-brand text-white border-0 gap-2 shadow-lg">
              <Save className="h-4 w-4" /> {saving ? "Saving…" : "Save changes"}
            </Button>
          </div>
        )}
      </main>
    </>
  );
}
