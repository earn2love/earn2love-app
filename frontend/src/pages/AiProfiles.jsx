import { useCallback, useEffect, useState } from "react";
import { Bot, Loader2, Plus, Save, Trash2 } from "lucide-react";
import { toast } from "sonner";

import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";

const EMPTY_PROFILE = {
  name: "",
  genderPresentation: "female",
  avatarUrl: "",
  voiceId: "",
  languages: ["English"],
  interests: "",
  personality: "",
  systemPrompt: "",
  premiumOnly: true,
  enabled: false,
};

export default function AiProfiles() {
  const [items, setItems] = useState([]);
  const [edit, setEdit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/ai-profiles");
      setItems(data.items || []);
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail || error));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    setSaving(true);
    try {
      await api.post("/ai-profiles", edit);
      toast.success("AI profile saved");
      setEdit(null);
      await load();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail || error));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this AI profile?")) return;
    await api.delete(`/ai-profiles/${id}`);
    await load();
  };

  return (
    <div>
      <Topbar title="AI Profiles" subtitle="Manage AI personalities available in Earn2Love" />

      <div className="p-6 space-y-5">
        <div className="flex justify-end">
          <Button onClick={() => setEdit({ ...EMPTY_PROFILE })}>
            <Plus className="h-4 w-4 mr-2" />
            Create AI Profile
          </Button>
        </div>

        {loading ? (
          <div className="grid place-items-center py-24">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {items.map((profile) => (
              <div key={profile.id} className="rounded-xl border border-border bg-card p-5">
                <div className="flex items-start justify-between">
                  <Bot className="h-5 w-5 text-pink-500" />
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    profile.enabled
                      ? "bg-emerald-500/10 text-emerald-500"
                      : "bg-muted text-muted-foreground"
                  }`}>
                    {profile.enabled ? "Active" : "Draft"}
                  </span>
                </div>

                <h3 className="mt-3 font-semibold">{profile.name}</h3>
                <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                  {profile.personality || "No personality description"}
                </p>

                <div className="mt-4 text-xs text-muted-foreground">
                  {profile.genderPresentation} · {profile.premiumOnly ? "Premium" : "Free"}
                </div>

                <div className="mt-4 flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setEdit(profile)}>
                    Edit
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => remove(profile.id)}>
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {edit && (
          <div className="rounded-xl border border-border bg-card p-5 space-y-4 max-w-3xl">
            <h3 className="font-semibold">
              {edit.id ? "Edit AI Profile" : "Create AI Profile"}
            </h3>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label>Name</Label>
                <Input
                  value={edit.name}
                  onChange={(event) => setEdit({ ...edit, name: event.target.value })}
                />
              </div>

              <div>
                <Label>Gender presentation</Label>
                <select
                  value={edit.genderPresentation}
                  onChange={(event) =>
                    setEdit({ ...edit, genderPresentation: event.target.value })
                  }
                  className="w-full h-10 rounded-md border border-border bg-background px-3"
                >
                  <option value="female">Female</option>
                  <option value="male">Male</option>
                  <option value="neutral">Neutral</option>
                </select>
              </div>

              <div>
                <Label>Avatar URL</Label>
                <Input
                  value={edit.avatarUrl}
                  onChange={(event) => setEdit({ ...edit, avatarUrl: event.target.value })}
                />
              </div>

              <div>
                <Label>Voice ID</Label>
                <Input
                  value={edit.voiceId}
                  onChange={(event) => setEdit({ ...edit, voiceId: event.target.value })}
                />
              </div>

              <div className="md:col-span-2">
                <Label>Interests</Label>
                <Input
                  value={edit.interests}
                  onChange={(event) => setEdit({ ...edit, interests: event.target.value })}
                />
              </div>
            </div>

            <div>
              <Label>Personality</Label>
              <Textarea
                value={edit.personality}
                onChange={(event) => setEdit({ ...edit, personality: event.target.value })}
              />
            </div>

            <div>
              <Label>System prompt</Label>
              <Textarea
                rows={7}
                value={edit.systemPrompt}
                onChange={(event) => setEdit({ ...edit, systemPrompt: event.target.value })}
              />
            </div>

            <div className="flex flex-wrap gap-6">
              <label className="flex items-center gap-3">
                <Switch
                  checked={!!edit.premiumOnly}
                  onCheckedChange={(premiumOnly) =>
                    setEdit({ ...edit, premiumOnly })
                  }
                />
                <span className="text-sm">Premium only</span>
              </label>

              <label className="flex items-center gap-3">
                <Switch
                  checked={!!edit.enabled}
                  onCheckedChange={(enabled) => setEdit({ ...edit, enabled })}
                />
                <span className="text-sm">Active in app</span>
              </label>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setEdit(null)}>Cancel</Button>
              <Button onClick={save} disabled={saving || !edit.name.trim()}>
                <Save className="h-4 w-4 mr-2" />
                Save AI Profile
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
