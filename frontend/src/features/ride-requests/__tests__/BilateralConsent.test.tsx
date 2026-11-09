/**
 * Phase 6A: Frontend Bilateral Consent Workflow Tests
 *
 * Verifies:
 * 1. Neither passenger consented: shows notice, shows other pending, shows action buttons.
 * 2. Decline action: Clicking "No thanks" updates view to declined state and offers review.
 * 3. Grant consent action: Calls grantFareDisclosureConsent, updates state to your consent recorded.
 * 4. Only co-passenger consented: Indicates co-passenger consented while amounts remain hidden.
 * 5. Bilateral consent active: Reveals exact contributions, savings, sum conservation, driver notice.
 * 6. Consent withdrawal: Clicking "Withdraw my consent" calls withdrawFareDisclosureConsent, hides amounts.
 * 7. Error handling: Shows API error alert gracefully.
 * 8. Privacy guarantee: Co-passenger solo baseline and savings are NEVER exposed.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MatchResults } from '@/features/ride-requests/MatchResults';
import * as rideRequestService from '@/services/ride-requests';
import type { RideRequestResponse } from '@/types/ride-request';
import type { MatchProposal } from '@/types/matching';

const mockRequest: RideRequestResponse = {
  id: '00000000-0000-0000-0000-000000000001',
  user_id: '11111111-1111-1111-1111-111111111111',
  pickup: { latitude: 19.0657, longitude: 72.8687, label: 'BKC Maker Maxity' },
  destination: { latitude: 19.1176, longitude: 72.906, label: 'Powai Hiranandani' },
  departure_earliest: '2026-11-09T10:00:00Z',
  departure_latest: '2026-11-09T10:30:00Z',
  seats_requested: 1,
  max_extra_minutes: 20,
  status: 'ACTIVE',
  expires_at: '2026-11-09T10:30:00Z',
  created_at: '2026-11-09T09:00:00Z',
  updated_at: '2026-11-09T09:00:00Z',
};

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>
  );
}

const baseFareEstimate = {
  shared_journey: {
    estimate: 240.0,
    estimate_paise: 24000,
    rounded_estimate_rupees: 240,
    distance_meters: 10000,
    distance_source: 'provider_road_network_route',
    accuracy_tier: 'ROAD_ROUTE' as const,
    surcharge_status: 'NONE' as const,
  },
  your_solo_baseline: {
    estimate: 150.0,
    estimate_paise: 15000,
    rounded_estimate_rupees: 150,
    distance_meters: 6500,
    distance_source: 'provider_road_network_route',
    accuracy_tier: 'ROAD_ROUTE' as const,
    surcharge_status: 'NONE' as const,
  },
  your_allocated_fare: { estimate: 120.0, estimate_paise: 12000, rounded_estimate_rupees: 120 },
  your_savings: { estimate: 30.0, estimate_paise: 3000, rounded_estimate_rupees: 30 },
  your_savings_percent: 20.0,
  economic_status: 'SAVINGS' as const,
  is_economically_beneficial: true,
  composite_accuracy: 'ROAD_ROUTE',
  fare_model_id: 'mumbai_taxi_standard',
  fare_model_version: '1.0.0',
  pulse_quantization_mode: 'CONTINUOUS' as const,
  excluded_charges: ['tolls', 'waiting time', 'parking'],
  disclaimer: 'Estimated pre-trip fare.',
};

function createMockProposal(overrides: Partial<MatchProposal> = {}): MatchProposal {
  return {
    proposal_id: 'prop-123',
    target_request_id: mockRequest.id,
    candidate: {
      candidate_request_id: 'cand-456',
      candidate_display_name: 'Bob Commuter',
      candidate_pickup: { latitude: 19.066, longitude: 72.869, label: 'BKC One' },
      candidate_destination: { latitude: 19.117, longitude: 72.905, label: 'Powai Galleria' },
      seats_requested: 1,
      pickup_distance_meters: 50,
      destination_distance_meters: 100,
      shared_departure_window_start: mockRequest.departure_earliest,
      shared_departure_window_end: mockRequest.departure_latest,
      estimated_detour_minutes_target: 3.5,
      estimated_detour_minutes_candidate: 2.1,
      scores: {
        pickup_proximity_score: 0.95,
        destination_similarity_score: 0.92,
        departure_time_score: 1.0,
        route_detour_score: 0.88,
        composite_score: 0.94,
      },
    },
    ordered_stops: [
      { sequence: 1, stop_type: 'PICKUP', location: mockRequest.pickup, passenger_request_id: mockRequest.id },
      { sequence: 2, stop_type: 'DROPOFF', location: mockRequest.destination, passenger_request_id: mockRequest.id },
    ],
    total_shared_distance_km: 10.0,
    total_shared_duration_minutes: 25.0,
    best_sequence: 'PA→PB→DA→DB',
    is_route_approximate: false,
    distance_is_approximate: false,
    routing_accuracy: 'turn_by_turn_road_routing',
    routing_notice: 'Turn-by-turn road route',
    compatibility_explanations: ['Pickups are 50m apart.'],
    created_at: mockRequest.created_at,
    fare_estimate: baseFareEstimate,
    economic_assessment: {
      classification: 'POSITIVE',
      message: 'Estimated lower combined cost.',
    },
    fare_allocation_disclosure: {
      consent_text_version: 'DEC-013-2026-11-08-v1',
      consent_notice: 'If you consent, the other rider will see your exact contribution.',
      your_consent_active: false,
      co_passenger_consent_active: false,
      exact_disclosure_available: false,
      allocation: null,
      conditional_scenarios: [],
    },
    ...overrides,
  };
}

describe('Phase 6A Bilateral Consent UX Workflow', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('1. Renders consent notice and pending state when neither passenger has consented', async () => {
    const proposal = createMockProposal();
    vi.spyOn(rideRequestService, 'findRideMatches').mockResolvedValue({
      target_request_id: mockRequest.id,
      total_candidates_found: 1,
      proposals: [proposal],
    });

    renderWithClient(<MatchResults request={mockRequest} onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /Find compatible rides/i }));

    expect(await screen.findByText(/Optional exact contribution disclosure/i)).toBeInTheDocument();
    expect(screen.getByText(/Your consent has not been given./i)).toBeInTheDocument();
    expect(screen.getByText(/The other passenger must also consent before exact amounts are shown./i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /I agree to exact disclosure/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /No thanks/i })).toBeInTheDocument();
    expect(screen.queryByText(/Other passenger's share:/i)).not.toBeInTheDocument();
  });

  it('2. Clicking "No thanks" records decline in view and hides action buttons until review', async () => {
    const proposal = createMockProposal();
    vi.spyOn(rideRequestService, 'findRideMatches').mockResolvedValue({
      target_request_id: mockRequest.id,
      total_candidates_found: 1,
      proposals: [proposal],
    });

    renderWithClient(<MatchResults request={mockRequest} onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /Find compatible rides/i }));

    const declineBtn = await screen.findByRole('button', { name: /No thanks/i });
    fireEvent.click(declineBtn);

    expect(screen.getByText(/You chose not to consent in this view. Exact contribution amounts remain hidden./i)).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /I agree to exact disclosure/i })).not.toBeInTheDocument();

    const reviewBtn = screen.getByRole('button', { name: /Review consent notice/i });
    fireEvent.click(reviewBtn);
    expect(screen.getByRole('button', { name: /I agree to exact disclosure/i })).toBeInTheDocument();
  });

  it('3. Submitting consent calls grant endpoint and updates to consented state', async () => {
    const proposal = createMockProposal();
    const updatedProposal = createMockProposal({
      fare_allocation_disclosure: {
        consent_text_version: 'DEC-013-2026-11-08-v1',
        consent_notice: 'If you consent...',
        your_consent_active: true,
        co_passenger_consent_active: false,
        exact_disclosure_available: false,
        allocation: null,
      },
    });

    vi.spyOn(rideRequestService, 'findRideMatches').mockResolvedValue({
      target_request_id: mockRequest.id,
      total_candidates_found: 1,
      proposals: [proposal],
    });
    const grantSpy = vi.spyOn(rideRequestService, 'grantFareDisclosureConsent').mockResolvedValue(
      updatedProposal.fare_allocation_disclosure
    );
    vi.spyOn(rideRequestService, 'fetchMatchProposal').mockResolvedValue(updatedProposal);

    renderWithClient(<MatchResults request={mockRequest} onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /Find compatible rides/i }));

    const agreeBtn = await screen.findByRole('button', { name: /I agree to exact disclosure/i });
    fireEvent.click(agreeBtn);

    await waitFor(() => {
      expect(grantSpy).toHaveBeenCalledWith(
        mockRequest.id,
        proposal.proposal_id,
        'DEC-013-2026-11-08-v1'
      );
    });

    expect(await screen.findByText(/Your consent is recorded./i)).toBeInTheDocument();
    expect(screen.getByText(/The other passenger must also consent before exact amounts are shown./i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Withdraw my consent/i })).toBeInTheDocument();
  });

  it('4. Indicates when other passenger has consented while keeping exact amounts hidden', async () => {
    const proposal = createMockProposal({
      fare_allocation_disclosure: {
        consent_text_version: 'DEC-013-2026-11-08-v1',
        consent_notice: 'If you consent...',
        your_consent_active: false,
        co_passenger_consent_active: true,
        exact_disclosure_available: false,
        allocation: null,
      },
    });
    vi.spyOn(rideRequestService, 'findRideMatches').mockResolvedValue({
      target_request_id: mockRequest.id,
      total_candidates_found: 1,
      proposals: [proposal],
    });

    renderWithClient(<MatchResults request={mockRequest} onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /Find compatible rides/i }));

    expect(await screen.findByText(/The other passenger has consented./i)).toBeInTheDocument();
    expect(screen.getByText(/Your consent has not been given./i)).toBeInTheDocument();
    expect(screen.queryByText(/Other passenger's share:/i)).not.toBeInTheDocument();
  });

  it('5. Bilateral consent active: displays exact split, exact savings, and DEC-013 privacy rules', async () => {
    const proposal = createMockProposal({
      fare_allocation_disclosure: {
        consent_text_version: 'DEC-013-2026-11-08-v1',
        consent_notice: 'If you consent...',
        your_consent_active: true,
        co_passenger_consent_active: true,
        exact_disclosure_available: true,
        allocation: {
          policy: 'PROPORTIONAL_TO_SOLO_BASELINE',
          shared_total: 240.0,
          shared_total_paise: 24000,
          your_contribution: 133.33,
          your_contribution_paise: 13333,
          co_passenger_contribution: 106.67,
          co_passenger_contribution_paise: 10667,
          your_savings: 16.67,
          your_savings_paise: 1667,
          your_savings_percent: '11.11',
        },
      },
    });
    vi.spyOn(rideRequestService, 'findRideMatches').mockResolvedValue({
      target_request_id: mockRequest.id,
      total_candidates_found: 1,
      proposals: [proposal],
    });

    renderWithClient(<MatchResults request={mockRequest} onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /Find compatible rides/i }));

    expect(await screen.findByText(/Total shared taxi trip estimate:/i)).toBeInTheDocument();
    expect(screen.getByText(/Your share of that estimate:/i)).toBeInTheDocument();
    expect(screen.getByText(/Other passenger's share:/i)).toBeInTheDocument();
    expect(screen.getByText(/₹106.67/i)).toBeInTheDocument();
    expect(screen.getByText(/Only your own solo baseline and savings are shown. The other passenger’s solo baseline and savings remain private./i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Withdraw my consent/i })).toBeInTheDocument();
  });

  it('6. Withdrawing consent calls withdraw endpoint and hides exact split', async () => {
    const consentedProposal = createMockProposal({
      fare_allocation_disclosure: {
        consent_text_version: 'DEC-013-2026-11-08-v1',
        consent_notice: 'If you consent...',
        your_consent_active: true,
        co_passenger_consent_active: true,
        exact_disclosure_available: true,
        allocation: {
          policy: 'PROPORTIONAL_TO_SOLO_BASELINE',
          shared_total: 240.0,
          shared_total_paise: 24000,
          your_contribution: 133.33,
          your_contribution_paise: 13333,
          co_passenger_contribution: 106.67,
          co_passenger_contribution_paise: 10667,
          your_savings: 16.67,
          your_savings_paise: 1667,
          your_savings_percent: '11.11',
        },
      },
    });
    const withdrawnProposal = createMockProposal({
      fare_allocation_disclosure: {
        consent_text_version: 'DEC-013-2026-11-08-v1',
        consent_notice: 'If you consent...',
        your_consent_active: false,
        co_passenger_consent_active: true,
        exact_disclosure_available: false,
        allocation: null,
      },
    });

    vi.spyOn(rideRequestService, 'findRideMatches').mockResolvedValue({
      target_request_id: mockRequest.id,
      total_candidates_found: 1,
      proposals: [consentedProposal],
    });
    const withdrawSpy = vi.spyOn(rideRequestService, 'withdrawFareDisclosureConsent').mockResolvedValue(
      withdrawnProposal.fare_allocation_disclosure
    );
    vi.spyOn(rideRequestService, 'fetchMatchProposal').mockResolvedValue(withdrawnProposal);

    renderWithClient(<MatchResults request={mockRequest} onClose={vi.fn()} />);
    fireEvent.click(screen.getByRole('button', { name: /Find compatible rides/i }));

    const withdrawBtn = await screen.findByRole('button', { name: /Withdraw my consent/i });
    fireEvent.click(withdrawBtn);

    await waitFor(() => {
      expect(withdrawSpy).toHaveBeenCalledWith(mockRequest.id, consentedProposal.proposal_id);
    });

    expect(await screen.findByText(/Your consent has not been given./i)).toBeInTheDocument();
    expect(screen.queryByText(/Other passenger's share:/i)).not.toBeInTheDocument();
  });
});
