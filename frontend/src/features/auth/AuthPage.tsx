/**
 * Polished, accessible, and responsive Authentication Page for Smart Share.
 * Implements Sign In, Create Account (Sign Up), and Forgot Password flows
 * aligned with the core Smart Share design system and urban mobility visual identity.
 */
import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  AlertCircle,
  Car,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Eye,
  EyeOff,
  Key,
  Leaf,
  Loader2,
  Lock,
  Mail,
  MapPin,
  Shield,
  User as UserIcon,
} from 'lucide-react';
import { useAuth } from '@/features/auth/AuthContext';

interface AuthPageProps {
  initialMode?: 'signin' | 'signup' | 'forgot';
}

export function AuthPage({ initialMode = 'signin' }: AuthPageProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const {
    isAuthenticated,
    loginWithEmail,
    signUpWithEmail,
    loginWithToken,
    sendPasswordReset,
    authError,
    clearError,
  } = useAuth();

  const [mode, setMode] = useState<'signin' | 'signup' | 'forgot'>(initialMode);

  // Form inputs
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [rememberMe, setRememberMe] = useState(true);
  const [agreedToTerms, setAgreedToTerms] = useState(false);

  // Password visibility
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Status & local validation
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [successNotice, setSuccessNotice] = useState<string | null>(null);
  const [emailConfirmationRequired, setEmailConfirmationRequired] = useState(false);

  // Developer token access accordion
  const [isDevTokenOpen, setIsDevTokenOpen] = useState(false);
  const [tokenInput, setTokenInput] = useState('');

  // If already authenticated, redirect to destination or home
  useEffect(() => {
    if (isAuthenticated) {
      const stateFrom = (location.state as { from?: { pathname?: string } })?.from?.pathname;
      navigate(stateFrom || '/', { replace: true });
    }
  }, [isAuthenticated, navigate, location.state]);

  const validateEmail = (val: string): boolean => {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val.trim());
  };

  const handleModeChange = (newMode: 'signin' | 'signup' | 'forgot') => {
    setMode(newMode);
    setLocalError(null);
    setSuccessNotice(null);
    setEmailConfirmationRequired(false);
    clearError();
  };

  const handleSignInSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim()) {
      setLocalError('Please enter your email address.');
      return;
    }
    if (!validateEmail(email)) {
      setLocalError('Please enter a valid email address.');
      return;
    }
    if (!password) {
      setLocalError('Please enter your password.');
      return;
    }

    setIsSubmitting(true);
    try {
      await loginWithEmail(email.trim(), password, rememberMe);
    } catch {
      // Error is handled and stored in AuthContext authError
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSignUpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!fullName.trim()) {
      setLocalError('Please enter your full name.');
      return;
    }
    if (!email.trim()) {
      setLocalError('Please enter your email address.');
      return;
    }
    if (!validateEmail(email)) {
      setLocalError('Please enter a valid email address.');
      return;
    }
    if (password.length < 6) {
      setLocalError('Password must be at least 6 characters long.');
      return;
    }
    if (password !== confirmPassword) {
      setLocalError('Passwords do not match. Please re-enter your password.');
      return;
    }
    if (!agreedToTerms) {
      setLocalError('You must agree to the Terms of Service and Privacy Policy.');
      return;
    }

    setIsSubmitting(true);
    try {
      const res = await signUpWithEmail(email.trim(), password, fullName.trim());
      if (res.requiresEmailConfirmation) {
        setEmailConfirmationRequired(true);
      }
    } catch {
      // Handled in context
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleForgotPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim()) {
      setLocalError('Please enter your email address.');
      return;
    }
    if (!validateEmail(email)) {
      setLocalError('Please enter a valid email address.');
      return;
    }

    setIsSubmitting(true);
    try {
      await sendPasswordReset(email.trim());
      setSuccessNotice(
        `A password recovery link has been dispatched to ${email.trim()}. Please check your inbox.`
      );
    } catch {
      // Handled in context
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDevTokenSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!tokenInput.trim()) {
      setLocalError('Please paste a valid access token.');
      return;
    }

    try {
      loginWithToken(tokenInput.trim());
      setTokenInput('');
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Invalid token');
    }
  };

  const activeError = localError || authError;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col items-center justify-center p-4 sm:p-6 lg:p-8">
      <div className="max-w-4xl w-full bg-white rounded-2xl shadow-xl border border-gray-200/80 overflow-hidden grid grid-cols-1 lg:grid-cols-12 transition-all">
        
        {/* Left Branding & Mobility Value Proposition Column (Desktop / Tablet) */}
        <div className="lg:col-span-5 bg-slate-50/90 p-6 sm:p-8 lg:p-10 flex flex-col justify-between border-b lg:border-b-0 lg:border-r border-gray-200">
          <div>
            {/* Header Brand Badge */}
            <div className="flex items-center gap-3 mb-6">
              <div className="w-11 h-11 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600 shadow-xs">
                <Car className="w-6 h-6" />
              </div>
              <div>
                <span className="text-2xs font-semibold uppercase tracking-wider text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-200">
                  Mumbai Hub
                </span>
                <h1 className="text-2xl font-bold tracking-tight text-gray-900 mt-0.5">
                  Smart Share
                </h1>
              </div>
            </div>

            <h2 className="text-lg sm:text-xl font-bold text-gray-900 leading-snug">
              Intelligent Cab-Pooling for Mumbai
            </h2>
            <p className="text-xs sm:text-sm text-gray-600 mt-2 leading-relaxed">
              Cut daily commute expenses, bypass suburban congestion, and travel safely along Western Express, BKC, and Sea Link corridors.
            </p>

            {/* Feature Highlights */}
            <div className="mt-8 space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shrink-0 mt-0.5">
                  <MapPin className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-gray-900">Smart Corridor Matching</h4>
                  <p className="text-2xs text-gray-500 leading-relaxed mt-0.5">
                    Auto-clusters riders along Terminal 1, Bandra, Lower Parel, and Andheri east routes.
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shrink-0 mt-0.5">
                  <Shield className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-gray-900">Fair & Consented Fare Splitting</h4>
                  <p className="text-2xs text-gray-500 leading-relaxed mt-0.5">
                    Proportional cost breakdown verified under bilateral disclosure protection (DEC-013).
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shrink-0 mt-0.5">
                  <Leaf className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="text-xs font-semibold text-gray-900">Green & Reliable Commuting</h4>
                  <p className="text-2xs text-gray-500 leading-relaxed mt-0.5">
                    Reduce Mumbai vehicular emissions while traveling in certified comfort.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Callout */}
          <div className="mt-8 pt-5 border-t border-gray-200 text-2xs text-gray-500 flex items-center justify-between">
            <span>Terminal 1 Airport & Corporate Hubs</span>
            <span className="font-mono text-2xs font-semibold text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
              NOVEX 2026
            </span>
          </div>
        </div>

        {/* Right Form Column */}
        <div className="lg:col-span-7 bg-white p-6 sm:p-8 lg:p-10 flex flex-col justify-center">
          
          {/* Email Confirmation Screen */}
          {emailConfirmationRequired ? (
            <div className="text-center py-6 space-y-4">
              <div className="w-14 h-14 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center mx-auto">
                <Mail className="w-7 h-7" />
              </div>
              <h3 className="text-xl font-bold text-gray-900">Verify Your Email</h3>
              <p className="text-xs sm:text-sm text-gray-600 max-w-md mx-auto leading-relaxed">
                We sent a verification link to <span className="font-semibold text-indigo-600">{email}</span>. Please click the link inside your email to activate your account and start pooling rides.
              </p>
              <div className="pt-2">
                <button
                  type="button"
                  onClick={() => handleModeChange('signin')}
                  className="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors cursor-pointer"
                >
                  Return to Sign In
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              
              {/* Top Navigation Tabs */}
              {mode !== 'forgot' && (
                <div className="flex bg-gray-100 p-1 rounded-xl text-xs font-semibold border border-gray-200/60" role="tablist">
                  <button
                    type="button"
                    role="tab"
                    aria-selected={mode === 'signin'}
                    onClick={() => handleModeChange('signin')}
                    className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                      mode === 'signin'
                        ? 'bg-white text-indigo-600 shadow-xs font-bold'
                        : 'text-gray-500 hover:text-gray-800 font-medium'
                    }`}
                  >
                    Sign In
                  </button>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={mode === 'signup'}
                    onClick={() => handleModeChange('signup')}
                    className={`flex-1 py-2 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                      mode === 'signup'
                        ? 'bg-white text-indigo-600 shadow-xs font-bold'
                        : 'text-gray-500 hover:text-gray-800 font-medium'
                    }`}
                  >
                    Create Account
                  </button>
                </div>
              )}

              {/* Forgot Password Header */}
              {mode === 'forgot' && (
                <div className="flex items-center justify-between pb-3 border-b border-gray-200">
                  <div>
                    <h3 className="text-lg font-bold text-gray-900">Reset Your Password</h3>
                    <p className="text-xs text-gray-500 mt-0.5">
                      Enter your account email to receive a recovery link.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleModeChange('signin')}
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 transition-colors cursor-pointer"
                  >
                    Back to Sign In
                  </button>
                </div>
              )}

              {/* Alert Banners */}
              {activeError && (
                <div
                  role="alert"
                  className="p-3 bg-red-50 border border-red-200 text-red-700 text-xs rounded-xl flex items-start gap-2.5"
                >
                  <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                  <div className="flex-1 text-left font-medium">{activeError}</div>
                  <button
                    type="button"
                    onClick={() => {
                      setLocalError(null);
                      clearError();
                    }}
                    className="text-red-500 hover:text-red-700 text-xs font-bold cursor-pointer"
                    aria-label="Dismiss alert"
                  >
                    ✕
                  </button>
                </div>
              )}

              {successNotice && (
                <div
                  role="status"
                  className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-xl flex items-start gap-2.5"
                >
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  <div className="flex-1 text-left font-medium">{successNotice}</div>
                </div>
              )}

              {/* Sign In Form */}
              {mode === 'signin' && (
                <form onSubmit={handleSignInSubmit} noValidate className="space-y-4 text-left">
                  <div>
                    <label htmlFor="login-email" className="block text-xs font-semibold text-gray-700 mb-1.5">
                      Email Address
                    </label>
                    <div className="relative">
                      <Mail className="w-4 h-4 text-gray-400 absolute left-3.5 top-3 pointer-events-none" />
                      <input
                        id="login-email"
                        type="email"
                        autoComplete="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="commuter@example.com"
                        required
                        className="w-full bg-white text-gray-900 text-xs pl-10 pr-3 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors placeholder:text-gray-400"
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="login-password" className="block text-xs font-semibold text-gray-700 mb-1.5">
                      Password
                    </label>
                    <div className="relative">
                      <Lock className="w-4 h-4 text-gray-400 absolute left-3.5 top-3 pointer-events-none" />
                      <input
                        id="login-password"
                        type={showPassword ? 'text' : 'password'}
                        autoComplete="current-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="••••••••"
                        required
                        className="w-full bg-white text-gray-900 text-xs pl-10 pr-10 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors placeholder:text-gray-400 font-mono"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((prev) => !prev)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                        aria-pressed={showPassword}
                        className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer p-0.5"
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Remember Me & Forgot Password Row */}
                  <div className="flex items-center justify-between text-xs text-gray-600 pt-1">
                    <label className="flex items-center gap-2 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        checked={rememberMe}
                        onChange={(e) => setRememberMe(e.target.checked)}
                        className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 cursor-pointer"
                      />
                      <span>Remember this device</span>
                    </label>

                    <button
                      type="button"
                      onClick={() => handleModeChange('forgot')}
                      className="text-xs font-medium text-indigo-600 hover:text-indigo-700 transition-colors cursor-pointer"
                    >
                      Forgot password?
                    </button>
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full py-2.5 sm:py-3 px-4 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white text-xs sm:text-sm font-semibold rounded-lg shadow-xs hover:shadow-sm disabled:opacity-50 flex items-center justify-center gap-2 transition-colors cursor-pointer mt-2"
                  >
                    {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                    Sign In
                  </button>
                </form>
              )}

              {/* Sign Up Form */}
              {mode === 'signup' && (
                <form onSubmit={handleSignUpSubmit} noValidate className="space-y-3.5 text-left">
                  <div>
                    <label htmlFor="signup-name" className="block text-xs font-semibold text-gray-700 mb-1">
                      Full Name
                    </label>
                    <div className="relative">
                      <UserIcon className="w-4 h-4 text-gray-400 absolute left-3.5 top-3 pointer-events-none" />
                      <input
                        id="signup-name"
                        type="text"
                        autoComplete="name"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        placeholder="e.g. Priya Sharma"
                        required
                        className="w-full bg-white text-gray-900 text-xs pl-10 pr-3 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors placeholder:text-gray-400"
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="signup-email" className="block text-xs font-semibold text-gray-700 mb-1">
                      Email Address
                    </label>
                    <div className="relative">
                      <Mail className="w-4 h-4 text-gray-400 absolute left-3.5 top-3 pointer-events-none" />
                      <input
                        id="signup-email"
                        type="email"
                        autoComplete="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="priya@example.com"
                        required
                        className="w-full bg-white text-gray-900 text-xs pl-10 pr-3 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors placeholder:text-gray-400"
                      />
                    </div>
                  </div>

                  <div>
                    <label htmlFor="signup-password" className="block text-xs font-semibold text-gray-700 mb-1">
                      Password
                    </label>
                    <div className="relative">
                      <Lock className="w-4 h-4 text-gray-400 absolute left-3.5 top-3 pointer-events-none" />
                      <input
                        id="signup-password"
                        type={showPassword ? 'text' : 'password'}
                        autoComplete="new-password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        placeholder="At least 6 characters"
                        required
                        minLength={6}
                        className="w-full bg-white text-gray-900 text-xs pl-10 pr-10 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors placeholder:text-gray-400 font-mono"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword((prev) => !prev)}
                        aria-label={showPassword ? 'Hide password' : 'Show password'}
                        aria-pressed={showPassword}
                        className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer p-0.5"
                      >
                        {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                    <p className="text-2xs text-gray-500 mt-1">Must be at least 6 characters.</p>
                  </div>

                  <div>
                    <label htmlFor="signup-confirm-password" className="block text-xs font-semibold text-gray-700 mb-1">
                      Confirm Password
                    </label>
                    <div className="relative">
                      <Lock className="w-4 h-4 text-gray-400 absolute left-3.5 top-3 pointer-events-none" />
                      <input
                        id="signup-confirm-password"
                        type={showConfirmPassword ? 'text' : 'password'}
                        autoComplete="new-password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="Repeat your password"
                        required
                        minLength={6}
                        className="w-full bg-white text-gray-900 text-xs pl-10 pr-10 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors placeholder:text-gray-400 font-mono"
                      />
                      <button
                        type="button"
                        onClick={() => setShowConfirmPassword((prev) => !prev)}
                        aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                        aria-pressed={showConfirmPassword}
                        className="absolute right-3 top-2.5 text-gray-400 hover:text-gray-600 transition-colors cursor-pointer p-0.5"
                      >
                        {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      </button>
                    </div>
                  </div>

                  {/* Terms & Conditions Checkbox */}
                  <div className="pt-1">
                    <label className="flex items-start gap-2 text-xs text-gray-600 cursor-pointer select-none">
                      <input
                        type="checkbox"
                        id="signup-terms"
                        checked={agreedToTerms}
                        onChange={(e) => setAgreedToTerms(e.target.checked)}
                        required
                        className="w-4 h-4 mt-0.5 rounded text-indigo-600 focus:ring-indigo-500 border-gray-300 cursor-pointer shrink-0"
                      />
                      <span className="leading-tight">
                        I agree to the Smart Share Terms of Service, Privacy Policy, and Bilateral Fare Disclosure rules.
                      </span>
                    </label>
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmitting || !agreedToTerms}
                    className="w-full py-2.5 sm:py-3 px-4 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white text-xs sm:text-sm font-semibold rounded-lg shadow-xs hover:shadow-sm disabled:opacity-50 flex items-center justify-center gap-2 transition-colors cursor-pointer mt-2"
                  >
                    {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                    Create Smart Share Account
                  </button>
                </form>
              )}

              {/* Forgot Password Form */}
              {mode === 'forgot' && (
                <form onSubmit={handleForgotPasswordSubmit} noValidate className="space-y-4 text-left">
                  <div>
                    <label htmlFor="forgot-email" className="block text-xs font-semibold text-gray-700 mb-1.5">
                      Account Email Address
                    </label>
                    <div className="relative">
                      <Mail className="w-4 h-4 text-gray-400 absolute left-3.5 top-3 pointer-events-none" />
                      <input
                        id="forgot-email"
                        type="email"
                        autoComplete="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="you@example.com"
                        required
                        className="w-full bg-white text-gray-900 text-xs pl-10 pr-3 py-2.5 rounded-lg border border-gray-300 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-colors placeholder:text-gray-400"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full py-2.5 sm:py-3 px-4 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white text-xs sm:text-sm font-semibold rounded-lg shadow-xs hover:shadow-sm disabled:opacity-50 flex items-center justify-center gap-2 transition-colors cursor-pointer"
                  >
                    {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                    Send Recovery Link
                  </button>
                </form>
              )}

              {/* Collapsible Developer Token Access Drawer */}
              <div className="pt-4 border-t border-gray-200 text-left">
                <button
                  type="button"
                  onClick={() => setIsDevTokenOpen((prev) => !prev)}
                  className="w-full flex items-center justify-between text-2xs text-gray-500 hover:text-gray-800 py-1 transition-colors cursor-pointer"
                >
                  <span className="flex items-center gap-1.5 font-semibold uppercase tracking-wider">
                    <Key className="w-3.5 h-3.5 text-indigo-600" />
                    Developer & Testing Token Access
                  </span>
                  {isDevTokenOpen ? <ChevronUp className="w-3.5 h-3.5 text-gray-400" /> : <ChevronDown className="w-3.5 h-3.5 text-gray-400" />}
                </button>

                {isDevTokenOpen && (
                  <form onSubmit={handleDevTokenSubmit} className="mt-3 space-y-2 bg-gray-50 p-3.5 rounded-xl border border-gray-200">
                    <p className="text-2xs text-gray-500">
                      Paste a raw Supabase JWT or development test access token to connect directly without password.
                    </p>
                    <label htmlFor="auth-token" className="block text-2xs font-semibold text-gray-700">
                      Bearer Access Token
                    </label>
                    <input
                      id="auth-token"
                      type="text"
                      value={tokenInput}
                      onChange={(e) => setTokenInput(e.target.value)}
                      placeholder="eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
                      className="w-full bg-white text-gray-900 text-2xs p-2 rounded-lg border border-gray-300 font-mono focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 placeholder:text-gray-400"
                    />
                    <button
                      type="submit"
                      disabled={!tokenInput.trim()}
                      className="w-full py-2 bg-gray-800 hover:bg-gray-900 text-white text-2xs font-semibold rounded-lg transition-colors disabled:opacity-40 cursor-pointer"
                    >
                      Connect Session
                    </button>
                  </form>
                )}
              </div>

            </div>
          )}

        </div>
      </div>
    </div>
  );
}
