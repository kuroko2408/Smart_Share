/**
 * Central environment configuration module.
 * Provides typed access to environment variables with defaults.
 */

function getEnv(key: string, fallback?: string): string {
  const value = import.meta.env[key] as string | undefined;
  // Treat empty string as missing
  const resolved = value && value.trim() !== '' ? value : undefined;
  if (resolved === undefined && fallback === undefined) {
    console.warn(`[env] Missing environment variable: ${key}`);
  }
  return resolved ?? fallback ?? '';
}

export const env = {
  apiBaseUrl: getEnv('VITE_API_BASE_URL', 'http://localhost:8000/api/v1'),
  supabaseUrl: getEnv('VITE_SUPABASE_URL'),
  supabaseAnonKey:
    getEnv('VITE_SUPABASE_ANON_KEY') || getEnv('VITE_SUPABASE_PUBLISHABLE_KEY'),
  mapTileUrl: getEnv(
    'VITE_MAP_TILE_URL',
    'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
  ),
  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
} as const;
