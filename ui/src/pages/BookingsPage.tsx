import { useEffect, useState } from "react";
import { useBookingsApi } from "../api/bookings";
import type { Booking } from "../types";

export default function BookingsPage() {
  const { getBookings, cancelBooking } = useBookingsApi();
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getBookings().then(setBookings).finally(() => setLoading(false));
  }, []);

  const handleCancel = async (id: string) => {
    await cancelBooking(id);

    setBookings((prev) =>
      prev.map((b) =>
        b.id === id ? { ...b, status: "cancelled" } : b
      )
    );
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div>
      <h2>My Bookings</h2>

      {bookings.map((b) => (
        <div key={b.id}>
          [{b.date}] {b.origin} to {b.destination} ({b.status})

          {b.status !== "cancelled" && (
            <button onClick={() => handleCancel(b.id)}>
              Cancel
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
