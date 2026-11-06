/**
 * Edit Ride Request Modal component.
 * Allows updating pickup/destination, departure window, seats, and detour tolerance for ACTIVE requests.
 */
import { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  Calendar,
  Loader2,
  MapPin,
  Navigation,
  X,
} from 'lucide-react';
import { MUMBAI_LOCATION_PRESETS } from '@/features/ride-requests/presets';
import { updateRideRequest } from '@/services/ride-requests';
import type { RideRequestResponse, RideRequestUpdate } from '@/types/ride-request';

interface EditRideRequestModalProps {
  request: RideRequestResponse | null;
  onClose: () => void;
  onSuccess?: () => void;
}

function toLocalDatetimeInput(isoString: string): string {
  try {
    const d = new Date(isoString);
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  } catch {
    return '';
  }
}

export function EditRideRequestModal({
  request,
  onClose,
  onSuccess,
}: EditRideRequestModalProps) {
  const queryClient = useQueryClient();

  const [pickupLabel, setPickupLabel] = useState('');
  const [pickupLat, setPickupLat] = useState('');
  const [pickupLon, setPickupLon] = useState('');

  const [destLabel, setDestLabel] = useState('');
  const [destLat, setDestLat] = useState('');
  const [destLon, setDestLon] = useState('');

  const [earliestInput, setEarliestInput] = useState('');
  const [latestInput, setLatestInput] = useState('');

  const [seatsRequested, setSeatsRequested] = useState<number>(1);
  const [maxExtraMinutes, setMaxExtraMinutes] = useState<number>(15);

  const [clientError, setClientError] = useState<string | null>(null);

  useEffect(() => {
    if (request) {
      setPickupLabel(request.pickup.label || '');
      setPickupLat(String(request.pickup.latitude));
      setPickupLon(String(request.pickup.longitude));

      setDestLabel(request.destination.label || '');
      setDestLat(String(request.destination.latitude));
      setDestLon(String(request.destination.longitude));

      setEarliestInput(toLocalDatetimeInput(request.departure_earliest));
      setLatestInput(toLocalDatetimeInput(request.departure_latest));

      setSeatsRequested(request.seats_requested);
      setMaxExtraMinutes(request.max_extra_minutes);
      setClientError(null);
    }
  }, [request]);

  const updateMutation = useMutation({
    mutationFn: (payload: RideRequestUpdate) => {
      if (!request) throw new Error('No active request');
      return updateRideRequest(request.id, payload);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ride-requests'] });
      if (onSuccess) onSuccess();
      onClose();
    },
    onError: (err: Error) => {
      setClientError(err.message || 'Failed to update ride request');
    },
  });

  if (!request) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setClientError(null);

    const pLat = parseFloat(pickupLat);
    const pLon = parseFloat(pickupLon);
    const dLat = parseFloat(destLat);
    const dLon = parseFloat(destLon);

    if (isNaN(pLat) || pLat < -90 || pLat > 90) {
      setClientError('Pickup latitude must be between -90 and 90.');
      return;
    }
    if (isNaN(pLon) || pLon < -180 || pLon > 180) {
      setClientError('Pickup longitude must be between -180 and 180.');
      return;
    }
    if (isNaN(dLat) || dLat < -90 || dLat > 90) {
      setClientError('Destination latitude must be between -90 and 90.');
      return;
    }
    if (isNaN(dLon) || dLon < -180 || dLon > 180) {
      setClientError('Destination longitude must be between -180 and 180.');
      return;
    }

    if (Math.abs(pLat - dLat) < 0.0001 && Math.abs(pLon - dLon) < 0.0001) {
      setClientError('Pickup and Destination coordinates cannot be identical.');
      return;
    }

    const earlyDate = new Date(earliestInput);
    const lateDate = new Date(latestInput);

    if (isNaN(earlyDate.getTime()) || isNaN(lateDate.getTime())) {
      setClientError('Please enter valid departure timestamps.');
      return;
    }

    if (lateDate < earlyDate) {
      setClientError('Latest departure cannot be earlier than earliest departure.');
      return;
    }

    const payload: RideRequestUpdate = {
      pickup: {
        latitude: pLat,
        longitude: pLon,
        label: pickupLabel.trim() || undefined,
      },
      destination: {
        latitude: dLat,
        longitude: dLon,
        label: destLabel.trim() || undefined,
      },
      departure_earliest: earlyDate.toISOString(),
      departure_latest: lateDate.toISOString(),
      seats_requested: seatsRequested,
      max_extra_minutes: maxExtraMinutes,
    };

    updateMutation.mutate(payload);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-5 space-y-4 text-left animate-in fade-in zoom-in-95 duration-150">
        {/* Header */}
        <div className="flex items-center justify-between border-b pb-3">
          <div>
            <h3 className="text-sm font-bold text-gray-900">Edit Ride Request</h3>
            <p className="text-2xs text-gray-500 font-mono">#{request.id.slice(0, 8)}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 rounded-lg p-1 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {clientError && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-start gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{clientError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Pickup */}
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-gray-700 flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-emerald-600" /> Pickup Location
              </label>
              <select
                onChange={(e) => {
                  const p = MUMBAI_LOCATION_PRESETS.find((x) => x.name === e.target.value);
                  if (p) {
                    setPickupLabel(p.name);
                    setPickupLat(String(p.latitude));
                    setPickupLon(String(p.longitude));
                  }
                }}
                className="text-2xs border border-gray-300 rounded px-1.5 py-0.5 bg-white"
              >
                <option value="">Presets...</option>
                {MUMBAI_LOCATION_PRESETS.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <input
              type="text"
              value={pickupLabel}
              onChange={(e) => setPickupLabel(e.target.value)}
              placeholder="Pickup landmark label"
              className="w-full text-xs px-2.5 py-1.5 border border-gray-300 rounded-lg bg-white"
              required
            />
            <div className="grid grid-cols-2 gap-2 text-2xs">
              <input
                type="number"
                step="any"
                value={pickupLat}
                onChange={(e) => setPickupLat(e.target.value)}
                placeholder="Lat"
                className="px-2 py-1 border border-gray-300 rounded bg-white font-mono"
                required
              />
              <input
                type="number"
                step="any"
                value={pickupLon}
                onChange={(e) => setPickupLon(e.target.value)}
                placeholder="Lon"
                className="px-2 py-1 border border-gray-300 rounded bg-white font-mono"
                required
              />
            </div>
          </div>

          {/* Destination */}
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-gray-700 flex items-center gap-1.5">
                <Navigation className="w-3.5 h-3.5 text-indigo-600" /> Destination
              </label>
              <select
                onChange={(e) => {
                  const p = MUMBAI_LOCATION_PRESETS.find((x) => x.name === e.target.value);
                  if (p) {
                    setDestLabel(p.name);
                    setDestLat(String(p.latitude));
                    setDestLon(String(p.longitude));
                  }
                }}
                className="text-2xs border border-gray-300 rounded px-1.5 py-0.5 bg-white"
              >
                <option value="">Presets...</option>
                {MUMBAI_LOCATION_PRESETS.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <input
              type="text"
              value={destLabel}
              onChange={(e) => setDestLabel(e.target.value)}
              placeholder="Destination landmark label"
              className="w-full text-xs px-2.5 py-1.5 border border-gray-300 rounded-lg bg-white"
              required
            />
            <div className="grid grid-cols-2 gap-2 text-2xs">
              <input
                type="number"
                step="any"
                value={destLat}
                onChange={(e) => setDestLat(e.target.value)}
                placeholder="Lat"
                className="px-2 py-1 border border-gray-300 rounded bg-white font-mono"
                required
              />
              <input
                type="number"
                step="any"
                value={destLon}
                onChange={(e) => setDestLon(e.target.value)}
                placeholder="Lon"
                className="px-2 py-1 border border-gray-300 rounded bg-white font-mono"
                required
              />
            </div>
          </div>

          {/* Departure Window */}
          <div className="bg-gray-50 border border-gray-200 rounded-xl p-3 space-y-2">
            <label className="text-xs font-bold text-gray-700 flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5 text-blue-600" /> Departure Window
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <div>
                <span className="text-2xs text-gray-500 block mb-0.5">Earliest</span>
                <input
                  type="datetime-local"
                  value={earliestInput}
                  onChange={(e) => setEarliestInput(e.target.value)}
                  className="w-full text-xs px-2 py-1.5 border border-gray-300 rounded-lg bg-white"
                  required
                />
              </div>
              <div>
                <span className="text-2xs text-gray-500 block mb-0.5">Latest</span>
                <input
                  type="datetime-local"
                  value={latestInput}
                  onChange={(e) => setLatestInput(e.target.value)}
                  className="w-full text-xs px-2 py-1.5 border border-gray-300 rounded-lg bg-white"
                  required
                />
              </div>
            </div>
          </div>

          {/* Seats & Detour */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-2xs font-bold text-gray-600 block mb-1">Seats Requested</label>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5, 6].map((num) => (
                  <button
                    type="button"
                    key={num}
                    onClick={() => setSeatsRequested(num)}
                    className={`flex-1 py-1 text-2xs font-semibold rounded border ${
                      seatsRequested === num
                        ? 'bg-indigo-600 text-white border-indigo-600'
                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100'
                    }`}
                  >
                    {num}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div className="flex justify-between items-center mb-1">
                <label className="text-2xs font-bold text-gray-600">Max Detour</label>
                <span className="text-2xs font-semibold text-indigo-700">+{maxExtraMinutes}m</span>
              </div>
              <input
                type="range"
                min={0}
                max={60}
                step={5}
                value={maxExtraMinutes}
                onChange={(e) => setMaxExtraMinutes(parseInt(e.target.value, 10))}
                className="w-full accent-indigo-600 cursor-pointer"
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2 pt-2 border-t">
            <button
              type="button"
              onClick={onClose}
              disabled={updateMutation.isPending}
              className="flex-1 py-2 text-xs font-semibold text-gray-600 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={updateMutation.isPending}
              className="flex-1 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl shadow-xs disabled:opacity-50 flex items-center justify-center gap-1.5 transition-colors"
            >
              {updateMutation.isPending && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
              Save Changes
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
