import { useQuery } from '@tanstack/react-query';
import { Car, Wifi, WifiOff, Loader2 } from 'lucide-react';
import { checkBackendHealth } from '@/services/health';

export function HomePage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['health'],
    queryFn: checkBackendHealth,
    retry: false,
    refetchInterval: 30_000,
  });

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col items-center justify-center p-6">
      <div className="bg-white rounded-2xl shadow-lg p-8 max-w-md w-full text-center space-y-6">
        <div className="flex items-center justify-center gap-3">
          <Car className="w-10 h-10 text-indigo-600" />
          <h1 className="text-3xl font-bold text-gray-900">Smart Share</h1>
        </div>

        <p className="text-gray-500 text-sm font-medium tracking-wide uppercase">
          Intelligent, Location-Based Cab Pooling
        </p>

        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-amber-800 text-sm font-medium">
          🚧 Under Development — NOVEX 2026 Hackathon
        </div>

        <div className="border-t pt-4">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-3 font-semibold">
            Backend Status
          </p>
          {isLoading && (
            <div className="flex items-center justify-center gap-2 text-gray-500 text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              Checking connection…
            </div>
          )}
          {isError && (
            <div className="flex items-center justify-center gap-2 text-red-500 text-sm">
              <WifiOff className="w-4 h-4" />
              Backend unreachable
            </div>
          )}
          {data && (
            <div className="flex items-center justify-center gap-2 text-green-600 text-sm">
              <Wifi className="w-4 h-4" />
              Backend connected — {data.status}
            </div>
          )}
        </div>

        <p className="text-xs text-gray-400">
          This prototype coordinates passenger matching and ride pooling. It is not an operational
          cab-dispatch service.
        </p>
      </div>
    </div>
  );
}
