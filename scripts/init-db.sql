-- AI Code Development Agent Database Initialization
-- This script sets up the initial database schema and data

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    permissions TEXT[] DEFAULT ARRAY['basic'],
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- Create chat sessions table
CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Create chat messages table
CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create agent operations table for audit logging
CREATE TABLE IF NOT EXISTS agent_operations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    operation_id VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    operation_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('started', 'in_progress', 'completed', 'failed', 'cancelled')),
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'
);

-- Create security scan results table
CREATE TABLE IF NOT EXISTS security_scan_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    scan_id VARCHAR(255) UNIQUE NOT NULL,
    operation_id UUID REFERENCES agent_operations(id) ON DELETE CASCADE,
    scan_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    vulnerabilities JSONB DEFAULT '[]',
    total_vulnerabilities INTEGER DEFAULT 0,
    critical_count INTEGER DEFAULT 0,
    high_count INTEGER DEFAULT 0,
    medium_count INTEGER DEFAULT 0,
    low_count INTEGER DEFAULT 0,
    scan_duration FLOAT,
    scanned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Create tool executions table
CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    execution_id VARCHAR(255) UNIQUE NOT NULL,
    operation_id UUID REFERENCES agent_operations(id) ON DELETE CASCADE,
    tool_name VARCHAR(100) NOT NULL,
    operation VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed', 'timeout')),
    input_data JSONB DEFAULT '{}',
    output_data JSONB DEFAULT '{}',
    error_message TEXT,
    duration FLOAT,
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Create system metrics table
CREATE TABLE IF NOT EXISTS system_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    metric_unit VARCHAR(50),
    tags JSONB DEFAULT '{}',
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_session_id ON chat_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_sessions_active ON chat_sessions(is_active) WHERE is_active = true;

CREATE INDEX IF NOT EXISTS idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_chat_messages_created_at ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_chat_messages_role ON chat_messages(role);

CREATE INDEX IF NOT EXISTS idx_agent_operations_operation_id ON agent_operations(operation_id);
CREATE INDEX IF NOT EXISTS idx_agent_operations_user_id ON agent_operations(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_operations_type ON agent_operations(operation_type);
CREATE INDEX IF NOT EXISTS idx_agent_operations_status ON agent_operations(status);
CREATE INDEX IF NOT EXISTS idx_agent_operations_started_at ON agent_operations(started_at);

CREATE INDEX IF NOT EXISTS idx_security_scans_scan_id ON security_scan_results(scan_id);
CREATE INDEX IF NOT EXISTS idx_security_scans_operation_id ON security_scan_results(operation_id);
CREATE INDEX IF NOT EXISTS idx_security_scans_type ON security_scan_results(scan_type);
CREATE INDEX IF NOT EXISTS idx_security_scans_scanned_at ON security_scan_results(scanned_at);

CREATE INDEX IF NOT EXISTS idx_tool_executions_execution_id ON tool_executions(execution_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_operation_id ON tool_executions(operation_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_tool_name ON tool_executions(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_executions_executed_at ON tool_executions(executed_at);

CREATE INDEX IF NOT EXISTS idx_system_metrics_name ON system_metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_system_metrics_collected_at ON system_metrics(collected_at);

-- Create triggers for updating timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_chat_sessions_updated_at BEFORE UPDATE ON chat_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (password: admin123)
INSERT INTO users (username, email, password_hash, full_name, permissions, is_active)
VALUES (
    'admin',
    'admin@aiagent.dev',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj7JdO8JQGOy',  -- admin123 hashed with bcrypt
    'System Administrator',
    ARRAY['admin', 'premium', 'basic'],
    true
) ON CONFLICT (username) DO NOTHING;

-- Insert test user (password: test123)
INSERT INTO users (username, email, password_hash, full_name, permissions, is_active)
VALUES (
    'testuser',
    'test@aiagent.dev',
    '$2b$12$V8K5VuJvxGbUq2YqC9vTi.y/XMGw0Q2jKdO8LQjBpT3FdO8JQGOz',  -- test123 hashed with bcrypt
    'Test User',
    ARRAY['basic'],
    true
) ON CONFLICT (username) DO NOTHING;

-- Create cleanup function for old data
CREATE OR REPLACE FUNCTION cleanup_old_data() RETURNS void AS $$
BEGIN
    -- Delete chat messages older than 90 days
    DELETE FROM chat_messages
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '90 days';

    -- Delete inactive chat sessions older than 30 days
    DELETE FROM chat_sessions
    WHERE is_active = false AND updated_at < CURRENT_TIMESTAMP - INTERVAL '30 days';

    -- Delete system metrics older than 30 days
    DELETE FROM system_metrics
    WHERE collected_at < CURRENT_TIMESTAMP - INTERVAL '30 days';

    -- Delete completed agent operations older than 30 days
    DELETE FROM agent_operations
    WHERE status IN ('completed', 'failed', 'cancelled')
    AND completed_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Create cleanup job (requires pg_cron extension - optional)
-- SELECT cron.schedule('cleanup_old_data', '0 2 * * *', 'SELECT cleanup_old_data();');

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO aiagent;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO aiagent;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO aiagent;