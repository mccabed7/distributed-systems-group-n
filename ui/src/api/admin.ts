import type { Booking, CreateRegistrationRequest } from "../types";
import { useApiClient } from "./client";

interface AdminApi {
  getBookingsForRegistration: (registration: string) => Promise<Booking[]>;
  cancelBooking: (id: string) => Promise<void>;
  createRegistration(request: CreateRegistrationRequest): Promise<void>;
}

export function useAdminApi(): AdminApi {
  const { request } = useApiClient();

  return {
    getBookingsForRegistration: registration => request(`/admin/bookings/${registration}`),

    cancelBooking: (id: string) =>
      // Technically we should use a proper /admin endpoint for this, however since we don't have authorization set up,
      // anybody can be an "admin", so there is no benefit in separating them. Obviously in a real system we would not
      // do this, but for this demo it's ~fine.
      request(`/bookings/${id}/cancel`, {
        method: "POST",
      }),

    createRegistration: body => request(
      "/admin/registrations",
      {
        method: "POST",
        body: JSON.stringify(body),
      },
    ),
  };
}
