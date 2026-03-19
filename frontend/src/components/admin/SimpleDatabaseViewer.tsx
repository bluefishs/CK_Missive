/**
 * 簡易資料庫檢視器
 * @description 提供資料庫表格概覽、關聯圖和 API 對應表功能
 */
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card, Tabs, Button, Space, Typography, Row, Col,
  Alert, App, Switch
} from 'antd';
import {
  DatabaseOutlined, TableOutlined, ReloadOutlined,
  BranchesOutlined, ApiOutlined,
} from '@ant-design/icons';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import {
  databaseMetadata,
  getCategoryColor,
  type TableMetadataItem
} from '../../config/databaseMetadata';
import { logger } from '../../utils/logger';
import type { DatabaseInfo } from '../../types/api';
import {
  DatabaseStatsCards, buildStatsFromTables,
  OverviewTable,
  RelationView, ApiMappingView, TableDetailModal,
  type EnhancedTableInfo,
} from './databaseViewer';

const { Title, Text } = Typography;

// 使用共享的表格元數據
const tableMetadata = databaseMetadata.table_metadata;

/** Fallback data when API is unreachable */
const FALLBACK_DATABASE_INFO: DatabaseInfo = {
  name: "ck_documents",
  size: "8597 kB",
  status: "healthy",
  totalRecords: 15,
  tables: [
    {
      name: "users",
      recordCount: 2,
      columns: [
        { name: "id", type: "integer", nullable: false, primaryKey: true },
        { name: "email", type: "character varying", nullable: false, primaryKey: false },
        { name: "username", type: "character varying", nullable: false, primaryKey: false }
      ],
      size: "80 kB",
      lastModified: "2024-01-01"
    },
    {
      name: "documents",
      recordCount: 0,
      columns: [
        { name: "id", type: "integer", nullable: false, primaryKey: true },
        { name: "doc_number", type: "character varying", nullable: false, primaryKey: false },
        { name: "subject", type: "character varying", nullable: false, primaryKey: false }
      ],
      size: "72 kB",
      lastModified: "2024-01-01"
    },
    {
      name: "contract_projects",
      recordCount: 0,
      columns: [
        { name: "id", type: "integer", nullable: false, primaryKey: true },
        { name: "project_name", type: "character varying", nullable: false, primaryKey: false }
      ],
      size: "32 kB",
      lastModified: "2024-01-01"
    }
  ]
};

export const SimpleDatabaseViewer: React.FC = () => {
  const { message } = App.useApp();
  const [showChineseNames, setShowChineseNames] = useState(true);
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [showDetails, setShowDetails] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  const {
    data: databaseInfo = null,
    isLoading: loading,
    refetch: refetchDatabaseInfo,
  } = useQuery({
    queryKey: ['database-info-enhanced'],
    queryFn: async () => {
      logger.debug('Fetching database info via apiClient');
      try {
        const data = await apiClient.post<DatabaseInfo>(API_ENDPOINTS.ADMIN_DATABASE.INFO, {});
        logger.debug('Database info loaded:', data);
        return data;
      } catch (error) {
        logger.error('獲取資料庫信息失敗:', error);
        logger.debug('Using fallback data for development mode');
        message.warning('使用離線資料模式（API連接失敗）');
        return FALLBACK_DATABASE_INFO;
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const enhancedTables: EnhancedTableInfo[] = databaseInfo?.tables.map(table => {
    const metadata = tableMetadata[table.name] as TableMetadataItem | undefined;
    const category = metadata?.category || 'unknown';
    return {
      ...table,
      chinese_name: metadata?.chinese_name || table.name,
      description: metadata?.description || '無描述',
      category,
      frontend_pages: metadata?.frontend_pages || [],
      api_endpoints: metadata?.api_endpoints || [],
      main_fields: metadata?.main_fields || [],
      color: getCategoryColor(category)
    };
  }) || [];

  const selectedTableData = enhancedTables.find(t => t.name === selectedTable);

  const handleViewDetail = (tableName: string) => {
    setSelectedTable(tableName);
    setShowDetails(true);
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* 標題區 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0, color: '#1976d2' }}>
            <DatabaseOutlined style={{ marginRight: 12 }} />
            增強型資料庫檢視
          </Title>
          <Text type="secondary">
            包含中英文對照、前端頁面對應的資料庫管理工具
          </Text>
        </Col>
        <Col>
          <Space>
            <Space>
              <Text>中文顯示:</Text>
              <Switch
                checked={showChineseNames}
                onChange={setShowChineseNames}
                checkedChildren="中"
                unCheckedChildren="英"
              />
            </Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => refetchDatabaseInfo()}
              loading={loading}
            >
              重新整理
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 統計資訊 */}
      {databaseInfo && (
        <DatabaseStatsCards
          {...buildStatsFromTables(databaseInfo.size, enhancedTables, databaseInfo.totalRecords)}
        />
      )}

      {/* 主內容區域 */}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="large"
          items={[
            {
              key: 'overview',
              label: <span><TableOutlined />表格概覽</span>,
              children: (
                <div>
                  <Alert
                    title="增強型資料庫檢視"
                    description="提供表格中英文對照、前端頁面對應關係、API端點資訊以及分類色彩標示功能"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  <OverviewTable
                    enhancedTables={enhancedTables}
                    loading={loading}
                    showChineseNames={showChineseNames}
                    onViewDetail={handleViewDetail}
                  />
                </div>
              )
            },
            {
              key: 'relations',
              label: <span><BranchesOutlined />關聯圖</span>,
              children: (
                <div>
                  <Alert
                    title="資料表關聯分析"
                    description="顯示各資料表之間的關聯關係以及與前端、API的對應情況"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  <RelationView
                    enhancedTables={enhancedTables}
                    showChineseNames={showChineseNames}
                  />
                </div>
              )
            },
            {
              key: 'api-mapping',
              label: <span><ApiOutlined />API 對應表</span>,
              children: (
                <div>
                  <Alert
                    title="API 端點對應關係"
                    description="完整的前端功能與後端API端點對應關係表"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  <ApiMappingView
                    enhancedTables={enhancedTables}
                    showChineseNames={showChineseNames}
                  />
                </div>
              )
            }
          ]}
        />
      </Card>

      {/* 表格詳情Modal */}
      <TableDetailModal
        open={showDetails}
        onClose={() => setShowDetails(false)}
        table={selectedTableData}
      />
    </div>
  );
};
