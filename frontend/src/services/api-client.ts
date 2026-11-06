/**
 * Reusable API client for the Smart Share backend.
 * Uses VITE_API_BASE_URL as the base. Handles JSON, HTTP errors consistently.
 * Attaches Supabase Bearer token when authenticated and notifies on 401 Unauthorized.
 */
import { env } from '@/lib/env';

export class ApiError extends Error {
  readonly status: number;
  readonly statusText: string;

  constructor(status: number, statusText: string, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
  }
}

let activeAuthToken: string | null = null;
const unauthorizedListeners = new Set<() => void>();

export function setAuthToken(token: string | null): void {
  activeAuthToken = token;
}

export function getAuthToken(): string | null {
  return activeAuthToken;
}

export function onUnauthorized(callback: () => void): () => void {
  unauthorizedListeners.add(callback);
  return () => {
    unauthorizedListeners.delete(callback);
  };
}

function notifyUnauthorized(): void {
  unauthorizedListeners.forEach((listener) => {
    try {
      listener();
    } catch (e) {
      console.error('[apiClient] Error in unauthorized listener', e);
    }
  });
}

type RequestOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  body?: unknown;
  headers?: Record<string, string>;
  signal?: AbortSignal;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {}, signal } = options;

  const authHeaders: Record<string, string> = {};
  if (activeAuthToken) {
    authHeaders['Authorization'] = `Bearer ${activeAuthToken}`;
  }

  const defaultHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
    ...authHeaders,
    ...headers,
  };

  const url = `${env.apiBaseUrl}${path}`;

  const response = await fetch(url, {
    method,
    headers: defaultHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (!response.ok) {
    let message = `HTTP ${response.status} ${response.statusText}`;
    try {
      const errorBody = (await response.json()) as { detail?: string; error?: { message?: string } };
      if (errorBody?.detail) {
        message = errorBody.detail;
      } else if (errorBody?.error?.message) {
        message = errorBody.error.message;
      }
    } catch {
      // ignore parse errors
    }

    if (response.status === 401) {
      notifyUnauthorized();
    }

    throw new ApiError(response.status, response.statusText, message);
  }

  // Handle 204 No Content
  if (response.status === 204) return undefined as T;

  return response.json() as Promise<T>;
}

export const apiClient = {
  get: <T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'GET' }),

  post: <T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, 'method' | 'body'>
  ) => request<T>(path, { ...options, method: 'POST', body }),

  put: <T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, 'method' | 'body'>
  ) => request<T>(path, { ...options, method: 'PUT', body }),

  patch: <T>(
    path: string,
    body?: unknown,
    options?: Omit<RequestOptions, 'method' | 'body'>
  ) => request<T>(path, { ...options, method: 'PATCH', body }),

  delete: <T>(path: string, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(path, { ...options, method: 'DELETE' }),
};
