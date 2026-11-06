/**
 * Ride Request Creation Form component.
 * Allows entering pickup, destination, departure window, seats, and detour tolerance.
 * Includes Mumbai landmark presets, client-side validation, and feedback states.
 */
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  Calendar,
  CheckCircle2,
  Clock,
  Loader2,
  MapPin,
  Navigation,
  Users,
} from 'lucide-react';
import { MUMBAI_LOCATION_PRESETS } from '@/features/ride-requests/presets';
import { createRideRequest } from '@/services/ride-requests';
import type { RideRequestCreate } from '@/types/ride-request';

interface RideRequestFormProps {
  onSuccess?: (createdId: string) => void;
}

function getDefaultDateTime(offsetMinutes: number): string {
  const d = new Date(Date.now() + offsetMinutes * 60_000);
  // Format for datetime-local input: YYYY-MM-DDTHH:mm
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export function RideRequestForm({ onSuccess }: RideRequestFormProps) {
  const queryClient = useQueryClient();

  // Coordinates & Labels
  const [pickupLabel, setPickupLabel] = useState(MUMBAI_LOCATION_PRESETS[0].name);
  const [pickupLat, setPickupLat] = useState(String(MUMBAI_LOCATION_PRESETS[0].latitude));
  const [pickupLon, setPickupLon] = useState(String(MUMBAI_LOCATION_PRESETS[0].longitude));

  const [destLabel, setDestLabel] = useState(MUMBAI_LOCATION_PRESETS[1].name);
  const [destLat, setDestLat] = useState(String(MUMBAI_LOCATION_PRESETS[1].latitude));
  const [destLon, setDestLon] = useState(String(MUMBAI_LOCATION_PRESETS[1].longitude));

  // Departure Window
  const [earliestInput, setEarliestInput] = useState(() => getDefaultDateTime(20));
  const [latestInput, setLatestInput] = useState(() => getDefaultDateTime(50));

  // Seats & Detour
  const [seatsRequested, setSeatsRequested] = useState<number>(1);
  const [maxExtraMinutes, setMaxExtraMinutes] = useState<number>(20);

  // Validation / Error States
  const [clientError, setClientError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (payload: RideRequestCreate) => createRideRequest(payload),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['ride-requests'] });
      setSuccessMessage('Ride request created successfully!');
      setClientError(null);
      if (onSuccess) {
        onSuccess(data.data.id);
      }
    },
    onError: (err: Error) => {
      setClientError(err.message || 'Failed to create ride request');
      setSuccessMessage(null);
    },
  });

  const handleApplyPresetPickup = (presetName: string) => {
    const found = MUMBAI_LOCATION_PRESETS.find((p) => p.name === presetName);
    if (found) {
      setPickupLabel(found.name);
      setPickupLat(String(found.latitude));
      setPickupLon(String(found.longitude));
    }
  };

  const handleApplyPresetDest = (presetName: string) => {
    const found = MUMBAI_LOCATION_PRESETS.find((p) => p.name === presetName);
    if (found) {
      setDestLabel(found.name);
      setDestLat(String(found.latitude));
      setDestLon(String(found.longitude));
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setClientError(null);
    setSuccessMessage(null);

    const pLat = parseFloat(pickupLat);
    const pLon = parseFloat(pickupLon);
    const dLat = parseFloat(destLat);
    const dLon = parseFloat(destLon);

    if (isNaN(pLat) || pLat < -90 || pLat > 90) {
      setClientError('Pickup latitude must be a valid number between -90 and 90.');
      return;
    }
    if (isNaN(pLon) || pLon < -180 || pLon > 180) {
      setClientError('Pickup longitude must be a valid number between -180 and 180.');
      return;
    }
    if (isNaN(dLat) || dLat < -90 || dLat > 90) {
      setClientError('Destination latitude must be a valid number between -90 and 90.');
      return;
    }
    if (isNaN(dLon) || dLon < -180 || dLon > 180) {
      setClientError('Destination longitude must be a valid number between -180 and 180.');
      return;
    }

    // Endpoints must not be identical
    if (Math.abs(pLat - dLat) < 0.0001 && Math.abs(pLon - dLon) < 0.0001) {
      setClientError('Pickup and Destination coordinates cannot be identical.');
      return;
    }

    const earlyDate = new Date(earliestInput);
    const lateDate = new Date(latestInput);

    if (isNaN(earlyDate.getTime()) || isNaN(lateDate.getTime())) {
      setClientError('Please provide valid earliest and latest departure timestamps.');
      return;
    }

    if (lateDate < earlyDate) {
      setClientError('Latest departure cannot be earlier than earliest departure.');
      return;
    }

    // Freshness check: must not be in past
    if (earlyDate.getTime() < Date.now() - 60_000) {
      setClientError('Earliest departure window cannot be in the past.');
      return;
    }

    const payload: RideRequestCreate = {
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

    createMutation.mutate(payload);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6 text-left">
      {/* Alert states */}
      {clientError && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-start gap-2">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <span>{clientError}</span>
        </div>
      )}

      {successMessage && (
        <div className="p-3 bg-green-50 border border-green-200 text-green-700 text-xs rounded-lg flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successMessage}</span>
        </div>
      )}

      {/* Pickup Location Section */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold text-gray-700 uppercase tracking-wide flex items-center gap-1.5">
            <MapPin className="w-4 h-4 text-emerald-600" /> Pickup Location
          </label>
          <select
            onChange={(e) => handleApplyPresetPickup(e.target.value)}
            value={pickupLabel}
            className="text-xs border border-gray-300 rounded px-2 py-1 bg-white text-gray-700"
          >
            <option value="">Quick Presets...</option>
            {MUMBAI_LOCATION_PRESETS.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <input
            type="text"
            value={pickupLabel}
            onChange={(e) => setPickupLabel(e.target.value)}
            placeholder="Pickup landmark name (e.g. Bandra Kurla Complex)"
            className="w-full text-xs px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-2xs text-gray-400 font-semibold block mb-0.5">Latitude</span>
            <input
              type="number"
              step="any"
              value={pickupLat}
              onChange={(e) => setPickupLat(e.target.value)}
              placeholder="19.0657"
              className="w-full text-xs px-2.5 py-1.5 border border-gray-300 rounded bg-white font-mono"
              required
            />
          </div>
          <div>
            <span className="text-2xs text-gray-400 font-semibold block mb-0.5">Longitude</span>
            <input
              type="number"
              step="any"
              value={pickupLon}
              onChange={(e) => setPickupLon(e.target.value)}
              placeholder="72.8687"
              className="w-full text-xs px-2.5 py-1.5 border border-gray-300 rounded bg-white font-mono"
              required
            />
          </div>
        </div>
      </div>

      {/* Destination Location Section */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-xs font-bold text-gray-700 uppercase tracking-wide flex items-center gap-1.5">
            <Navigation className="w-4 h-4 text-indigo-600" /> Destination
          </label>
          <select
            onChange={(e) => handleApplyPresetDest(e.target.value)}
            value={destLabel}
            className="text-xs border border-gray-300 rounded px-2 py-1 bg-white text-gray-700"
          >
            <option value="">Quick Presets...</option>
            {MUMBAI_LOCATION_PRESETS.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <input
            type="text"
            value={destLabel}
            onChange={(e) => setDestLabel(e.target.value)}
            placeholder="Destination landmark (e.g. Mumbai Airport T2)"
            className="w-full text-xs px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:outline-none"
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-2 text-xs">
          <div>
            <span className="text-2xs text-gray-400 font-semibold block mb-0.5">Latitude</span>
            <input
              type="number"
              step="any"
              value={destLat}
              onChange={(e) => setDestLat(e.target.value)}
              placeholder="19.0886"
              className="w-full text-xs px-2.5 py-1.5 border border-gray-300 rounded bg-white font-mono"
              required
            />
          </div>
          <div>
            <span className="text-2xs text-gray-400 font-semibold block mb-0.5">Longitude</span>
            <input
              type="number"
              step="any"
              value={destLon}
              onChange={(e) => setDestLon(e.target.value)}
              placeholder="72.8679"
              className="w-full text-xs px-2.5 py-1.5 border border-gray-300 rounded bg-white font-mono"
              required
            />
          </div>
        </div>
      </div>

      {/* Departure Window Section */}
      <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-3">
        <label className="text-xs font-bold text-gray-700 uppercase tracking-wide flex items-center gap-1.5">
          <Calendar className="w-4 h-4 text-blue-600" /> Departure Window (Local Time)
        </label>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
          <div>
            <span className="text-2xs text-gray-500 font-medium block mb-1">Earliest Departure</span>
            <input
              type="datetime-local"
              value={earliestInput}
              onChange={(e) => setEarliestInput(e.target.value)}
              className="w-full text-xs px-2.5 py-2 border border-gray-300 rounded-lg bg-white"
              required
            />
          </div>
          <div>
            <span className="text-2xs text-gray-500 font-medium block mb-1">Latest Departure</span>
            <input
              type="datetime-local"
              value={latestInput}
              onChange={(e) => setLatestInput(e.target.value)}
              className="w-full text-xs px-2.5 py-2 border border-gray-300 rounded-lg bg-white"
              required
            />
          </div>
        </div>
      </div>

      {/* Seats & Detour Preferences */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Seats */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-2">
          <label className="text-xs font-bold text-gray-700 uppercase tracking-wide flex items-center gap-1.5">
            <Users className="w-4 h-4 text-purple-600" /> Seats Required
          </label>
          <div className="flex gap-2">
            {[1, 2, 3, 4, 5, 6].map((num) => (
              <button
                type="button"
                key={num}
                onClick={() => setSeatsRequested(num)}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg border transition-all ${
                  seatsRequested === num
                    ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                    : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-100'
                }`}
              >
                {num}
              </button>
            ))}
          </div>
        </div>

        {/* Max Extra Detour */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-2">
          <div className="flex items-center justify-between">
            <label className="text-xs font-bold text-gray-700 uppercase tracking-wide flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-amber-600" /> Max Detour Time
            </label>
            <span className="text-xs font-semibold text-indigo-700">+{maxExtraMinutes} mins</span>
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
          <div className="flex justify-between text-2xs text-gray-400">
            <span>Direct (0m)</span>
            <span>Balanced (15m)</span>
            <span>Flexible (60m)</span>
          </div>
        </div>
      </div>

      {/* Submit Button */}
      <button
        type="submit"
        disabled={createMutation.isPending}
        className="w-full py-2.5 px-4 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow-md disabled:opacity-50 flex items-center justify-center gap-2 transition-all"
      >
        {createMutation.isPending ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Creating Ride Request...
          </>
        ) : (
          'Publish Ride Request'
        )}
      </button>
    </form>
  );
}
