/**
 * Authentication service managing Supabase Auth REST calls, official Supabase client, and session storage.
 */
import { env } from '@/lib/env';
import { getSupabase } from '@/lib/supabase';
import { setAuthToken, getAuthToken } from '@/services/api-client';
import type { AuthSession, User } from '@/types/auth';

export const SESSION_STORAGE_KEY = 'smartshare_auth_session';
export const REMEMBER_ME_KEY = 'smartshare_remember_me';

/**
 * Format raw Supabase authentication errors into friendly, understandable user messages.
 */
export function formatAuthError(rawMessage: string): string {
  const lower = rawMessage.toLowerCase();
  if (lower.includes('invalid login credentials') || lower.includes('invalid credentials')) {
    return 'Invalid email or password. Please check your credentials and try again.';
  }
  if (lower.includes('email not confirmed')) {
    return 'Your email address is not yet confirmed. Please check your inbox for the verification link.';
  }
  if (lower.includes('user already registered') || lower.includes('already exists')) {
    return 'An account with this email already exists. Please sign in or reset your password.';
  }
  if (lower.includes('password should be at least') || lower.includes('password must be')) {
    return 'Password must be at least 6 characters long.';
  }
  if (lower.includes('rate limit') || lower.includes('too many requests')) {
    return 'Too many login attempts. Please wait a few moments before trying again.';
  }
  if (lower.includes('network') || lower.includes('fetch') || lower.includes('failed to fetch')) {
    return 'Unable to reach the authentication service. Please check your network connection.';
  }
  return rawMessage;
}

/**
 * Decode JWT payload claims without requiring an external cryptographic library.
 */
export function decodeJwtClaims(token: string): Record<string, unknown> | null {
  try {
    const parts = token.split('.');
    if (parts.length < 2) return null;
    const base64Url = parts[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload) as Record<string, unknown>;
  } catch {
    return null;
  }
}

/**
 * Construct a User object from decoded JWT claims or provided details.
 */
export function claimsToUser(claims: Record<string, unknown>): User {
  const sub = typeof claims.sub === 'string' ? claims.sub : '00000000-0000-0000-0000-000000000000';
  const email = typeof claims.email === 'string' ? claims.email : undefined;
  const role = typeof claims.role === 'string' ? claims.role : undefined;
  const user_metadata =
    typeof claims.user_metadata === 'object' && claims.user_metadata !== null
      ? (claims.user_metadata as Record<string, unknown>)
      : undefined;
  const app_metadata =
    typeof claims.app_metadata === 'object' && claims.app_metadata !== null
      ? (claims.app_metadata as Record<string, unknown>)
      : undefined;

  return {
    id: sub,
    email,
    role,
    user_metadata,
    app_metadata,
  };
}

let memoryStore: Record<string, string> = {};

function getStorage() {
  try {
    if (typeof window !== 'undefined' && window.localStorage && typeof window.localStorage.getItem === 'function') {
      return window.localStorage;
    }
    if (typeof localStorage !== 'undefined' && typeof localStorage.getItem === 'function') {
      return localStorage;
    }
  } catch {
    // fallback
  }
  return {
    getItem: (key: string) => memoryStore[key] ?? null,
    setItem: (key: string, val: string) => {
      memoryStore[key] = val;
    },
    removeItem: (key: string) => {
      delete memoryStore[key];
    },
    clear: () => {
      memoryStore = {};
    },
  };
}

/**
 * Set Remember Me preference in storage.
 */
export function setRememberMePreference(remember: boolean): void {
  try {
    getStorage().setItem(REMEMBER_ME_KEY, remember ? 'true' : 'false');
  } catch {
    // ignore
  }
}

/**
 * Get Remember Me preference from storage (defaults to true).
 */
export function getRememberMePreference(): boolean {
  try {
    const val = getStorage().getItem(REMEMBER_ME_KEY);
    return val !== 'false';
  } catch {
    return true;
  }
}

/**
 * Retrieve persisted session from storage and register token with apiClient.
 */
export function getPersistedSession(): AuthSession | null {
  try {
    const raw = getStorage().getItem(SESSION_STORAGE_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw) as AuthSession;
    if (session?.access_token) {
      // Optional check for token expiration
      if (session.expires_at) {
        const nowSec = Math.floor(Date.now() / 1000);
        if (session.expires_at < nowSec) {
          // Token is expired
          clearPersistedSession();
          return null;
        }
      }
      setAuthToken(session.access_token);
      return session;
    }
  } catch (e) {
    console.warn('[auth] Failed to parse stored session:', e);
  }
  return null;
}

/**
 * Save session to storage and register with apiClient.
 */
export function persistSession(session: AuthSession, rememberMe: boolean = true): void {
  setRememberMePreference(rememberMe);
  getStorage().setItem(SESSION_STORAGE_KEY, JSON.stringify(session));
  setAuthToken(session.access_token);
}

