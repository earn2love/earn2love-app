import { useCallback, useEffect, useState } from "react";
import { Gamepad2, Loader2, Plus, Save, Trash2 } from "lucide-react";
import { toast } from "sonner";

import api, { formatApiError } from "@/lib/api";
import { Topbar } from "@/components/Topbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";

const EMPTY_GAME = {
  name: "",
  category: "quiz",
  description: "",
  difficulty: "medium",
  rewardSilver: 0,
  rewardGold: 0,
  dailyLimit: 5,
  regions: ["UK", "IN"],
  enabled: false,
};

export default function Games() {
  const [items, setItems] = useState([]);
  const [edit, setEdit] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const { data } = await api.get("/games");
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
      await api.post("/games", edit);
      toast.success("Game saved");
      setEdit(null);
      await load();
    } catch (error) {
      toast.error(formatApiError(error.response?.data?.detail || error));
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id) => {
    if (!window.confirm("Delete this game?")) return;
    await api.delete(`/games/${id}`);
    await load();
  };

  return (
    <div>
      <Topbar title="Games" subtitle="Configure the Earn2Love games catalogue" />

      <div className="p-6 space-y-5">
        <div className="flex justify-end">
          <Button onClick={() => setEdit({ ...EMPTY_GAME })}>
            <Plus className="h-4 w-4 mr-2" />
            Create Game
          </Button>
        </div>

        {loading ? (
          <div className="grid place-items-center py-24">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        ) : (
          <div className="grid md:grid-cols-2 xl:grid-cols-3 gap-4">
            {items.map((game) => (
              <div key={game.id} className="rounded-xl border border-border bg-card p-5">
                <div className="flex items-start justify-between">
                  <Gamepad2 className="h-5 w-5 text-pink-500" />
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    game.enabled
                      ? "bg-emerald-500/10 text-emerald-500"
                      : "bg-muted text-muted-foreground"
                  }`}>
                    {game.enabled ? "Live" : "Draft"}
                  </span>
                </div>

                <h3 className="mt-3 font-semibold">{game.name}</h3>
                <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                  {game.description || "No description"}
                </p>

                <div className="mt-4 text-xs text-muted-foreground">
                  {game.category} · {game.difficulty} · {game.dailyLimit || 0}/day
                </div>

                <div className="mt-4 flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setEdit(game)}>
                    Edit
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => remove(game.id)}>
                    <Trash2 className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}

        {edit && (
          <div className="rounded-xl border border-border bg-card p-5 space-y-4 max-w-3xl">
            <h3 className="font-semibold">{edit.id ? "Edit Game" : "Create Game"}</h3>

            <div className="grid md:grid-cols-2 gap-4">
              <div>
                <Label>Name</Label>
                <Input
                  value={edit.name}
                  onChange={(event) => setEdit({ ...edit, name: event.target.value })}
                />
              </div>

              <div>
                <Label>Category</Label>
                <Input
                  value={edit.category}
                  onChange={(event) => setEdit({ ...edit, category: event.target.value })}
                />
              </div>

              <div>
                <Label>Difficulty</Label>
                <select
                  value={edit.difficulty}
                  onChange={(event) => setEdit({ ...edit, difficulty: event.target.value })}
                  className="w-full h-10 rounded-md border border-border bg-background px-3"
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>

              <div>
                <Label>Daily limit</Label>
                <Input
                  type="number"
                  value={edit.dailyLimit}
                  onChange={(event) => setEdit({ ...edit, dailyLimit: Number(event.target.value) })}
                />
              </div>

              <div>
                <Label>Silver reward</Label>
                <Input
                  type="number"
                  value={edit.rewardSilver}
                  onChange={(event) => setEdit({ ...edit, rewardSilver: Number(event.target.value) })}
                />
              </div>

              <div>
                <Label>Gold reward</Label>
                <Input
                  type="number"
                  value={edit.rewardGold}
                  onChange={(event) => setEdit({ ...edit, rewardGold: Number(event.target.value) })}
                />
              </div>
            </div>

            <div>
              <Label>Description</Label>
              <Textarea
                value={edit.description}
                onChange={(event) => setEdit({ ...edit, description: event.target.value })}
              />
            </div>

            <div className="flex items-center gap-3">
              <Switch
                checked={!!edit.enabled}
                onCheckedChange={(enabled) => setEdit({ ...edit, enabled })}
              />
              <Label>Published and visible in the app</Label>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => setEdit(null)}>Cancel</Button>
              <Button onClick={save} disabled={saving || !edit.name.trim()}>
                <Save className="h-4 w-4 mr-2" />
                Save Game
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
