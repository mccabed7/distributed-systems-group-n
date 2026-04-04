export type Role = "user" | "admin"

export interface User {
	id: string;
	username: string;
	role: Role;
	token: string;
}

export type Location = string;

export type BookingStatus = "successful" | "cancelled";

export interface BookingRequest {
  origin: Location;
  destination: Location;
  date: string;
}

export interface Booking extends BookingRequest {
  id: string;
  status: BookingStatus;
};
