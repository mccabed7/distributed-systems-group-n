import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useBookingsApi } from "../api/bookings";
import type { Location } from "../types"

export default function CreateBookingPage() {
  const [request, setRequest] = useState<BookingRequest>({});
  const [loading, setLoading] = useState(false);
  const [idempotencyKey] = useState(() => crypto.randomUUID());

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
    <form onSubmit={handleSubmit}>
      <h2>Create Booking</h2>

      <input
        placeholder="Origin"
        value={request.origin}
        onChange={(e) => setRequest(previous => ({ ...previous, origin: e.target.value}))}
      />

      <input
        placeholder="Destination"
        value={request.destination}
        onChange={(e) => setRequest(previous => ({ ...previous, destination: e.target.value}))}
      />

      <input
        type="date"
        value={request.date}
        onChange={(e) => setRequest(previous => ({ ...previous, date: e.target.value}))}
      />

      <button type="submit" disabled={loading}>
        {loading ? "Creating..." : "Create Booking"}
      </button>
    </form>
  );
}
