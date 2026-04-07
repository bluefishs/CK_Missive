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

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';
import { logger } from '../services/logger';
import { ResponsiveContent } from '@ck-shared/ui-components';
import {
  Card,
  Button,
  Space,
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

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys, defaultQueryOptions } from '../config/queryConfig';
import { DocumentList } from '../components/document/DocumentList';
// 複製功能已停用 (2026-01-12)
// import { DocumentOperations } from '../components/document/DocumentOperations';
import { useDocuments, useDocumentStatistics } from '../hooks';
import {
  documentsApi,
} from '../api/documentsApi';
import { Document } from '../types';
import { ClickableStatCard } from '../components/common';

const { Title, Text } = Typography;

export const DocumentNumbersPage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { message } = App.useApp();

  const [statFilter, setStatFilter] = useState<string | null>(null);

  // 分頁狀態
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0,
  });

  // 統計資料 (React Query)
  const { data: stats } = useDocumentStatistics();

  // 下一個可用字號 (React Query)
  const { data: nextNumber, isLoading: nextNumberLoading } = useQuery({
    queryKey: ['documents', 'next-send-number'],
    queryFn: () => documentsApi.getNextSendNumber(),
    ...defaultQueryOptions.statistics,
  });

  // 公文操作狀態
  const [_documentOperation, setDocumentOperation] = useState<{
    type: 'view' | 'edit' | 'create' | 'copy' | null;
    document: Document | null;
    visible: boolean;
  }>({ type: null, document: null, visible: false });
  void _documentOperation; // suppress noUnusedLocals — value used in commented JSX below

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
    queryClient.invalidateQueries({ queryKey: queryKeys.documents.statistics });
    queryClient.invalidateQueries({ queryKey: ['documents', 'next-send-number'] });
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
    navigate(ROUTES.SEND_DOCUMENT_CREATE);
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
        queryClient.invalidateQueries({ queryKey: ['documents', 'next-send-number'] });
        message.success(`已刪除公文: ${deleteModal.document.doc_number}`);
        setDeleteModal({ open: false, document: null });
      } catch (error) {
        logger.error('刪除公文失敗:', error);
        message.error('刪除公文失敗');
      }
    }
  };

  const handleExport = async () => {
    setIsExporting(true);
    try {
      await documentsApi.exportDocuments({ category: 'send' });
      message.success('發文資料已匯出');
    } catch (error) {
      logger.error('匯出失敗:', error);
      message.error('匯出失敗');
    } finally {
      setIsExporting(false);
    }
  };

  // ==========================================================================
  // 渲染
  // ==========================================================================

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
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
              <Space vertical size={0}>
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
          <ClickableStatCard
            title="總發文數"
            value={stats?.send_count ?? stats?.send ?? 0}
            icon={<NumberOutlined />}
            active={statFilter === 'all'}
            onClick={() => setStatFilter(statFilter === 'all' ? null : 'all')}
          />
        </Col>
        <Col xs={24} sm={6}>
          <ClickableStatCard
            title="電子交換"
            value={stats?.delivery_method_stats?.electronic ?? 0}
            icon={<CloudOutlined />}
            color="#52c41a"
            suffix="筆"
            active={statFilter === 'electronic'}
            onClick={() => setStatFilter(statFilter === 'electronic' ? null : 'electronic')}
          />
        </Col>
        <Col xs={24} sm={6}>
          <ClickableStatCard
            title="紙本郵寄"
            value={stats?.delivery_method_stats?.paper ?? 0}
            icon={<MailOutlined />}
            color="#faad14"
            suffix="筆"
            active={statFilter === 'paper'}
            onClick={() => setStatFilter(statFilter === 'paper' ? null : 'paper')}
          />
        </Col>
        <Col xs={24} sm={6}>
          <ClickableStatCard
            title="本年度發文數"
            value={stats?.current_year_send_count ?? 0}
            icon={<CalendarOutlined />}
            color="#1890ff"
            active={statFilter === 'current_year'}
            onClick={() => setStatFilter(statFilter === 'current_year' ? null : 'current_year')}
          />
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
    </ResponsiveContent>
  );
};

export default DocumentNumbersPage;
