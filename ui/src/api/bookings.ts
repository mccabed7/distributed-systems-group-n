import type { Booking, BookingRequest } from "../types";
import { useApiClient } from "./client";

interface BookingsApi {
  createBooking: (data: BookingRequest, idempotencyKey: string): Promise<Booking>;
  getBookings(): () => Promise<Booking[]>;
  cancelBooking: (id: string): Promise<void>;
}

export function useBookingsApi(): BookingsApi {
  const { request } = useApiClient();

  return {
    createBooking: (data: BookingRequest, idempotencyKey: string) =>
      request("/bookings", {
        method: "POST",
        headers: {
          "X-Request-Id": idempotencyKey,
        },
        body: JSON.stringify(data),
      }),

    getBookings: () => request("/bookings"),

    cancelBooking: id => request(`/bookings/${id}/cancel`, {
      method: "POST",
    }),
  };
}
