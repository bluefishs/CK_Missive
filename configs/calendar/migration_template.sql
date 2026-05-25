
-- 行事曆整合相關資料表

-- 專案通知設定表
CREATE TABLE IF NOT EXISTS project_notifications (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    user_id INTEGER REFERENCES users(id),
    notification_type VARCHAR(50),
    is_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 提醒規則表
CREATE TABLE IF NOT EXISTS reminder_rules (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES document_calendar_events(id),
    reminder_type VARCHAR(50),
    trigger_minutes_before INTEGER,
    notification_channels TEXT[], -- email, system, calendar
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 同步狀態追蹤表
CREATE TABLE IF NOT EXISTS calendar_sync_status (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES document_calendar_events(id),
    sync_provider VARCHAR(50), -- google, outlook等
    external_event_id VARCHAR(255),
    last_sync_at TIMESTAMP,
    sync_status VARCHAR(50), -- synced, pending, failed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
