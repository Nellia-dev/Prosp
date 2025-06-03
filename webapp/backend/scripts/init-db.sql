-- Database initialization script for Nellia Prospector
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Grant permissions to postgres user
GRANT ALL PRIVILEGES ON DATABASE nellia_prospector TO postgres;

-- Log successful initialization
SELECT 'Nellia Prospector database initialization completed successfully' AS status;
