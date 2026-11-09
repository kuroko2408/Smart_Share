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
import type { MatchListResponse, MatchProposal } from '@/types/matching';

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

export async function findRideMatches(requestId: string): Promise<MatchListResponse> {
  const response = await apiClient.post<{ data: MatchListResponse }>(`/ride-requests/${requestId}/matches`);
  return response.data;
}

export async function fetchRideMatches(requestId: string): Promise<MatchListResponse> {
  const response = await apiClient.get<{ data: MatchListResponse }>(`/ride-requests/${requestId}/matches`);
  return response.data;
}

export async function fetchMatchProposal(
  requestId: string,
  proposalId: string
): Promise<MatchProposal> {
  const response = await apiClient.get<{ data: MatchProposal }>(
    `/matches/${proposalId}?request_id=${encodeURIComponent(requestId)}`
  );
  return response.data;
}

export async function fetchFareDisclosureConsent(
  requestId: string,
  proposalId: string
) {
  const response = await apiClient.get<{ data: MatchProposal['fare_allocation_disclosure'] }>(
    `/matches/${proposalId}/disclosure-consent?request_id=${encodeURIComponent(requestId)}`
  );
  return response.data;
}

export async function grantFareDisclosureConsent(
  requestId: string,
  proposalId: string,
  consentTextVersion: string
) {
  const response = await apiClient.post<{ data: MatchProposal['fare_allocation_disclosure'] }>(
    `/matches/${proposalId}/disclosure-consent?request_id=${encodeURIComponent(requestId)}`,
    { consent_text_version: consentTextVersion, disclosure_mode: 'EXACT' }
  );
  return response.data;
}

export async function withdrawFareDisclosureConsent(requestId: string, proposalId: string) {
  const response = await apiClient.delete<{ data: MatchProposal['fare_allocation_disclosure'] }>(
    `/matches/${proposalId}/disclosure-consent?request_id=${encodeURIComponent(requestId)}`
  );
  return response.data;
}
