import { useWebSocket } from "../context/WebSocketContext";
import "./NotificationsPanel.css";

export default function NotificationsPanel() {
  const { notifications } = useWebSocket();

  return (
    <div className="notifications-panel">
      {notifications.slice(-5).map((n, i) => (
        <div key={i} className="notification">
          {n.content}
        </div>
      ))}
    </div>
  );
}
