import { createContext, useContext, useEffect, useState } from "react";
import {
  onAuthStateChanged, signInWithEmailAndPassword, signInWithPopup, signOut,
} from "firebase/auth";
import { auth, googleProvider } from "@/lib/firebase";
import api, { formatApiError } from "@/lib/api";

const AuthContext = createContext(null);

function initialsOf(name, email) {
  const base = name || email || "A";
  return base.split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();
}

export function AuthProvider({ children }) {
  const [admin, setAdmin] = useState(null); // null = checking, false = not admin
  const [ready, setReady] = useState(false);
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    const unsub = onAuthStateChanged(auth, async (user) => {
      if (!user) {
        setAdmin(false); setReady(true); return;
      }
      try {
        await user.getIdToken(true); // refresh to pick up latest claims
        const { data } = await api.get("/auth/me");
        setAdmin({ ...data, initials: initialsOf(data.name, data.email) });
        setAuthError("");
      } catch (e) {
        // Signed in to Firebase but not an admin (no role claim) or token invalid
        setAuthError(formatApiError(e.response?.data?.detail) || "Access denied");
        await signOut(auth).catch(() => {});
        setAdmin(false);
      } finally {
        setReady(true);
      }
    });
    return unsub;
  }, []);

  const loginEmail = async (email, password) => {
    setAuthError("");
    try {
      await signInWithEmailAndPassword(auth, email, password);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e.code === "auth/invalid-credential" ? "Invalid email or password" : (e.message || "Login failed") };
    }
  };

  const loginGoogle = async () => {
    setAuthError("");
    try {
      await signInWithPopup(auth, googleProvider);
      return { ok: true };
    } catch (e) {
      return { ok: false, error: e.message || "Google sign-in failed" };
    }
  };

  const logout = async () => {
    await signOut(auth).catch(() => {});
    setAdmin(false);
  };

  const can = (module) => {
    if (!admin || !admin.permissions) return false;
    if (admin.permissions === "*") return true;
    return admin.permissions.includes(module);
  };

  return (
    <AuthContext.Provider value={{ admin, ready, authError, loginEmail, loginGoogle, logout, can }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
