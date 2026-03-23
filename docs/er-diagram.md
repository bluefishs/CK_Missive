# ER Diagram — CK_Missive 資料庫結構

> 自動生成，請勿手動編輯。執行 `python backend/scripts/extract_er_model.py` 重新生成。

```mermaid
erDiagram
    agent_query_traces ||--o{ agent_tool_call_logs : "trace_id"
    users ||--o{ ai_conversation_feedback : "user_id"
    users ||--o{ ai_search_history : "user_id"
    government_agencies ||--o{ canonical_entities : "linked_agency_id"
    taoyuan_projects ||--o{ canonical_entities : "linked_project_id"
    government_agencies ||--o{ contract_projects : "client_agency_id"
    documents ||--o{ document_ai_analyses : "document_id"
    documents ||--o{ document_attachments : "document_id"
    users ||--o{ document_attachments : "uploaded_by"
    users ||--o{ document_calendar_events : "assigned_user_id"
    users ||--o{ document_calendar_events : "created_by"
    documents ||--o{ document_calendar_events : "document_id"
    documents ||--o{ document_chunks : "document_id"
    documents ||--o{ document_entities : "document_id"
    canonical_entities ||--o{ document_entity_mentions : "canonical_entity_id"
    documents ||--o{ document_entity_mentions : "document_id"
    contract_projects ||--o{ documents : "contract_project_id"
    government_agencies ||--o{ documents : "receiver_agency_id"
    government_agencies ||--o{ documents : "sender_agency_id"
    canonical_entities ||--o{ entity_aliases : "canonical_entity_id"
    documents ||--o{ entity_relations : "document_id"
    documents ||--o{ entity_relationships : "first_document_id"
    canonical_entities ||--o{ entity_relationships : "source_entity_id"
    canonical_entities ||--o{ entity_relationships : "target_entity_id"
    erp_quotations ||--o{ erp_billings : "erp_quotation_id"
    erp_invoices ||--o{ erp_billings : "invoice_id"
    erp_quotations ||--o{ erp_invoices : "erp_quotation_id"
    users ||--o{ erp_quotations : "created_by"
    erp_quotations ||--o{ erp_vendor_payables : "erp_quotation_id"
    partner_vendors ||--o{ erp_vendor_payables : "vendor_id"
    document_calendar_events ||--o{ event_reminders : "event_id"
    users ||--o{ event_reminders : "recipient_user_id"
    expense_invoices ||--o{ expense_invoice_items : "invoice_id"
    users ||--o{ expense_invoices : "user_id"
    partner_vendors ||--o{ expense_invoices : "vendor_id"
    users ||--o{ finance_ledgers : "user_id"
    partner_vendors ||--o{ finance_ledgers : "vendor_id"
    government_agencies ||--o{ government_agencies : "parent_agency_id"
    documents ||--o{ graph_ingestion_events : "document_id"
    pm_cases ||--o{ pm_case_staff : "pm_case_id"
    users ||--o{ pm_case_staff : "user_id"
    users ||--o{ pm_cases : "created_by"
    pm_cases ||--o{ pm_milestones : "pm_case_id"
    contract_projects ||--o{ project_agency_contacts : "project_id"
    contract_projects ||--o{ project_user_assignments : "project_id"
    users ||--o{ project_user_assignments : "user_id"
    contract_projects ||--o{ project_vendor_association : "project_id"
    partner_vendors ||--o{ project_vendor_association : "vendor_id"
    site_navigation_items ||--o{ site_navigation_items : "parent_id"
    users ||--o{ staff_certifications : "user_id"
    users ||--o{ system_notifications : "recipient_id"
    users ||--o{ system_notifications : "user_id"
    taoyuan_dispatch_orders ||--o{ taoyuan_contract_payments : "dispatch_order_id"
    taoyuan_dispatch_orders ||--o{ taoyuan_dispatch_attachments : "dispatch_order_id"
    users ||--o{ taoyuan_dispatch_attachments : "uploaded_by"
    taoyuan_dispatch_orders ||--o{ taoyuan_dispatch_document_link : "dispatch_order_id"
    documents ||--o{ taoyuan_dispatch_document_link : "document_id"
    canonical_entities ||--o{ taoyuan_dispatch_entity_link : "canonical_entity_id"
    taoyuan_dispatch_orders ||--o{ taoyuan_dispatch_entity_link : "dispatch_order_id"
    documents ||--o{ taoyuan_dispatch_orders : "agency_doc_id"
    documents ||--o{ taoyuan_dispatch_orders : "company_doc_id"
    contract_projects ||--o{ taoyuan_dispatch_orders : "contract_project_id"
    taoyuan_dispatch_orders ||--o{ taoyuan_dispatch_project_link : "dispatch_order_id"
    taoyuan_projects ||--o{ taoyuan_dispatch_project_link : "taoyuan_project_id"
    taoyuan_dispatch_orders ||--o{ taoyuan_dispatch_work_types : "dispatch_order_id"
    documents ||--o{ taoyuan_document_project_link : "document_id"
    taoyuan_projects ||--o{ taoyuan_document_project_link : "taoyuan_project_id"
    contract_projects ||--o{ taoyuan_projects : "contract_project_id"
    taoyuan_dispatch_orders ||--o{ taoyuan_work_records : "dispatch_order_id"
    documents ||--o{ taoyuan_work_records : "document_id"
    documents ||--o{ taoyuan_work_records : "incoming_doc_id"
    documents ||--o{ taoyuan_work_records : "outgoing_doc_id"
    taoyuan_work_records ||--o{ taoyuan_work_records : "parent_record_id"
    taoyuan_projects ||--o{ taoyuan_work_records : "taoyuan_project_id"
    users ||--o{ user_sessions : "user_id"

    agent_learnings {
        int id "PK"
        varchar session_id "NOT NULL"
        varchar learning_type "NOT NULL"
        text content "NOT NULL"
        varchar content_hash "NOT NULL"
        text source_question
        float8 confidence
        int hit_count
        bool is_active
        timestamptz created_at
        timestamptz updated_at
    }
    agent_query_traces {
        int id "PK"
        varchar query_id "NOT NULL"
        text question "NOT NULL"
        varchar context
        varchar route_type "NOT NULL"
        int plan_tool_count
        int hint_count
        int iterations
        int total_results
        bool correction_triggered
        bool react_triggered
        int citation_count
        int citation_verified
        int answer_length
        int total_ms
        varchar model_used
        smallint feedback_score
        varchar feedback_text
        timestamptz feedback_at
        varchar answer_preview
        jsonb tools_used
        timestamptz created_at "NOT NULL"
    }
    agent_tool_call_logs {
        int id "PK"
        int trace_id "FK,NOT NULL"
        varchar tool_name "NOT NULL"
        jsonb params
        bool success "NOT NULL"
        int result_count
        int duration_ms
        varchar error_message
        smallint call_order
        timestamptz created_at "NOT NULL"
    }
    ai_conversation_feedback {
        int id "PK"
        int user_id "FK"
        varchar conversation_id "NOT NULL"
        int message_index "NOT NULL"
        varchar feature_type "NOT NULL"
        int score "NOT NULL"
        text question
        varchar answer_preview
        varchar feedback_text
        int latency_ms
        varchar model
        timestamptz created_at
    }
    ai_prompt_versions {
        int id "PK"
        varchar feature "NOT NULL"
        int version "NOT NULL"
        text system_prompt "NOT NULL"
        text user_template
        bool is_active "NOT NULL"
        varchar description
        varchar created_by
        timestamptz created_at
    }
    ai_search_history {
        int id "PK"
        int user_id "FK"
        text query "NOT NULL"
        json parsed_intent
        int results_count
        varchar search_strategy
        varchar source
        bool synonym_expanded
        varchar related_entity
        int latency_ms
        float8 confidence
        timestamptz created_at
        vector query_embedding
        int feedback_score
    }
    ai_synonyms {
        int id "PK"
        varchar category "NOT NULL"
        text words "NOT NULL"
        bool is_active "NOT NULL"
        timestamptz created_at
        timestamptz updated_at
    }
    audit_logs {
        bigint id "PK"
        varchar table_name "NOT NULL"
        int record_id "NOT NULL"
        varchar action "NOT NULL"
        text changes
        int user_id
        varchar user_name
        varchar source
        varchar ip_address
        bool is_critical
        timestamp created_at
    }
    canonical_entities {
        int id "PK"
        varchar canonical_name "NOT NULL"
        varchar entity_type "NOT NULL"
        text description
        int alias_count
        int mention_count
        timestamp first_seen_at
        timestamp last_seen_at
        timestamp created_at
        timestamp updated_at
        vector embedding
        int linked_agency_id "FK"
        int linked_project_id "FK"
        varchar source_project "NOT NULL"
        varchar external_id
        jsonb external_meta
    }
    contract_projects {
        int id "PK"
        varchar project_name "NOT NULL"
        varchar project_code
        int year
        varchar category
        varchar status
        varchar client_agency
        numeric contract_amount
        date start_date
        date end_date
        text description
        timestamp created_at
        timestamp updated_at
        varchar contract_number
        varchar contract_type
        varchar location
        varchar procurement_method
        float8 winning_amount
        date completion_date
        date acceptance_date
        int completion_percentage
        date warranty_end_date
        varchar contact_person
        varchar contact_phone
        text notes
        int client_agency_id "FK"
        varchar project_path
        varchar agency_contact_person
        varchar agency_contact_phone
        varchar agency_contact_email
        varchar contract_doc_number
        int progress
        varchar case_nature
        bool has_dispatch_management
        varchar client_type
    }
    document_ai_analyses {
        int id "PK"
        int document_id "FK,NOT NULL"
        text summary
        float8 summary_confidence
        varchar suggested_doc_type
        float8 doc_type_confidence
        varchar suggested_category
        float8 category_confidence
        text classification_reasoning
        jsonb keywords
        float8 keywords_confidence
        varchar llm_provider
        varchar llm_model
        int processing_ms
        varchar source_text_hash
        varchar analysis_version
        varchar status
        text error_message
        bool is_stale
        timestamp analyzed_at
        timestamp created_at
        timestamp updated_at
    }
    document_attachments {
        int id "PK"
        int document_id "FK,NOT NULL"
        varchar file_name
        varchar file_path
        int file_size
        varchar mime_type
        timestamp created_at
        timestamp updated_at
        varchar storage_type
        varchar original_name
        varchar checksum
        int uploaded_by "FK"
    }
    document_calendar_events {
        int id "PK"
        int document_id "FK"
        varchar title "NOT NULL"
        text description
        timestamp start_date "NOT NULL"
        timestamp end_date
        bool all_day
        varchar event_type
        varchar priority
        varchar location
        int assigned_user_id "FK"
        int created_by "FK"
        timestamp created_at
        timestamp updated_at
        varchar google_event_id
        varchar google_sync_status
        varchar status
    }
    document_chunks {
        int id "PK"
        int document_id "FK,NOT NULL"
        int chunk_index "NOT NULL"
        text chunk_text "NOT NULL"
        int start_char
        int end_char
        int token_count
        timestamp created_at
        vector embedding
    }
    document_entities {
        int id "PK"
        int document_id "FK,NOT NULL"
        varchar entity_name "NOT NULL"
        varchar entity_type "NOT NULL"
        float8 confidence
        varchar context
        timestamp extracted_at
    }
    document_entity_mentions {
        int id "PK"
        int document_id "FK,NOT NULL"
        int canonical_entity_id "FK,NOT NULL"
        varchar mention_text "NOT NULL"
        float8 confidence
        varchar context
        timestamp created_at
    }
    documents {
        int id "PK"
        varchar auto_serial "NOT NULL"
        varchar category
        date send_date
        date receive_date
        varchar sender
        varchar receiver
        text title
        varchar status
        timestamp created_at
        timestamp updated_at
        varchar doc_number
        varchar doc_type
        varchar subject
        date doc_date
        int sender_agency_id "FK"
        int receiver_agency_id "FK"
        int contract_project_id "FK"
        varchar delivery_method
        varchar cloud_file_link
        bool has_attachment
        varchar dispatch_format
        varchar assignee
        text notes
        text content
        text ck_note
        vector embedding
        varchar normalized_sender
        varchar normalized_receiver
        text cc_receivers
        text keywords
        bool ner_pending "NOT NULL"
        tsvector search_vector
    }
    einvoice_sync_logs {
        int id "PK"
        varchar buyer_ban "NOT NULL"
        date query_start "NOT NULL"
        date query_end "NOT NULL"
        varchar status "NOT NULL"
        int total_fetched "NOT NULL"
        int new_imported "NOT NULL"
        int skipped_duplicate "NOT NULL"
        int detail_fetched "NOT NULL"
        text error_message
        timestamp started_at
        timestamp completed_at
    }
    entity_aliases {
        int id "PK"
        varchar alias_name "NOT NULL"
        int canonical_entity_id "FK,NOT NULL"
        varchar source
        float8 confidence
        timestamp created_at
    }
    entity_relations {
        int id "PK"
        varchar source_entity_name "NOT NULL"
        varchar source_entity_type "NOT NULL"
        varchar target_entity_name "NOT NULL"
        varchar target_entity_type "NOT NULL"
        varchar relation_type "NOT NULL"
        varchar relation_label
        int document_id "FK,NOT NULL"
        float8 confidence
        timestamp extracted_at
    }
    entity_relationships {
        int id "PK"
        int source_entity_id "FK,NOT NULL"
        int target_entity_id "FK,NOT NULL"
        varchar relation_type "NOT NULL"
        varchar relation_label
        float8 weight
        timestamp valid_from
        timestamp valid_to
        timestamp invalidated_at
        int first_document_id "FK"
        int document_count
        timestamp created_at
        timestamp updated_at
        varchar source_project "NOT NULL"
    }
    erp_billings {
        int id "PK"
        int erp_quotation_id "FK,NOT NULL"
        varchar billing_period
        date billing_date "NOT NULL"
        numeric billing_amount "NOT NULL"
        int invoice_id "FK"
        varchar payment_status
        date payment_date
        numeric payment_amount
        text notes
        timestamp created_at
        timestamp updated_at
    }
    erp_invoices {
        int id "PK"
        int erp_quotation_id "FK,NOT NULL"
        varchar invoice_number "NOT NULL"
        date invoice_date "NOT NULL"
        numeric amount "NOT NULL"
        numeric tax_amount
        varchar invoice_type
        varchar description
        varchar status
        timestamp voided_at
        text notes
        timestamp created_at
        timestamp updated_at
    }
    erp_quotations {
        int id "PK"
        varchar case_code "NOT NULL"
        varchar case_name
        int year
        numeric total_price
        numeric tax_amount
        numeric outsourcing_fee
        numeric personnel_fee
        numeric overhead_fee
        numeric other_cost
        varchar status
        text notes
        int created_by "FK"
        timestamp created_at
        timestamp updated_at
        numeric budget_limit
    }
    erp_vendor_payables {
        int id "PK"
        int erp_quotation_id "FK,NOT NULL"
        varchar vendor_name "NOT NULL"
        varchar vendor_code
        numeric payable_amount "NOT NULL"
        varchar description
        date due_date
        date paid_date
        numeric paid_amount
        varchar payment_status
        varchar invoice_number
        text notes
        timestamp created_at
        timestamp updated_at
        int vendor_id "FK"
    }
    event_reminders {
        int id "PK"
        int event_id "FK,NOT NULL"
        int recipient_user_id "FK"
        varchar reminder_type "NOT NULL"
        timestamp reminder_time "NOT NULL"
        text message
        bool is_sent
        varchar status
        int priority
        timestamp next_retry_at
        int retry_count
        timestamp created_at
        timestamp updated_at
        varchar recipient_email
        varchar notification_type "NOT NULL"
        int reminder_minutes
        varchar title
        timestamp sent_at
        int max_retries "NOT NULL"
    }
    expense_invoice_items {
        int id "PK"
        int invoice_id "FK,NOT NULL"
        varchar item_name "NOT NULL"
        numeric qty "NOT NULL"
        numeric unit_price "NOT NULL"
        numeric amount "NOT NULL"
        timestamp created_at
    }
    expense_invoices {
        int id "PK"
        varchar inv_num "NOT NULL"
        date date "NOT NULL"
        numeric amount "NOT NULL"
        numeric tax_amount
        varchar buyer_ban
        varchar seller_ban
        varchar case_code
        int user_id "FK"
        varchar category
        varchar status "NOT NULL"
        varchar source "NOT NULL"
        varchar source_image_path
        text raw_qr_data
        varchar notes
        timestamp created_at
        timestamp updated_at
        varchar receipt_image_path
        varchar mof_invoice_track
        varchar mof_period
        timestamp synced_at
        varchar currency "NOT NULL"
        numeric original_amount
        numeric exchange_rate
        int vendor_id "FK"
    }
    finance_ledgers {
        int id "PK"
        varchar case_code
        varchar source_type "NOT NULL"
        int source_id
        numeric amount "NOT NULL"
        varchar entry_type "NOT NULL"
        varchar category
        varchar description
        int user_id "FK"
        date transaction_date "NOT NULL"
        timestamp created_at
        timestamp updated_at
        int vendor_id "FK"
    }
    government_agencies {
        int id "PK"
        varchar agency_name "NOT NULL"
        varchar agency_code
        varchar agency_type
        varchar contact_person
        varchar phone
        varchar email
        text address
        timestamp created_at
        timestamp updated_at
        varchar agency_short_name
        varchar tax_id
        bool is_self "NOT NULL"
        int parent_agency_id "FK"
        varchar source "NOT NULL"
    }
    graph_ingestion_events {
        int id "PK"
        int document_id "FK,NOT NULL"
        varchar event_type "NOT NULL"
        int entities_found
        int entities_new
        int entities_merged
        int relations_found
        varchar llm_provider
        int processing_ms
        varchar status
        text error_message
        timestamp created_at
    }
    kb_chunks {
        int id "PK"
        varchar file_path "NOT NULL"
        varchar filename "NOT NULL"
        varchar section_title
        text content "NOT NULL"
        int chunk_index
        timestamp created_at
        timestamp updated_at
        vector embedding
    }
    notifications {
        bigint id "PK"
        varchar type "NOT NULL"
        varchar severity "NOT NULL"
        varchar title "NOT NULL"
        text message "NOT NULL"
        varchar source_table
        int source_id
        jsonb changes
        int user_id
        varchar user_name
        bool is_read
        timestamp read_at
        int read_by
        timestamp created_at
    }
    partner_vendors {
        int id "PK"
        varchar vendor_name "NOT NULL"
        varchar vendor_code
        varchar contact_person
        varchar phone
        varchar email
        text address
        varchar business_type
        int rating
        timestamp created_at
        timestamp updated_at
    }
    pm_case_staff {
        int id "PK"
        int pm_case_id "FK,NOT NULL"
        int user_id "FK"
        varchar staff_name "NOT NULL"
        varchar role "NOT NULL"
        bool is_primary
        date start_date
        date end_date
        varchar notes
        timestamp created_at
    }
    pm_cases {
        int id "PK"
        varchar case_code "NOT NULL"
        varchar case_name "NOT NULL"
        int year
        varchar category
        varchar client_name
        varchar client_contact
        varchar client_phone
        numeric contract_amount
        varchar status "NOT NULL"
        int progress
        date start_date
        date end_date
        date actual_end_date
        varchar location
        text description
        text notes
        int created_by "FK"
        timestamp created_at
        timestamp updated_at
    }
    pm_milestones {
        int id "PK"
        int pm_case_id "FK,NOT NULL"
        varchar milestone_name "NOT NULL"
        varchar milestone_type
        date planned_date
        date actual_date
        varchar status
        int sort_order
        text notes
        timestamp created_at
        timestamp updated_at
    }
    project_agency_contacts {
        int id "PK"
        int project_id "FK,NOT NULL"
        varchar contact_name "NOT NULL"
        varchar position
        varchar department
        varchar phone
        varchar mobile
        varchar email
        bool is_primary
        text notes
        timestamp created_at
        timestamp updated_at
        varchar line_name
        varchar org_short_name
        varchar category
        varchar cloud_path
        varchar related_project_name
    }
    project_user_assignments {
        int id "PK"
        int project_id "FK,NOT NULL"
        int user_id "FK,NOT NULL"
        varchar role
        bool is_primary
        date assignment_date
        date start_date
        date end_date
        varchar status
        text notes
        timestamp created_at
        timestamp updated_at
    }
    project_vendor_association {
        int project_id "PK,FK"
        int vendor_id "PK,FK"
        varchar role
        numeric contract_amount
        date start_date
        date end_date
        varchar status
        timestamp created_at
        timestamp updated_at
    }
    site_configurations {
        int id "PK"
        varchar key "NOT NULL"
        text value
        varchar description
        varchar category
        bool is_active
        timestamp created_at
        timestamp updated_at
    }
    site_navigation_items {
        int id "PK"
        varchar title "NOT NULL"
        varchar key "NOT NULL"
        varchar path
        varchar icon
        int sort_order
        int parent_id "FK"
        bool is_enabled
        bool is_visible
        int level
        varchar description
        varchar target
        text permission_required
        timestamp created_at
        timestamp updated_at
    }
    staff_certifications {
        int id "PK"
        int user_id "FK,NOT NULL"
        varchar cert_type "NOT NULL"
        varchar cert_name "NOT NULL"
        varchar issuing_authority
        varchar cert_number
        date issue_date
        date expiry_date
        varchar status
        text notes
        varchar attachment_path
        timestamp created_at
        timestamp updated_at
    }
    system_notifications {
        int id "PK"
        int user_id "FK"
        int recipient_id "FK"
        varchar title "NOT NULL"
        text message "NOT NULL"
        varchar notification_type
        bool is_read
        timestamp created_at
        timestamp read_at
        jsonb data
    }
    taoyuan_contract_payments {
        int id "PK"
        int dispatch_order_id "FK,NOT NULL"
        date work_01_date
        numeric work_01_amount
        date work_02_date
        numeric work_02_amount
        date work_03_date
        numeric work_03_amount
        date work_04_date
        numeric work_04_amount
        date work_05_date
        numeric work_05_amount
        date work_06_date
        numeric work_06_amount
        date work_07_date
        numeric work_07_amount
        numeric current_amount
        numeric cumulative_amount
        numeric remaining_amount
        date acceptance_date
        timestamp created_at
        timestamp updated_at
    }
    taoyuan_dispatch_attachments {
        int id "PK"
        int dispatch_order_id "FK,NOT NULL"
        varchar file_name
        varchar file_path
        int file_size
        varchar mime_type
        varchar storage_type
        varchar original_name
        varchar checksum
        int uploaded_by "FK"
        timestamp created_at
        timestamp updated_at
    }
    taoyuan_dispatch_document_link {
        int id "PK"
        int dispatch_order_id "FK,NOT NULL"
        int document_id "FK,NOT NULL"
        varchar link_type "NOT NULL"
        timestamp created_at
        varchar confidence
    }
    taoyuan_dispatch_entity_link {
        int id "PK"
        int dispatch_order_id "FK,NOT NULL"
        int canonical_entity_id "FK,NOT NULL"
        varchar source "NOT NULL"
        float8 confidence "NOT NULL"
        timestamp created_at
    }
    taoyuan_dispatch_orders {
        int id "PK"
        int contract_project_id "FK"
        varchar dispatch_no "NOT NULL"
        int agency_doc_id "FK"
        int company_doc_id "FK"
        varchar project_name
        varchar work_type
        varchar sub_case_name
        varchar deadline
        varchar case_handler
        varchar survey_unit
        varchar cloud_folder
        varchar project_folder
        timestamp created_at
        timestamp updated_at
        varchar contact_note
        int batch_no
        varchar batch_label
        varchar agency_doc_number_raw
        varchar company_doc_number_raw
    }
    taoyuan_dispatch_project_link {
        int id "PK"
        int dispatch_order_id "FK,NOT NULL"
        int taoyuan_project_id "FK,NOT NULL"
        timestamp created_at
    }
    taoyuan_dispatch_work_types {
        int id "PK"
        int dispatch_order_id "FK,NOT NULL"
        varchar work_type "NOT NULL"
        int sort_order
        timestamp created_at
    }
    taoyuan_document_project_link {
        int id "PK"
        int document_id "FK,NOT NULL"
        int taoyuan_project_id "FK,NOT NULL"
        varchar link_type
        varchar notes
        timestamp created_at
    }
    taoyuan_projects {
        int id "PK"
        int contract_project_id "FK"
        int sequence_no
        int review_year
        varchar case_type
        varchar district
        varchar project_name "NOT NULL"
        varchar start_point
        varchar end_point
        numeric road_length
        numeric current_width
        numeric planned_width
        int public_land_count
        int private_land_count
        int rc_count
        int iron_sheet_count
        numeric construction_cost
        numeric land_cost
        numeric compensation_cost
        numeric total_cost
        varchar review_result
        varchar urban_plan
        date completion_date
        varchar proposer
        text remark
        varchar sub_case_name
        varchar case_handler
        varchar survey_unit
        varchar land_agreement_status
        varchar land_expropriation_status
        varchar building_survey_status
        date actual_entry_date
        varchar acceptance_status
        timestamp created_at
        timestamp updated_at
        varchar start_coordinate
        varchar end_coordinate
    }
    taoyuan_work_records {
        int id "PK"
        int dispatch_order_id "FK,NOT NULL"
        int taoyuan_project_id "FK"
        int incoming_doc_id "FK"
        int outgoing_doc_id "FK"
        varchar milestone_type "NOT NULL"
        varchar description
        varchar submission_type
        date record_date "NOT NULL"
        date deadline_date
        date completed_date
        varchar status
        int sort_order
        text notes
        timestamp created_at
        timestamp updated_at
        int batch_no
        varchar batch_label
        int document_id "FK"
        int parent_record_id "FK"
        varchar work_category
    }
    user_sessions {
        int id "PK"
        int user_id "FK,NOT NULL"
        varchar token_jti "NOT NULL"
        varchar refresh_token
        varchar ip_address
        text user_agent
        text device_info
        timestamp created_at
        timestamp expires_at "NOT NULL"
        timestamp last_activity
        bool is_active
        timestamp revoked_at
    }
    users {
        int id "PK"
        varchar username "NOT NULL"
        varchar email "NOT NULL"
        varchar password_hash
        varchar full_name
        bool is_active
        bool is_admin
        bool is_superuser
        varchar google_id
        varchar avatar_url
        varchar auth_provider
        int login_count
        text permissions
        varchar role
        bool email_verified
        timestamp created_at
        timestamp last_login
        timestamp updated_at
        varchar department
        varchar position
        int failed_login_attempts "NOT NULL"
        timestamptz locked_until
        varchar password_reset_token
        timestamptz password_reset_expires
        bool mfa_enabled "NOT NULL"
        varchar mfa_secret
        text mfa_backup_codes
        varchar email_verification_token
        timestamptz email_verification_expires
        varchar line_user_id
        varchar line_display_name
    }
```

## 統計

| 指標 | 數值 |
|------|------|
| 總表數 | 56 |
| 總欄位數 | 783 |
| 外鍵關聯 | 78 |
| 自訂列舉型別 | 0 |
