import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { ProtectedRoute } from '../ProtectedRoute';
import * as AuthContextModule from '../AuthContext';
import type { AuthContextType } from '../AuthContext';

describe('ProtectedRoute', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  const mockAuthContext = (overrides: Partial<AuthContextType> = {}) => {
    const defaultContext: AuthContextType = {
      session: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      isSessionExpired: false,
      authError: null,
      loginWithEmail: vi.fn(),
      signUpWithEmail: vi.fn(),
      loginWithToken: vi.fn(),
      logout: vi.fn(),
      sendPasswordReset: vi.fn(),
      updatePassword: vi.fn(),
      clearError: vi.fn(),
      ...overrides,
    };
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue(defaultContext);
  };

  it('renders loading state when session is initializing', () => {
    mockAuthContext({ isLoading: true, isAuthenticated: false });

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>Secret Dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText(/Verifying session…/i)).toBeInTheDocument();
    expect(screen.queryByText('Secret Dashboard')).not.toBeInTheDocument();
  });

  it('redirects to /login when unauthenticated', () => {
    mockAuthContext({ isLoading: false, isAuthenticated: false });

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route path="/login" element={<div>Login Page Mock</div>} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>Secret Dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Login Page Mock')).toBeInTheDocument();
    expect(screen.queryByText('Secret Dashboard')).not.toBeInTheDocument();
  });

  it('renders children when authenticated', () => {
    mockAuthContext({
      isLoading: false,
      isAuthenticated: true,
      user: { id: 'test-user-id', email: 'user@test.com' },
    });

    render(
      <MemoryRouter initialEntries={['/dashboard']}>
        <Routes>
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <div>Secret Dashboard</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText('Secret Dashboard')).toBeInTheDocument();
  });
});
