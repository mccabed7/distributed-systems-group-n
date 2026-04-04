import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

interface Props {
  children: JSX.Element;
  requireAdmin?: boolean;
}

export default function ProtectedRoute({ children, requireAdmin }: Props) {
  const { isAuthenticated, user } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  if (requireAdmin && user?.role !== "admin") {
    return <Navigate to="/bookings" />;
  }

  return children;
}
