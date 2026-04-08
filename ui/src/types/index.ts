export type Role = "user" | "admin"

export interface User {
	id: string;
	username: string;
	role: Role;
	token: string;
}

export type Location = string;

export type BookingStatus = "SUCCESSFUL" | "CANCELLED" | "PENDING" | "FAILED";

export interface BookingRequest {
  start_location: Location;
  end_location: Location;
  booking_date: string;
}

export interface Booking extends BookingRequest {
  id: string;
  status: BookingStatus;
};

export interface Notification {
  message_id: string;
  content: string;
}

export interface CreateRegistrationRequest {
  user_id: string;
  registration_id: string;
}
