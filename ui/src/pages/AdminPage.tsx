import React, { useEffect, useState } from "react";
import { useAdminApi } from "../api/admin";
import type { Booking } from "../types";

export default function AdminPage() {
  const { getBookingsForRegistration, cancelBooking } = useAdminApi();
  const [registration, setRegistration] = useState<string>("");
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(false);

  const handleBookingQuery = async (e: React.FormEvent) => {
    if (!registration) {
	  setBookings([]);
	  return;
    }

    setLoading(true);
    getBookingsForRegistration(registration)
      .then(setBookings)
      .finally(() => setLoading(false));
  };

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
      <h2>All Bookings (Admin)</h2>

      <input
        placeholder="Registration"
        value={registration}
        onChange={e => setRegistration(e.target.value)}
      />

      <button type="submit" disabled={loading} onClick={handleBookingQuery}>
        {loading ? "Loading..." : "Query"}
      </button>

      {bookings.map((b) => (
        <div key={b.id}>
          User: {b.userId} | {b.origin} to {b.destination} ({b.status})

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
