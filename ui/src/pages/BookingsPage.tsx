import { useEffect, useState } from "react";
import { useBookingsApi } from "../api/bookings";
import type { Booking } from "../types";
import BookingsList from "../components/BookingsList";
import "./BookingsPage.css";
import { useWebSocket } from "../context/WebSocketContext";

export default function BookingsPage() {
  const { getBookings, cancelBooking } = useBookingsApi();
  const [bookings, setBookings] = useState<Booking[]>([]);
  const [loading, setLoading] = useState(true);
  const { subscribe } = useWebSocket();

  useEffect(() => {
    getBookings().then(setBookings).finally(() => setLoading(false));

    const unsubscribe = subscribe(msg => {
      setLoading(true);
      getBookings().then(setBookings).finally(() => setLoading(false));
    });

    return unsubscribe;
  }, []);

  const handleCancel = async (id: string) => {
    await cancelBooking(id);

    setBookings((prev) =>
      prev.map((b) =>
        b.id === id ? { ...b, status: "CANCELLED" } : b
      )
    );
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="bookings-page">
      <h2>My Bookings</h2>
      <BookingsList
        bookings={bookings}
        loading={loading}
        onCancel={handleCancel}
      />
    </div>
  );
}
