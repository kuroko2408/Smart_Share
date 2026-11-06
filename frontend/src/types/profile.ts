/**
 * User Profile API response and request shapes matching FastAPI contracts.
 */

export interface Profile {
  id: string;
  display_name: string;
  avatar_url: string | null;
  is_onboarding_completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProfileResponse {
  data: Profile;
  message: string;
}

export interface ProfileUpdateRequest {
  display_name?: string;
  avatar_url?: string | null;
}
