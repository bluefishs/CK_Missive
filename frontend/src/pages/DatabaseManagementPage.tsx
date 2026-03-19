import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { logger } from '../services/logger';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  Card, Tabs, Button, Space, Typography, Row, Col,
  Statistic, Alert, App, Tag,
  Switch, Drawer
} from 'antd';
import {
  DatabaseOutlined, TableOutlined, SearchOutlined, ReloadOutlined,
  InfoCircleOutlined, WarningOutlined, CodeOutlined,
  CheckCircleOutlined, ExclamationCircleOutlined,
  EyeOutlined, UpOutlined
} from '@ant-design/icons';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { SimpleDatabaseViewer } from '../components/admin/SimpleDatabaseViewer';
import type { DatabaseInfo, QueryResult, IntegrityResult, TableDataResponse } from '../types/api';
import { TablesTab, DataTab, QueryTab, IntegrityTab } from './databaseManagement';

const { Title, Text } = Typography;

export const DatabaseManagementPage: React.FC = () => {
  const { message, modal } = App.useApp();
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [tableData, setTableData] = useState<TableDataResponse>({ columns: [], rows: [] });
  const [customQuery, setCustomQuery] = useState<string>('SELECT * FROM documents LIMIT 10;');
  const [queryResult, setQueryResult] = useState<QueryResult | null>(null);
  const [integrityResult, setIntegrityResult] = useState<IntegrityResult | null>(null);
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [useEnhancedView, setUseEnhancedView] = useState(false);
  const [enhancedDrawerVisible, setEnhancedDrawerVisible] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const {
    data: databaseInfo = null,
    isLoading: dbInfoLoading,
    refetch: refetchDatabaseInfo,
  } = useQuery({
    queryKey: ['database-info'],
    queryFn: () => apiClient.post<DatabaseInfo>(API_ENDPOINTS.ADMIN_DATABASE.INFO, {}),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const loading = dbInfoLoading || actionLoading;

  const fetchDatabaseInfo = () => {
    refetchDatabaseInfo();
  };

  const fetchTableData = async (tableName: string, limit: number = 50, offset: number = 0) => {
    setActionLoading(true);
    try {
      const data = await apiClient.post<TableDataResponse>(API_ENDPOINTS.ADMIN_DATABASE.TABLE(tableName), { limit, offset });
      setTableData(data);
      setSelectedTable(tableName);
      message.success(`載入 ${tableName} 數據成功`);
    } catch (error) {
      logger.error('獲取表格數據失敗:', error);
      message.error('獲取表格數據失敗');
    } finally {
      setActionLoading(false);
    }
  };

  const executeQuery = async () => {
    if (!customQuery.trim()) {
      message.warning('請輸入查詢語句');
      return;
    }

    setActionLoading(true);
    try {
      const result = await apiClient.post<QueryResult>(API_ENDPOINTS.ADMIN_DATABASE.QUERY, { query: customQuery });
      setQueryResult(result);
      message.success(`查詢完成，返回 ${result.totalRows} 條結果，耗時 ${result.executionTime}ms`);
    } catch (error: unknown) {
      logger.error('查詢執行失敗:', error);
      message.error(`查詢執行失敗: ${error instanceof Error ? error.message : '未知錯誤'}`);
    } finally {
      setActionLoading(false);
    }
  };

  const checkIntegrity = async () => {
    setActionLoading(true);
    try {
      const result = await apiClient.post<IntegrityResult>(API_ENDPOINTS.ADMIN_DATABASE.INTEGRITY, {});
      setIntegrityResult(result);

      if (result.issues.length === 0) {
        message.success('數據完整性檢查通過');
      } else {
        modal.warning({
          title: '發現數據問題',
          content: (
            <div>
              {result.issues.map((issue, index) => (
                <div key={index}>
                  <Text type="danger">{issue.table}</Text>: {issue.description}
                </div>
              ))}
            </div>
          )
        });
      }
    } catch (error) {
      logger.error('完整性檢查失敗:', error);
      message.error('完整性檢查失敗');
    } finally {
      setActionLoading(false);
    }
  };

  const exportTableData = async (tableName: string) => {
    try {
      message.success(`開始匯出 ${tableName} 數據...`);
    } catch (_error) {
      message.error('匯出失敗');
    }
  };

  return (
    <ResponsiveContent maxWidth="full" padding="medium" style={{ background: '#f5f5f5', minHeight: '100vh' }}>
      <div style={{ maxWidth: 1400, margin: '0 auto' }}>

        <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
          <Col>
            <Title level={2} style={{ margin: 0, color: '#1976d2' }}>
              <DatabaseOutlined style={{ marginRight: 12 }} />
              資料庫管理
              {useEnhancedView && (
                <Tag color="green" style={{ marginLeft: 8 }}>增強模式</Tag>
              )}
            </Title>
            <Typography.Text type="secondary" style={{ fontSize: '14px' }}>
              {useEnhancedView
                ? '增強檢視：包含關聯圖、中英文對照、前端頁面對應'
                : '標準檢視：基本資料庫管理功能'
              }
            </Typography.Text>
          </Col>
          <Col>
            <Space>
              <Space>
                <Typography.Text>檢視模式:</Typography.Text>
                <Switch
                  checked={useEnhancedView}
                  onChange={setUseEnhancedView}
                  checkedChildren="增強"
                  unCheckedChildren="標準"
                />
              </Space>
              <Button
                icon={<EyeOutlined />}
                onClick={() => setEnhancedDrawerVisible(true)}
                type="primary"
                ghost
              >
                開啟增強檢視
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={fetchDatabaseInfo}
                loading={loading}
              >
                重新整理
              </Button>
              <Button
                icon={<WarningOutlined />}
                onClick={checkIntegrity}
                loading={loading}
              >
                完整性檢查
              </Button>
            </Space>
          </Col>
        </Row>

        {databaseInfo && (
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={12} md={6}>
              <Card>
                <Statistic
                  title="資料庫大小"
                  value={databaseInfo.size}
                  prefix={<DatabaseOutlined style={{ color: '#1976d2' }} />}
                  styles={{ content: { color: '#1976d2' } }}
                />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card>
                <Statistic
                  title="資料表數量"
                  value={databaseInfo.tables.length}
                  prefix={<TableOutlined style={{ color: '#52c41a' }} />}
                  styles={{ content: { color: '#52c41a' } }}
                />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card>
                <Statistic
                  title="總記錄數"
                  value={databaseInfo.totalRecords}
                  prefix={<InfoCircleOutlined style={{ color: '#faad14' }} />}
                  styles={{ content: { color: '#faad14' } }}
                />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card>
                <Statistic
                  title="資料庫狀態"
                  value={databaseInfo.status === 'healthy' ? '正常' : '警告'}
                  prefix={
                    databaseInfo.status === 'healthy' ?
                    <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                    <ExclamationCircleOutlined style={{ color: '#faad14' }} />
                  }
                  styles={{ content: {
                    color: databaseInfo.status === 'healthy' ? '#52c41a' : '#faad14'
                  } }}
                />
              </Card>
            </Col>
          </Row>
        )}

        {useEnhancedView ? (
          <SimpleDatabaseViewer />
        ) : (
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Alert
                title="升級提示"
                description={
                  <Space>
                    <span>嘗試新的增強檢視模式，包含關聯圖、中英文對照、前端頁面對應等進階功能</span>
                    <Button
                      size="small"
                      type="link"
                      icon={<UpOutlined />}
                      onClick={() => setUseEnhancedView(true)}
                    >
                      立即體驗
                    </Button>
                  </Space>
                }
                type="info"
                showIcon
                closable
              />
            </div>
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              size="large"
              items={[
                {
                  key: 'overview',
                  label: <span><TableOutlined />資料表概覽</span>,
                  children: (
                    <TablesTab
                      tables={databaseInfo?.tables || []}
                      onFetchTableData={fetchTableData}
                      onExportTableData={exportTableData}
                    />
                  )
                },
                {
                  key: 'data',
                  label: <span><SearchOutlined />資料檢視</span>,
                  children: (
                    <DataTab
                      selectedTable={selectedTable}
                      tableData={tableData}
                      tables={databaseInfo?.tables || []}
                      loading={loading}
                      onFetchTableData={fetchTableData}
                      onExportTableData={exportTableData}
                    />
                  )
                },
                {
                  key: 'query',
                  label: <span><CodeOutlined />SQL 查詢</span>,
                  children: (
                    <QueryTab
                      customQuery={customQuery}
                      onQueryChange={setCustomQuery}
                      queryResult={queryResult}
                      loading={loading}
                      onExecuteQuery={executeQuery}
                    />
                  )
                },
                {
                  key: 'integrity',
                  label: <span><WarningOutlined />完整性檢查</span>,
                  children: (
                    <IntegrityTab
                      integrityResult={integrityResult}
                      loading={loading}
                      onCheckIntegrity={checkIntegrity}
                    />
                  )
                }
              ]}
            />
          </Card>
        )}

        <Drawer
          title="增強型資料庫檢視"
          onClose={() => setEnhancedDrawerVisible(false)}
          open={enhancedDrawerVisible}
          destroyOnHidden
          styles={{ wrapper: { width: '90%' }, body: { padding: 0 } }}
        >
          <SimpleDatabaseViewer />
        </Drawer>

      </div>
    </ResponsiveContent>
  );
};
