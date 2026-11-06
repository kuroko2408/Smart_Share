/**
 * Cancel Ride Request Confirmation Modal.
 * Prompts user for explicit confirmation before cancelling an active/matched request.
 */
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, AlertTriangle, Loader2, X } from 'lucide-react';
import { cancelRideRequest } from '@/services/ride-requests';
import type { RideRequestResponse } from '@/types/ride-request';

interface CancelRideRequestModalProps {
  request: RideRequestResponse | null;
  onClose: () => void;
  onSuccess?: () => void;
}

export function CancelRideRequestModal({
  request,
  onClose,
  onSuccess,
}: CancelRideRequestModalProps) {
  const queryClient = useQueryClient();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const cancelMutation = useMutation({
    mutationFn: () => {
      if (!request) throw new Error('No request to cancel');
      return cancelRideRequest(request.id);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ride-requests'] });
      if (onSuccess) onSuccess();
      onClose();
    },
    onError: (err: Error) => {
      setErrorMsg(err.message || 'Failed to cancel ride request');
    },
  });

  if (!request) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-sm w-full p-5 space-y-4 text-left animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center text-rose-600 shrink-0">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 rounded-lg p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div>
          <h3 className="text-sm font-bold text-gray-900">Cancel Ride Request?</h3>
          <p className="text-xs text-gray-500 mt-1">
            Are you sure you want to cancel this request? Once cancelled, it will not be considered for
            passenger matching.
          </p>
        </div>

        {/* Route Summary */}
        <div className="bg-gray-50 p-3 rounded-xl text-2xs space-y-1 text-gray-700 border border-gray-200">
          <div className="font-semibold text-gray-900">
            #{request.id.slice(0, 8)}: {request.pickup.label || 'Pickup'} → {request.destination.label || 'Destination'}
          </div>
          <div className="text-gray-500">
            Status: <span className="font-semibold text-indigo-700">{request.status}</span>
          </div>
        </div>

        {errorMsg && (
          <div className="p-2.5 bg-red-50 border border-red-200 text-red-600 text-xs rounded-lg flex items-start gap-1.5">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex items-center gap-2 pt-2 border-t">
          <button
            type="button"
            onClick={onClose}
            disabled={cancelMutation.isPending}
            className="flex-1 py-2 text-xs font-semibold text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors"
          >
            Keep Request
          </button>
          <button
            type="button"
            onClick={() => cancelMutation.mutate()}
            disabled={cancelMutation.isPending}
            className="flex-1 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-xl shadow-xs disabled:opacity-50 flex items-center justify-center gap-1.5 transition-colors"
          >
            {cancelMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            Yes, Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
