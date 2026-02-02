/**
 * 發文字號管理頁面 (重構版)
 *
 * 統一服務來源，重用公文管理的列表元件與 API
 * 預設篩選 category='send' (發文)
 * 保留「下一個可用發文字號」預覽功能
 *
 * @version 3.2.0
 * @date 2026-01-07
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Button,
  Space,
  Statistic,
  Row,
  Col,
  Typography,
  App,
  Modal,
} from 'antd';
import type { TablePaginationConfig, FilterValue, SorterResult, TableCurrentDataSource } from 'antd/es/table/interface';
import {
  ReloadOutlined,
  FileTextOutlined,
  NumberOutlined,
  SendOutlined,
  CloudOutlined,
  MailOutlined,
  CalendarOutlined,
} from '@ant-design/icons';

import { useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '../config/queryConfig';
import { DocumentList } from '../components/document/DocumentList';
// 複製功能已停用 (2026-01-12)
// import { DocumentOperations } from '../components/document/DocumentOperations';
import { useDocuments } from '../hooks';
import {
  documentsApi,
  DocumentStatistics,
  NextSendNumberResponse,
} from '../api/documentsApi';
import { Document } from '../types';

const { Title, Text } = Typography;

export const DocumentNumbersPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  // 分頁狀態
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0,
  });

  // 統計資料
  const [stats, setStats] = useState<DocumentStatistics | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);

  // 下一個可用字號
  const [nextNumber, setNextNumber] = useState<NextSendNumberResponse | null>(null);
  const [nextNumberLoading, setNextNumberLoading] = useState(false);

  // 公文操作狀態
  const [documentOperation, setDocumentOperation] = useState<{
    type: 'view' | 'edit' | 'create' | 'copy' | null;
    document: Document | null;
    visible: boolean;
  }>({ type: null, document: null, visible: false });

  // 刪除確認 Modal
  const [deleteModal, setDeleteModal] = useState<{
    open: boolean;
    document: Document | null;
  }>({ open: false, document: null });

  // 排序狀態
  const [sortField, setSortField] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<'ascend' | 'descend' | null>(null);

  // 匯出狀態
  const [isExporting, setIsExporting] = useState(false);

  // 使用統一的 useDocuments hook，預設篩選發文 (category='send')
  const {
    data: documentsData,
    isLoading,
    error: queryError,
    refetch,
  } = useDocuments({
    category: 'send', // 固定篩選發文
    page: pagination.page,
    limit: pagination.limit,
    ...(sortField && { sortBy: sortField }),
    ...(sortOrder && { sortOrder: sortOrder === 'ascend' ? 'asc' : 'desc' }),
  });

  // 載入統計資料
  const loadStats = useCallback(async () => {
    setStatsLoading(true);
    try {
      const result = await documentsApi.getStatistics();
      setStats(result);
    } catch (error) {
      console.error('載入統計失敗:', error);
    } finally {
      setStatsLoading(false);
    }
  }, []);

  // 載入下一個可用字號 (使用新的 documentsApi)
  const loadNextNumber = useCallback(async () => {
    setNextNumberLoading(true);
    try {
      const result = await documentsApi.getNextSendNumber();
      setNextNumber(result);
    } catch (error) {
      console.error('載入下一個字號失敗:', error);
    } finally {
      setNextNumberLoading(false);
    }
  }, []);

  // 初始載入
  useEffect(() => {
    loadStats();
    loadNextNumber();
  }, [loadStats, loadNextNumber]);

  // 更新分頁資料
  useEffect(() => {
    if (documentsData?.pagination) {
      setPagination({
        page: documentsData.pagination.page ?? 1,
        limit: documentsData.pagination.limit ?? 20,
        total: documentsData.pagination.total ?? 0,
        totalPages: documentsData.pagination.total_pages ?? 0,
      });
    }
  }, [documentsData]);

  // 顯示錯誤訊息
  useEffect(() => {
    if (queryError) {
      message.error(queryError instanceof Error ? queryError.message : '載入資料失敗');
    }
  }, [queryError, message]);

  // 取得安全的公文列表
  const documents = documentsData?.items ?? [];

  // ==========================================================================
  // 事件處理
  // ==========================================================================

  const handleTableChange = (
    paginationConfig: TablePaginationConfig,
    _filters: Record<string, FilterValue | null>,
    sorter: SorterResult<Document> | SorterResult<Document>[],
    _extra: TableCurrentDataSource<Document>
  ) => {
    if (paginationConfig) {
      const newPage = paginationConfig.current ?? pagination.page;
      const newLimit = paginationConfig.pageSize ?? pagination.limit;
      setPagination((prev) => ({
        ...prev,
        page: newPage,
        limit: newLimit,
      }));
    }

    // 處理單一或多重排序
    const singleSorter = Array.isArray(sorter) ? sorter[0] : sorter;
    if (singleSorter?.field) {
      setSortField(String(singleSorter.field));
      setSortOrder(singleSorter.order ?? null);
    } else {
      setSortField('');
      setSortOrder(null);
    }
  };

  const handleRefresh = () => {
    refetch();
    loadStats();
    loadNextNumber();
  };

  // 公文操作
  const handleViewDocument = (document: Document) => {
    // 導航到詳情頁
    navigate(`/documents/${document.id}`);
  };

  const handleEditDocument = (document: Document) => {
    // 導航到詳情頁（編輯模式）
    navigate(`/documents/${document.id}`);
  };

  const handleCreateDocument = () => {
    // 導航到新增發文頁面
    navigate('/document-numbers/create');
  };

  const handleCopyDocument = (document: Document) => {
    setDocumentOperation({ type: 'copy', document, visible: true });
  };

  const handleDeleteDocument = (document: Document) => {
    setDeleteModal({ open: true, document });
  };

  const handleConfirmDelete = async () => {
    if (deleteModal.document) {
      try {
        await documentsApi.deleteDocument(deleteModal.document.id);
        queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
        message.success(`已刪除公文: ${deleteModal.document.doc_number}`);
        refetch();
        loadStats();
        loadNextNumber();
        setDeleteModal({ open: false, document: null });
      } catch (error) {
        console.error('刪除公文失敗:', error);
        message.error('刪除公文失敗');
      }
    }
  };

  // 複製公文處理 - 功能已停用 (2026-01-12)
  // const handleSaveDocument = async (documentData: Partial<Document>): Promise<Document | void> => {
  //   try {
  //     // 只處理複製
  //     if (documentOperation.type !== 'copy') return;
  //
  //     const payload = {
  //       ...documentData,
  //       category: '發文',
  //       doc_type: '發文',
  //     };
  //
  //     const result = await documentsApi.createDocument(payload as any);
  //     message.success('發文複製成功！');
  //
  //     setDocumentOperation({ type: null, document: null, visible: false });
  //     refetch();
  //     loadStats();
  //     loadNextNumber();
  //     return result;
  //   } catch (error) {
  //     console.error('複製公文失敗:', error);
  //     throw error;
  //   }
  // };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      await documentsApi.exportDocuments({ category: 'send' });
      message.success('發文資料已匯出');
    } catch (error) {
      console.error('匯出失敗:', error);
      message.error('匯出失敗');
    } finally {
      setIsExporting(false);
    }
  };

  // ==========================================================================
  // 渲染
  // ==========================================================================

  return (
    <div style={{ padding: '24px' }}>
      {/* 頁面標題 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 24,
        }}
      >
        <Title level={2} style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
          <FileTextOutlined style={{ marginRight: 8 }} />
          發文字號管理
        </Title>

        <Button
          icon={<ReloadOutlined />}
          onClick={handleRefresh}
          loading={isLoading}
        >
          重新整理
        </Button>
      </div>

      {/* 下一個可用發文字號預覽 */}
      {nextNumber && (
        <Card
          loading={nextNumberLoading}
          style={{
            marginBottom: 24,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            border: 'none',
          }}
        >
          <Row gutter={16} align="middle">
            <Col flex="1">
              <Space direction="vertical" size={0}>
                <Text style={{ color: 'white', opacity: 0.8, fontSize: '14px' }}>
                  下一個可用發文字號
                </Text>
                <Title level={3} style={{ margin: '4px 0', color: 'white' }}>
                  {nextNumber.full_number}
                </Title>
                <Text style={{ color: 'white', opacity: 0.9 }}>
                  {nextNumber.year}年 (民國{nextNumber.roc_year}年) • 流水號{' '}
                  {nextNumber.sequence_number.toString().padStart(6, '0')}
                </Text>
              </Space>
            </Col>
            <Col>
              <Button
                type="primary"
                size="large"
                icon={<SendOutlined />}
                onClick={handleCreateDocument}
                style={{
                  background: 'rgba(255,255,255,0.2)',
                  borderColor: 'white',
                  color: 'white',
                }}
              >
                建立新發文
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* 統計卡片 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="總發文數"
              value={stats?.send_count ?? stats?.send ?? 0}
              prefix={<NumberOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="電子交換"
              value={stats?.delivery_method_stats?.electronic ?? 0}
              prefix={<CloudOutlined />}
              valueStyle={{ color: '#52c41a' }}
              suffix="筆"
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="紙本郵寄"
              value={stats?.delivery_method_stats?.paper ?? 0}
              prefix={<MailOutlined />}
              valueStyle={{ color: '#faad14' }}
              suffix="筆"
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card loading={statsLoading}>
            <Statistic
              title="本年度發文數"
              value={stats?.current_year_send_count ?? 0}
              prefix={<CalendarOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 發文列表 - 使用統一的 DocumentList 元件 */}
      <Card>
        <DocumentList
          documents={documents}
          loading={isLoading}
          total={pagination.total}
          pagination={{
            current: pagination.page,
            pageSize: pagination.limit,
          }}
          sortField={sortField}
          sortOrder={sortOrder}
          onTableChange={handleTableChange}
          onEdit={handleEditDocument}
          onDelete={handleDeleteDocument}
          onView={handleViewDocument}
          onCopy={handleCopyDocument}
          onExport={handleExport}
          isExporting={isExporting}
        />
      </Card>

      {/* 刪除確認 Modal */}
      <Modal
        title="確認刪除"
        open={deleteModal.open}
        onOk={handleConfirmDelete}
        onCancel={() => setDeleteModal({ open: false, document: null })}
        okText="刪除"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        <p>確定要刪除公文「{deleteModal.document?.doc_number}」嗎？此操作無法復原。</p>
      </Modal>

      {/* 公文操作 Modal (檢視/編輯/新增/複製) - 複製功能已停用 (2026-01-12) */}
      {/* <DocumentOperations
        document={documentOperation.document}
        operation={documentOperation.type}
        visible={documentOperation.visible}
        onClose={() => setDocumentOperation({ type: null, document: null, visible: false })}
        onSave={handleSaveDocument}
      /> */}
    </div>
  );
};

export default DocumentNumbersPage;
