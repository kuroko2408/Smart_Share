/**
 * Component tests for Ride Requests: Form, Card, and List.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { RideRequestCard } from '@/features/ride-requests/RideRequestCard';
import { RideRequestForm } from '@/features/ride-requests/RideRequestForm';
import { RideRequestList } from '@/features/ride-requests/RideRequestList';
import { MatchResults } from '@/features/ride-requests/MatchResults';
import * as rideRequestService from '@/services/ride-requests';
import type { RideRequestResponse } from '@/types/ride-request';

const mockRequest: RideRequestResponse = {
  id: '00000000-0000-0000-0000-000000000001',
  user_id: '11111111-1111-1111-1111-111111111111',
  pickup: {
    latitude: 19.0657,
    longitude: 72.8687,
    label: 'Bandra Kurla Complex (BKC)',
  },
  destination: {
    latitude: 19.0886,
    longitude: 72.8679,
    label: 'Mumbai Airport (T2 CSMIA)',
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

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('Ride Request UI Components', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('RideRequestForm', () => {
    it('renders all input fields and presets', () => {
      renderWithClient(<RideRequestForm />);

      expect(screen.getByText(/Pickup Location/i)).toBeInTheDocument();
      expect(screen.getByText(/Destination/i)).toBeInTheDocument();
      expect(screen.getByText(/Departure Window/i)).toBeInTheDocument();
      expect(screen.getByText(/Seats Required/i)).toBeInTheDocument();
      expect(screen.getByText(/Max Detour Time/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Publish Ride Request/i })).toBeInTheDocument();
    });

    it('validates identical endpoints before submitting', async () => {
      renderWithClient(<RideRequestForm />);

      // Set pickup and destination coordinates to identical values
      const latInputs = screen.getAllByPlaceholderText(/19\./i);
      const lonInputs = screen.getAllByPlaceholderText(/72\./i);

      fireEvent.change(latInputs[0], { target: { value: '19.0500' } });
      fireEvent.change(lonInputs[0], { target: { value: '72.8500' } });

      fireEvent.change(latInputs[1], { target: { value: '19.0500' } });
      fireEvent.change(lonInputs[1], { target: { value: '72.8500' } });

      const submitBtn = screen.getByRole('button', { name: /Publish Ride Request/i });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(
          screen.getByText(/Pickup and Destination coordinates cannot be identical/i)
        ).toBeInTheDocument();
      });
    });

    it('submits valid payload and triggers onSuccess', async () => {
      const onSuccessSpy = vi.fn();
      vi.spyOn(rideRequestService, 'createRideRequest').mockResolvedValue({
        data: mockRequest,
        message: 'Created',
      });

      renderWithClient(<RideRequestForm onSuccess={onSuccessSpy} />);

      const submitBtn = screen.getByRole('button', { name: /Publish Ride Request/i });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(onSuccessSpy).toHaveBeenCalledWith(mockRequest.id);
      });
    });
  });

  describe('RideRequestCard', () => {
    it('displays route, status, departure window, and action buttons', () => {
      const onViewDetails = vi.fn();
      const onEdit = vi.fn();
      const onCancel = vi.fn();

      render(
        <RideRequestCard
          request={mockRequest}
          onViewDetails={onViewDetails}
          onEdit={onEdit}
          onCancel={onCancel}
          onFindMatches={vi.fn()}
        />
      );

      expect(screen.getByText(/Bandra Kurla Complex/i)).toBeInTheDocument();
      expect(screen.getByText(/Mumbai Airport/i)).toBeInTheDocument();
      expect(screen.getByText(/Active/i)).toBeInTheDocument();
      expect(screen.getByText(/2 seats/i)).toBeInTheDocument();

      // Action clicks
      const detailsBtn = screen.getByRole('button', { name: /Details/i });
      fireEvent.click(detailsBtn);
      expect(onViewDetails).toHaveBeenCalledWith(mockRequest);

      const editBtn = screen.getByRole('button', { name: /Edit/i });
      fireEvent.click(editBtn);
      expect(onEdit).toHaveBeenCalledWith(mockRequest);

      const cancelBtn = screen.getByRole('button', { name: /Cancel/i });
      fireEvent.click(cancelBtn);
      expect(onCancel).toHaveBeenCalledWith(mockRequest);
    });

    it('hides edit button for CANCELLED request', () => {
      const cancelled = { ...mockRequest, status: 'CANCELLED' as const };
      render(
        <RideRequestCard
          request={cancelled}
          onViewDetails={vi.fn()}
          onEdit={vi.fn()}
          onCancel={vi.fn()}
          onFindMatches={vi.fn()}
        />
      );

      expect(screen.queryByRole('button', { name: /Edit/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /Cancel/i })).not.toBeInTheDocument();
      expect(screen.getByText(/Cancelled/i)).toBeInTheDocument();
    });
  });

  describe('RideRequestList', () => {
    it('renders empty state when no requests are found', async () => {
      vi.spyOn(rideRequestService, 'fetchUserRideRequests').mockResolvedValue({
        data: [],
        pagination: { total: 0, limit: 50, offset: 0, has_more: false },
        message: 'Empty',
      });

      renderWithClient(<RideRequestList />);

      await waitFor(() => {
        expect(screen.getByText(/No ride requests found/i)).toBeInTheDocument();
      });
    });

    it('renders cards when requests exist and opens modals', async () => {
      vi.spyOn(rideRequestService, 'fetchUserRideRequests').mockResolvedValue({
        data: [mockRequest],
        pagination: { total: 1, limit: 50, offset: 0, has_more: false },
        message: 'Success',
      });

      renderWithClient(<RideRequestList />);

      await waitFor(() => {
        expect(screen.getByText(/Bandra Kurla Complex/i)).toBeInTheDocument();
      });

      // Test opening details modal
      const detailsBtn = screen.getByRole('button', { name: /Details/i });
      fireEvent.click(detailsBtn);

      await waitFor(() => {
        expect(screen.getByText(/Ride Request Details/i)).toBeInTheDocument();
      });

      // Close details modal
      const closeBtn = screen.getByRole('button', { name: /Close Details/i });
      fireEvent.click(closeBtn);

      await waitFor(() => {
        expect(screen.queryByText(/Ride Request Details/i)).not.toBeInTheDocument();
      });
    });
  });

  describe('MatchResults', () => {
    it('starts discovery, shows ranked results, route accuracy, and match explanation', async () => {
      vi.spyOn(rideRequestService, 'findRideMatches').mockResolvedValue({
        target_request_id: mockRequest.id,
        total_candidates_found: 1,
        proposals: [{
          proposal_id: 'proposal-1',
          target_request_id: mockRequest.id,
          candidate: {
            candidate_request_id: 'candidate-1',
            candidate_display_name: 'Rider',
            candidate_pickup: { latitude: 19.066, longitude: 72.869, label: 'Nearby' },
            candidate_destination: { latitude: 19.09, longitude: 72.87, label: 'Airport' },
            seats_requested: 1,
            pickup_distance_meters: 200,
            destination_distance_meters: 300,
            shared_departure_window_start: mockRequest.departure_earliest,
            shared_departure_window_end: mockRequest.departure_latest,
            estimated_detour_minutes_target: 4,
            estimated_detour_minutes_candidate: 2,
            scores: { pickup_proximity_score: .9, destination_similarity_score: .8, departure_time_score: 1, route_detour_score: .7, composite_score: .85 },
          },
          ordered_stops: [
            { sequence: 1, stop_type: 'PICKUP', location: mockRequest.pickup, passenger_request_id: mockRequest.id },
            { sequence: 2, stop_type: 'DROPOFF', location: mockRequest.destination, passenger_request_id: mockRequest.id },
          ],
          total_shared_distance_km: 8,
          total_shared_duration_minutes: 30,
          best_sequence: 'PA→PB→DA→DB',
          is_route_approximate: true,
          distance_is_approximate: true,
          routing_accuracy: 'geographic_approximation',
          routing_notice: 'Approximate geographic fallback',
          compatibility_explanations: ['Pickups are nearby.'],
          created_at: mockRequest.created_at,
        }],
      });
      renderWithClient(<MatchResults request={mockRequest} onClose={vi.fn()} />);
      fireEvent.click(screen.getByRole('button', { name: /Find compatible rides/i }));
      expect(await screen.findByText(/85% match/i)).toBeInTheDocument();
      expect(screen.getByText(/Approximate geographic fallback/i)).toBeInTheDocument();
      fireEvent.click(screen.getByRole('button', { name: /Why this suggestion/i }));
      expect(screen.getByText(/departure timing 100%/i)).toBeInTheDocument();
      expect(rideRequestService.findRideMatches).toHaveBeenCalledWith(mockRequest.id);
    });

    it('displays empty state when no compatible proposals are found', async () => {
      vi.spyOn(rideRequestService, 'findRideMatches').mockResolvedValue({
        target_request_id: mockRequest.id,
        total_candidates_found: 0,
        proposals: [],
      });
      renderWithClient(<MatchResults request={mockRequest} onClose={vi.fn()} />);
      fireEvent.click(screen.getByRole('button', { name: /Find compatible rides/i }));
      expect(
        await screen.findByText(/No compatible active requests found/i)
      ).toBeInTheDocument();
    });

    it('displays error state and retry button when matching fails', async () => {
      vi.spyOn(rideRequestService, 'findRideMatches').mockRejectedValue(
        new Error('Network error connecting to matching service')
      );
      renderWithClient(<MatchResults request={mockRequest} onClose={vi.fn()} />);
      fireEvent.click(screen.getByRole('button', { name: /Find compatible rides/i }));
      expect(
        await screen.findByText(/Network error connecting to matching service/i)
      ).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Try again/i })).toBeInTheDocument();
    });
  });
});
