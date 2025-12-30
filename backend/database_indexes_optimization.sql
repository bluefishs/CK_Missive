-- 資料庫索引優化腳本
-- 乾坤測繪公文管理系統效能優化

-- =============================================
-- 1. 公文文件表 (documents) 索引優化
-- =============================================

-- 公文日期範圍查詢索引 (最常用的查詢條件)
CREATE INDEX IF NOT EXISTS idx_documents_doc_date_range ON documents(doc_date) WHERE doc_date IS NOT NULL;

-- 公文類型 + 日期組合索引 (用於按類型和日期篩選)
CREATE INDEX IF NOT EXISTS idx_documents_type_date ON documents(doc_type, doc_date) WHERE doc_date IS NOT NULL;

-- 發文機關查詢索引
CREATE INDEX IF NOT EXISTS idx_documents_sender_agency ON documents(sender_agency_id) WHERE sender_agency_id IS NOT NULL;

-- 受文機關查詢索引
CREATE INDEX IF NOT EXISTS idx_documents_receiver_agency ON documents(receiver_agency_id) WHERE receiver_agency_id IS NOT NULL;

-- 承攬案件關聯索引
CREATE INDEX IF NOT EXISTS idx_documents_contract_project ON documents(contract_project_id) WHERE contract_project_id IS NOT NULL;

-- 公文狀態查詢索引
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status) WHERE status IS NOT NULL;

-- 年度統計查詢優化索引 (提取年份)
CREATE INDEX IF NOT EXISTS idx_documents_year_extract ON documents(EXTRACT(year FROM doc_date)) WHERE doc_date IS NOT NULL;

-- 全文搜尋索引 (主旨欄位)
CREATE INDEX IF NOT EXISTS idx_documents_subject_gin ON documents USING gin(to_tsvector('chinese', subject));

-- 複合索引：狀態 + 日期 (用於統計活躍公文)
CREATE INDEX IF NOT EXISTS idx_documents_status_date ON documents(status, doc_date) WHERE doc_date IS NOT NULL AND status IS NOT NULL;

-- =============================================
-- 2. 機關單位表 (government_agencies) 索引優化
-- =============================================

-- 機關名稱搜尋索引
CREATE INDEX IF NOT EXISTS idx_agencies_name_gin ON government_agencies USING gin(to_tsvector('chinese', agency_name));

-- 機關類型索引
CREATE INDEX IF NOT EXISTS idx_agencies_type ON government_agencies(agency_type) WHERE agency_type IS NOT NULL;

-- 機關代碼索引 (如果需要快速查找)
CREATE INDEX IF NOT EXISTS idx_agencies_code ON government_agencies(agency_code) WHERE agency_code IS NOT NULL;

-- =============================================
-- 3. 廠商表 (partner_vendors) 索引優化
-- =============================================

-- 廠商名稱搜尋索引
CREATE INDEX IF NOT EXISTS idx_vendors_name_gin ON partner_vendors USING gin(to_tsvector('chinese', vendor_name));

-- 業務類型索引
CREATE INDEX IF NOT EXISTS idx_vendors_business_type ON partner_vendors(business_type) WHERE business_type IS NOT NULL;

-- 評等索引 (用於廠商評級查詢)
CREATE INDEX IF NOT EXISTS idx_vendors_rating ON partner_vendors(rating) WHERE rating IS NOT NULL;

-- 廠商代碼索引
CREATE INDEX IF NOT EXISTS idx_vendors_code ON partner_vendors(vendor_code) WHERE vendor_code IS NOT NULL;

-- =============================================
-- 4. 承攬案件表 (contract_projects) 索引優化
-- =============================================

-- 專案年度索引 (最常用的篩選條件)
CREATE INDEX IF NOT EXISTS idx_projects_year ON contract_projects(year);

-- 專案狀態索引
CREATE INDEX IF NOT EXISTS idx_projects_status ON contract_projects(status) WHERE status IS NOT NULL;

-- 專案類別索引
CREATE INDEX IF NOT EXISTS idx_projects_category ON contract_projects(category) WHERE category IS NOT NULL;

-- 委託機關索引
CREATE INDEX IF NOT EXISTS idx_projects_client_agency ON contract_projects(client_agency) WHERE client_agency IS NOT NULL;

-- 合約金額範圍查詢索引
CREATE INDEX IF NOT EXISTS idx_projects_contract_amount ON contract_projects(contract_amount) WHERE contract_amount IS NOT NULL;

-- 專案日期範圍索引
CREATE INDEX IF NOT EXISTS idx_projects_date_range ON contract_projects(start_date, end_date) WHERE start_date IS NOT NULL;

-- 專案名稱全文搜尋索引
CREATE INDEX IF NOT EXISTS idx_projects_name_gin ON contract_projects USING gin(to_tsvector('chinese', project_name));

-- 複合索引：年度 + 狀態 (常用組合查詢)
CREATE INDEX IF NOT EXISTS idx_projects_year_status ON contract_projects(year, status) WHERE status IS NOT NULL;

-- =============================================
-- 5. 使用者表 (users) 索引優化
-- =============================================

-- 電子郵件索引 (登入查詢)
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_unique ON users(email);

-- 使用者名稱索引
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_username_unique ON users(username);

-- 活躍用戶索引
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active) WHERE is_active = true;

-- Google ID 索引 (OAuth 登入)
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL;

-- 最後登入時間索引
CREATE INDEX IF NOT EXISTS idx_users_last_login ON users(last_login) WHERE last_login IS NOT NULL;

