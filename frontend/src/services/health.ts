import { env } from '@/lib/env';

export type HealthResponse = { status: string };

export async function checkBackendHealth(): Promise<HealthResponse> {
  // Health endpoint is at the root of the backend, not under /api/v1
  const baseUrl = env.apiBaseUrl.replace(/\/api\/v1\/?$/, '');
  const response = await fetch(`${baseUrl}/health`);
  if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
  return response.json() as Promise<HealthResponse>;
}
