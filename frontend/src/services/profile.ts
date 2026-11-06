/**
 * Profile service communicating with backend /users/me endpoints.
 */
import { apiClient } from '@/services/api-client';
import type { ProfileResponse, ProfileUpdateRequest } from '@/types/profile';

export async function fetchUserProfile(): Promise<ProfileResponse> {
  return apiClient.get<ProfileResponse>('/users/me');
}

export async function updateUserProfile(
  payload: ProfileUpdateRequest
): Promise<ProfileResponse> {
  return apiClient.patch<ProfileResponse>('/users/me', payload);
}
