-- =============================================================================
-- Smart Share — Development Database Initialization
-- =============================================================================
-- This script runs automatically during container initialization or can be
-- executed manually when provisioning a fresh PostgreSQL database.

-- 1. Enable PostGIS for geospatial point types and spatial index queries
CREATE EXTENSION IF NOT EXISTS postgis;

-- 2. Enable UUID generator extension for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verification notice
DO $$
BEGIN
    RAISE NOTICE 'PostGIS version: %', PostGIS_Version();
END $$;
