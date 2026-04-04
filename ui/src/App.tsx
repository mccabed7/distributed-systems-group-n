import { Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import BookingsPage from "./pages/BookingsPage";
import CreateBookingPage from "./pages/CreateBookingPage";
import AdminPage from "./pages/AdminPage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/bookings" element={<BookingsPage />} />
      <Route path="/bookings/new" element={<CreateBookingPage />} />
      <Route path="/admin" element={<AdminPage />} />
      <Route path="*" element={<Navigate to="/login" />} />
    </Routes>
  );
}
