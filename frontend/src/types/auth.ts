/**
 * Authentication and user session models.
 */

export interface UserMetadata {
  full_name?: string;
  name?: string;
  avatar_url?: string;
  [key: string]: unknown;
}

export interface User {
  id: string;
  email?: string;
  role?: string;
  user_metadata?: UserMetadata;
  app_metadata?: Record<string, unknown>;
}

export interface AuthSession {
  access_token: string;
  token_type: string;
  expires_at?: number;
  user: User;
}

export interface LoginCredentials {
  email: string;
  password: string;
}
