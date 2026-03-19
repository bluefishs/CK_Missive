-- Add client_type column to contract_projects
-- Tracks the source type of the client: agency (government), vendor, or other
ALTER TABLE contract_projects ADD COLUMN IF NOT EXISTS client_type VARCHAR(20) DEFAULT 'agency';

COMMENT ON COLUMN contract_projects.client_type IS '委託來源: agency=機關 vendor=廠商 other=其他';
