import React, { useEffect, useState } from "react";
import { useAdminApi } from "../api/admin";
import type { Booking, CreateRegistrationRequest } from "../types";
import BookingsList from "../components/BookingsList";
import "./AdminPage.css";

export default function AdminPage() {
  const { getBookingsForRegistration, cancelBooking, createRegistration } = useAdminApi();
  const [registration, setRegistration] = useState<string>("");
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(false);
  const [createRegistrationRequest, setCreateRegistrationRequest] = useState<CreateRegistrationRequest>({});
  const [creating, setCreating] = useState(false);

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

  const handleCreateRegistration = async () => {
    if (!createRegistrationRequest.user_id || !createRegistrationRequest.registration_id) {
      return;
    }

    setCreating(true);
    try {
      await createRegistration(createRegistrationRequest);
      setCreateRegistrationRequest({});
    } finally {
      setCreating(false);
    }
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="admin-page">
      <h2>Admin Bookings</h2>
      <div className="card registration-card">
        <h3>Create Registration</h3>

        <div className="form-row">
          <input
            className="input"
            placeholder="User ID"
            value={createRegistrationRequest.user_id}
            onChange={e => setCreateRegistrationRequest(prev => ({ ...prev, user_id: e.target.value}))}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleCreateRegistration();
              }
            }}
          />

          <input
            className="input"
            placeholder="Vehicle Registration"
            value={createRegistrationRequest.registration_id}
            onChange={e => setCreateRegistrationRequest(prev => ({ ...prev, registration_id: e.target.value}))}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleCreateRegistration();
              }
            }}
          />

          <button
            className="button button-primary"
            onClick={handleCreateRegistration}
            disabled={creating}
          >
            {creating ? "Creating..." : "Add"}
          </button>
        </div>
      </div>

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
