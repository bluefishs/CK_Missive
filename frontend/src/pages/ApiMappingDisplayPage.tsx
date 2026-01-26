/**
 * ApiMappingDisplayPage - API 對應參考頁面
 *
 * ⚠️ 開發參考頁面 (REFERENCE ONLY)
 * ================================
 * 此頁面顯示靜態的 API 對應關係，僅供開發人員參考。
 *
 * 重要說明：
 * - 此數據為靜態示例，可能與實際 API 不同步
 * - 正式 API 文件請參考 /api/docs (Swagger UI)
 * - 此頁面不會從後端獲取數據
 *
 * @version 1.0.0
 * @status REFERENCE
 */
import React, { useEffect, useState } from 'react';
import { Card, Typography, Table, Spin, Alert } from 'antd';

const { Title, Paragraph } = Typography;

interface ApiMappingItem {
  feature: string;
  api: string;
  backendFiles: string;
  description: string;
}

// 強制使用 fallback 數據，避免任何 API 調用問題
const FALLBACK_DATA: ApiMappingItem[] = [
  {
    feature: '儀表板統計',
    api: 'GET /api/dashboard/stats',
    backendFiles: 'backend/app/api/endpoints/dashboard.py',
    description: '獲取儀表板統計數據，包括文件數量、項目數量等'
  },
  {
    feature: '文件列表',
    api: 'GET /api/documents',
    backendFiles: 'backend/app/api/endpoints/documents.py',
    description: '獲取文件列表，支援分頁、篩選和搜尋功能'
  },
  {
    feature: '文件詳情',
    api: 'GET /api/documents/{id}',
    backendFiles: 'backend/app/api/endpoints/documents.py',
    description: '獲取指定文件的詳細資訊'
  },
  {
    feature: '創建文件',
    api: 'POST /api/documents',
    backendFiles: 'backend/app/api/endpoints/documents.py',
    description: '創建新的文件記錄'
  },
  {
    feature: '用戶管理',
    api: 'GET /api/auth/users',
    backendFiles: 'backend/app/core/auth_service.py',
    description: '獲取用戶列表和管理用戶資訊'
  },
  {
    feature: '網站配置',
    api: 'GET /api/site-management/config',
    backendFiles: 'backend/app/api/endpoints/site_management.py',
    description: '獲取和管理網站配置參數'
  },
  {
    feature: '導覽管理',
    api: 'GET /api/site-management/navigation',
    backendFiles: 'backend/app/api/endpoints/site_management.py',
    description: '管理網站導覽選單結構'
  },
  {
    feature: '行事曆功能',
    api: 'POST /api/calendar/events/list',
    backendFiles: 'backend/app/api/endpoints/document_calendar.py',
    description: '管理行事曆事件的 CRUD 操作 (POST 資安機制)'
  },
  {
    feature: '案件管理',
    api: 'GET /api/contract-cases',
    backendFiles: 'backend/app/api/endpoints/contract_case.py',
    description: '管理合約案件資訊'
  },
  {
    feature: '廠商管理',
    api: 'GET /api/vendors',
    backendFiles: 'backend/app/api/endpoints/vendor.py',
    description: '管理廠商資訊和聯絡方式'
  },
  {
    feature: '機構管理',
    api: 'GET /api/agencies',
    backendFiles: 'backend/app/api/endpoints/agency.py',
    description: '管理政府機構資訊'
  },
  {
    feature: '用戶權限',
    api: 'GET /api/admin/permissions',
    backendFiles: 'backend/app/api/endpoints/admin.py',
    description: '管理用戶權限和角色分配'
  }
];

export const ApiMappingDisplayPage: React.FC = () => {
  const [apiMappings, setApiMappings] = useState<ApiMappingItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    // 直接載入靜態數據（參考用途）
    setApiMappings(FALLBACK_DATA);
    setLoading(false);
  }, []);

  const columns = [
    {
      title: '前端功能描述',
      dataIndex: 'feature',
      key: 'feature',
      width: '20%',
    },
    {
      title: 'API 端點 (Method & Path)',
      dataIndex: 'api',
      key: 'api',
      width: '25%',
      render: (text: string) => <code style={{ background: '#f5f5f5', padding: '2px 4px' }}>{text}</code>,
    },
    {
      title: '相關後端檔案',
      dataIndex: 'backendFiles',
      key: 'backendFiles',
      width: '25%',
    },
    {
      title: '說明',
      dataIndex: 'description',
      key: 'description',
      width: '30%',
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>前端功能與後端 API 對應關係 (開發版)</Title>
      <Paragraph>
        本頁面展示了前端功能與後端 API 端點之間的對應關係。
        這是開發模式下的靜態數據，用於展示系統架構。
        詳細 API 文件請參考 Swagger UI (<code>/api/docs</code>)。
      </Paragraph>

      <Alert
        message="開發模式"
        description="目前顯示的是開發用的靜態 API 對應數據，實際部署時會從後端動態獲取。"
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      {loading && (
        <div style={{ textAlign: 'center', margin: '20px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: '10px' }}>載入中...</div>
        </div>
      )}

      {!loading && (
        <Card>
          <Table
            columns={columns}
            dataSource={apiMappings}
            rowKey={(record) => record.api}
            pagination={false}
            bordered
            size="middle"
            title={() => `共 ${apiMappings.length} 個 API 端點`}
          />
        </Card>
      )}
    </div>
  );
};