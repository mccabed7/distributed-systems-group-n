import React, { useEffect, useState } from "react";
import { useAdminApi } from "../api/admin";
import type { Booking } from "../types";
import BookingsList from "../components/BookingsList";
import "./AdminPage.css";

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
    <div className="admin-page">
      <h2>Admin Bookings</h2>

      <div className="card query-card">
        <div className="query-row">
          <input
            className="input"
            placeholder="Registration"
            value={registration}
            onChange={e => setRegistration(e.target.value)}
            onKeyDown={e => {
              if (e.key !== "Enter") {
                return;
              }
		      handleBookingQuery();
            }}
          />

          <button
            className="button button-primary"
            onClick={handleBookingQuery}
            disabled={loading || !registration}
          >
            {loading ? "Loading..." : "Query"}
          </button>
        </div>
      </div>

      <BookingsList
        bookings={bookings}
        loading={loading}
        onCancel={handleCancel}
      />
    </div>
  );
}
