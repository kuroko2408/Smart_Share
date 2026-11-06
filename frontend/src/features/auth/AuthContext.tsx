/**
 * React Context for Authentication and Session State.
 */
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react';
import { onUnauthorized } from '@/services/api-client';
import {
  clearPersistedSession,
  createSessionFromToken,
  getPersistedSession,
  signInWithSupabase,
} from '@/services/auth';
import type { AuthSession } from '@/types/auth';

interface AuthContextType {
  session: AuthSession | null;
  isAuthenticated: boolean;
  isSessionExpired: boolean;
  authError: string | null;
  loginWithEmail: (email: string, pass: string) => Promise<void>;
  loginWithToken: (token: string) => void;
  logout: () => void;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<AuthSession | null>(() => getPersistedSession());
  const [isSessionExpired, setIsSessionExpired] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);

  // Register unauthorized listener from apiClient
  useEffect(() => {
    const unregister = onUnauthorized(() => {
      setIsSessionExpired(true);
      clearPersistedSession();
      setSession(null);
    });
    return unregister;
  }, []);

  const loginWithEmail = async (email: string, pass: string) => {
    setAuthError(null);
    setIsSessionExpired(false);
    try {
      const newSession = await signInWithSupabase(email, pass);
      setSession(newSession);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Authentication failed';
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

  const logout = () => {
    clearPersistedSession();
    setSession(null);
    setIsSessionExpired(false);
    setAuthError(null);
  };

  const clearError = () => {
    setAuthError(null);
  };

  return (
    <AuthContext.Provider
      value={{
        session,
        isAuthenticated: !!session,
        isSessionExpired,
        authError,
        loginWithEmail,
        loginWithToken,
        logout,
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