/**
 * Clear stored session and deregister token from apiClient.
 */
export function clearPersistedSession(): void {
  getStorage().removeItem(SESSION_STORAGE_KEY);
  setAuthToken(null);
}

/**
 * Authenticate with Supabase Auth via email and password.
 * Prioritizes official Supabase client, with graceful fallback to GoTrue REST endpoint.
 */
export async function signInWithSupabase(
  email: string,
  password: string,
  rememberMe: boolean = true
): Promise<AuthSession> {
  const trimmedEmail = email.trim();
  const supabase = getSupabase();

  if (supabase) {
    const { data, error } = await supabase.auth.signInWithPassword({
      email: trimmedEmail,
      password,
    });

    if (error) {
      throw new Error(formatAuthError(error.message));
    }

    if (!data.session || !data.user) {
      throw new Error('Authentication succeeded but no session was returned.');
    }

    const session: AuthSession = {
      access_token: data.session.access_token,
      token_type: data.session.token_type || 'bearer',
      expires_at: data.session.expires_at,
      user: {
        id: data.user.id,
        email: data.user.email,
        role: data.user.role,
        user_metadata: data.user.user_metadata,
        app_metadata: data.user.app_metadata,
      },
    };

    persistSession(session, rememberMe);
    return session;
  }

  // Fallback to direct REST endpoint if Supabase client is not instantiated
  if (!env.supabaseUrl || !env.supabaseAnonKey) {
    throw new Error(
      'Supabase credentials (VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY) are not configured.'
    );
  }

  const cleanUrl = env.supabaseUrl.replace(/\/+$/, '');
  const authEndpoint = `${cleanUrl}/auth/v1/token?grant_type=password`;

  const response = await fetch(authEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      apikey: env.supabaseAnonKey,
    },
    body: JSON.stringify({ email: trimmedEmail, password }),
  });

  if (!response.ok) {
    let errMsg = `Sign-in failed (HTTP ${response.status})`;
    try {
      const body = (await response.json()) as { error_description?: string; msg?: string; message?: string };
      errMsg = body.error_description || body.msg || body.message || errMsg;
    } catch {
      // ignore
    }
    throw new Error(formatAuthError(errMsg));
  }

  const data = (await response.json()) as {
    access_token: string;
    token_type: string;
    expires_at?: number;
    user: User;
  };

  const session: AuthSession = {
    access_token: data.access_token,
    token_type: data.token_type || 'bearer',
    expires_at: data.expires_at,
    user: data.user,
  };

  persistSession(session, rememberMe);
  return session;
}

/**
 * Register a new user with Supabase Auth.
 * Passes full_name in user_metadata for automatic backend profile creation.
 */
export async function signUpWithSupabase(
  email: string,
  password: string,
  fullName: string
): Promise<{
  session: AuthSession | null;
  requiresEmailConfirmation: boolean;
  user: User | null;
}> {
  const trimmedEmail = email.trim();
  const trimmedName = fullName.trim();
  const supabase = getSupabase();

  if (supabase) {
    const { data, error } = await supabase.auth.signUp({
      email: trimmedEmail,
      password,
      options: {
        data: {
          full_name: trimmedName,
          name: trimmedName,
        },
      },
    });

    if (error) {
      throw new Error(formatAuthError(error.message));
    }

    if (data.session && data.user) {
      const session: AuthSession = {
        access_token: data.session.access_token,
        token_type: data.session.token_type || 'bearer',
        expires_at: data.session.expires_at,
        user: {
          id: data.user.id,
          email: data.user.email,
          role: data.user.role,
          user_metadata: data.user.user_metadata,
          app_metadata: data.user.app_metadata,
        },
      };
      persistSession(session, true);
      return { session, requiresEmailConfirmation: false, user: session.user };
    }

    // Email confirmation required or session not returned immediately
    const user: User | null = data.user
      ? {
          id: data.user.id,
          email: data.user.email,
          role: data.user.role,
          user_metadata: data.user.user_metadata,
          app_metadata: data.user.app_metadata,
        }
      : null;

    return { session: null, requiresEmailConfirmation: true, user };
  }

  // REST fallback
  if (!env.supabaseUrl || !env.supabaseAnonKey) {
    throw new Error(
      'Supabase credentials (VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY) are not configured.'
    );
  }

  const cleanUrl = env.supabaseUrl.replace(/\/+$/, '');
  const authEndpoint = `${cleanUrl}/auth/v1/signup`;

  const response = await fetch(authEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      apikey: env.supabaseAnonKey,
    },
    body: JSON.stringify({
      email: trimmedEmail,
      password,
      data: {
        full_name: trimmedName,
        name: trimmedName,
      },
    }),
  });

  if (!response.ok) {
    let errMsg = `Registration failed (HTTP ${response.status})`;
    try {
      const body = (await response.json()) as { error_description?: string; msg?: string; message?: string };
      errMsg = body.error_description || body.msg || body.message || errMsg;
    } catch {
      // ignore
    }
    throw new Error(formatAuthError(errMsg));
  }

  const data = (await response.json()) as {
    access_token?: string;
    token_type?: string;
    expires_at?: number;
    user?: User;
  };

  if (data.access_token && data.user) {
    const session: AuthSession = {
      access_token: data.access_token,
      token_type: data.token_type || 'bearer',
      expires_at: data.expires_at,
      user: data.user,
    };
    persistSession(session, true);
    return { session, requiresEmailConfirmation: false, user: session.user };
  }

  return {
    session: null,
    requiresEmailConfirmation: true,
    user: data.user ?? null,
  };
}

