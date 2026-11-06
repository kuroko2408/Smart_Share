/**
 * Authentication service managing Supabase Auth REST calls and session storage.
 */
import { env } from '@/lib/env';
import { setAuthToken } from '@/services/api-client';
import type { AuthSession, User } from '@/types/auth';

const SESSION_STORAGE_KEY = 'smartshare_auth_session';

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
 * Retrieve persisted session from localStorage and register token with apiClient.
 */
export function getPersistedSession(): AuthSession | null {
  try {
    const raw = getStorage().getItem(SESSION_STORAGE_KEY);
    if (!raw) return null;
    const session = JSON.parse(raw) as AuthSession;
    if (session?.access_token) {
      setAuthToken(session.access_token);
      return session;
    }
  } catch (e) {
    console.warn('[auth] Failed to parse stored session:', e);
  }
  return null;
}

/**
 * Save session to localStorage and register with apiClient.
 */
export function persistSession(session: AuthSession): void {
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
 * Authenticate with Supabase Auth GoTrue endpoint via email and password.
 */
export async function signInWithSupabase(
  email: string,
  password: string
): Promise<AuthSession> {
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
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    let errMsg = `Sign-in failed (HTTP ${response.status})`;
    try {
      const body = (await response.json()) as { error_description?: string; msg?: string; message?: string };
      errMsg = body.error_description || body.msg || body.message || errMsg;
    } catch {
      // ignore
    }
    throw new Error(errMsg);
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

  persistSession(session);
  return session;
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

  persistSession(session);
  return session;
}
