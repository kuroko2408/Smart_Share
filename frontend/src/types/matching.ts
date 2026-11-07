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

export interface MatchProposal {
  proposal_id: string;
  target_request_id: string;
  candidate: MatchCandidate;
  ordered_stops: MatchStop[];
  total_shared_distance_km: number;
  total_shared_duration_minutes: number;
  best_sequence: string;
  is_route_approximate: boolean;
  distance_is_approximate: boolean;
  routing_accuracy: string;
  routing_notice: string;
  compatibility_explanations: string[];
  created_at: string;
}

export interface MatchListResponse {
  target_request_id: string;
  total_candidates_found: number;
  proposals: MatchProposal[];
}
