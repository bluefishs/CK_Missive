-- 建立 event_reminders 表格

CREATE TABLE event_reminders (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL,
    reminder_type VARCHAR(50) NOT NULL DEFAULT 'email',
    reminder_time TIMESTAMP NOT NULL,
    message TEXT,
    is_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (event_id) REFERENCES document_calendar_events(id) ON DELETE CASCADE
);
CREATE INDEX idx_event_reminders_event_id ON event_reminders(event_id);
CREATE INDEX idx_event_reminders_reminder_time ON event_reminders(reminder_time);

-- 建立 system_notifications 表格

CREATE TABLE system_notifications (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    notification_type VARCHAR(50) DEFAULT 'info',
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP WITH TIME ZONE,
    data JSONB,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_system_notifications_user_id ON system_notifications(user_id);
CREATE INDEX idx_system_notifications_is_read ON system_notifications(is_read);
CREATE INDEX idx_system_notifications_created_at ON system_notifications(created_at);
