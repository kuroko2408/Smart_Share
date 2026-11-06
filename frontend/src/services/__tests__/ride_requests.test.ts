/**
 * Unit tests for Ride Requests API service.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { apiClient } from '@/services/api-client';
import {
  cancelRideRequest,
  createRideRequest,
  fetchRideRequestById,
  fetchUserRideRequests,
  updateRideRequest,
} from '@/services/ride-requests';
import type {
  PaginatedRideRequestsResponse,
  RideRequestCreate,
  RideRequestResponse,
  SingleRideRequestResponse,
} from '@/types/ride-request';

const mockSampleRequest: RideRequestResponse = {
  id: '00000000-0000-0000-0000-000000000001',
  user_id: '11111111-1111-1111-1111-111111111111',
  pickup: {
    latitude: 19.0657,
    longitude: 72.8687,
    label: 'Bandra Kurla Complex',
  },
  destination: {
    latitude: 19.0886,
    longitude: 72.8679,
    label: 'Mumbai Airport T2',
  },
  departure_earliest: '2026-11-07T10:00:00Z',
  departure_latest: '2026-11-07T10:30:00Z',
  seats_requested: 2,
  max_extra_minutes: 20,
  status: 'ACTIVE',
  expires_at: '2026-11-07T10:30:00Z',
  created_at: '2026-11-06T12:00:00Z',
  updated_at: '2026-11-06T12:00:00Z',
};

describe('Ride Requests Service', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('createRideRequest posts payload to /ride-requests', async () => {
    const payload: RideRequestCreate = {
      pickup: { latitude: 19.0657, longitude: 72.8687, label: 'BKC' },
      destination: { latitude: 19.0886, longitude: 72.8679, label: 'Airport' },
      departure_earliest: '2026-11-07T10:00:00Z',
      departure_latest: '2026-11-07T10:30:00Z',
      seats_requested: 1,
      max_extra_minutes: 15,
    };

    const mockResponse: SingleRideRequestResponse = {
      data: mockSampleRequest,
      message: 'Ride request created successfully',
    };

    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValue(mockResponse);

    const result = await createRideRequest(payload);
    expect(postSpy).toHaveBeenCalledWith('/ride-requests', payload);
    expect(result.data.id).toBe(mockSampleRequest.id);
  });

  it('fetchUserRideRequests queries /ride-requests with optional params', async () => {
    const mockListResponse: PaginatedRideRequestsResponse = {
      data: [mockSampleRequest],
      pagination: { total: 1, limit: 20, offset: 0, has_more: false },
      message: 'Ride requests retrieved successfully',
    };

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(mockListResponse);

    const result = await fetchUserRideRequests({ status: 'ACTIVE', limit: 10, offset: 0 });
    expect(getSpy).toHaveBeenCalledWith('/ride-requests?status=ACTIVE&limit=10&offset=0');
    expect(result.data).toHaveLength(1);
    expect(result.pagination.total).toBe(1);
  });

  it('fetchRideRequestById retrieves single request', async () => {
    const mockResponse: SingleRideRequestResponse = {
      data: mockSampleRequest,
      message: 'Ride request retrieved successfully',
    };

    const getSpy = vi.spyOn(apiClient, 'get').mockResolvedValue(mockResponse);

    const result = await fetchRideRequestById(mockSampleRequest.id);
    expect(getSpy).toHaveBeenCalledWith(`/ride-requests/${mockSampleRequest.id}`);
    expect(result.data.status).toBe('ACTIVE');
  });

  it('updateRideRequest patches /ride-requests/{id}', async () => {
    const updated = { ...mockSampleRequest, seats_requested: 3 };
    const mockResponse: SingleRideRequestResponse = {
      data: updated,
      message: 'Ride request updated successfully',
    };

    const patchSpy = vi.spyOn(apiClient, 'patch').mockResolvedValue(mockResponse);

    const result = await updateRideRequest(mockSampleRequest.id, { seats_requested: 3 });
    expect(patchSpy).toHaveBeenCalledWith(`/ride-requests/${mockSampleRequest.id}`, {
      seats_requested: 3,
    });
    expect(result.data.seats_requested).toBe(3);
  });

  it('cancelRideRequest posts to /ride-requests/{id}/cancel', async () => {
    const cancelled = { ...mockSampleRequest, status: 'CANCELLED' as const };
    const mockResponse: SingleRideRequestResponse = {
      data: cancelled,
      message: 'Ride request cancelled successfully',
    };

    const postSpy = vi.spyOn(apiClient, 'post').mockResolvedValue(mockResponse);

    const result = await cancelRideRequest(mockSampleRequest.id);
    expect(postSpy).toHaveBeenCalledWith(`/ride-requests/${mockSampleRequest.id}/cancel`);
    expect(result.data.status).toBe('CANCELLED');
  });
});
