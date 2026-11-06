/**
 * API service for passenger ride requests.
 * Interacts with /api/v1/ride-requests endpoints.
 */
import { apiClient } from '@/services/api-client';
import type {
  PaginatedRideRequestsResponse,
  RideRequestCreate,
  RideRequestStatus,
  RideRequestUpdate,
  SingleRideRequestResponse,
} from '@/types/ride-request';

export interface ListRideRequestsParams {
  status?: RideRequestStatus;
  limit?: number;
  offset?: number;
}

/**
 * Create a new passenger ride request.
 */
export async function createRideRequest(
  payload: RideRequestCreate
): Promise<SingleRideRequestResponse> {
  return apiClient.post<SingleRideRequestResponse>('/ride-requests', payload);
}

/**
 * List ride requests belonging to the authenticated user.
 */
export async function fetchUserRideRequests(
  params: ListRideRequestsParams = {}
): Promise<PaginatedRideRequestsResponse> {
  const queryParts: string[] = [];
  if (params.status) {
    queryParts.push(`status=${encodeURIComponent(params.status)}`);
  }
  if (params.limit !== undefined) {
    queryParts.push(`limit=${encodeURIComponent(params.limit)}`);
  }
  if (params.offset !== undefined) {
    queryParts.push(`offset=${encodeURIComponent(params.offset)}`);
  }

  const queryString = queryParts.length > 0 ? `?${queryParts.join('&')}` : '';
  return apiClient.get<PaginatedRideRequestsResponse>(`/ride-requests${queryString}`);
}

/**
 * Retrieve details of a single ride request.
 */
export async function fetchRideRequestById(
  requestId: string
): Promise<SingleRideRequestResponse> {
  return apiClient.get<SingleRideRequestResponse>(`/ride-requests/${requestId}`);
}

/**
 * Update an active ride request.
 */
export async function updateRideRequest(
  requestId: string,
  payload: RideRequestUpdate
): Promise<SingleRideRequestResponse> {
  return apiClient.patch<SingleRideRequestResponse>(`/ride-requests/${requestId}`, payload);
}

/**
 * Cancel an active or matched ride request.
 */
export async function cancelRideRequest(
  requestId: string
): Promise<SingleRideRequestResponse> {
  return apiClient.post<SingleRideRequestResponse>(`/ride-requests/${requestId}/cancel`);
}
