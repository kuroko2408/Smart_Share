/**
 * Ride Request List component.
 * Displays paginated/filtered list of ride requests with state modals.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  AlertCircle,
  Car,
  Filter,
  Loader2,
  PlusCircle,
  RefreshCw,
} from 'lucide-react';
import { CancelRideRequestModal } from '@/features/ride-requests/CancelRideRequestModal';
import { EditRideRequestModal } from '@/features/ride-requests/EditRideRequestModal';
import { RideRequestCard } from '@/features/ride-requests/RideRequestCard';
import { RideRequestDetailsModal } from '@/features/ride-requests/RideRequestDetailsModal';
import { fetchUserRideRequests } from '@/services/ride-requests';
import type { RideRequestResponse, RideRequestStatus } from '@/types/ride-request';

interface RideRequestListProps {
  onCreateNewClick?: () => void;
}

const STATUS_FILTERS: { label: string; value: RideRequestStatus | 'ALL' }[] = [
  { label: 'All', value: 'ALL' },
  { label: 'Active', value: 'ACTIVE' },
  { label: 'Matched', value: 'MATCHED' },
  { label: 'Cancelled', value: 'CANCELLED' },
  { label: 'Expired', value: 'EXPIRED' },
];

export function RideRequestList({ onCreateNewClick }: RideRequestListProps) {
  const [selectedStatus, setSelectedStatus] = useState<RideRequestStatus | 'ALL'>('ALL');

  // Modals state
  const [detailsRequest, setDetailsRequest] = useState<RideRequestResponse | null>(null);
  const [editRequest, setEditRequest] = useState<RideRequestResponse | null>(null);
  const [cancelRequest, setCancelRequest] = useState<RideRequestResponse | null>(null);

  const {
    data: listResponse,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ['ride-requests', selectedStatus],
    queryFn: () =>
      fetchUserRideRequests({
        status: selectedStatus === 'ALL' ? undefined : selectedStatus,
        limit: 50,
      }),
  });

  const requests = listResponse?.data || [];

  return (
    <div className="space-y-4 text-left">
      {/* Filter and Refresh Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2.5">
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0 scrollbar-none">
          <Filter className="w-3.5 h-3.5 text-gray-400 shrink-0 mr-1" />
          {STATUS_FILTERS.map((f) => (
            <button
              type="button"
              key={f.value}
              onClick={() => setSelectedStatus(f.value)}
              className={`px-2.5 py-1 rounded-full text-2xs font-semibold whitespace-nowrap transition-all ${
                selectedStatus === f.value
                  ? 'bg-indigo-600 text-white shadow-xs'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 self-end sm:self-auto">
          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-1.5 text-gray-500 hover:text-indigo-600 hover:bg-gray-100 rounded-lg transition-colors flex items-center gap-1 text-2xs font-medium"
            title="Refresh list"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? 'animate-spin' : ''}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>

          {onCreateNewClick && (
            <button
              type="button"
              onClick={onCreateNewClick}
              className="px-2.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-2xs font-semibold flex items-center gap-1 shadow-xs transition-colors"
            >
              <PlusCircle className="w-3.5 h-3.5" /> New Request
            </button>
          )}
        </div>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="py-12 flex flex-col items-center justify-center gap-3 text-gray-500">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-600" />
          <p className="text-xs">Loading ride requests…</p>
        </div>
      )}

      {/* Error State */}
      {isError && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-xl space-y-2">
          <div className="flex items-center gap-2 font-semibold text-xs">
            <AlertCircle className="w-4 h-4 text-red-500" /> Failed to load ride requests
          </div>
          <p className="text-2xs text-red-600">
            {error instanceof Error ? error.message : 'Unknown error occurred'}
          </p>
          <button
            type="button"
            onClick={() => refetch()}
            className="px-3 py-1 bg-red-600 text-white text-2xs font-semibold rounded-lg hover:bg-red-700 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !isError && requests.length === 0 && (
        <div className="py-12 px-4 border-2 border-dashed border-gray-200 rounded-2xl flex flex-col items-center justify-center text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-indigo-50 flex items-center justify-center text-indigo-600">
            <Car className="w-6 h-6" />
          </div>
          <div>
            <h4 className="text-sm font-semibold text-gray-800">No ride requests found</h4>
            <p className="text-xs text-gray-500 max-w-xs mt-0.5">
              {selectedStatus === 'ALL'
                ? "You haven't published any ride requests yet."
                : `No requests with status '${selectedStatus}'.`}
            </p>
          </div>
          {onCreateNewClick && (
            <button
              type="button"
              onClick={onCreateNewClick}
              className="px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-xs transition-colors flex items-center gap-1.5"
            >
              <PlusCircle className="w-4 h-4" /> Create Ride Request
            </button>
          )}
        </div>
      )}

      {/* Request Cards List */}
      {!isLoading && !isError && requests.length > 0 && (
        <div className="space-y-3">
          {requests.map((req) => (
            <RideRequestCard
              key={req.id}
              request={req}
              onViewDetails={(r) => setDetailsRequest(r)}
              onEdit={(r) => setEditRequest(r)}
              onCancel={(r) => setCancelRequest(r)}
            />
          ))}
        </div>
      )}

      {/* Details Modal */}
      <RideRequestDetailsModal
        request={detailsRequest}
        onClose={() => setDetailsRequest(null)}
      />

      {/* Edit Modal */}
      <EditRideRequestModal
        request={editRequest}
        onClose={() => setEditRequest(null)}
        onSuccess={() => refetch()}
      />

      {/* Cancel Modal */}
      <CancelRideRequestModal
        request={cancelRequest}
        onClose={() => setCancelRequest(null)}
        onSuccess={() => refetch()}
      />
    </div>
  );
}
