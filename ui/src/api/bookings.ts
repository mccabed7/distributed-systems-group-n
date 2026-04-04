import type { Booking, BookingRequest } from "../types";
import { useApiClient } from "./client";

export function useBookingsApi() {
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
  };
}
