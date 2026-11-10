/**
 * Supabase client instance configuration for Smart Share.
 * Initializes the official Supabase Auth & PostgreSQL client using environment credentials.
 */
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { env } from '@/lib/env';

let supabaseInstance: SupabaseClient | null = null;

/**
 * Returns true if Supabase URL and anon key are properly configured.
 */
export function isSupabaseConfigured(): boolean {
  return Boolean(env.supabaseUrl && env.supabaseAnonKey);
}

/**
 * Lazily initialize and return the singleton Supabase client instance.
 * Returns null if Supabase environment variables are missing (e.g. local mocked tests).
 */
export function getSupabase(): SupabaseClient | null {
  if (supabaseInstance) {
    return supabaseInstance;
  }

  const url = env.supabaseUrl?.trim();
  const key = env.supabaseAnonKey?.trim();

  if (!url || !key) {
    return null;
  }

  try {
    supabaseInstance = createClient(url, key, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        storageKey: 'sb_smartshare_auth',
      },
    });
    return supabaseInstance;
  } catch (err) {
    console.warn('[supabase] Failed to initialize Supabase client:', err);
    return null;
  }
}

/**
 * For testing purposes: reset or replace the singleton instance.
 */
export function setSupabaseInstanceForTesting(client: SupabaseClient | null): void {
  supabaseInstance = client;
}
