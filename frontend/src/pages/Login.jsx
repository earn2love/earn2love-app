import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Heart, Loader2, ShieldCheck } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import api, { formatApiError } from "@/lib/api";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState("login"); // login | forgot

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    if (mode === "forgot") {
      try {
        await api.post("/auth/forgot-password", { email });
        toast.success("If the account exists, a reset link has been generated (see server logs).");
        setMode("login");
      } catch (err) {
        setError(formatApiError(err.response?.data?.detail) || err.message);
      }
      setBusy(false);
      return;
    }
    const res = await login(email, password);
    setBusy(false);
    if (res.ok) navigate("/");
    else setError(res.error);
  };

  const quickFill = () => { setEmail("ram@earn2love.com"); setPassword("Owner@2026"); };

  return (
    <div className="min-h-screen w-full flex bg-background">
      {/* Left brand panel */}
      <div className="hidden lg:flex flex-col justify-between w-[46%] p-12 relative overflow-hidden bg-sidebar text-white">
        <div className="absolute -top-24 -right-24 h-96 w-96 rounded-full gradient-brand opacity-30 blur-3xl" />
        <div className="absolute bottom-0 -left-20 h-80 w-80 rounded-full bg-pink-600 opacity-20 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <div className="grid place-items-center h-11 w-11 rounded-xl gradient-brand">
            <Heart className="h-6 w-6 text-white" fill="currentColor" />
          </div>
          <div>
            <p className="font-display font-extrabold text-xl tracking-tight">Earn2Love</p>
            <p className="text-xs text-white/50 tracking-wide">Admin Console</p>
          </div>
        </div>
        <div className="relative">
          <h2 className="font-display text-4xl font-extrabold leading-tight tracking-tight">
            Communicate.<br />Connect. <span className="text-gradient-brand">Collect.</span>
          </h2>
          <p className="text-white/50 mt-4 max-w-sm text-sm leading-relaxed">
            The operational control center for the Earn2Love platform — moderation, payments,
            verification, wallets and analytics across the UK &amp; India.
          </p>
        </div>
        <div className="relative flex items-center gap-2 text-xs text-white/40">
          <ShieldCheck className="h-4 w-4" /> Role-based access · Audit logged · 18+ platform
        </div>
      </div>

      {/* Right form */}
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-sm animate-fade-up">
          <div className="lg:hidden flex items-center gap-2.5 mb-8">
            <div className="grid place-items-center h-10 w-10 rounded-xl gradient-brand">
              <Heart className="h-5 w-5 text-white" fill="currentColor" />
            </div>
            <p className="font-display font-extrabold text-lg">Earn2Love Admin</p>
          </div>

          <h1 className="font-display text-2xl font-bold tracking-tight">
            {mode === "login" ? "Welcome back" : "Reset password"}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            {mode === "login" ? "Sign in to the admin console" : "Enter your admin email to receive a reset link"}
          </p>

          <form onSubmit={submit} className="mt-7 space-y-4" data-testid="login-form">
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input id="email" data-testid="login-email" type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)} placeholder="you@earn2love.com" className="h-11 bg-card" />
            </div>
            {mode === "login" && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <button type="button" onClick={() => setMode("forgot")} data-testid="forgot-link"
                    className="text-xs text-primary hover:underline">Forgot password?</button>
                </div>
                <Input id="password" data-testid="login-password" type="password" required value={password}
                  onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" className="h-11 bg-card" />
              </div>
            )}

            {error && (
              <p data-testid="login-error" className="text-sm text-rose-500 bg-rose-500/10 border border-rose-500/20 rounded-md px-3 py-2">
                {error}
              </p>
            )}

            <Button type="submit" data-testid="login-submit" disabled={busy}
              className="w-full h-11 gradient-brand text-white font-semibold hover:opacity-90 border-0">
              {busy && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {mode === "login" ? "Sign in" : "Send reset link"}
            </Button>

            {mode === "forgot" && (
              <button type="button" onClick={() => setMode("login")} className="w-full text-xs text-muted-foreground hover:text-foreground">
                Back to sign in
              </button>
            )}
          </form>

          {mode === "login" && (
            <button onClick={quickFill} data-testid="demo-fill"
              className="mt-6 w-full text-xs text-muted-foreground border border-dashed border-border rounded-md py-2.5 hover:border-primary/40 hover:text-foreground transition-colors">
              Demo Owner login → <span className="font-mono">ram@earn2love.com / Owner@2026</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
