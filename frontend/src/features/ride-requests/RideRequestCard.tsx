/**
 * Individual Ride Request Card component.
 * Displays route endpoints, departure window, status badge, and actions.
 */
import {
  Calendar,
  Clock,
  Edit2,
  Eye,
  MapPin,
  Navigation,
  Users,
  XCircle,
} from 'lucide-react';
import type { RideRequestResponse, RideRequestStatus } from '@/types/ride-request';

interface RideRequestCardProps {
  request: RideRequestResponse;
  onViewDetails: (request: RideRequestResponse) => void;
  onEdit: (request: RideRequestResponse) => void;
  onCancel: (request: RideRequestResponse) => void;
  onFindMatches: (request: RideRequestResponse) => void;
}

export function formatDateTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

export function getStatusBadge(status: RideRequestStatus) {
  switch (status) {
    case 'ACTIVE':
      return (
        <span className="px-2 py-0.5 rounded-full text-2xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
          ● Active
        </span>
      );
    case 'MATCHED':
      return (
        <span className="px-2 py-0.5 rounded-full text-2xs font-semibold bg-blue-50 text-blue-700 border border-blue-200">
          ● Matched
        </span>
      );
    case 'CANCELLED':
      return (
        <span className="px-2 py-0.5 rounded-full text-2xs font-semibold bg-gray-100 text-gray-600 border border-gray-200">
          Cancelled
        </span>
      );
    case 'EXPIRED':
      return (
        <span className="px-2 py-0.5 rounded-full text-2xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
          Expired
        </span>
      );
    case 'COMPLETED':
      return (
        <span className="px-2 py-0.5 rounded-full text-2xs font-semibold bg-purple-50 text-purple-700 border border-purple-200">
          Completed
        </span>
      );
    default:
      return (
        <span className="px-2 py-0.5 rounded-full text-2xs font-semibold bg-gray-100 text-gray-700">
          {status}
        </span>
      );
  }
}

export function RideRequestCard({
  request,
  onViewDetails,
  onEdit,
  onCancel,
  onFindMatches,
}: RideRequestCardProps) {
  const isEditable = request.status === 'ACTIVE';
  const isCancellable = request.status === 'ACTIVE' || request.status === 'MATCHED';

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 shadow-xs hover:shadow-md transition-shadow text-left space-y-3">
      {/* Header: Status and ID */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {getStatusBadge(request.status)}
          <span className="text-2xs text-gray-400 font-mono">
            #{request.id.slice(0, 8)}
          </span>
        </div>
        <span className="text-2xs text-gray-400">
          Created {formatDateTime(request.created_at)}
        </span>
      </div>

      {/* Route: Pickup & Destination */}
      <div className="space-y-1.5 border-l-2 border-indigo-200 pl-3 py-0.5">
        <div className="flex items-start gap-1.5 text-xs text-gray-800">
          <MapPin className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
          <span className="font-medium truncate">
            {request.pickup.label || `${request.pickup.latitude.toFixed(4)}, ${request.pickup.longitude.toFixed(4)}`}
          </span>
        </div>
        <div className="flex items-start gap-1.5 text-xs text-gray-800">
          <Navigation className="w-3.5 h-3.5 text-indigo-600 shrink-0 mt-0.5" />
          <span className="font-medium truncate">
            {request.destination.label || `${request.destination.latitude.toFixed(4)}, ${request.destination.longitude.toFixed(4)}`}
          </span>
        </div>
      </div>

      {/* Metadata Badges */}
      <div className="grid grid-cols-2 gap-2 text-2xs text-gray-600 bg-gray-50 p-2 rounded-lg">
        <div className="flex items-center gap-1 truncate">
          <Calendar className="w-3 h-3 text-gray-400 shrink-0" />
          <span className="truncate">{formatDateTime(request.departure_earliest)}</span>
        </div>
        <div className="flex items-center gap-1 truncate">
          <Clock className="w-3 h-3 text-gray-400 shrink-0" />
          <span>until {formatDateTime(request.departure_latest)}</span>
        </div>
        <div className="flex items-center gap-1">
          <Users className="w-3 h-3 text-gray-400 shrink-0" />
          <span>{request.seats_requested} seat{request.seats_requested > 1 ? 's' : ''}</span>
        </div>
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3 text-gray-400 shrink-0" />
          <span>+{request.max_extra_minutes}m detour</span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-end gap-1.5 border-t pt-2.5">
        {isEditable && (
          <button type="button" onClick={() => onFindMatches(request)} className="px-2.5 py-1 text-2xs font-semibold text-indigo-700 hover:bg-indigo-50 rounded-md transition-colors flex items-center gap-1">
            <Navigation className="w-3 h-3" /> Find matches
          </button>
        )}
        <button
          type="button"
          onClick={() => onViewDetails(request)}
          className="px-2.5 py-1 text-2xs font-semibold text-gray-600 hover:text-indigo-600 hover:bg-gray-100 rounded-md transition-colors flex items-center gap-1"
        >
          <Eye className="w-3 h-3" /> Details
        </button>

        {isEditable && (
          <button
            type="button"
            onClick={() => onEdit(request)}
            className="px-2.5 py-1 text-2xs font-semibold text-indigo-600 hover:bg-indigo-50 rounded-md transition-colors flex items-center gap-1"
          >
            <Edit2 className="w-3 h-3" /> Edit
          </button>
        )}

        {isCancellable && (
          <button
            type="button"
            onClick={() => onCancel(request)}
            className="px-2.5 py-1 text-2xs font-semibold text-rose-600 hover:bg-rose-50 rounded-md transition-colors flex items-center gap-1"
          >
            <XCircle className="w-3 h-3" /> Cancel
          </button>
        )}
      </div>
    </div>
  );
}
