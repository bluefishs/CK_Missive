/**
 * 資料庫元數據配置
 * @description 資料表結構、關聯與分類定義
 * @extracted_from EnhancedDatabaseViewer.tsx
 */

export interface TableRelationship {
  table: string;
  type: 'one_to_many' | 'many_to_one' | 'many_to_many';
  foreign_key: string;
  description: string;
}

export interface ColumnMetadata {
  chinese_name: string;
  type: string;
  description: string;
}

export interface TableMetadataItem {
  chinese_name: string;
  description: string;
  category: string;
  frontend_pages: string[];
  primary_key: string;
  relationships: TableRelationship[];
  columns?: Record<string, ColumnMetadata>;
  api_endpoints?: string[];
  main_fields?: string[];
}

export interface CategoryInfo {
  chinese_name: string;
  description: string;
  color: string;
  icon: string;
}

export interface DatabaseMetadata {
  table_metadata: Record<string, TableMetadataItem>;
  categories: Record<string, CategoryInfo>;
}

/**
 * 取得分類顯示名稱
 */
export const getCategoryDisplayName = (category: string): string => {
  const names: Record<string, string> = {
    core: '核心業務',
    business: '業務管理',
    auth: '身份驗證',
    system: '系統配置',
    integration: '整合服務',
    reference: '參考資料',
    relation: '關聯表'
  };
  return names[category] || category;
};

/**
 * 取得分類顏色
 */
export const getCategoryColor = (category: string): string => {
  const colors: Record<string, string> = {
    core: '#1976d2',
    business: '#52c41a',
    auth: '#fa8c16',
    system: '#722ed1',
    integration: '#13c2c2',
    reference: '#eb2f96',
    relation: '#666666'
  };
  return colors[category] || '#999999';
};

