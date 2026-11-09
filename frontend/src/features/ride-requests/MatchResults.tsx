import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, Loader2, Route, Search, X } from 'lucide-react';
import { fetchMatchProposal, findRideMatches, grantFareDisclosureConsent, withdrawFareDisclosureConsent } from '@/services/ride-requests';
import type { MatchProposal } from '@/types/matching';
import type { RideRequestResponse } from '@/types/ride-request';

function scorePercent(score: number) {
  return `${Math.round(score * 100)}%`;
}

function formatRupees(amount: number) {
  return `₹${amount.toFixed(2)}`;
}

function routeDistanceLabel(source?: string) {
  if (source === 'provider_road_network_route') return 'road route';
  if (source === 'provider_matrix_table') return 'routing matrix estimate';
  if (source === 'calibrated_tortuosity_fallback') return 'approximate geographic route';
  if (source === 'geodesic_spheroid') return 'straight-line geographic estimate';
  return 'estimated route';
}

export function MatchResults({
  request,
  onClose,
}: {
  request: RideRequestResponse;
  onClose: () => void;
}) {
  const [selected, setSelected] = useState<MatchProposal | null>(null);
  const [proposalsMap, setProposalsMap] = useState<Record<string, MatchProposal>>({});
  const [loadingGeometryId, setLoadingGeometryId] = useState<string | null>(null);
  const [declinedConsentIds, setDeclinedConsentIds] = useState<string[]>([]);

  const consentMutation = useMutation({
    mutationFn: async ({ proposal, withdraw }: { proposal: MatchProposal; withdraw: boolean }) => {
      if (withdraw) {
        await withdrawFareDisclosureConsent(request.id, proposal.proposal_id);
      } else {
        const version = proposal.fare_allocation_disclosure?.consent_text_version;
        if (!version) throw new Error('The current disclosure notice is unavailable. Refresh the proposal.');
        await grantFareDisclosureConsent(request.id, proposal.proposal_id, version);
      }
      return fetchMatchProposal(request.id, proposal.proposal_id);
    },
    onSuccess: (proposal) => {
      setProposalsMap((prev) => ({ ...prev, [proposal.proposal_id]: proposal }));
      setSelected((current) => current?.proposal_id === proposal.proposal_id ? proposal : current);
    },
  });

  const discovery = useMutation({
    mutationFn: () => findRideMatches(request.id),
    onSuccess: (data) => {
      const map: Record<string, MatchProposal> = {};
      data.proposals.forEach((p) => {
        map[p.proposal_id] = p;
      });
      setProposalsMap(map);
    },
  });

  const handleLoadGeometry = async (proposalId: string) => {
    setLoadingGeometryId(proposalId);
    try {
      const enriched = await fetchMatchProposal(request.id, proposalId);
      setProposalsMap((prev) => ({
        ...prev,
        [proposalId]: enriched,
      }));
      if (selected?.proposal_id === proposalId) {
        setSelected(enriched);
      }
    } catch {
      // Keep existing proposal if load fails
    } finally {
      setLoadingGeometryId(null);
    }
  };

  const displayedProposals = discovery.data?.proposals.map(
    (p) => proposalsMap[p.proposal_id] || p
  ) || [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4" role="dialog" aria-modal="true" aria-label="Ride matches">
      <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-5 shadow-xl">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Compatible ride requests</h2>
            <p className="text-sm text-gray-500">Suggestions only. Pairwise matching with road route normalization.</p>
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

        {discovery.isPending && <div className="flex items-center justify-center gap-2 py-10 text-sm text-gray-600"><Loader2 className="h-5 w-5 animate-spin" /> Evaluating nearby candidates and road routing…</div>}
        {discovery.isError && <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700"><AlertCircle className="mr-2 inline h-4 w-4" />{discovery.error.message}<button type="button" onClick={() => discovery.mutate()} className="ml-3 font-semibold underline">Try again</button></div>}
        {discovery.data && displayedProposals.length === 0 && <p className="rounded-lg bg-gray-50 p-5 text-center text-sm text-gray-600">No compatible active requests found. Try again closer to your departure time.</p>}

        {!!displayedProposals.length && <div className="space-y-3">
          {displayedProposals.map((proposal) => {
            const targetMetrics = proposal.passenger_metrics?.[proposal.target_request_id];
            const candidateMetrics = proposal.passenger_metrics?.[proposal.candidate.candidate_request_id];
            const isGeometryReady = Boolean(proposal.route_geometry?.coordinates?.length);
            const isLoadingThis = loadingGeometryId === proposal.proposal_id;

            return (
              <article key={proposal.proposal_id} className="rounded-xl border border-gray-200 p-4">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="font-semibold text-gray-900">{proposal.candidate.candidate_display_name}</h3>
                    <p className="text-xs text-gray-500">
                      Pickup {Math.round(proposal.candidate.pickup_distance_meters)} m away · destination {Math.round(proposal.candidate.destination_distance_meters / 100) / 10} km away
                    </p>
                  </div>
                  <span className="rounded-full bg-indigo-50 px-3 py-1 text-sm font-bold text-indigo-700">
                    {scorePercent(proposal.candidate.scores.composite_score)} match
                  </span>
                </div>

                <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-gray-600 sm:grid-cols-4">
                  <span>Departure windows overlap</span>
                  <span>
                    Your detour +{proposal.candidate.estimated_detour_minutes_target.toFixed(1)} min
                    {targetMetrics ? ` (+${targetMetrics.detour_distance_km.toFixed(1)} km)` : ''}
                  </span>
                  <span>
                    Other detour +{proposal.candidate.estimated_detour_minutes_candidate.toFixed(1)} min
                    {candidateMetrics ? ` (+${candidateMetrics.detour_distance_km.toFixed(1)} km)` : ''}
                  </span>
                  <span>
                    {proposal.total_shared_duration_minutes.toFixed(0)} min ({proposal.total_shared_distance_km.toFixed(1)} km {routeDistanceLabel(proposal.distance_source)})
                  </span>
                </div>

                <div className="mt-2 flex flex-wrap items-center justify-between gap-2 pt-1">
                  <div className="flex items-center gap-2">
                    {isGeometryReady ? (
                      <span className="inline-flex items-center gap-1 rounded bg-emerald-50 px-2 py-0.5 text-[11px] font-medium text-emerald-700">
                        <CheckCircle2 className="h-3 w-3" /> Route geometry ready ({proposal.route_geometry?.coordinates.length} points)
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleLoadGeometry(proposal.proposal_id)}
                        disabled={isLoadingThis}
                        className="inline-flex items-center gap-1 rounded bg-gray-100 px-2 py-0.5 text-[11px] font-medium text-gray-700 hover:bg-gray-200 disabled:opacity-50"
                      >
                        {isLoadingThis ? <Loader2 className="h-3 w-3 animate-spin" /> : <Route className="h-3 w-3" />}
                        Load route geometry
                      </button>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => setSelected(selected?.proposal_id === proposal.proposal_id ? null : proposal)}
                    className="text-xs font-semibold text-indigo-700 hover:underline"
                  >
                    {selected?.proposal_id === proposal.proposal_id ? 'Hide details' : 'Why this suggestion?'}
                  </button>
                </div>

                {(proposal.is_route_approximate || proposal.distance_is_approximate) && (
                  <p className="mt-2 rounded-md bg-amber-50 p-2 text-xs text-amber-800">
                    {proposal.is_route_approximate
                      ? `Approximate route estimate: ${proposal.routing_notice}`
                      : 'Matrix-estimated distance; load full geometry for turn-by-turn road precision.'}
                  </p>
                )}

                {proposal.fare_estimate ? <section className="mt-3 rounded-lg border border-indigo-100 bg-indigo-50/60 p-3" aria-label="Pre-trip fare estimate">
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs font-semibold text-gray-800">Estimated pre-trip fare & allocation</p>
                    {proposal.fare_estimate.economic_status === 'SAVINGS' && proposal.fare_estimate.your_savings && proposal.fare_estimate.your_savings.estimate > 0 ? (
                      <span className="inline-flex items-center rounded-full bg-emerald-100 px-2 py-0.5 text-[11px] font-semibold text-emerald-800">
                        Save {formatRupees(proposal.fare_estimate.your_savings.estimate)} ({proposal.fare_estimate.your_savings_percent?.toFixed(1)}%)
                      </span>
                    ) : proposal.fare_estimate.economic_status === 'BREAK_EVEN' ? (
                      <span className="inline-flex items-center rounded-full bg-gray-200 px-2 py-0.5 text-[11px] font-semibold text-gray-700">
                        Break-even (₹0.00 saved)
                      </span>
                    ) : proposal.fare_estimate.economic_status === 'UNATTRACTIVE' ? (
                      <span className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-[11px] font-semibold text-amber-800">
                        Financially unattractive
                      </span>
                    ) : null}
                  </div>

                  <div className="mt-2 grid gap-1.5 text-xs text-gray-700 sm:grid-cols-3">
                    <div className="rounded bg-white/70 p-1.5 border border-indigo-50">
                      <span className="text-[11px] text-gray-500 block">Shared journey:</span>
                      <strong className="text-gray-900">{formatRupees(proposal.fare_estimate.shared_journey.estimate)}</strong>
                      <span className="text-[10px] text-gray-500 block">(original agreed fare · {proposal.fare_estimate.shared_journey.accuracy_tier.replaceAll('_', ' ').toLowerCase()})</span>
                    </div>
                    <div className="rounded bg-white/70 p-1.5 border border-indigo-50">
                      <span className="text-[11px] text-gray-500 block">Your solo baseline:</span>
                      <strong className="text-gray-900">{formatRupees(proposal.fare_estimate.your_solo_baseline.estimate)}</strong>
                      <span className="text-[10px] text-gray-500 block">({proposal.fare_estimate.your_solo_baseline.accuracy_tier.replaceAll('_', ' ').toLowerCase()})</span>
                    </div>
                    {proposal.fare_estimate.your_allocated_fare ? (
                      <div className="rounded bg-white/70 p-1.5 border border-indigo-50">
                        <span className="text-[11px] text-gray-500 block">Your allocated share:</span>
                        <strong className="text-indigo-700">{formatRupees(proposal.fare_estimate.your_allocated_fare.estimate)}</strong>
                        {proposal.fare_estimate.your_savings && proposal.fare_estimate.your_savings.estimate > 0 ? (
                          <span className="text-[10px] text-emerald-600 block font-medium">Save {formatRupees(proposal.fare_estimate.your_savings.estimate)}</span>
                        ) : proposal.fare_estimate.economic_status === 'UNATTRACTIVE' ? (
                          <span className="text-[10px] text-amber-700 block font-medium">+₹{Math.abs(proposal.fare_estimate.your_savings?.estimate || 0).toFixed(2)} vs solo</span>
                        ) : (
                          <span className="text-[10px] text-gray-500 block">No savings</span>
                        )}
                      </div>
                    ) : null}
                  </div>

                  {proposal.fare_estimate.shared_journey.surcharge_status === 'CONDITIONAL' && proposal.fare_estimate.shared_journey.fare_range && (
                    <p className="mt-1 text-xs text-amber-800">
                      Shared fare range for day/night tariff: {formatRupees(proposal.fare_estimate.shared_journey.fare_range.minimum.estimate)}–{formatRupees(proposal.fare_estimate.shared_journey.fare_range.maximum.estimate)}
                    </p>
                  )}
                  {proposal.fare_estimate.your_solo_baseline.surcharge_status === 'CONDITIONAL' && proposal.fare_estimate.your_solo_baseline.fare_range && (
                    <p className="mt-1 text-xs text-amber-800">
                      Your solo baseline day/night range: {formatRupees(proposal.fare_estimate.your_solo_baseline.fare_range.minimum.estimate)}–{formatRupees(proposal.fare_estimate.your_solo_baseline.fare_range.maximum.estimate)}
                    </p>
                  )}
                  <p className="mt-1 text-[11px] text-gray-600">
                    {proposal.fare_estimate.pulse_quantization_mode} estimate · accuracy: {proposal.fare_estimate.composite_accuracy.replaceAll('_', ' ').toLowerCase()}
                  </p>
                  <p className="mt-1 text-[11px] text-gray-500">
                    DEC-013 privacy notice: Co-passenger baseline and contribution remain confidential until bilateral consent. Driver receives 100% of agreed shared fare.
                  </p>
                  <p className="mt-1 text-[11px] text-gray-600">{proposal.fare_estimate.disclaimer}</p>
                </section> : <p className="mt-3 rounded-lg bg-amber-50 p-3 text-xs text-amber-800">Fare estimate is unavailable for this route. The match suggestion remains available with its routing accuracy shown above.</p>}

                {proposal.economic_assessment && (
                  <section
                    aria-label="Economic comparison"
                    className={`mt-2 rounded-lg border p-3 text-xs ${
                      proposal.economic_assessment.classification === 'NEGATIVE'
                        ? 'border-amber-300 bg-amber-50 text-amber-900'
                        : proposal.economic_assessment.classification === 'POSITIVE'
                          ? 'border-emerald-200 bg-emerald-50 text-emerald-900'
                          : 'border-gray-200 bg-gray-50 text-gray-700'
                    }`}
                  >
                    <p className="font-semibold">
                      {proposal.economic_assessment.classification === 'NEGATIVE'
                        ? 'Not a money-saving option'
                        : proposal.economic_assessment.classification === 'POSITIVE'
                          ? 'Estimated lower combined cost'
                          : proposal.economic_assessment.classification === 'CONDITIONAL'
                            ? 'Cost comparison depends on the tariff window'
                            : 'Estimated break-even'}
                    </p>
                    <p className="mt-1">{proposal.economic_assessment.message}</p>
                  </section>
                )}

                {proposal.fare_allocation_disclosure && (
                  <section className="mt-2 rounded-lg border border-gray-200 bg-white p-3 text-xs text-gray-700" aria-label="Fare contribution disclosure">
                    <p className="font-semibold text-gray-900">Optional exact contribution disclosure</p>
                    <p className="mt-1">{proposal.fare_allocation_disclosure.consent_notice}</p>
                    <p className="mt-1">This is separate consent for sharing the exact contribution with the other passenger. It does not accept the ride.</p>
                    {proposal.fare_allocation_disclosure.exact_disclosure_available && proposal.fare_allocation_disclosure.allocation ? (
                      <div className="mt-2 rounded bg-emerald-50 p-2 text-emerald-900">
                        <p>Total shared taxi trip estimate: <strong>{formatRupees(proposal.fare_allocation_disclosure.allocation.shared_total)}</strong></p>
                        <p>Your share of that estimate: <strong>{formatRupees(proposal.fare_allocation_disclosure.allocation.your_contribution)}</strong></p>
                        <p>Other passenger's share: <strong>{formatRupees(proposal.fare_allocation_disclosure.allocation.co_passenger_contribution)}</strong></p>
                        <p>Your estimated savings versus your separate trip: <strong>{formatRupees(proposal.fare_allocation_disclosure.allocation.your_savings)} ({Number(proposal.fare_allocation_disclosure.allocation.your_savings_percent).toFixed(2)}%)</strong></p>
                        <p className="mt-1 text-[11px]">Only your own solo baseline and savings are shown. The other passenger’s solo baseline and savings remain private.</p>
                        <button type="button" onClick={() => consentMutation.mutate({ proposal, withdraw: true })} disabled={consentMutation.isPending} className="mt-2 font-semibold underline disabled:opacity-50">Withdraw my consent</button>
                      </div>
                    ) : proposal.fare_allocation_disclosure.exact_disclosure_available && (proposal.fare_allocation_disclosure.conditional_scenarios?.length ?? 0) > 0 ? (
                      <div className="mt-2 space-y-2 rounded bg-amber-50 p-2 text-amber-950">
                        <p className="font-semibold">Contributions depend on the tariff time</p>
                        {proposal.fare_allocation_disclosure.conditional_scenarios?.map((scenario) => (
                          <div key={scenario.tariff_period} className="rounded border border-amber-200 bg-white p-2">
                            <p className="font-semibold">{scenario.tariff_period === 'DAY' ? 'Day tariff' : 'Night tariff'} · {scenario.economic_classification === 'POSITIVE' ? 'lower estimated total' : scenario.economic_classification === 'NEGATIVE' ? 'higher estimated total' : 'approximately break-even'}</p>
                            <p>Shared taxi estimate: {formatRupees(scenario.shared_total)}</p>
                            <p>Your contribution: {formatRupees(scenario.your_contribution)} · Other passenger: {formatRupees(scenario.co_passenger_contribution)}</p>
                            <p>Your estimated savings versus your separate trip: {formatRupees(scenario.your_savings)} ({Number(scenario.your_savings_percent).toFixed(2)}%)</p>
                          </div>
                        ))}
                        <p className="text-[11px]">Only your own solo baseline and savings are shown. The other passenger’s solo baseline and savings remain private.</p>
                        <button type="button" onClick={() => consentMutation.mutate({ proposal, withdraw: true })} disabled={consentMutation.isPending} className="mt-1 font-semibold underline disabled:opacity-50">Withdraw my consent</button>
                      </div>
                    ) : (
                      <div className="mt-2">
                        <p>{proposal.fare_allocation_disclosure.your_consent_active ? 'Your consent is recorded.' : declinedConsentIds.includes(proposal.proposal_id) ? 'You chose not to consent in this view. Exact contribution amounts remain hidden.' : 'Your consent has not been given.'} {proposal.fare_allocation_disclosure.co_passenger_consent_active ? 'The other passenger has consented.' : 'The other passenger must also consent before exact amounts are shown.'}</p>
                        {!proposal.fare_allocation_disclosure.your_consent_active && !declinedConsentIds.includes(proposal.proposal_id) && <div className="mt-2 flex flex-wrap gap-2"><button type="button" onClick={() => consentMutation.mutate({ proposal, withdraw: false })} disabled={consentMutation.isPending} className="rounded bg-indigo-600 px-3 py-1.5 font-semibold text-white disabled:opacity-50">{consentMutation.isPending ? 'Recording…' : 'I agree to exact disclosure'}</button><button type="button" onClick={() => setDeclinedConsentIds((ids) => [...ids, proposal.proposal_id])} className="rounded border border-gray-300 px-3 py-1.5 font-semibold text-gray-700">No thanks</button></div>}
                        {declinedConsentIds.includes(proposal.proposal_id) && <button type="button" onClick={() => setDeclinedConsentIds((ids) => ids.filter((id) => id !== proposal.proposal_id))} className="mt-2 font-semibold text-indigo-700 underline">Review consent notice</button>}
                        {proposal.fare_allocation_disclosure.your_consent_active && <button type="button" onClick={() => consentMutation.mutate({ proposal, withdraw: true })} disabled={consentMutation.isPending} className="mt-2 font-semibold text-indigo-700 underline disabled:opacity-50">Withdraw my consent</button>}
                        {consentMutation.isError && <p role="alert" className="mt-2 text-red-700">{consentMutation.error.message}</p>}
                      </div>
                    )}
                  </section>
                )}

                {selected?.proposal_id === proposal.proposal_id && (
                  <div className="mt-3 rounded-lg bg-gray-50 p-3 text-xs text-gray-700">
                    <p className="mb-2 font-semibold">Compatibility & Route breakdown</p>
                    <ul className="mb-2 list-disc space-y-1 pl-4">
                      {proposal.compatibility_explanations.map((explanation) => (
                        <li key={explanation}>{explanation}</li>
                      ))}
                    </ul>
                    <p>
                      Pickup proximity {scorePercent(proposal.candidate.scores.pickup_proximity_score)} · destination and direction {scorePercent(proposal.candidate.scores.destination_similarity_score)} · departure timing {scorePercent(proposal.candidate.scores.departure_time_score)} · detour fit {scorePercent(proposal.candidate.scores.route_detour_score)}
                    </p>
                    <p className="mt-2 font-medium">
                      Sequence ({proposal.best_sequence}): {proposal.ordered_stops.map((stop) => `${stop.stop_type.toLowerCase()} ${stop.location.label || `${stop.location.latitude.toFixed(3)}, ${stop.location.longitude.toFixed(3)}`}`).join(' → ')}
                    </p>
                    {proposal.route_legs && proposal.route_legs.length > 0 && (
                      <div className="mt-2 rounded border border-gray-200 bg-white p-2">
                        <p className="font-semibold text-gray-800 mb-1">Route legs breakdown:</p>
                        <div className="space-y-1">
                          {proposal.route_legs.map((leg) => (
                            <div key={leg.sequence} className="flex justify-between text-[11px] text-gray-600">
                              <span>Leg {leg.sequence}: {leg.start_label || 'Stop'} → {leg.end_label || 'Stop'}</span>
                              <span className="font-mono">{leg.distance_km.toFixed(2)} km ({leg.duration_minutes.toFixed(1)} min)</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                    <p className="mt-2 text-[11px] text-gray-500">
                      Routing accuracy: {proposal.routing_accuracy.replaceAll('_', ' ')} · Source: {proposal.distance_source?.replaceAll('_', ' ') || 'standard'} · Detour gating: time-based. This is a proposal, not an accepted ride.
                    </p>
                  </div>
                )}
              </article>
            );
          })}
        </div>}
      </div>
    </div>
  );
}
