import { NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useWebSocket } from "../context/WebSocketContext"
import "./Navbar.css";

interface LinkProps {
  to: string;
  label: JSX.Element;
}

const Link = ({ to, children }: LinkProps) => (
  <NavLink to={to} end className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}>
    {children}
  </NavLink>
)

const WebSocketState = () => {
  const { status } = useWebSocket();

  return <span className={`ws-indicator ${status}`}>
    ● WS
    {status === "disconnected" && " Reconnecting"}
    {status === "error" && " Failed"}
  </span>
}

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  return (
    <nav className="navbar">
      <div className="nav-left">
        <Link to="/bookings">Bookings</Link>
        <Link to="/bookings/new">Create Booking</Link>
        {user?.role === "admin" && (
          <Link to="/admin">Admin</Link>
        )}
      </div>

      <div className="nav-right">
        {user && (
          <>
            <span className="user-info">
              {user.username} ({user.role})
            </span>
            <button className="button button-secondary" onClick={handleLogout}>Logout</button>
            <WebSocketState />
          </>
        )}
      </div>
    </nav>
  );
}
