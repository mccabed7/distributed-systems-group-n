import { Routes, Route, Navigate, useLocation } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import BookingsPage from "./pages/BookingsPage";
import CreateBookingPage from "./pages/CreateBookingPage";
import AdminPage from "./pages/AdminPage";
import ProtectedRoute from "./components/ProtectedRoute";
import Navbar from "./components/Navbar";
import { useAuth } from "./context/AuthContext";
import NotificationsPanel from "./components/NotificationsPanel"
import "./App.css";

export default function App() {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  const showNavbar = isAuthenticated && location.pathname !== "/login";

  return (
    <div className="app-container">
      {showNavbar && <Navbar />}
      <div className="page-container">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/bookings"
            element={
              <ProtectedRoute>
                <BookingsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/bookings/new"
            element={
              <ProtectedRoute>
                <CreateBookingPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute requireAdmin>
                <AdminPage />
              </ProtectedRoute>
            }
          />
          <Route path="*" element={<Navigate to="/login" />} />
        </Routes>
      </div>
      <NotificationsPanel />
    </div>
  );
}
