import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { HomePage } from '../HomePage';
import * as healthService from '@/services/health';

function renderWithClient(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
  return render(<QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>);
}

describe('HomePage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
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
});
