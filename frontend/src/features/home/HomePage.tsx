/**
 * Main Home & Minimal Integration Screen for Smart Share Phase 2.
 * Includes:
 * - Live backend connection status monitor
 * - Real Supabase / Bearer token authentication flow
 * - Authenticated user profile retrieval & display
 * - Loading, success, and error states
 * - Expired and unauthorized session handling
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  AlertTriangle,
  Car,
  Key,
  Loader2,
  Lock,
  LogOut,
  Mail,
  ShieldCheck,
  Wifi,
  WifiOff,
} from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';
import { ProfileCard } from '@/features/profile/ProfileCard';
import { env } from '@/lib/env';
import { checkBackendHealth } from '@/services/health';

export function HomePage() {
  const {
    session,
    isAuthenticated,
    isSessionExpired,
    authError,
    loginWithEmail,
    loginWithToken,
    logout,
    clearError,
  } = useAuth();

  const [authMode, setAuthMode] = useState<'token' | 'supabase'>('token');
  const [emailInput, setEmailInput] = useState('');
  const [passwordInput, setPasswordInput] = useState('');
  const [tokenInput, setTokenInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { data: healthData, isLoading: isHealthLoading, isError: isHealthError } = useQuery({
    queryKey: ['health'],
    queryFn: checkBackendHealth,
    retry: false,
    refetchInterval: 30_000,
  });

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!emailInput || !passwordInput) return;
    setIsSubmitting(true);
    try {
      await loginWithEmail(emailInput, passwordInput);
      setEmailInput('');
      setPasswordInput('');
    } catch {
      // Handled in context
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleTokenSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!tokenInput.trim()) return;
    setIsSubmitting(true);
    try {
      loginWithToken(tokenInput.trim());
      setTokenInput('');
    } catch {
      // Handled in context
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col items-center justify-center p-4 sm:p-6">
      <div className="bg-white rounded-2xl shadow-lg p-6 sm:p-8 max-w-lg w-full text-center space-y-6">
        {/* Header */}
        <div className="flex items-center justify-center gap-3">
          <Car className="w-10 h-10 text-indigo-600" />
          <h1 className="text-3xl font-bold text-gray-900">Smart Share</h1>
        </div>

        <p className="text-gray-500 text-sm font-medium tracking-wide uppercase">
          Intelligent, Location-Based Cab Pooling
        </p>

        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-2.5 text-amber-800 text-sm font-medium">
          🚧 Under Development — NOVEX 2026 Hackathon
        </div>

        {/* Backend Status Section */}
        <div className="border-t pt-4">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-3 font-semibold">
            Backend Status
          </p>
          {isHealthLoading && (
            <div className="flex items-center justify-center gap-2 text-gray-500 text-sm">
              <Loader2 className="w-4 h-4 animate-spin" />
              Checking connection…
            </div>
          )}
          {isHealthError && (
            <div className="flex items-center justify-center gap-2 text-red-500 text-sm font-medium">
              <WifiOff className="w-4 h-4" />
              Backend unreachable
            </div>
          )}
          {healthData && (
            <div className="flex items-center justify-center gap-2 text-green-600 text-sm font-medium">
              <Wifi className="w-4 h-4" />
              Backend connected — {healthData.status}
            </div>
          )}
        </div>

        {/* Expired Session Alert */}
        {isSessionExpired && (
          <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-lg flex items-center gap-2 text-left">
            <AlertTriangle className="w-4 h-4 shrink-0 text-red-500" />
            <div>
              <span className="font-semibold">Session Expired or Unauthorized:</span> Please re-authenticate with valid credentials.
            </div>
          </div>
        )}

        {/* Authenticated State vs Login State */}
        {isAuthenticated && session ? (
          <div className="border-t pt-5 space-y-4">
            <div className="flex items-center justify-between text-xs text-gray-500 px-1">
              <span className="flex items-center gap-1 font-semibold text-indigo-700">
                <ShieldCheck className="w-4 h-4" /> Authenticated Session
              </span>
              <button
                type="button"
                onClick={logout}
                className="inline-flex items-center gap-1 text-gray-500 hover:text-red-600 transition-colors"
                title="Sign out of current session"
              >
                <LogOut className="w-3.5 h-3.5" /> Sign Out
              </button>
            </div>

            {/* Profile Card displaying real profile from GET /users/me */}
            <ProfileCard />
          </div>
        ) : (
          <div className="border-t pt-5 space-y-4 text-left">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wide">
                Authentication & Integration
              </h2>
              {/* Mode switch */}
              <div className="flex bg-gray-100 p-0.5 rounded-lg text-xs font-medium">
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode('token');
                    clearError();
                  }}
                  className={`px-2.5 py-1 rounded-md transition-all ${
                    authMode === 'token'
                      ? 'bg-white text-indigo-600 shadow-xs font-semibold'
                      : 'text-gray-500 hover:text-gray-800'
                  }`}
                >
                  Bearer Token
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAuthMode('supabase');
                    clearError();
                  }}
                  className={`px-2.5 py-1 rounded-md transition-all ${
                    authMode === 'supabase'
                      ? 'bg-white text-indigo-600 shadow-xs font-semibold'
                      : 'text-gray-500 hover:text-gray-800'
                  }`}
                >
                  Supabase Auth
                </button>
              </div>
            </div>

            {/* Auth error message */}
            {authError && (
              <div className="p-2.5 bg-red-50 border border-red-200 text-red-600 text-xs rounded-lg flex items-start gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{authError}</span>
              </div>
            )}

            {/* Bearer Token Input Mode */}
            {authMode === 'token' && (
              <form onSubmit={handleTokenSubmit} className="space-y-3">
                <p className="text-xs text-gray-500">
                  Provide a Supabase JWT or development access token to authenticate and retrieve your profile from the backend.
                </p>
                <div>
                  <label htmlFor="auth-token" className="block text-xs font-semibold text-gray-700 mb-1">
                    Bearer Access Token
                  </label>
                  <div className="relative">
                    <Key className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
                    <input
                      id="auth-token"
                      type="text"
                      value={tokenInput}
                      onChange={(e) => setTokenInput(e.target.value)}
                      placeholder="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
                      required
                      className="w-full text-xs pl-9 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 font-mono"
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={isSubmitting || !tokenInput.trim()}
                  className="w-full py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm disabled:opacity-50 flex items-center justify-center gap-1.5 transition-colors"
                >
                  {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Connect Session
                </button>
              </form>
            )}

            {/* Supabase Password Sign-in Mode */}
            {authMode === 'supabase' && (
              <form onSubmit={handleEmailSubmit} className="space-y-3">
                {!env.supabaseUrl && (
                  <p className="text-2xs text-amber-600 bg-amber-50 p-2 rounded border border-amber-200">
                    Note: VITE_SUPABASE_URL is not set in frontend/.env.local. Configure your Supabase project settings to enable direct password sign-in.
                  </p>
                )}
                <div>
                  <label htmlFor="auth-email" className="block text-xs font-semibold text-gray-700 mb-1">
                    Email Address
                  </label>
                  <div className="relative">
                    <Mail className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
                    <input
                      id="auth-email"
                      type="email"
                      value={emailInput}
                      onChange={(e) => setEmailInput(e.target.value)}
                      placeholder="user@example.com"
                      required
                      className="w-full text-xs pl-9 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>
                </div>
                <div>
                  <label htmlFor="auth-pass" className="block text-xs font-semibold text-gray-700 mb-1">
                    Password
                  </label>
                  <div className="relative">
                    <Lock className="w-4 h-4 text-gray-400 absolute left-3 top-2.5" />
                    <input
                      id="auth-pass"
                      type="password"
                      value={passwordInput}
                      onChange={(e) => setPasswordInput(e.target.value)}
                      placeholder="••••••••"
                      required
                      className="w-full text-xs pl-9 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                    />
                  </div>
                </div>
                <button
                  type="submit"
                  disabled={isSubmitting || !emailInput || !passwordInput}
                  className="w-full py-2 px-4 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm disabled:opacity-50 flex items-center justify-center gap-1.5 transition-colors"
                >
                  {isSubmitting && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  Sign In with Supabase
                </button>
              </form>
            )}
          </div>
        )}

        {/* Disclaimer footer */}
        <p className="text-xs text-gray-400 border-t pt-3">
          This prototype coordinates passenger matching and ride pooling. It is not an operational
          cab-dispatch service.
        </p>
      </div>
    </div>
  );
}