export const databaseMetadata: DatabaseMetadata = {
  "table_metadata": {
    "alembic_version": {
      "chinese_name": "資料庫版本控制",
      "description": "Alembic 遷移版本記錄",
      "category": "system",
      "frontend_pages": [],
      "primary_key": "version_num",
      "relationships": []
    },
    "users": {
      "chinese_name": "使用者管理",
      "description": "系統使用者帳號與權限管理",
      "category": "auth",
      "frontend_pages": ["/admin/user-management", "/profile"],
      "primary_key": "id",
      "relationships": [
        { "table": "user_sessions", "type": "one_to_many", "foreign_key": "user_id", "description": "使用者登入會話記錄" },
        { "table": "documents", "type": "one_to_many", "foreign_key": "created_by", "description": "使用者建立的公文" }
      ],
      "api_endpoints": ["GET /api/auth/users", "POST /api/auth/register", "GET /api/auth/me", "PUT /api/admin/user-management/users/{id}"],
      "main_fields": ["id", "email", "username", "full_name", "is_active", "is_admin"],
      "columns": {
        "id": { "chinese_name": "使用者ID", "type": "INTEGER", "description": "主鍵，自動遞增" },
        "username": { "chinese_name": "使用者名稱", "type": "VARCHAR(50)", "description": "登入帳號名稱" },
        "email": { "chinese_name": "電子郵件", "type": "VARCHAR(100)", "description": "使用者電子郵件地址" },
        "full_name": { "chinese_name": "全名", "type": "VARCHAR(100)", "description": "使用者真實姓名" },
        "is_active": { "chinese_name": "啟用狀態", "type": "BOOLEAN", "description": "帳號是否啟用" },
        "is_admin": { "chinese_name": "管理員權限", "type": "BOOLEAN", "description": "是否為管理員" },
        "role": { "chinese_name": "角色", "type": "VARCHAR(20)", "description": "使用者角色權限" },
        "created_at": { "chinese_name": "建立時間", "type": "TIMESTAMP", "description": "帳號建立時間" }
      }
    },
    "user_sessions": {
      "chinese_name": "使用者會話",
      "description": "使用者登入會話管理",
      "category": "auth",
      "frontend_pages": [],
      "primary_key": "id",
      "relationships": [
        { "table": "users", "type": "many_to_one", "foreign_key": "user_id", "description": "會話所屬使用者" }
      ],
      "api_endpoints": ["POST /api/auth/login", "POST /api/auth/logout", "GET /api/auth/check"],
      "main_fields": ["id", "user_id", "session_token", "created_at", "expires_at"]
    },
    "documents": {
      "chinese_name": "公文管理",
      "description": "公文文件資料管理",
      "category": "core",
      "frontend_pages": ["/documents", "/documents/create", "/documents/:id", "/dashboard"],
      "primary_key": "id",
      "relationships": [
        { "table": "users", "type": "many_to_one", "foreign_key": "created_by", "description": "公文建立者" },
        { "table": "calendar_events", "type": "one_to_many", "foreign_key": "document_id", "description": "相關行事曆事件" }
      ],
      "api_endpoints": ["GET /api/documents", "POST /api/documents", "GET /api/documents/{id}", "PUT /api/documents/{id}", "DELETE /api/documents/{id}"],
      "main_fields": ["id", "doc_number", "subject", "content", "doc_date", "status"],
      "columns": {
        "id": { "chinese_name": "公文ID", "type": "INTEGER", "description": "主鍵，自動遞增" },
        "doc_number": { "chinese_name": "公文字號", "type": "VARCHAR(100)", "description": "公文編號" },
        "subject": { "chinese_name": "主旨", "type": "TEXT", "description": "公文主旨內容" },
        "content": { "chinese_name": "內容", "type": "TEXT", "description": "公文詳細內容" },
        "doc_type": { "chinese_name": "公文類型", "type": "VARCHAR(50)", "description": "收文/發文等類型" },
        "category": { "chinese_name": "類別", "type": "VARCHAR(100)", "description": "公文分類" },
        "status": { "chinese_name": "狀態", "type": "VARCHAR(50)", "description": "處理狀態" },
        "doc_date": { "chinese_name": "公文日期", "type": "DATE", "description": "公文發文日期" },
        "created_at": { "chinese_name": "建立時間", "type": "TIMESTAMP", "description": "記錄建立時間" }
      }
    },
    "contract_projects": {
      "chinese_name": "承攬案件",
      "description": "承攬專案管理",
      "category": "business",
      "frontend_pages": ["/projects", "/contract-cases", "/dashboard"],
      "primary_key": "id",
      "relationships": [
        { "table": "project_vendor_association", "type": "one_to_many", "foreign_key": "project_id", "description": "專案廠商關聯" }
      ],
      "api_endpoints": ["GET /api/projects", "POST /api/projects", "GET /api/projects/{id}", "PUT /api/projects/{id}"],
      "main_fields": ["id", "project_name", "contract_number", "start_date", "end_date", "status"]
    },
    "partner_vendors": {
      "chinese_name": "合作廠商",
      "description": "合作廠商資料管理",
      "category": "business",
      "frontend_pages": ["/vendors"],
      "primary_key": "id",
      "relationships": [
        { "table": "project_vendor_association", "type": "one_to_many", "foreign_key": "vendor_id", "description": "廠商專案關聯" }
      ],
      "api_endpoints": ["GET /api/vendors", "POST /api/vendors", "GET /api/vendors/{id}", "PUT /api/vendors/{id}"],
      "main_fields": ["id", "vendor_name", "contact_person", "phone", "email", "address"]
    },
    "project_vendor_association": {
      "chinese_name": "專案廠商關聯",
      "description": "專案與廠商的多對多關聯表",
      "category": "relation",
      "frontend_pages": ["/projects", "/vendors"],
      "primary_key": "id",
      "relationships": [
        { "table": "contract_projects", "type": "many_to_one", "foreign_key": "project_id", "description": "關聯的專案" },
        { "table": "partner_vendors", "type": "many_to_one", "foreign_key": "vendor_id", "description": "關聯的廠商" }
      ],
      "api_endpoints": ["GET /api/project-vendors", "POST /api/project-vendors"],
      "main_fields": ["project_id", "vendor_id", "role", "contract_amount"]
    },
    "government_agencies": {
      "chinese_name": "政府機關",
      "description": "政府機關單位資料",
      "category": "reference",
      "frontend_pages": ["/agencies"],
      "primary_key": "id",
      "relationships": [],
      "api_endpoints": ["GET /api/agencies", "POST /api/agencies", "GET /api/agencies/{id}"],
      "main_fields": ["id", "agency_name", "agency_code", "contact_person", "phone", "address"]
    },
    "calendar_events": {
      "chinese_name": "行事曆事件",
      "description": "Google Calendar 同步事件",
      "category": "integration",
      "frontend_pages": ["/calendar"],
      "primary_key": "id",
      "relationships": [
        { "table": "documents", "type": "many_to_one", "foreign_key": "document_id", "description": "關聯的公文" }
      ],
      "api_endpoints": ["GET /api/pure-calendar/events", "POST /api/pure-calendar/events", "PUT /api/pure-calendar/events/{id}"],
      "main_fields": ["id", "title", "start_time", "end_time", "description", "google_event_id"]
    },
    "calendar_sync_logs": {
      "chinese_name": "行事曆同步記錄",
      "description": "Google Calendar 同步日誌",
      "category": "system",
      "frontend_pages": [],
      "primary_key": "id",
      "relationships": [],
      "api_endpoints": [],
      "main_fields": ["id", "operation", "status", "message", "sync_time"]
    },
    "cases": {
      "chinese_name": "案件管理",
      "description": "案件追蹤管理",
      "category": "business",
      "frontend_pages": ["/contract-cases"],
      "primary_key": "id",
      "relationships": [],
      "api_endpoints": ["GET /api/contract-cases", "POST /api/contract-cases", "GET /api/contract-cases/{id}"],
      "main_fields": ["id", "case_number", "title", "status", "created_at"]
    },
    "doc_number_sequences": {
      "chinese_name": "公文字號序號",
      "description": "公文字號自動編號管理",
      "category": "system",
      "frontend_pages": ["/document-numbers"],
      "primary_key": "id",
      "relationships": [],
      "api_endpoints": ["GET /api/document-numbers/sequences", "POST /api/document-numbers/generate"],
      "main_fields": ["id", "prefix", "year", "sequence_number", "last_used"]
    },
    "site_configurations": {
      "chinese_name": "網站設定",
      "description": "系統配置參數",
      "category": "system",
      "frontend_pages": ["/admin/site-management"],
      "primary_key": "id",
      "relationships": [],
      "api_endpoints": ["GET /api/site-management/config", "PUT /api/site-management/config"],
      "main_fields": ["id", "key", "value", "description", "is_public"]
    },
    "site_navigation_items": {
      "chinese_name": "導航項目",
      "description": "網站導航選單管理",
      "category": "system",
      "frontend_pages": ["/admin/site-management"],
      "primary_key": "id",
      "relationships": [],
      "api_endpoints": ["GET /api/site-management/navigation", "POST /api/site-management/navigation", "PUT /api/site-management/navigation/{id}"],
      "main_fields": ["id", "title", "path", "icon", "sort_order", "parent_id"]
    }
  },
  "categories": {
    "core": {
      "chinese_name": "核心業務",
      "description": "公文管理等核心功能",
      "color": "#1976d2",
      "icon": "FileTextOutlined"
    },
    "business": {
      "chinese_name": "業務管理",
      "description": "承攬案件、廠商管理等",
      "color": "#52c41a",
      "icon": "ShopOutlined"
    },
    "auth": {
      "chinese_name": "認證授權",
      "description": "使用者管理與權限控制",
      "color": "#fa8c16",
      "icon": "UserOutlined"
    },
    "system": {
      "chinese_name": "系統管理",
      "description": "系統配置與維護功能",
      "color": "#722ed1",
      "icon": "SettingOutlined"
    },
    "integration": {
      "chinese_name": "外部整合",
      "description": "與外部系統的整合功能",
      "color": "#13c2c2",
      "icon": "ApiOutlined"
    },
    "reference": {
      "chinese_name": "參考資料",
      "description": "基礎參考資料管理",
      "color": "#eb2f96",
      "icon": "BookOutlined"
    },
    "relation": {
      "chinese_name": "關聯表",
      "description": "多對多關係連接表",
      "color": "#666666",
      "icon": "LinkOutlined"
    }
  }
};
