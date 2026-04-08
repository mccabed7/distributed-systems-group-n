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
          <label>Origin</label>
          <input
            className="input"
            value={request.origin}
            onChange={(e) => setRequest(previous => ({ ...previous, origin: e.target.value}))}
            placeholder="Enter origin"
          />
        </div>

        <div className="form-group">
          <label>Destination</label>
          <input
            className="input"
            value={request.destination}
            onChange={(e) => setRequest(previous => ({ ...previous, destination: e.target.value}))}
            placeholder="Enter destination"
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
            value={request.date}
            onChange={(e) => setRequest(previous => ({ ...previous, date: e.target.value}))}
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
