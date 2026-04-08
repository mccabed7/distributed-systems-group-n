import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useBookingsApi } from "../api/bookings";
import type { Location } from "../types"
import "./CreateBookingPage.css";

export default function CreateBookingPage() {
  const [request, setRequest] = useState<BookingRequest>({});
  const [loading, setLoading] = useState(false);
  const [idempotencyKey, setIdempotencyKey] = useState(() => crypto.randomUUID());

  const { createBooking } = useBookingsApi();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) {
	  return;
    }

    setLoading(true);

    try {
      await createBooking(request, idempotencyKey);
      navigate("/bookings");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="create-booking-page">
      <form className="card booking-form" onSubmit={handleSubmit}>
        <h2>Create Booking</h2>
        <div className="form-group">
          <label>Start location</label>
          <input
            className="input"
            value={request.start_location}
            onChange={(e) => setRequest(previous => ({ ...previous, start_location: e.target.value}))}
            placeholder="Enter start location"
          />
        </div>

        <div className="form-group">
          <label>End location</label>
          <input
            className="input"
            value={request.end_location}
            onChange={(e) => setRequest(previous => ({ ...previous, end_location: e.target.value}))}
            placeholder="Enter end location"
          />
        </div>

        <div className="form-group">
          <label>Idempotency key</label>
          <input
            className="input"
            value={idempotencyKey}
            onChange={(e) => setIdempotencyKey(e.target.value)}
          />
        </div>

        <div className="form-group">
          <label>Date</label>
          <input
            className="input"
            type="date"
            value={request.booking_date}
            onChange={(e) => setRequest(previous => ({ ...previous, booking_date: e.target.value}))}
          />
        </div>

        <button
          className="button button-primary"
          type="submit"
          disabled={loading}
        >
          {loading ? "Creating..." : "Create booking"}
        </button>
      </form>
    </div>
  );
}
