-- PostgreSQL initialization script
-- This script is automatically run when the container starts for the first time

-- Create the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create database if it doesn't exist (handled by docker-compose)
-- Tables will be created by SQLAlchemy via alembic or init_db()

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON DATABASE oxytec_db TO oxytec;
