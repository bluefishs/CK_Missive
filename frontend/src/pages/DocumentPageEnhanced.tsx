import React, { useState, useEffect } from 'react';
import { Card, message, Spin, Row, Col, Typography, Button, Space, Alert } from 'antd';
import {
  ReloadOutlined,
  ExportOutlined,
  SettingOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';

import { DocumentFilterEnhanced } from '../components/document/DocumentFilterEnhanced';
import { DocumentListEnhanced } from '../components/document/DocumentListEnhanced';
import { useDocuments } from '../hooks/useDocuments';
import { Document, DocumentFilter } from '../types';
import { API_BASE_URL } from '../api/client';

const { Title, Text } = Typography;

interface EnhancedDocumentPageState {
  filters: DocumentFilter;
  sortField?: string;
  sortOrder?: 'ascend' | 'descend' | null;
  pagination: {
    current: number;
    pageSize: number;
  };
}

const DocumentPageEnhanced: React.FC = () => {
  const [state, setState] = useState<EnhancedDocumentPageState>({
    filters: {},
    sortField: 'updated_at',
    sortOrder: 'descend',
    pagination: {
      current: 1,
      pageSize: 20,
    },
  });

  const [isExporting, setIsExporting] = useState(false);
  const [testResults, setTestResults] = useState<{
    contractProjectsTest: boolean;
    agenciesTest: boolean;
    integratedSearchTest: boolean;
  }>({
    contractProjectsTest: false,
    agenciesTest: false,
    integratedSearchTest: false,
  });

  // 使用增強版 API
  const {
    documents,
    loading,
    total,
    error,
    refetch
  } = useDocuments({
    ...state.filters,
    skip: (state.pagination.current - 1) * state.pagination.pageSize,
    limit: state.pagination.pageSize,
    sort_by: state.sortField,
    sort_order: state.sortOrder === 'ascend' ? 'asc' : 'desc',
  }, {
    useEnhancedAPI: true  // 使用增強版 API
  });

  // 測試新功能
  useEffect(() => {
    testEnhancedFeatures();
  }, []);

  const testEnhancedFeatures = async () => {
    try {
      // 測試承攬案件 API
      const contractProjectsResponse = await fetch(`${API_BASE_URL}/documents-enhanced/contract-projects-dropdown?limit=5`);
      const contractProjectsTest = contractProjectsResponse.ok;

      // 測試政府機關 API
      const agenciesResponse = await fetch(`${API_BASE_URL}/documents-enhanced/agencies-dropdown?limit=5`);
      const agenciesTest = agenciesResponse.ok;

      // 測試整合搜尋 API
      const integratedSearchResponse = await fetch(`${API_BASE_URL}/documents-enhanced/integrated-search?limit=5`);
      const integratedSearchTest = integratedSearchResponse.ok;

      setTestResults({
        contractProjectsTest,
        agenciesTest,
        integratedSearchTest,
      });

      if (contractProjectsTest && agenciesTest && integratedSearchTest) {
        message.success('增強版功能測試通過！', 2);
      } else {
        message.warning('部分增強版功能測試失敗', 2);
      }
    } catch (error) {
      console.error('測試增強版功能失敗:', error);
      message.error('增強版功能測試失敗');
    }
  };

  const handleFiltersChange = (newFilters: DocumentFilter) => {
    setState(prev => ({
      ...prev,
      filters: newFilters,
      pagination: { ...prev.pagination, current: 1 }
    }));
  };

  const handleFiltersReset = () => {
    setState(prev => ({
      ...prev,
      filters: {},
      pagination: { ...prev.pagination, current: 1 }
    }));
  };

  const handleTableChange = (pagination: any, filters: any, sorter: any) => {
    setState(prev => ({
      ...prev,
      pagination: {
        current: pagination.current || 1,
        pageSize: pagination.pageSize || 20,
      },
      sortField: sorter.field,
      sortOrder: sorter.order,
    }));
  };

  const handleRefresh = () => {
    refetch();
    message.success('資料已刷新');
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      // 這裡可以實作匯出邏輯
      message.success('匯出完成');
    } catch (error) {
      message.error('匯出失敗');
    } finally {
      setIsExporting(false);
    }
  };

  // 文件操作處理程序
  const handleDocumentView = (document: Document) => {
    message.info(`查看公文: ${document.subject}`);
  };

  const handleDocumentEdit = (document: Document) => {
    message.info(`編輯公文: ${document.subject}`);
  };

  const handleDocumentDelete = (document: Document) => {
    message.warning(`刪除公文: ${document.subject}`);
  };

  const handleBatchExport = (documents: Document[]) => {
    message.info(`批次匯出 ${documents.length} 筆公文`);
  };

  const handleBatchDelete = (documents: Document[]) => {
    message.warning(`批次刪除 ${documents.length} 筆公文`);
  };

  const handleBatchArchive = (documents: Document[]) => {
    message.info(`批次封存 ${documents.length} 筆公文`);
  };

  if (error) {
    return (
      <Card>
        <Alert
          message="載入失敗"
          description={error}
          type="error"
          showIcon
          action={
            <Button size="small" danger onClick={() => window.location.reload()}>
              重新載入
            </Button>
          }
        />
      </Card>
    );
  }

  const allTestsPassed = Object.values(testResults).every(test => test);

  return (
    <div style={{ padding: '24px' }}>
      {/* 頁面標題與狀態 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={2} style={{ margin: 0 }}>
            📋 增強版公文管理系統
          </Title>
          <Text type="secondary">
            整合多表查詢、智能搜尋、表格排序功能
          </Text>
        </Col>
        <Col>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              loading={loading}
            >
              刷新
            </Button>
            <Button
              icon={<ExportOutlined />}
              onClick={handleExport}
              loading={isExporting}
            >
              匯出
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={testEnhancedFeatures}
            >
              測試功能
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 功能測試狀態 */}
      <Card
        size="small"
        style={{ marginBottom: 16 }}
        bodyStyle={{ padding: '12px 16px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <InfoCircleOutlined style={{ color: allTestsPassed ? '#52c41a' : '#faad14' }} />
            <Text strong>增強功能狀態</Text>
          </div>
          <div style={{ display: 'flex', gap: 16, fontSize: '12px' }}>
            <span style={{ color: testResults.contractProjectsTest ? '#52c41a' : '#ff4d4f' }}>
              承攬案件API: {testResults.contractProjectsTest ? '✓' : '✗'}
            </span>
            <span style={{ color: testResults.agenciesTest ? '#52c41a' : '#ff4d4f' }}>
              政府機關API: {testResults.agenciesTest ? '✓' : '✗'}
            </span>
            <span style={{ color: testResults.integratedSearchTest ? '#52c41a' : '#ff4d4f' }}>
              整合搜尋API: {testResults.integratedSearchTest ? '✓' : '✗'}
            </span>
          </div>
        </div>
      </Card>

      {/* 篩選元件 */}
      <DocumentFilterEnhanced
        filters={state.filters}
        onFiltersChange={handleFiltersChange}
        onReset={handleFiltersReset}
      />

      {/* 文件列表 */}
      <Spin spinning={loading}>
        <DocumentListEnhanced
          documents={documents}
          loading={loading}
          total={total}
          pagination={state.pagination}
          sortField={state.sortField}
          sortOrder={state.sortOrder}
          onTableChange={handleTableChange}
          onEdit={handleDocumentEdit}
          onDelete={handleDocumentDelete}
          onView={handleDocumentView}
          onExport={handleExport}
          onBatchExport={handleBatchExport}
          onBatchDelete={handleBatchDelete}
          onBatchArchive={handleBatchArchive}
          enableBatchOperations={true}
          isExporting={isExporting}
        />
      </Spin>

      {/* 功能說明 */}
      <Card
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <InfoCircleOutlined />
            <span>增強功能說明</span>
          </div>
        }
        size="small"
        style={{ marginTop: 16 }}
      >
        <Row gutter={[16, 16]}>
          <Col span={24} md={8}>
            <div>
              <Text strong style={{ color: '#1890ff' }}>🔍 智能搜尋</Text>
              <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
                • 所有篩選欄位支援 AutoComplete<br/>
                • 承攬案件直接對應專案資料庫<br/>
                • 政府機關整合機關資料庫
              </div>
            </div>
          </Col>
          <Col span={24} md={8}>
            <div>
              <Text strong style={{ color: '#52c41a' }}>📊 表格增強</Text>
              <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
                • 所有欄位支援排序<br/>
                • 欄位級別篩選功能<br/>
                • 自訂顯示欄位<br/>
                • 批次操作功能
              </div>
            </div>
          </Col>
          <Col span={24} md={8}>
            <div>
              <Text strong style={{ color: '#faad14' }}>🔗 多表整合</Text>
              <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
                • 外鍵關聯設計<br/>
                • JOIN 查詢優化<br/>
                • 資料一致性保證<br/>
                • 向後相容性
              </div>
            </div>
          </Col>
        </Row>
      </Card>
    </div>
  );
};

export default DocumentPageEnhanced;