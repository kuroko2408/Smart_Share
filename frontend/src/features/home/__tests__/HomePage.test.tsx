import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HomePage } from '../HomePage';
import { AuthProvider } from '@/features/auth/AuthContext';
import * as healthService from '@/services/health';
import * as profileService from '@/services/profile';
import { clearPersistedSession } from '@/services/auth';

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>{ui}</AuthProvider>
    </QueryClientProvider>
  );
}

describe('HomePage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    clearPersistedSession();
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    clearPersistedSession();
    localStorage.clear();
  });

  it('renders initial brand elements and loading state', () => {
    vi.spyOn(healthService, 'checkBackendHealth').mockImplementation(
      () => new Promise(() => {}) // never resolves to keep in loading state
    );

    renderWithClient(<HomePage />);

    expect(screen.getByText('Smart Share')).toBeInTheDocument();
    expect(screen.getByText(/Checking connection…/i)).toBeInTheDocument();
  });

  it('displays connected status when health check succeeds', async () => {
    vi.spyOn(healthService, 'checkBackendHealth').mockResolvedValue({
      status: 'ok',
      service: 'smart-share-backend',
    });

    renderWithClient(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText(/Backend connected — ok/i)).toBeInTheDocument();
    });
  });

  it('displays unreachable failure state when health check fails', async () => {
    vi.spyOn(healthService, 'checkBackendHealth').mockRejectedValue(
      new Error('Connection refused')
    );

    renderWithClient(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText(/Backend unreachable/i)).toBeInTheDocument();
    });
  });

  it('connects with bearer token and displays authenticated profile', async () => {
    vi.spyOn(healthService, 'checkBackendHealth').mockResolvedValue({
      status: 'ok',
      service: 'smart-share-backend',
    });

    vi.spyOn(profileService, 'fetchUserProfile').mockResolvedValue({
      data: {
        id: '11111111-2222-3333-4444-555555555555',
        display_name: 'Verified Commuter',
        avatar_url: null,
        is_onboarding_completed: true,
        created_at: '2026-11-06T12:00:00Z',
        updated_at: '2026-11-06T12:30:00Z',
      },
      message: 'Profile retrieved successfully',
    });

    renderWithClient(<HomePage />);

    // Check that login form is rendered
    const tokenInput = screen.getByLabelText(/Bearer Access Token/i);
    const connectButton = screen.getByRole('button', { name: /Connect Session/i });

    // Enter fake valid JWT
    const fakePayload = btoa(JSON.stringify({ sub: '11111111-2222-3333-4444-555555555555' }));
    const fakeToken = `header.${fakePayload}.sig`;

    fireEvent.change(tokenInput, { target: { value: fakeToken } });
    fireEvent.click(connectButton);

    // Profile card should appear
    await waitFor(() => {
      expect(screen.getByText('Verified Commuter')).toBeInTheDocument();
      expect(screen.getByText(/Completed/i)).toBeInTheDocument();
      expect(screen.getByText(/Sign Out/i)).toBeInTheDocument();
    });

    // Sign out
    const signOutBtn = screen.getByRole('button', { name: /Sign Out/i });
    fireEvent.click(signOutBtn);

    await waitFor(() => {
      expect(screen.getByLabelText(/Bearer Access Token/i)).toBeInTheDocument();
    });
  });
});
