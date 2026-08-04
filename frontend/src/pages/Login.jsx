import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, ShieldCheck } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { auth } from "@/lib/firebase";
import { sendPasswordResetEmail } from "firebase/auth";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { homeForRole } from "@/lib/portal";

export default function Login() {
  const { loginEmail, loginGoogle, admin } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [mode, setMode] = useState("login"); // login | forgot

  // Redirect only once AuthContext has committed the admin (avoids race with onAuthStateChanged).
  useEffect(() => {
    if (admin) navigate(homeForRole(admin.role), { replace: true });
  }, [admin, navigate]);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    if (mode === "forgot") {
      try {
        await sendPasswordResetEmail(auth, email);
        toast.success("Password reset email sent (if the account exists).");
        setMode("login");
      } catch (err) {
        setError(err.message || "Could not send reset email");
      }
      setBusy(false);
      return;
    }
    const res = await loginEmail(email, password);
    setBusy(false);
    if (!res.ok) setError(res.error);
  };

  const googleLogin = async () => {
    setError("");
    setBusy(true);
    const res = await loginGoogle();
    setBusy(false);
    if (!res.ok) setError(res.error);
  };

  return (
    <div className="min-h-screen w-full flex bg-background">
      {/* Left brand panel */}
      <div className="hidden lg:flex flex-col justify-between w-[46%] p-12 relative overflow-hidden bg-sidebar text-white">
        <div className="absolute -top-24 -right-24 h-96 w-96 rounded-full gradient-brand opacity-30 blur-3xl" />
        <div className="absolute bottom-0 -left-20 h-80 w-80 rounded-full bg-pink-600 opacity-20 blur-3xl" />
        <div className="relative flex items-center gap-3">
          <div className="grid place-items-center h-11 w-11 rounded-xl overflow-hidden bg-white/95 ring-1 ring-white/10">
            <img src="/earn2love-logo.png" alt="Earn2Love" className="h-full w-full object-cover" />
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
            <div className="grid place-items-center h-10 w-10 rounded-xl overflow-hidden bg-white/95 ring-1 ring-black/5">
              <img src="/earn2love-logo.png" alt="Earn2Love" className="h-full w-full object-cover" />
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

            {mode === "login" && (
              <>
                <div className="flex items-center gap-3 py-1">
                  <div className="h-px flex-1 bg-border" />
                  <span className="text-[11px] text-muted-foreground uppercase tracking-wide">or</span>
                  <div className="h-px flex-1 bg-border" />
                </div>
                <Button type="button" data-testid="login-google" onClick={googleLogin} disabled={busy}
                  variant="outline" className="w-full h-11 gap-2 font-medium">
                  <svg className="h-4 w-4" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z"/><path fill="#FBBC05" d="M5.84 14.1a6.6 6.6 0 0 1 0-4.2V7.06H2.18a11 11 0 0 0 0 9.88l3.66-2.84z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"/></svg>
                  Continue with Google
                </Button>
              </>
            )}

            {mode === "forgot" && (
              <button type="button" onClick={() => setMode("login")} className="w-full text-xs text-muted-foreground hover:text-foreground">
                Back to sign in
              </button>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}