/**
 * Sign out of the active Supabase session and purge local credentials.
 */
export async function signOutUser(): Promise<void> {
  const supabase = getSupabase();
  if (supabase) {
    try {
      await supabase.auth.signOut();
    } catch (e) {
      console.warn('[auth] Supabase signOut error:', e);
    }
  }
  clearPersistedSession();
}

/**
 * Request password recovery email from Supabase Auth.
 */
export async function sendPasswordResetEmail(email: string, redirectTo?: string): Promise<void> {
  const trimmedEmail = email.trim();
  const targetRedirect =
    redirectTo ||
    (typeof window !== 'undefined'
      ? `${window.location.origin}/reset-password`
      : 'http://localhost:5173/reset-password');

  const supabase = getSupabase();
  if (supabase) {
    const { error } = await supabase.auth.resetPasswordForEmail(trimmedEmail, {
      redirectTo: targetRedirect,
    });
    if (error) {
      throw new Error(formatAuthError(error.message));
    }
    return;
  }

  // REST fallback
  if (!env.supabaseUrl || !env.supabaseAnonKey) {
    throw new Error(
      'Supabase credentials (VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY) are not configured.'
    );
  }

  const cleanUrl = env.supabaseUrl.replace(/\/+$/, '');
  const authEndpoint = `${cleanUrl}/auth/v1/recover`;

  const response = await fetch(authEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      apikey: env.supabaseAnonKey,
    },
    body: JSON.stringify({
      email: trimmedEmail,
      redirectTo: targetRedirect,
    }),
  });

  if (!response.ok) {
    let errMsg = `Password reset request failed (HTTP ${response.status})`;
    try {
      const body = (await response.json()) as { error_description?: string; msg?: string; message?: string };
      errMsg = body.error_description || body.msg || body.message || errMsg;
    } catch {
      // ignore
    }
    throw new Error(formatAuthError(errMsg));
  }
}

/**
 * Update the user's password using the active authenticated session or recovery session.
 */
export async function updateUserPassword(newPassword: string): Promise<void> {
  const supabase = getSupabase();
  if (supabase) {
    const { error } = await supabase.auth.updateUser({ password: newPassword });
    if (error) {
      throw new Error(formatAuthError(error.message));
    }
    return;
  }

  // REST fallback
  const currentToken = getAuthToken();
  if (!currentToken) {
    throw new Error('No active authentication or recovery session to update password.');
  }

  if (!env.supabaseUrl || !env.supabaseAnonKey) {
    throw new Error(
      'Supabase credentials (VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY) are not configured.'
    );
  }

  const cleanUrl = env.supabaseUrl.replace(/\/+$/, '');
  const authEndpoint = `${cleanUrl}/auth/v1/user`;

  const response = await fetch(authEndpoint, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      apikey: env.supabaseAnonKey,
      Authorization: `Bearer ${currentToken}`,
    },
    body: JSON.stringify({ password: newPassword }),
  });

  if (!response.ok) {
    let errMsg = `Failed to update password (HTTP ${response.status})`;
    try {
      const body = (await response.json()) as { error_description?: string; msg?: string; message?: string };
      errMsg = body.error_description || body.msg || body.message || errMsg;
    } catch {
      // ignore
    }
    throw new Error(formatAuthError(errMsg));
  }
}

/**
 * Create an active session from a raw JWT access token string.
 * Automatically extracts user claims from token payload.
 */
export function createSessionFromToken(rawToken: string): AuthSession {
  const token = rawToken.trim();
  if (!token) {
    throw new Error('Access token cannot be empty.');
  }

  const claims = decodeJwtClaims(token);
  let user: User;

  if (claims && claims.sub) {
    user = claimsToUser(claims);
  } else {
    // If not a standard decodable JWT, fallback to a placeholder identifier
    user = {
      id: '00000000-0000-0000-0000-000000000001',
      email: 'user@smartshare.local',
    };
  }

  const expires_at =
    claims && typeof claims.exp === 'number' ? claims.exp : Math.floor(Date.now() / 1000) + 3600;

  const session: AuthSession = {
    access_token: token,
    token_type: 'bearer',
    expires_at,
    user,
  };

  persistSession(session, true);
  return session;
}
