import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

interface LinkProps {
  to: string;
  label: JSX.Element;
}

const Link = ({ to, children }: LinkProps) => (
  <NavLink to={to} style={({ isActive }) => ({
    fontWeight: isActive ? "bold" : "normal",
  })}>
    {children}
  </NavLink>
)

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav style={{ display: "flex", gap: "1rem", padding: "1rem", borderBottom: "1px solid #ccc" }}>
      <Link to="/bookings">Bookings</Link>
      <Link to="/bookings/new">Create Booking</Link>

      {user?.role === "admin" && (
        <Link to="/admin">Admin</Link>
      )}

      <div style={{ marginLeft: "auto" }}>
        {user && (
          <>
            <span style={{ marginRight: "1rem" }}>
              {user.username} ({user.role})
            </span>
            <button onClick={handleLogout}>Logout</button>
          </>
        )}
      </div>
    </nav>
  );
}
