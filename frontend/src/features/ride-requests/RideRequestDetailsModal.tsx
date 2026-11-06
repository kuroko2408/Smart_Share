/**
 * Ride Request Details Modal.
 * Shows detailed breakdown of request parameters, coordinates, timestamps, and status.
 */
import {
  Calendar,
  Clock,
  MapPin,
  Navigation,
  Shield,
  Users,
  X,
} from 'lucide-react';
import { formatDateTime, getStatusBadge } from '@/features/ride-requests/RideRequestCard';
import type { RideRequestResponse } from '@/types/ride-request';

interface RideRequestDetailsModalProps {
  request: RideRequestResponse | null;
  onClose: () => void;
}

export function RideRequestDetailsModal({
  request,
  onClose,
}: RideRequestDetailsModalProps) {
  if (!request) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-5 space-y-4 text-left animate-in fade-in zoom-in-95 duration-150">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b pb-3">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-bold text-gray-900">Ride Request Details</h3>
            {getStatusBadge(request.status)}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 rounded-lg p-1 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Request ID */}
        <div className="text-2xs text-gray-400 font-mono bg-gray-50 p-2 rounded-lg flex items-center justify-between">
          <span>Request ID:</span>
          <span className="font-semibold text-gray-600 select-all">{request.id}</span>
        </div>

        {/* Spatial Locations */}
        <div className="space-y-3">
          <div className="border border-emerald-100 bg-emerald-50/50 p-3 rounded-xl space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-800">
              <MapPin className="w-3.5 h-3.5 text-emerald-600" /> Pickup Location
            </div>
            <p className="text-xs text-gray-900 font-medium">{request.pickup.label || 'Unlabeled'}</p>
            <p className="text-2xs text-gray-500 font-mono">
              Latitude: {request.pickup.latitude.toFixed(6)}, Longitude: {request.pickup.longitude.toFixed(6)}
            </p>
          </div>

          <div className="border border-indigo-100 bg-indigo-50/50 p-3 rounded-xl space-y-1">
            <div className="flex items-center gap-1.5 text-xs font-bold text-indigo-800">
              <Navigation className="w-3.5 h-3.5 text-indigo-600" /> Destination
            </div>
            <p className="text-xs text-gray-900 font-medium">{request.destination.label || 'Unlabeled'}</p>
            <p className="text-2xs text-gray-500 font-mono">
              Latitude: {request.destination.latitude.toFixed(6)}, Longitude: {request.destination.longitude.toFixed(6)}
            </p>
          </div>
        </div>

        {/* Departure Window & Settings */}
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="p-2.5 bg-gray-50 rounded-xl space-y-1">
            <span className="text-2xs text-gray-400 font-medium block flex items-center gap-1">
              <Calendar className="w-3 h-3" /> Earliest Departure
            </span>
            <p className="font-semibold text-gray-800">{formatDateTime(request.departure_earliest)}</p>
          </div>

          <div className="p-2.5 bg-gray-50 rounded-xl space-y-1">
            <span className="text-2xs text-gray-400 font-medium block flex items-center gap-1">
              <Clock className="w-3 h-3" /> Latest Departure
            </span>
            <p className="font-semibold text-gray-800">{formatDateTime(request.departure_latest)}</p>
          </div>

          <div className="p-2.5 bg-gray-50 rounded-xl space-y-1">
            <span className="text-2xs text-gray-400 font-medium block flex items-center gap-1">
              <Users className="w-3 h-3" /> Seats Requested
            </span>
            <p className="font-semibold text-gray-800">{request.seats_requested} Person{request.seats_requested > 1 ? 's' : ''}</p>
          </div>

          <div className="p-2.5 bg-gray-50 rounded-xl space-y-1">
            <span className="text-2xs text-gray-400 font-medium block flex items-center gap-1">
              <Shield className="w-3 h-3" /> Detour Tolerance
            </span>
            <p className="font-semibold text-gray-800">Up to +{request.max_extra_minutes} mins</p>
          </div>
        </div>

        {/* Timestamps */}
        <div className="border-t pt-3 text-2xs text-gray-400 space-y-1">
          <div className="flex justify-between">
            <span>Created At:</span>
            <span>{new Date(request.created_at).toLocaleString()}</span>
          </div>
          <div className="flex justify-between">
            <span>Last Updated:</span>
            <span>{new Date(request.updated_at).toLocaleString()}</span>
          </div>
          {request.expires_at && (
            <div className="flex justify-between text-amber-700">
              <span>Expires At:</span>
              <span>{new Date(request.expires_at).toLocaleString()}</span>
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={onClose}
          className="w-full py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold rounded-xl transition-colors"
        >
          Close Details
        </button>
      </div>
    </div>
  );
}
