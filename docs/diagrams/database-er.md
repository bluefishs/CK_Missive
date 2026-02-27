# CK_Missive Database ER Diagram

```mermaid
erDiagram
    contract_projects }o--o{ project_vendor_association : ""
    partner_vendors }o--o{ project_vendor_association : ""
    contract_projects }o--o{ project_user_assignments : ""
    users }o--o{ project_user_assignments : ""
    users ||--o{ document_calendar_events : ""
    government_agencies ||--o{ contract_projects : ""
    contract_projects ||--o{ documents : ""
    government_agencies ||--o{ documents : ""
    site_navigation_items ||--o{ site_navigation_items : ""
    users ||--o{ ai_search_history : ""
    users ||--o{ ai_conversation_feedback : ""
    contract_projects ||--o{ taoyuan_projects : ""
    contract_projects ||--o{ taoyuan_dispatch_orders : ""
    documents ||--o{ taoyuan_dispatch_orders : ""

    %% ── 關聯表 ──
    project_vendor_association {
        int project_id PK,FK
        int vendor_id PK,FK
        string role
        float contract_amount
        date start_date
        date end_date
        string status
        datetime created_at
        datetime updated_at
    }
    project_user_assignments {
        int id PK
        int project_id FK
        int user_id FK
        string role
        boolean is_primary
        date assignment_date
        date start_date
        date end_date
        string status
        text notes
        datetime created_at
        datetime updated_at
    }

    %% ── 行事曆模組 ──
    document_calendar_events {
        int id PK
        int document_id FK "關聯的公文ID"
        string title "事件標題"
        text description "事件描述"
        datetime start_date "開始時間"
        datetime end_date "結束時間"
        boolean all_day "全天事件"
        string event_type "事件類型"
        string priority "優先級"
        string location "地點"
        int assigned_user_id FK "指派使用者ID"
        int created_by FK "建立者ID"
        datetime created_at "建立時間"
        datetime updated_at "更新時間"
        string status "事件狀態: pending/completed/cancelled"
        string google_event_id "Google Calendar 事件 ID"
        string google_sync_status "同步狀態: pending/synced/failed"
    }
    event_reminders {
        int id PK
        int event_id FK
        int recipient_user_id FK "接收用戶ID"
        string reminder_type "提醒類型"
        datetime reminder_time "提醒時間"
        text message "提醒訊息"
        boolean is_sent "是否已發送"
        string status "提醒狀態"
        int priority "優先級 (1-5, 5最高)"
        datetime next_retry_at "下次重試時間"
        int retry_count "重試次數"
        datetime created_at "建立時間"
        datetime updated_at "更新時間"
        string recipient_email "接收者Email"
        string notification_type "通知類型"
        int reminder_minutes "提前提醒分鐘數"
        string title "提醒標題"
        datetime sent_at "發送時間"
        int max_retries "最大重試次數"
    }

    %% ── 基礎實體 ──
    partner_vendors {
        int id PK
        string vendor_name "廠商名稱"
        string vendor_code UK "廠商代碼"
        string contact_person "聯絡人"
        string phone "電話"
        string email "電子郵件"
        string address "地址"
        string business_type "業務類型"
        int rating "評等"
        datetime created_at
        datetime updated_at
    }
    contract_projects {
        int id PK
        string project_name "案件名稱"
        int year "年度"
        string client_agency "委託單位"
        string contract_doc_number "契約文號"
        string project_code UK "專案編號"
        string category "案件類別"
        string case_nature "案件性質"
        string status "執行狀態"
        float contract_amount "契約金額"
        float winning_amount "得標金額"
        date start_date "開始日期"
        date end_date "結束日期"
        int progress "完成進度 (0-100)"
        string project_path "專案路徑"
        text notes "備註"
        text description "專案描述"
        datetime created_at
        datetime updated_at
        string contract_number "合約編號"
        string contract_type "合約類型"
        string location "專案地點"
        string procurement_method "採購方式"
        date completion_date "完工日期"
        date acceptance_date "驗收日期"
        int completion_percentage "完成百分比"
        date warranty_end_date "保固結束日期"
        string contact_person "聯絡人"
        string contact_phone "聯絡電話"
        int client_agency_id FK "委託機關ID"
        string agency_contact_person "機關承辦人"
        string agency_contact_phone "機關承辦電話"
        string agency_contact_email "機關承辦Email"
    }
    government_agencies {
        int id PK
        string agency_name "機關名稱"
        string agency_short_name "機關簡稱"
        string agency_code "機關代碼"
        string agency_type "機關類型"
        string contact_person "聯絡人"
        string phone "電話"
        string address "地址"
        string email "電子郵件"
        datetime created_at "建立時間"
        datetime updated_at "更新時間"
    }
    users {
        int id PK
        string username UK
        string email UK
        string password_hash
        string full_name
        boolean is_active
        boolean is_admin
        datetime created_at
        datetime last_login
        boolean is_superuser
        string google_id
        string avatar_url
        string auth_provider
        int login_count
        text permissions
        string role
        datetime updated_at
        boolean email_verified
        string department "部門名稱"
        string position "職稱"
        int failed_login_attempts "連續登入失敗次數"
        datetime locked_until "帳號鎖定到期時間"
        string password_reset_token "密碼重設 token (SHA-256 hash)"
        datetime password_reset_expires "密碼重設 token 過期時間"
        string email_verification_token "Email 驗證 token (SHA-256 hash)"
        datetime email_verification_expires "Email 驗證 token 過期時間"
        boolean mfa_enabled "是否啟用 TOTP MFA"
        string mfa_secret "TOTP secret (base32 encoded)"
        text mfa_backup_codes "備用碼 (JSON 格式, SHA-256 hashed)"
    }

    %% ── 公文模組 ──
    documents {
        int id PK
        string auto_serial "流水序號 (R0001=收文, S0001=發文)"
        string doc_number "公文文號"
        string doc_type "公文類型 (收文/發文)"
        string subject "主旨"
        string sender "發文單位"
        string receiver "受文單位"
        date doc_date "發文日期 (西元)"
        date receive_date "收文日期 (西元)"
        string status "處理狀態"
        string category "收發文分類"
        string delivery_method "發文形式"
        boolean has_attachment "是否含附件"
        int contract_project_id FK "關聯的承攬案件ID"
        int sender_agency_id FK "發文機關ID"
        int receiver_agency_id FK "受文機關ID"
        date send_date "發文日期"
        text title "標題"
        text content "說明"
        string cloud_file_link "雲端檔案連結"
        string dispatch_format "發文形式"
        string assignee "承辦人（多人以逗號分隔）"
        text notes "備註"
        text ck_note "簡要說明(乾坤備註)"
        datetime created_at "建立時間"
        datetime updated_at "更新時間"
    }
    document_attachments {
        int id PK "附件唯一識別ID"
        int document_id FK "關聯的公文ID"
        string file_name "檔案名稱"
        string file_path "檔案路徑"
        int file_size "檔案大小(bytes)"
        string mime_type "MIME類型"
        string storage_type "儲存類型: local/network/s3"
        string original_name "原始檔案名稱"
        string checksum "SHA256 校驗碼"
        int uploaded_by FK "上傳者 ID"
        datetime created_at "建立時間"
        datetime updated_at "更新時間"
    }

    %% ── AI 實體提取 ──
    document_entities {
        int id PK
        string entity_name "實體名稱"
        float confidence "提取信心度 0.0~1.0"
        string context "實體出現的上下文片段"
        datetime extracted_at "提取時間"
    }
    entity_relations {
        int id PK
        string source_entity_name "來源實體名稱"
        string source_entity_type "來源實體類型"
        string target_entity_name "目標實體名稱"
        string target_entity_type "目標實體類型"
        string relation_type "關係類型 (如 issues_permit, belongs_to)"
        string relation_label "關係顯示標籤"
        float confidence "提取信心度 0.0~1.0"
        datetime extracted_at "提取時間"
    }

    %% ── 知識圖譜 ──
    canonical_entities {
        int id PK
        string canonical_name "正規化名稱"
        text description "實體描述"
        int alias_count "別名數量"
        int mention_count "總被提及次數"
        datetime first_seen_at "首次出現"
        datetime last_seen_at "最近出現"
        datetime created_at
        datetime updated_at
    }
    entity_aliases {
        int id PK
        string alias_name "別名文字"
        float confidence "匹配信心度"
        datetime created_at
    }
    document_entity_mentions {
        int id PK
        string mention_text "原始提取文字"
        float confidence "提取信心度"
        string context "上下文片段"
        datetime created_at
    }
    entity_relationships {
        int id PK
        string relation_type "關係類型"
        string relation_label "顯示文字"
        float weight "關係權重（佐證公文數）"
        datetime valid_from "關係起始時間"
        datetime valid_to "關係結束時間（NULL=仍有效）"
        datetime invalidated_at "軟刪除時間（永不實際刪除）"
        int document_count "佐證公文數"
        datetime created_at
        datetime updated_at
    }
    graph_ingestion_events {
        int id PK
        int entities_found "找到的實體數"
        int entities_new "新建的正規實體數"
        int entities_merged "合併到既有實體數"
        int relations_found "找到的關係數"
        string llm_provider "使用的 LLM 提供者"
        int processing_ms "處理耗時 (ms)"
        text error_message "錯誤訊息"
        datetime created_at
    }

    %% ── 專案人員 ──
    project_agency_contacts {
        int id PK
        int project_id FK "關聯的專案ID"
        string contact_name "承辦人姓名"
        string position "職稱"
        string department "單位/科室"
        string phone "電話"
        string mobile "手機"
        string email "電子郵件"
        boolean is_primary "是否為主要承辦人"
        text notes "備註"
        datetime created_at "建立時間"
        datetime updated_at "更新時間"
        string line_name "LINE名稱"
        string org_short_name "單位簡稱"
        string category "類別(機關/乾坤/廠商)"
        string cloud_path "專案雲端路徑"
        string related_project_name "對應工程名稱"
    }
    staff_certifications {
        int id PK
        int user_id FK "關聯的使用者ID"
        string cert_type "證照類型: 核發證照/評量證書/訓練證明"
        string cert_name "證照名稱"
        string issuing_authority "核發機關"
        string cert_number "證照編號"
        date issue_date "核發日期"
        date expiry_date "有效期限（可為空表示永久有效）"
        string status "狀態: 有效/已過期/已撤銷"
        text notes "備註"
        string attachment_path "證照掃描檔路徑"
        datetime created_at "建立時間"
        datetime updated_at "更新時間"
    }

    %% ── 系統 + AI ──
    system_notifications {
        int id PK
        int user_id FK "接收者ID"
        int recipient_id FK "接收者ID (別名)"
        string title "通知標題"
        text message "通知內容"
        string notification_type "通知類型"
        boolean is_read "是否已讀"
        datetime created_at "建立時間"
        datetime read_at "已讀時間"
        jsonb data "附加資料"
    }
    user_sessions {
        int id PK
        int user_id FK
        string token_jti UK
        string refresh_token
        string ip_address
        text user_agent
        text device_info
        datetime created_at
        datetime expires_at
        datetime last_activity
        boolean is_active
        datetime revoked_at
    }
    site_navigation_items {
        int id PK
        string title "導航標題"
        string key UK "導航鍵值"
        string path "路徑"
        string icon "圖標"
        int sort_order "排序"
        int parent_id FK "父級ID"
        boolean is_enabled "是否啟用"
        boolean is_visible "是否顯示"
        int level "層級"
        string description "描述"
        string target "打開方式"
        text permission_required "所需權限(JSON格式)"
        datetime created_at "建立時間"
        datetime updated_at "更新時間"
    }
    site_configurations {
        int id PK
        string key UK "配置鍵"
        text value "配置值"
        string description "描述"
        string category "分類"
        boolean is_active "是否啟用"
        datetime created_at "建立時間"
        datetime updated_at "更新時間"
    }
    ai_prompt_versions {
        int id PK
        string feature "功能名稱"
        int version "版本號"
        text system_prompt "系統提示詞"
        text user_template "使用者提示詞模板"
        boolean is_active "是否為啟用版本"
        string description "版本說明"
        string created_by "建立者"
        datetime created_at "建立時間"
    }
    ai_search_history {
        int id PK
        int user_id FK "使用者 ID"
        text query "原始查詢文字"
        json parsed_intent "解析後的意圖 JSON"
        int results_count "搜尋結果數量"
        string search_strategy "搜尋策略"
        string source "來源"
        boolean synonym_expanded "是否同義詞擴展"
        string related_entity "關聯實體"
        int latency_ms "回應時間 ms"
        float confidence "意圖信心度"
        int feedback_score "使用者回饋 (1=有用, -1=無用, NULL=未評)"
        datetime created_at "建立時間"
    }
    ai_conversation_feedback {
        int id PK
        int user_id FK "使用者 ID"
        string conversation_id "對話 ID (前端生成)"
        int message_index "訊息序號"
        string feature_type "功能類型 (agent/rag)"
        int score "評分 (1=有用, -1=無用)"
        text question "使用者問題"
        string answer_preview "回答前 200 字"
        string feedback_text "文字回饋 (可選)"
        int latency_ms "回答延遲 ms"
        string model "使用的模型"
        datetime created_at "建立時間"
    }
    ai_synonyms {
        int id PK
        string category "分類"
        text words "同義詞列表，逗號分隔"
        boolean is_active "是否啟用"
        datetime created_at "建立時間"
        datetime updated_at "更新時間"
    }

    %% ── 桃園派工 ──
    taoyuan_projects {
        int id PK
        int contract_project_id FK "關聯承攬案件"
        int sequence_no "項次"
        int review_year "審議年度"
        string case_type "案件類型"
        string district "行政區"
        string project_name "工程名稱"
        string start_point "工程起點"
        string start_coordinate "起點坐標(經緯度)"
        string end_point "工程迄點"
        string end_coordinate "迄點坐標(經緯度)"
        float road_length "道路長度(公尺)"
        float current_width "現況路寬"
        float planned_width "計畫路寬"
        int public_land_count "公有土地筆數"
        int private_land_count "私有土地筆數"
        int rc_count "RC數量"
        int iron_sheet_count "鐵皮屋數量"
        float construction_cost "工程費"
        float land_cost "用地費"
        float compensation_cost "補償費"
        float total_cost "總經費"
        string review_result "審議結果"
        string urban_plan "都市計畫"
        date completion_date "完工日期"
        string proposer "提案人"
        text remark "備註"
        string sub_case_name "分案名稱"
        string case_handler "案件承辦"
        string survey_unit "查估單位"
        string land_agreement_status "土地協議進度"
        string land_expropriation_status "土地徵收進度"
        string building_survey_status "地上物查估進度"
        date actual_entry_date "實際進場日期"
        string acceptance_status "驗收狀態"
        datetime created_at
        datetime updated_at
    }
    taoyuan_dispatch_orders {
        int id PK
        int contract_project_id FK "關聯承攬案件"
        string dispatch_no UK "派工單號"
        int agency_doc_id FK "關聯機關公文"
        int company_doc_id FK "關聯乾坤公文"
        string project_name "工程名稱/派工事項"
        string work_type "作業類別(可多選,逗號分隔)"
        string sub_case_name "分案名稱/派工備註"
        string deadline "履約期限"
        string case_handler "案件承辦"
        string survey_unit "查估單位"
        string cloud_folder "雲端資料夾"
        string project_folder "專案資料夾"
        string contact_note "聯絡備註"
        datetime created_at
        datetime updated_at
    }
    taoyuan_dispatch_project_link {
        int id PK
        int dispatch_order_id FK
        int taoyuan_project_id FK
        datetime created_at
    }
    taoyuan_dispatch_document_link {
        int id PK
        int dispatch_order_id FK
        int document_id FK
        string link_type "agency_incoming/company_outgoing"
        datetime created_at
    }
    taoyuan_document_project_link {
        int id PK
        int document_id FK
        int taoyuan_project_id FK
        string link_type "關聯類型：agency_incoming/company_outgoing"
        string notes "關聯備註"
        datetime created_at
    }
    taoyuan_contract_payments {
        int id PK
        int dispatch_order_id FK
        date work_01_date "01.地上物查估-派工日期"
        float work_01_amount "01.地上物查估-派工金額"
        date work_02_date "02.土地協議市價查估-派工日期"
        float work_02_amount "02.土地協議市價查估-派工金額"
        date work_03_date "03.土地徵收市價查估-派工日期"
        float work_03_amount "03.土地徵收市價查估-派工金額"
        date work_04_date "04.相關計畫書製作-派工日期"
        float work_04_amount "04.相關計畫書製作-派工金額"
        date work_05_date "05.測量作業-派工日期"
        float work_05_amount "05.測量作業-派工金額"
        date work_06_date "06.樁位測釘作業-派工日期"
        float work_06_amount "06.樁位測釘作業-派工金額"
        date work_07_date "07.辦理教育訓練-派工日期"
        float work_07_amount "07.辦理教育訓練-派工金額"
        float current_amount "本次派工金額"
        float cumulative_amount "累進派工金額"
        float remaining_amount "剩餘金額"
        date acceptance_date "完成驗收日期"
        datetime created_at
        datetime updated_at
    }
    taoyuan_dispatch_work_types {
        int id PK
        int dispatch_order_id
        string work_type
        int sort_order "排序順序"
        datetime created_at
    }
    taoyuan_dispatch_attachments {
        int id PK
        string file_name "儲存檔案名稱"
        string file_path "檔案路徑"
        int file_size "檔案大小(bytes)"
        string mime_type "MIME類型"
        string storage_type "儲存類型: local/network/s3"
        string original_name "原始檔案名稱"
        string checksum "SHA256 校驗碼"
        datetime created_at
        datetime updated_at
    }
    taoyuan_work_records {
        int id PK
        int dispatch_order_id
        int taoyuan_project_id
        int incoming_doc_id
        int outgoing_doc_id
        int document_id
        int parent_record_id
        string work_category
        int batch_no
        string batch_label
        string milestone_type
        string description "事項描述"
        string submission_type
        date record_date "紀錄日期(民國轉西元)"
        date deadline_date "期限日期"
        date completed_date "完成日期"
        string status
        int sort_order "排序順序"
        text notes "備註"
        datetime created_at
        datetime updated_at
    }

```

<!--
  Schema Diagram — generated 2026-02-27T17:21:26
  Models: 34 entities + 2 association tables
  Columns: 471
  Foreign Keys: 17

  Modules:
    關聯表: project_vendor_association, project_user_assignments
    行事曆模組: document_calendar_events, event_reminders
    基礎實體: partner_vendors, contract_projects, government_agencies, users
    公文模組: documents, document_attachments
    AI 實體提取: document_entities, entity_relations
    知識圖譜: canonical_entities, entity_aliases, document_entity_mentions, entity_relationships, graph_ingestion_events
    專案人員: project_agency_contacts, staff_certifications
    系統 + AI: system_notifications, user_sessions, site_navigation_items, site_configurations, ai_prompt_versions, ai_search_history, ai_conversation_feedback, ai_synonyms
    桃園派工: taoyuan_projects, taoyuan_dispatch_orders, taoyuan_dispatch_project_link, taoyuan_dispatch_document_link, taoyuan_document_project_link, taoyuan_contract_payments, taoyuan_dispatch_work_types, taoyuan_dispatch_attachments, taoyuan_work_records
-->
