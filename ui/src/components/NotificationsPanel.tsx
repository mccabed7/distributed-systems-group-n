import { useWebSocket } from "../context/WebSocketContext";

export default function NotificationsPanel() {
  const { notifications } = useWebSocket();

  return (
    <div style={{ position: "fixed", bottom: 0, right: 0, width: 300 }}>
      {notifications.slice(-5).map((n, i) => (
        <div key={i} style={{ background: "#eee", margin: 2, padding: 4 }}>
          {n.content}
        </div>
      ))}
    </div>
  );
}
