import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { AlertCircle, Loader2, Search, X } from 'lucide-react';
import { findRideMatches } from '@/services/ride-requests';
import type { MatchProposal } from '@/types/matching';
import type { RideRequestResponse } from '@/types/ride-request';

function scorePercent(score: number) {
  return `${Math.round(score * 100)}%`;
}

export function MatchResults({
  request,
  onClose,
}: {
  request: RideRequestResponse;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState<MatchProposal | null>(null);
  const discovery = useMutation({ mutationFn: () => findRideMatches(request.id) });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-label="Ride matches">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-5 shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Compatible ride requests</h2>
            <p className="text-sm text-gray-500">Suggestions only. No ride group is created.</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close matches" className="rounded-lg p-2 text-gray-500 hover:bg-gray-100"><X className="h-4 w-4" /></button>
        </div>

        {!discovery.data && !discovery.isPending && !discovery.isError && (
          <div className="py-8 text-center">
            <p className="mb-4 text-sm text-gray-600">Search active requests within 2 km of your pickup.</p>
            <button type="button" onClick={() => discovery.mutate()} className="inline-flex items-center gap-2 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700">
              <Search className="h-4 w-4" /> Find compatible rides
            </button>
          </div>
        )}

        {discovery.isPending && <div className="flex items-center justify-center gap-2 py-10 text-sm text-gray-600"><Loader2 className="h-5 w-5 animate-spin" /> Checking nearby requests and route options…</div>}
        {discovery.isError && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700"><AlertCircle className="mr-2 inline h-4 w-4" />{discovery.error.message}<button type="button" onClick={() => discovery.mutate()} className="ml-3 font-semibold underline">Try again</button></div>}
        {discovery.data && discovery.data.proposals.length === 0 && <p className="rounded-lg bg-gray-50 p-5 text-center text-sm text-gray-600">No compatible active requests found. Try again closer to your departure time.</p>}

        {!!discovery.data?.proposals.length && <div className="space-y-3">
          {discovery.data.proposals.map((proposal) => <article key={proposal.proposal_id} className="rounded-xl border border-gray-200 p-4">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div><h3 className="font-semibold text-gray-900">{proposal.candidate.candidate_display_name}</h3><p className="text-xs text-gray-500">Pickup {Math.round(proposal.candidate.pickup_distance_meters)} m away · destination {Math.round(proposal.candidate.destination_distance_meters / 100) / 10} km away</p></div>
              <span className="rounded-full bg-indigo-50 px-3 py-1 text-sm font-bold text-indigo-700">{scorePercent(proposal.candidate.scores.composite_score)} match</span>
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-600 sm:grid-cols-4">
              <span>Departure windows overlap</span><span>Your detour +{proposal.candidate.estimated_detour_minutes_target.toFixed(1)} min</span><span>Other detour +{proposal.candidate.estimated_detour_minutes_candidate.toFixed(1)} min</span><span>{proposal.total_shared_duration_minutes.toFixed(0)} min shared trip</span>
            </div>
            {(proposal.is_route_approximate || proposal.distance_is_approximate) && <p className="mt-3 rounded-md bg-amber-50 p-2 text-xs text-amber-800">{proposal.is_route_approximate ? `Approximate route estimate: ${proposal.routing_notice}` : 'Road-network duration estimate; shared distance is an approximate geographic calculation.'}</p>}
            <button type="button" onClick={() => setSelected(proposal)} className="mt-3 text-sm font-semibold text-indigo-700 hover:underline">Why this suggestion?</button>
            {selected?.proposal_id === proposal.proposal_id && <div className="mt-3 rounded-lg bg-gray-50 p-3 text-xs text-gray-700">
              <p className="mb-2 font-semibold">Compatibility breakdown</p>
              <ul className="mb-2 list-disc space-y-1 pl-4">{proposal.compatibility_explanations.map((explanation) => <li key={explanation}>{explanation}</li>)}</ul>
              <p>Pickup proximity {scorePercent(proposal.candidate.scores.pickup_proximity_score)} · destination and direction {scorePercent(proposal.candidate.scores.destination_similarity_score)} · departure timing {scorePercent(proposal.candidate.scores.departure_time_score)} · detour fit {scorePercent(proposal.candidate.scores.route_detour_score)}</p>
              <p className="mt-2">Stops: {proposal.ordered_stops.map((stop) => `${stop.stop_type.toLowerCase()} ${stop.location.label || `${stop.location.latitude.toFixed(3)}, ${stop.location.longitude.toFixed(3)}`}`).join(' → ')}</p>
              <p className="mt-1">Route accuracy: {proposal.routing_accuracy.replaceAll('_', ' ')}. Distance is approximate: {proposal.distance_is_approximate ? 'yes' : 'no'}. This is a proposal, not an accepted shared ride.</p>
            </div>}
          </article>)}
        </div>}
      </div>
    </div>
  );
}
