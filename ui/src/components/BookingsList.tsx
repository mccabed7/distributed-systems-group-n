import type { Booking } from "../types";
import "./BookingsList.css";

interface Props {
  bookings: Booking[];
  onCancel: (id: string) => Promise<void>;
  loading?: boolean;
}

export default function BookingList({
  bookings,
  onCancel,
  loading = false,
}: Props) {
  if (loading) {
    return <div>Loading...</div>;
  }

  if (bookings.length === 0) {
    return <div className="card empty-state">No bookings found.</div>;
  }

  return (
    <div className="bookings-list">
      {bookings.map((b) => (
        <div key={b.id} className="card booking-item">
          <div className="booking-info">
            <div className="route">
              {b.origin} to {b.destination}
            </div>

            <div className="meta">
              <span>{new Date(b.date).toLocaleDateString()}</span>
              <span className={`status ${b.status}`}>
                {b.status}
              </span>
            </div>
          </div>

          <div className="booking-actions">
            {b.status !== "cancelled" && (
              <button
                className="button button-danger"
                onClick={() => onCancel(b.id)}
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
