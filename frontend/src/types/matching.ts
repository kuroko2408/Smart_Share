import type { LocationPoint } from '@/types/ride-request';

export interface MatchScores {
  pickup_proximity_score: number;
  destination_similarity_score: number;
  departure_time_score: number;
  route_detour_score: number;
  composite_score: number;
}

export interface MatchCandidate {
  candidate_request_id: string;
  candidate_display_name: string;
  candidate_pickup: LocationPoint;
  candidate_destination: LocationPoint;
  seats_requested: number;
  pickup_distance_meters: number;
  destination_distance_meters: number;
  shared_departure_window_start: string;
  shared_departure_window_end: string;
  estimated_detour_minutes_target: number;
  estimated_detour_minutes_candidate: number;
  scores: MatchScores;
}

export interface MatchStop {
  sequence: number;
  stop_type: 'PICKUP' | 'DROPOFF';
  location: LocationPoint;
  passenger_request_id: string;
}

export interface GeoJSONLineString {
  type: 'LineString';
  coordinates: [number, number][];
}

export interface RouteLeg {
  sequence: number;
  start_stop_id: string;
  end_stop_id: string;
  start_label?: string | null;
  end_label?: string | null;
  distance_meters: number;
  distance_km: number;
  duration_seconds: number;
  duration_minutes: number;
}

export interface PassengerJourneyDetail {
  passenger_request_id: string;
  solo_direct_distance_km: number;
  solo_direct_distance_meters: number;
  solo_direct_duration_minutes: number;
  solo_direct_duration_seconds: number;
  pooled_distance_km: number;
  pooled_distance_meters: number;
  pooled_duration_minutes: number;
  pooled_duration_seconds: number;
  detour_distance_km: number;
  detour_distance_meters: number;
  detour_duration_minutes: number;
}

export interface FareAmount {
  estimate: number;
  estimate_paise: number;
  rounded_estimate_rupees: number;
}

export interface FareComponentEstimate extends FareAmount {
  distance_meters: number;
  distance_source: string;
  accuracy_tier: 'ROAD_ROUTE' | 'MATRIX_SCREENING' | 'CALIBRATED_FALLBACK' | 'GEODESIC_ONLY';
  surcharge_status: 'NONE' | 'APPLIED' | 'CONDITIONAL';
  fare_range?: { minimum: FareAmount; maximum: FareAmount } | null;
}

export interface MatchFareEstimate {
  shared_journey: FareComponentEstimate;
  your_solo_baseline: FareComponentEstimate;
  composite_accuracy: string;
  fare_model_id: string;
  fare_model_version: string;
  pulse_quantization_mode: 'CONTINUOUS' | 'CEILING' | 'FLOOR';
  excluded_charges: string[];
  disclaimer: string;
}

export interface EconomicAssessment {
  classification: 'POSITIVE' | 'BREAK_EVEN' | 'NEGATIVE' | 'CONDITIONAL';
  message: string;
}

export interface FareAllocation {
  policy: 'PROPORTIONAL_TO_SOLO_BASELINE';
  shared_total: number;
  shared_total_paise: number;
  your_contribution: number;
  your_contribution_paise: number;
  co_passenger_contribution: number;
  co_passenger_contribution_paise: number;
  your_savings: number;
  your_savings_paise: number;
  your_savings_percent: string;
}

export interface FareAllocationDisclosure {
  consent_text_version: string;
  consent_notice: string;
  your_consent_active: boolean;
  co_passenger_consent_active: boolean;
  exact_disclosure_available: boolean;
  allocation?: FareAllocation | null;
  conditional_scenarios?: FareAllocationScenario[];
}

export interface FareAllocationScenario {
  tariff_period: 'DAY' | 'NIGHT';
  economic_classification: 'POSITIVE' | 'BREAK_EVEN' | 'NEGATIVE';
  shared_total: number;
  shared_total_paise: number;
  your_contribution: number;
  your_contribution_paise: number;
  co_passenger_contribution: number;
  co_passenger_contribution_paise: number;
  your_savings: number;
  your_savings_paise: number;
  your_savings_percent: string;
}

export interface MatchProposal {
  proposal_id: string;
  target_request_id: string;
  candidate: MatchCandidate;
  ordered_stops: MatchStop[];
  total_shared_distance_km: number;
  total_shared_distance_meters?: number;
  total_shared_duration_minutes: number;
  total_shared_duration_seconds?: number;
  best_sequence: string;
  is_route_approximate: boolean;
  distance_is_approximate: boolean;
  distance_source?: string;
  routing_accuracy: string;
  routing_notice: string;
  compatibility_explanations: string[];
  created_at: string;
  route_geometry?: GeoJSONLineString | null;
  route_legs?: RouteLeg[];
  passenger_metrics?: Record<string, PassengerJourneyDetail>;
  fare_estimate?: MatchFareEstimate | null;
  economic_assessment?: EconomicAssessment | null;
  fare_allocation_disclosure?: FareAllocationDisclosure | null;
}

export interface MatchListResponse {
  target_request_id: string;
  total_candidates_found: number;
  proposals: MatchProposal[];
}