-- =============================================
-- 6. 日曆事件表 (document_calendar_events) 索引優化
-- =============================================

-- 事件日期範圍索引
CREATE INDEX IF NOT EXISTS idx_calendar_events_date_range ON document_calendar_events(start_date, end_date);

-- 關聯公文索引
CREATE INDEX IF NOT EXISTS idx_calendar_events_document ON document_calendar_events(document_id);

-- 指派使用者索引
CREATE INDEX IF NOT EXISTS idx_calendar_events_assigned_user ON document_calendar_events(assigned_user_id) WHERE assigned_user_id IS NOT NULL;

-- 事件類型索引
CREATE INDEX IF NOT EXISTS idx_calendar_events_type ON document_calendar_events(event_type) WHERE event_type IS NOT NULL;

-- =============================================
-- 7. 提醒事件表 (event_reminders) 索引優化
-- =============================================

-- 提醒時間索引 (用於排程查詢)
CREATE INDEX IF NOT EXISTS idx_reminders_time ON event_reminders(reminder_time);

-- 待發送提醒索引
CREATE INDEX IF NOT EXISTS idx_reminders_pending ON event_reminders(is_sent, reminder_time) WHERE is_sent = false;

-- 接收用戶索引
CREATE INDEX IF NOT EXISTS idx_reminders_recipient ON event_reminders(recipient_user_id) WHERE recipient_user_id IS NOT NULL;

-- =============================================
-- 8. 系統通知表 (system_notifications) 索引優化
-- =============================================

-- 用戶通知索引
CREATE INDEX IF NOT EXISTS idx_notifications_user ON system_notifications(user_id) WHERE user_id IS NOT NULL;

-- 未讀通知索引
CREATE INDEX IF NOT EXISTS idx_notifications_unread ON system_notifications(user_id, is_read, created_at) WHERE is_read = false;

-- 通知創建時間索引
CREATE INDEX IF NOT EXISTS idx_notifications_created_at ON system_notifications(created_at);

-- =============================================
-- 9. 網站導航表 (site_navigation_items) 索引優化
-- =============================================

-- 啟用狀態 + 排序索引
CREATE INDEX IF NOT EXISTS idx_navigation_enabled_order ON site_navigation_items(is_enabled, sort_order) WHERE is_enabled = true;

-- 父級項目索引
CREATE INDEX IF NOT EXISTS idx_navigation_parent ON site_navigation_items(parent_id) WHERE parent_id IS NOT NULL;

-- =============================================
-- 10. 外鍵約束檢查 (確保資料完整性)
-- =============================================

-- 檢查並新增缺少的外鍵約束
DO $$
BEGIN
    -- documents 表的外鍵約束
    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                   WHERE constraint_name = 'fk_documents_sender_agency') THEN
        ALTER TABLE documents ADD CONSTRAINT fk_documents_sender_agency
        FOREIGN KEY (sender_agency_id) REFERENCES government_agencies(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                   WHERE constraint_name = 'fk_documents_receiver_agency') THEN
        ALTER TABLE documents ADD CONSTRAINT fk_documents_receiver_agency
        FOREIGN KEY (receiver_agency_id) REFERENCES government_agencies(id) ON DELETE SET NULL;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.table_constraints
                   WHERE constraint_name = 'fk_documents_contract_project') THEN
        ALTER TABLE documents ADD CONSTRAINT fk_documents_contract_project
        FOREIGN KEY (contract_project_id) REFERENCES contract_projects(id) ON DELETE SET NULL;
    END IF;
END $$;

-- =============================================
-- 11. 統計資料更新 (優化查詢計劃)
-- =============================================

-- 更新統計資料以優化查詢計劃
ANALYZE documents;
ANALYZE government_agencies;
ANALYZE partner_vendors;
ANALYZE contract_projects;
ANALYZE users;
ANALYZE document_calendar_events;
ANALYZE event_reminders;
ANALYZE system_notifications;

-- =============================================
-- 12. 效能監控查詢
-- =============================================

-- 查看索引使用情況
-- SELECT schemaname, tablename, indexname, idx_tup_read, idx_tup_fetch
-- FROM pg_stat_user_indexes
-- ORDER BY idx_tup_read DESC;

-- 查看表掃描統計
-- SELECT schemaname, tablename, seq_tup_read, idx_tup_fetch,
--        seq_tup_read / (seq_tup_read + idx_tup_fetch + 1) AS seq_ratio
-- FROM pg_stat_user_tables
-- WHERE seq_tup_read + idx_tup_fetch > 0
-- ORDER BY seq_ratio DESC;

-- =============================================
-- 13. 索引維護建議
-- =============================================

/*
定期維護建議：

1. 每週執行 ANALYZE 更新統計資料
2. 每月檢查索引使用率，移除未使用的索引
3. 監控查詢效能，根據慢查詢日誌優化
4. 定期 VACUUM 清理無效數據
5. 監控索引膨脹，必要時重建索引

監控指令：
- SELECT * FROM pg_stat_activity WHERE state = 'active';
- SELECT * FROM pg_stat_user_indexes ORDER BY idx_tup_read DESC;
- SELECT tablename, size, pg_size_pretty(size) FROM (
    SELECT tablename, pg_total_relation_size(tablename::regclass) AS size
    FROM pg_tables WHERE schemaname = 'public'
  ) AS table_sizes ORDER BY size DESC;
*/