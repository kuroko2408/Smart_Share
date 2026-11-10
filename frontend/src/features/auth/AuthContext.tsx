/**
 * React Context for Authentication, Session State, and Cross-Tab Synchronization.
 */
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { getSupabase } from '@/lib/supabase';
import { onUnauthorized } from '@/services/api-client';
import {
  clearPersistedSession,
  createSessionFromToken,
  getPersistedSession,
  persistSession,
  sendPasswordResetEmail,
  signInWithSupabase,
  signOutUser,
  signUpWithSupabase,
  updateUserPassword,
  SESSION_STORAGE_KEY,
} from '@/services/auth';
import type { AuthSession, User } from '@/types/auth';

export interface AuthContextType {
  session: AuthSession | null;
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isSessionExpired: boolean;
  authError: string | null;
  loginWithEmail: (email: string, pass: string, rememberMe?: boolean) => Promise<void>;
  signUpWithEmail: (
    email: string,
    pass: string,
    fullName: string
  ) => Promise<{ requiresEmailConfirmation: boolean }>;
  loginWithToken: (token: string) => void;
  logout: () => Promise<void>;
  sendPasswordReset: (email: string) => Promise<void>;
  updatePassword: (newPassword: string) => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(() => getPersistedSession());
  const [isLoading, setIsLoading] = useState(false);
  const [isSessionExpired, setIsSessionExpired] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Initialize session and wire up cross-tab & Supabase auth state listeners
  useEffect(() => {
    let isMounted = true;

    // 1. Initial restoration from local storage
    const initial = getPersistedSession();
    if (initial) {
      setSession(initial);
    }

    // 2. Optional Supabase client listener
    const supabase = getSupabase();
    let authListenerSubscription: { unsubscribe: () => void } | null = null;

    if (supabase) {
      // Check current session from Supabase only if we don't already have an active valid session
      if (!initial) {
        setIsLoading(true);
        supabase.auth.getSession().then(({ data: { session: sbSession } }) => {
          if (!isMounted) return;
          if (sbSession && sbSession.user) {
            const mapped: AuthSession = {
              access_token: sbSession.access_token,
              token_type: sbSession.token_type || 'bearer',
              expires_at: sbSession.expires_at,
              user: {
                id: sbSession.user.id,
                email: sbSession.user.email,
                role: sbSession.user.role,
                user_metadata: sbSession.user.user_metadata,
                app_metadata: sbSession.user.app_metadata,
              },
            };
            persistSession(mapped);
            setSession(mapped);
          }
          setIsLoading(false);
        }).catch(() => {
          if (isMounted) setIsLoading(false);
        });
      }

      const { data: { subscription } } = supabase.auth.onAuthStateChange(
        (event, sbSession) => {
          if (!isMounted) return;
          if (event === 'SIGNED_OUT') {
            setSession((curr) => {
              if (curr) {
                clearPersistedSession();
                return null;
              }
              return null;
            });
          } else if (sbSession && (event === 'SIGNED_IN' || event === 'TOKEN_REFRESHED' || event === 'USER_UPDATED')) {
            const mapped: AuthSession = {
              access_token: sbSession.access_token,
              token_type: sbSession.token_type || 'bearer',
              expires_at: sbSession.expires_at,
              user: {
                id: sbSession.user.id,
                email: sbSession.user.email,
                role: sbSession.user.role,
                user_metadata: sbSession.user.user_metadata,
                app_metadata: sbSession.user.app_metadata,
              },
            };
            persistSession(mapped);
            setSession(mapped);
            setIsSessionExpired(false);
          }
        }
      );
      authListenerSubscription = subscription;
    }

    // 3. Cross-tab storage synchronization
    const handleStorageChange = (e: StorageEvent) => {
      if (!isMounted) return;
      if (e.key === SESSION_STORAGE_KEY) {
        const updated = getPersistedSession();
        setSession(updated);
        if (!updated) {
          setIsSessionExpired(false);
        }
      }
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('storage', handleStorageChange);
    }

    return () => {
      isMounted = false;
      if (authListenerSubscription) {
        authListenerSubscription.unsubscribe();
      }
      if (typeof window !== 'undefined') {
        window.removeEventListener('storage', handleStorageChange);
      }
    };
  }, []);

  // Register 401 unauthorized listener from apiClient
  useEffect(() => {
    const unregister = onUnauthorized(() => {
      setIsSessionExpired(true);
      clearPersistedSession();
      setSession(null);
    });
    return unregister;
  }, []);

  const loginWithEmail = async (email: string, pass: string, rememberMe: boolean = true) => {
    setAuthError(null);
    setIsSessionExpired(false);
    try {
      const newSession = await signInWithSupabase(email, pass, rememberMe);
      setSession(newSession);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Authentication failed';
      setAuthError(message);
      throw err;
    }
  };

  const signUpWithEmail = async (
    email: string,
    pass: string,
    fullName: string
  ): Promise<{ requiresEmailConfirmation: boolean }> => {
    setAuthError(null);
    setIsSessionExpired(false);
    try {
      const result = await signUpWithSupabase(email, pass, fullName);
      if (result.session) {
        setSession(result.session);
      }
      return { requiresEmailConfirmation: result.requiresEmailConfirmation };
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Registration failed';
      setAuthError(message);
      throw err;
    }
  };

  const loginWithToken = (token: string) => {
    setAuthError(null);
    setIsSessionExpired(false);
    try {
      const newSession = createSessionFromToken(token);
      setSession(newSession);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Invalid token';
      setAuthError(message);
      throw err;
    }
  };

  const logout = async () => {
    try {
      await signOutUser();
    } finally {
      setSession(null);
      setIsSessionExpired(false);
      setAuthError(null);
    }
  };

  const sendPasswordReset = async (email: string) => {
    setAuthError(null);
    try {
      await sendPasswordResetEmail(email);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to send reset email';
      setAuthError(message);
      throw err;
    }
  };

  const updatePassword = async (newPassword: string) => {
    setAuthError(null);
    try {
      await updateUserPassword(newPassword);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update password';
      setAuthError(message);
      throw err;
    }
  };

  const clearError = () => {
    setAuthError(null);
  };

  return (
    <AuthContext.Provider
      value={{
        session,
        user: session?.user ?? null,
        isAuthenticated: !!session,
        isLoading,
        isSessionExpired,
        authError,
        loginWithEmail,
        signUpWithEmail,
        loginWithToken,
        logout,
        sendPasswordReset,
        updatePassword,
        clearError,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
