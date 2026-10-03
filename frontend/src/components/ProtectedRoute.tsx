import { Navigate, useLocation } from "react-router-dom";
import { useSession } from "../auth/SessionContext";

export default function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useSession();
  const location = useLocation();
  if (loading) return <div className="page-state">Checking your session…</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}
