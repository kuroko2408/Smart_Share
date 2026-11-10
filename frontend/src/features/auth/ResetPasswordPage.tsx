/**
 * Dedicated Password Recovery / Reset Page for Smart Share.
 * Ingests recovery tokens from email redirect and allows users to set a new password.
 */
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AlertCircle,
  Car,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  Lock,
} from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';
import { getSupabase } from '@/lib/supabase';

export function ResetPasswordPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { updatePassword, loginWithToken, isAuthenticated, authError, clearError } = useAuth();

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  // Ingest recovery token from URL hash fragment or query parameter if present
  useEffect(() => {
    // Check hash fragment (#access_token=...&type=recovery)
    const hash = window.location.hash;
    if (hash && hash.includes('access_token')) {
      const params = new URLSearchParams(hash.replace(/^#/, ''));
      const accessToken = params.get('access_token');
      const type = params.get('type');
      if (accessToken && type === 'recovery') {
        loginWithToken(accessToken);
      }
    }

    // Check PKCE exchange if code is present in query parameters
    const searchParams = new URLSearchParams(location.search);
    const code = searchParams.get('code');
    const supabase = getSupabase();
    if (code && supabase) {
      supabase.auth.exchangeCodeForSession(code).then(({ data, error }) => {
        if (!error && data.session) {
          loginWithToken(data.session.access_token);
        }
      }).catch((err) => {
        console.warn('[reset-password] PKCE exchange error:', err);
      });
    }
  }, [location, loginWithToken]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (newPassword.length < 6) {
      setLocalError('Password must be at least 6 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setLocalError('Passwords do not match. Please re-enter your password.');
      return;
    }

    setIsSubmitting(true);
    try {
      await updatePassword(newPassword);
      setIsSuccess(true);
    } catch {
      // Handled in context
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeError = localError || authError;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-gray-100 flex items-center justify-center p-4 sm:p-6">
      <div className="max-w-md w-full bg-white/10 backdrop-blur-xl border border-white/20 rounded-3xl shadow-2xl p-6 sm:p-8 text-center space-y-6">
        
        {/* Header Icon */}
        <div className="w-14 h-14 rounded-2xl bg-indigo-500/20 border border-indigo-400/40 text-indigo-300 flex items-center justify-center mx-auto shadow-inner">
          <KeyRound className="w-7 h-7" />
        </div>

        <div>
          <h1 className="text-2xl font-extrabold text-white">Set New Password</h1>
          <p className="text-xs text-gray-400 mt-1">
            Choose a secure password with at least 6 characters.
          </p>
        </div>

        {/* Success State */}
        {isSuccess ? (
          <div className="space-y-4 py-2">
            <div className="p-4 bg-emerald-500/15 border border-emerald-500/40 text-emerald-200 text-xs rounded-xl flex items-center gap-3 text-left">
              <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              <div>
                <span className="font-bold">Password Updated Successfully!</span>
                <p className="text-2xs text-emerald-300/90 mt-0.5">
                  Your Smart Share account password has been updated. You can now access your cab-pooling dashboard.
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={() => navigate(isAuthenticated ? '/' : '/login')}
              className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg transition-colors cursor-pointer flex items-center justify-center gap-2"
            >
              <Car className="w-4 h-4" /> Go to Dashboard
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} noValidate className="space-y-4 text-left">
            {activeError && (
              <div
                role="alert"
                className="p-3 bg-red-500/15 border border-red-500/40 text-red-200 text-xs rounded-xl flex items-start gap-2.5"
              >
                <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                <div className="flex-1 font-medium">{activeError}</div>
              </div>
            )}

            <div>
              <label htmlFor="new-password" className="block text-xs font-semibold text-gray-300 mb-1.5">
                New Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-gray-400 absolute left-3.5 top-3 pointer-events-none" />
                <input
                  id="new-password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="At least 6 characters"
                  required
                  minLength={6}
                  className="w-full bg-slate-800/90 text-white text-xs pl-10 pr-10 py-2.5 rounded-xl border border-white/10 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all placeholder:text-gray-500 font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((prev) => !prev)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  aria-pressed={showPassword}
                  className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-200 transition-colors cursor-pointer"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div>
              <label htmlFor="confirm-new-password" className="block text-xs font-semibold text-gray-300 mb-1.5">
                Confirm New Password
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-gray-400 absolute left-3.5 top-3 pointer-events-none" />
                <input
                  id="confirm-new-password"
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="Repeat your new password"
                  required
                  minLength={6}
                  className="w-full bg-slate-800/90 text-white text-xs pl-10 pr-10 py-2.5 rounded-xl border border-white/10 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all placeholder:text-gray-500 font-mono"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword((prev) => !prev)}
                  aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                  aria-pressed={showConfirmPassword}
                  className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-200 transition-colors cursor-pointer"
                >
                  {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold rounded-xl shadow-lg disabled:opacity-50 flex items-center justify-center gap-2 transition-all cursor-pointer mt-2"
            >
              {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              Update Password
            </button>

            <div className="pt-2 text-center">
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors cursor-pointer font-medium"
              >
                Back to Sign In
              </button>
            </div>
          </form>
        )}

      </div>
    </div>
  );
}
