import React, { useState, useEffect } from 'react';
import { Card, Spin, Row, Col, Typography, Button, Space, Alert, App } from 'antd';
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
import { API_ENDPOINTS } from '../api/endpoints';
import { useResponsive } from '../hooks/useResponsive';
import { HideOn } from '../components/common/ResponsiveContainer';

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
  const { message } = App.useApp();
  const { isMobile, isTablet, responsiveValue } = useResponsive();
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
    data,
    isLoading: loading,
    error,
    refetch
  } = useDocuments({
    ...state.filters,
    page: state.pagination.current,
    limit: state.pagination.pageSize,
  });

  // 從 data 中提取文件列表和總數
  const documents = data?.items ?? [];
  const total = data?.pagination?.total ?? 0;

  // 測試新功能
  useEffect(() => {
    testEnhancedFeatures();
  }, []);

  const testEnhancedFeatures = async () => {
    try {
      // 測試承攬案件 API (POST)
      const contractProjectsResponse = await fetch(`${API_BASE_URL}/documents-enhanced/contract-projects-dropdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 5 })
      });
      const contractProjectsTest = contractProjectsResponse.ok;

      // 測試政府機關 API (POST)
      const agenciesResponse = await fetch(`${API_BASE_URL}/documents-enhanced/agencies-dropdown`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 5 })
      });
      const agenciesTest = agenciesResponse.ok;

      // 測試整合搜尋 API (POST) - 如果端點存在
      let integratedSearchTest = true;
      try {
        const integratedSearchResponse = await fetch(`${API_BASE_URL}${API_ENDPOINTS.DOCUMENTS.INTEGRATED_SEARCH}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ limit: 5 })
        });
        integratedSearchTest = integratedSearchResponse.ok;
      } catch {
        integratedSearchTest = false;
      }

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
      // 構建匯出請求參數，將篩選條件傳遞給後端
      const exportParams: {
        category?: string;
        year?: number;
        keyword?: string;
        status?: string;
        contract_case?: string;
        sender?: string;
        receiver?: string;
      } = {};

      // 映射篩選條件到匯出 API 參數
      if (state.filters.doc_type) {
        exportParams.category = state.filters.doc_type;
      }
      if (state.filters.category) {
        exportParams.category = state.filters.category;
      }
      if (state.filters.year) {
        exportParams.year = state.filters.year;
      }
      if (state.filters.keyword) {
        exportParams.keyword = state.filters.keyword;
      }
      if (state.filters.search) {
        exportParams.keyword = state.filters.search;
      }
      if (state.filters.status) {
        exportParams.status = state.filters.status;
      }
      if (state.filters.contract_case) {
        exportParams.contract_case = state.filters.contract_case;
      }
      if (state.filters.sender) {
        exportParams.sender = state.filters.sender;
      }
      if (state.filters.receiver) {
        exportParams.receiver = state.filters.receiver;
      }

      // 調用後端匯出 API
      const response = await fetch(`${API_BASE_URL}/documents-enhanced/export/excel`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(exportParams),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `匯出失敗 (${response.status})`);
      }

      // 從 response headers 取得檔名
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `乾坤測繪公文紀錄_${new Date().toISOString().slice(0, 10).replace(/-/g, '')}.xlsx`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename\*?=(?:UTF-8'')?["']?([^"';\n]+)/i);
        if (filenameMatch && filenameMatch[1]) {
          filename = decodeURIComponent(filenameMatch[1]);
        }
      }

      // 下載檔案
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      message.success('匯出完成');
    } catch (error) {
      console.error('匯出失敗:', error);
      message.error(error instanceof Error ? error.message : '匯出失敗');
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
          description={error?.message || '發生未知錯誤'}
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

  // 響應式間距
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  return (
    <div style={{ padding: pagePadding }}>
      {/* 頁面標題與狀態 */}
      <Row
        justify="space-between"
        align={isMobile ? 'top' : 'middle'}
        gutter={[0, 12]}
        style={{ marginBottom: isMobile ? 16 : 24 }}
      >
        <Col xs={24} sm={24} md={12}>
          <Title level={isMobile ? 4 : 2} style={{ margin: 0 }}>
            📋 {isMobile ? '公文管理' : '增強版公文管理系統'}
          </Title>
          <HideOn mobile>
            <Text type="secondary">
              整合多表查詢、智能搜尋、表格排序功能
            </Text>
          </HideOn>
        </Col>
        <Col xs={24} sm={24} md={12} style={{ textAlign: isMobile ? 'left' : 'right' }}>
          <Space wrap size={isMobile ? 'small' : 'middle'}>
            <Button
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              loading={loading}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : '刷新'}
            </Button>
            <Button
              icon={<ExportOutlined />}
              onClick={handleExport}
              loading={isExporting}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : '匯出'}
            </Button>
            <HideOn mobile>
              <Button
                icon={<SettingOutlined />}
                onClick={testEnhancedFeatures}
              >
                測試功能
              </Button>
            </HideOn>
          </Space>
        </Col>
      </Row>

      {/* 功能測試狀態 - 手機版隱藏 */}
      <HideOn mobile>
        <Card
          size="small"
          style={{ marginBottom: 16 }}
          bodyStyle={{ padding: '12px 16px' }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <InfoCircleOutlined style={{ color: allTestsPassed ? '#52c41a' : '#faad14' }} />
              <Text strong>增強功能狀態</Text>
            </div>
            <div style={{ display: 'flex', gap: isTablet ? 8 : 16, fontSize: '12px', flexWrap: 'wrap' }}>
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
      </HideOn>

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

      {/* 功能說明 - 手機版隱藏 */}
      <HideOn mobile>
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
            <Col xs={24} sm={12} md={8}>
              <div>
                <Text strong style={{ color: '#1890ff' }}>🔍 智能搜尋</Text>
                <div style={{ fontSize: '12px', color: '#666', marginTop: 4 }}>
                  • 所有篩選欄位支援 AutoComplete<br/>
                  • 承攬案件直接對應專案資料庫<br/>
                  • 政府機關整合機關資料庫
                </div>
              </div>
            </Col>
            <Col xs={24} sm={12} md={8}>
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
            <Col xs={24} sm={24} md={8}>
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
      </HideOn>
    </div>
  );
};

export default DocumentPageEnhanced;