import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Heart } from "lucide-react";

export function ProtectedRoute({ children }) {
  const { admin, ready } = useAuth();
  if (!ready) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <Heart className="h-8 w-8 animate-pulse text-pink-500" fill="currentColor" />
          <p className="text-sm text-muted-foreground">Loading Earn2Love Admin…</p>
        </div>
      </div>
    );
  }
  if (!admin) return <Navigate to="/login" replace />;
  return children;
}
