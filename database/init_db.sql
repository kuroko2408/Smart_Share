-- =============================================================================
-- Smart Share — Development Database Initialization
-- =============================================================================
-- This script runs automatically during container initialization or can be
-- executed manually when provisioning a fresh PostgreSQL database.

-- 1. Enable PostGIS for geospatial point types and spatial index queries
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Enable UUID generator extension for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 3. Local Development Only: Lightweight stub for Supabase Auth schema
-- In production (Supabase), auth.users is managed natively by Supabase Auth (GoTrue).
-- This stub ensures foreign keys referencing auth.users(id) succeed in local Docker.
-- NEVER DEPLOY THIS SECTION TO A MANAGED SUPABASE DATABASE.
CREATE SCHEMA IF NOT EXISTS auth;
CREATE TABLE IF NOT EXISTS auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Verification notice
DO $$
BEGIN
    RAISE NOTICE 'PostGIS version: %', PostGIS_Version();
END $$;
