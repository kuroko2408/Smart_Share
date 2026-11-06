import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  decodeJwtClaims,
  createSessionFromToken,
  getPersistedSession,
  clearPersistedSession,
} from '@/services/auth';
import { setAuthToken, getAuthToken, apiClient, onUnauthorized } from '@/services/api-client';

describe('Auth & API Client Services', () => {
  beforeEach(() => {
    clearPersistedSession();
    localStorage.clear();
    setAuthToken(null);
  });

  it('correctly decodes JWT payload claims', () => {
    const claims = { sub: 'test-user-id', email: 'test@example.com', exp: 1700000000 };
    const base64Url = btoa(JSON.stringify(claims));
    const token = `header.${base64Url}.signature`;

    const decoded = decodeJwtClaims(token);
    expect(decoded).toEqual(claims);
  });

  it('creates and persists session from token', () => {
    const claims = { sub: 'e79b940e-744a-4d2b-b8c8-f40a1b63b01a', email: 'commuter@smart.local' };
    const token = `header.${btoa(JSON.stringify(claims))}.sig`;

    const session = createSessionFromToken(token);
    expect(session.access_token).toBe(token);
    expect(session.user.id).toBe('e79b940e-744a-4d2b-b8c8-f40a1b63b01a');
    expect(session.user.email).toBe('commuter@smart.local');

    // Check token registered with apiClient
    expect(getAuthToken()).toBe(token);

    // Check persisted in storage
    const stored = getPersistedSession();
    expect(stored?.access_token).toBe(token);
  });

  it('notifies onUnauthorized listener on 401 response', async () => {
    const unauthorizedCallback = vi.fn();
    const unregister = onUnauthorized(unauthorizedCallback);

    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: 'Token expired' }), {
        status: 401,
        statusText: 'Unauthorized',
        headers: { 'Content-Type': 'application/json' },
      })
    );

    await expect(apiClient.get('/users/me')).rejects.toThrow();
    expect(unauthorizedCallback).toHaveBeenCalledTimes(1);

    unregister();
  });
});
