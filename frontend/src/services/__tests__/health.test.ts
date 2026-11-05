import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { checkBackendHealth } from '../health';

describe('health service', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('calls the health endpoint and returns parsed json on success', async () => {
    const mockResponse = { status: 'ok', service: 'smart-share-backend' };
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue(mockResponse),
    } as unknown as Response);

    const result = await checkBackendHealth();

    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    const calledUrl = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(calledUrl).toContain('/health');
    expect(result).toEqual(mockResponse);
  });

  it('throws an error when backend health returns non-ok status', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: vi.fn().mockResolvedValue({ detail: 'Service Unavailable' }),
    } as unknown as Response);

    await expect(checkBackendHealth()).rejects.toThrow('Health check failed: 503');
  });

  it('propagates error when network fetch fails', async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new Error('Network connection refused'));

    await expect(checkBackendHealth()).rejects.toThrow('Network connection refused');
  });
});
