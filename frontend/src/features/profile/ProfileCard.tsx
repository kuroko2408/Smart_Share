/**
 * Authenticated Profile Retrieval and Display Component.
 * Supports view, inline display_name update, onboarding status, and loading/error states.
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Edit2,
  Loader2,
  User as UserIcon,
} from 'lucide-react';
import { fetchUserProfile, updateUserProfile } from '@/services/profile';
import type { ProfileUpdateRequest } from '@/types/profile';

export function ProfileCard() {
  const queryClient = useQueryClient();
  const [isEditing, setIsEditing] = useState(false);
  const [displayNameInput, setDisplayNameInput] = useState('');
  const [updateSuccessMsg, setUpdateSuccessMsg] = useState<string | null>(null);

  const {
    data: profileResponse,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: ['profile'],
    queryFn: fetchUserProfile,
    retry: 1,
  });

  const updateMutation = useMutation({
    mutationFn: (payload: ProfileUpdateRequest) => updateUserProfile(payload),
    onSuccess: (data) => {
      queryClient.setQueryData(['profile'], data);
      setIsEditing(false);
      setUpdateSuccessMsg('Display name updated successfully!');
      setTimeout(() => setUpdateSuccessMsg(null), 4000);
    },
  });

  const profile = profileResponse?.data;

  const handleStartEdit = () => {
    setDisplayNameInput(profile?.display_name || '');
    setIsEditing(true);
    setUpdateSuccessMsg(null);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!displayNameInput.trim()) return;
    updateMutation.mutate({ display_name: displayNameInput.trim() });
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-full bg-indigo-100 flex items-center justify-center animate-pulse">
            <Loader2 className="w-6 h-6 text-indigo-600 animate-spin" />
          </div>
          <div className="space-y-2 flex-1">
            <div className="h-4 bg-gray-200 rounded w-1/3 animate-pulse" />
            <div className="h-3 bg-gray-100 rounded w-1/2 animate-pulse" />
          </div>
        </div>
        <p className="text-sm text-gray-500 text-center">Loading authenticated profile…</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-white rounded-xl border border-red-200 p-6 shadow-sm space-y-4 text-left">
        <div className="flex items-start gap-3 text-red-600">
          <AlertCircle className="w-5 h-5 mt-0.5 shrink-0" />
          <div>
            <h3 className="font-semibold text-sm">Failed to retrieve profile</h3>
            <p className="text-xs text-red-500 mt-1">
              {error instanceof Error ? error.message : 'Unknown error occurred'}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => refetch()}
          className="w-full py-2 px-4 bg-red-50 hover:bg-red-100 text-red-700 text-xs font-semibold rounded-lg transition-colors"
        >
          Retry Profile Retrieval
        </button>
      </div>
    );
  }

  if (!profile) return null;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm space-y-5 text-left">
      {/* Header with Avatar & Identity */}
      <div className="flex items-center gap-4">
        <div className="w-14 h-14 rounded-full bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 shrink-0">
          {profile.avatar_url ? (
            <img
              src={profile.avatar_url}
              alt={profile.display_name}
              className="w-full h-full rounded-full object-cover"
            />
          ) : (
            <UserIcon className="w-7 h-7" />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-gray-900 truncate">
              {profile.display_name || 'Pending Onboarding'}
            </h2>
            <button
              type="button"
              onClick={handleStartEdit}
              className="p-1 text-gray-400 hover:text-indigo-600 rounded transition-colors"
              title="Edit Display Name"
            >
              <Edit2 className="w-3.5 h-3.5" />
            </button>
          </div>
          <p className="text-xs text-gray-500 font-mono truncate" title={profile.id}>
            ID: {profile.id}
          </p>
        </div>
      </div>

      {/* Onboarding Status Badge */}
      <div className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg text-xs">
        <span className="text-gray-500 font-medium">Onboarding Status:</span>
        {profile.is_onboarding_completed ? (
          <span className="inline-flex items-center gap-1 text-green-700 font-semibold bg-green-100 px-2.5 py-0.5 rounded-full">
            <CheckCircle2 className="w-3.5 h-3.5" /> Completed
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-amber-700 font-semibold bg-amber-100 px-2.5 py-0.5 rounded-full">
            <AlertCircle className="w-3.5 h-3.5" /> Pending Profile Setup
          </span>
        )}
      </div>

      {/* Edit Form */}
      {isEditing && (
        <form onSubmit={handleSave} className="space-y-3 pt-2 border-t border-gray-100">
          <div>
            <label htmlFor="display_name" className="block text-xs font-semibold text-gray-700 mb-1">
              Update Display Name
            </label>
            <input
              id="display_name"
              type="text"
              value={displayNameInput}
              onChange={(e) => setDisplayNameInput(e.target.value)}
              placeholder="Enter your public display name"
              maxLength={100}
              required
              className="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
            />
          </div>
          {updateMutation.isError && (
            <p className="text-xs text-red-500">
              {updateMutation.error instanceof Error
                ? updateMutation.error.message
                : 'Failed to update profile'}
            </p>
          )}
          <div className="flex gap-2">
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="flex-1 py-1.5 px-3 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm disabled:opacity-50 flex items-center justify-center gap-1.5"
            >
              {updateMutation.isPending && <Loader2 className="w-3 h-3 animate-spin" />}
              Save
            </button>
            <button
              type="button"
              onClick={() => setIsEditing(false)}
              className="py-1.5 px-3 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-medium rounded-lg"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {/* Success Notification */}
      {updateSuccessMsg && (
        <div className="p-2.5 bg-green-50 border border-green-200 text-green-700 text-xs rounded-lg flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{updateSuccessMsg}</span>
        </div>
      )}

      {/* Metadata Timestamps */}
      <div className="grid grid-cols-2 gap-2 text-2xs text-gray-400 border-t border-gray-100 pt-3">
        <div className="flex items-center gap-1 truncate">
          <Clock className="w-3 h-3 shrink-0" />
          <span>Joined: {new Date(profile.created_at).toLocaleDateString()}</span>
        </div>
        <div className="flex items-center gap-1 truncate justify-end">
          <span>Updated: {new Date(profile.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
        </div>
      </div>
    </div>
  );
}
