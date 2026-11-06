/**
 * TypeScript type definitions for Ride Requests.
 * Matches backend Pydantic schemas in app/schemas/ride_request.py.
 */

export type RideRequestStatus =
  | 'ACTIVE'
  | 'MATCHED'
  | 'CANCELLED'
  | 'EXPIRED'
  | 'COMPLETED';

export interface LocationPoint {
  latitude: number;
  longitude: number;
  label?: string | null;
}

export interface RideRequestCreate {
  pickup: LocationPoint;
  destination: LocationPoint;
  departure_earliest: string; // ISO 8601 UTC
  departure_latest: string; // ISO 8601 UTC
  seats_requested?: number; // 1 to 6 (default 1)
  max_extra_minutes?: number; // 0 to 180 (default 15)
}

export interface RideRequestUpdate {
  pickup?: LocationPoint;
  destination?: LocationPoint;
  departure_earliest?: string;
  departure_latest?: string;
  seats_requested?: number;
  max_extra_minutes?: number;
}

export interface RideRequestResponse {
  id: string;
  user_id: string;
  pickup: LocationPoint;
  destination: LocationPoint;
  departure_earliest: string;
  departure_latest: string;
  seats_requested: number;
  max_extra_minutes: number;
  status: RideRequestStatus;
  expires_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface PaginationMeta {
  total: number;
  limit: number;
  offset: number;
  has_more: boolean;
}

export interface PaginatedRideRequestsResponse {
  data: RideRequestResponse[];
  pagination: PaginationMeta;
  message: string;
}

export interface SingleRideRequestResponse {
  data: RideRequestResponse;
  message: string;
}
