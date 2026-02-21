import React, { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Typography, Button, Space, Modal, App } from 'antd';
import type { TablePaginationConfig, FilterValue, SorterResult, TableCurrentDataSource } from 'antd/es/table/interface';
import { PlusOutlined, ReloadOutlined, UploadOutlined } from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';
import { DocumentFilter } from '../components/document/DocumentFilter';
import { DocumentTabs } from '../components/document/DocumentTabs';
import { DocumentImport } from '../components/document/DocumentImport';
import { exportDocumentsToExcel } from '../utils/exportUtils';
import {
  useDocuments,
  useDeleteDocument,
  useAuthGuard,
  useResponsive,
} from '../hooks';
import { useDocumentsStore } from '../store';
import { Document, DocumentFilter as IDocumentFilter } from '../types';
import { calendarIntegrationService } from '../services/calendarIntegrationService';
import { queryKeys } from '../config/queryConfig';
import { logger } from '../utils/logger';

const { Title } = Typography;

/**
 * 公文管理頁面
 *
 * 架構說明：
 * - React Query: 唯一的伺服器資料來源（公文列表）
 * - Zustand: 僅存儲 UI 狀態（篩選條件、分頁設定）
 * - Mutation Hooks: 處理建立/更新/刪除，自動失效快取
 */
export const DocumentPage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  // RWD 響應式
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  // 權限控制
  const { hasPermission } = useAuthGuard();
  const canCreate = hasPermission('documents:create');
  const canEdit = hasPermission('documents:edit');
  const canDelete = hasPermission('documents:delete');

  // Zustand: 只用於 UI 狀態（篩選條件、分頁設定）
  const { filters, pagination, setFilters, setPagination, resetFilters } = useDocumentsStore();

  // 排序狀態（本地 UI 狀態）
  const [sortField, setSortField] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<'ascend' | 'descend' | null>(null);

  // Modal 狀態
  const [deleteModal, setDeleteModal] = useState<{
    open: boolean;
    document: Document | null;
  }>({ open: false, document: null });

  const [importModalVisible, setImportModalVisible] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isAddingToCalendar, setIsAddingToCalendar] = useState(false);

  // 注意：查看、編輯、新增、複製公文已改為導航模式
  // 參見 docs/specifications/UI_DESIGN_STANDARDS.md

  // ============================================================================
  // React Query: 唯一的伺服器資料來源
  // ============================================================================
  const {
    data: documentsData,
    isLoading,
    error: queryError,
    refetch,
  } = useDocuments({
    ...filters,
    page: pagination.page,
    limit: pagination.limit,
    ...(sortField && { sortBy: sortField }),
    ...(sortOrder && { sortOrder: sortOrder === 'ascend' ? 'asc' : 'desc' }),
  });

  // 直接從 React Query 取得資料（不經過 Zustand）
  const documents = documentsData?.items ?? [];
  const totalCount = documentsData?.pagination?.total ?? 0;

  // ============================================================================
  // Mutation Hooks: 自動處理快取失效
  // ============================================================================
  const deleteMutation = useDeleteDocument();

  // 強制刷新（直接調用 refetch）
  const forceRefresh = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
    await refetch();
  }, [queryClient, refetch]);

  // 顯示錯誤訊息
  React.useEffect(() => {
    if (queryError) {
      message.error(queryError instanceof Error ? queryError.message : '載入公文資料失敗');
    }
  }, [queryError, message]);

  // ============================================================================
  // 篩選與分頁處理
  // ============================================================================
  const handleFiltersChange = (newFilters: IDocumentFilter) => {
    setPagination({ page: 1 });
    setFilters(newFilters);
  };

  const handleResetFilters = () => {
    setPagination({ page: 1 });
    setSortField('');
    setSortOrder(null);
    resetFilters();
  };

  const handleTableChange = (
    paginationInfo: TablePaginationConfig,
    _filters: Record<string, FilterValue | null>,
    sorter: SorterResult<Document> | SorterResult<Document>[],
    _extra: TableCurrentDataSource<Document>
  ) => {
    if (paginationInfo && (paginationInfo.current !== pagination.page || paginationInfo.pageSize !== pagination.limit)) {
      setPagination({
        page: paginationInfo.current || 1,
        limit: paginationInfo.pageSize || 10,
      });
    }

    // 處理單一或多重排序
    const singleSorter = Array.isArray(sorter) ? sorter[0] : sorter;
    if (singleSorter && singleSorter.field) {
      setSortField(String(singleSorter.field));
      setSortOrder(singleSorter.order ?? null);
    } else {
      setSortField('');
      setSortOrder(null);
    }
  };

  // ============================================================================
  // 公文操作處理（使用導航模式）
  // ============================================================================
  const handleViewDocument = (document: Document) => {
    navigate(`/documents/${document.id}`);
  };

  const handleEditDocument = (document: Document) => {
    navigate(`/documents/${document.id}/edit`);
  };

  const handleCreateDocument = () => {
    navigate('/documents/create');
  };

  const handleDeleteDocument = (document: Document) => {
    setDeleteModal({ open: true, document });
  };

  const handleAddToCalendar = async (document: Document) => {
    setIsAddingToCalendar(true);
    try {
      await calendarIntegrationService.addDocumentToCalendar(document);
    } catch (error) {
      logger.error('Calendar integration failed:', error);
    } finally {
      setIsAddingToCalendar(false);
    }
  };

  // ============================================================================
  // 批量操作
  // ============================================================================
  // ============================================================================
  // 刪除操作（保留確認 Modal，符合 UI 規範）
  // ============================================================================
  const handleConfirmDelete = async () => {
    if (deleteModal.document) {
      try {
        await deleteMutation.mutateAsync(deleteModal.document.id);
        message.success(`已刪除公文: ${deleteModal.document.doc_number}`);
        setDeleteModal({ open: false, document: null });
      } catch (error) {
        logger.error('刪除公文失敗:', error);
        message.error('刪除公文失敗');
      }
    }
  };

  const handleExportExcel = async () => {
    setIsExporting(true);
    try {
      // 生成檔名：乾坤測繪公文紀錄_年月日
      const now = new Date();
      const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '');
      const filename = `乾坤測繪公文紀錄_${dateStr}`;
      await exportDocumentsToExcel(documents, filename, filters);
      message.success('文件已成功匯出');
    } catch (error) {
      logger.error('匯出失敗:', error);
      message.error('匯出 Excel 失敗');
    } finally {
      setIsExporting(false);
    }
  };

  // ============================================================================
  // 渲染
  // ============================================================================
  const renderMainContent = () => {
    return (
      <DocumentTabs
        documents={documents}
        loading={isLoading}
        filters={{ ...filters, page: pagination.page, limit: pagination.limit }}
        total={totalCount}
        onEdit={canEdit ? handleEditDocument : () => {}}
        onDelete={canDelete ? handleDeleteDocument : () => {}}
        onView={handleViewDocument}
        onExport={handleExportExcel}
        onTableChange={handleTableChange}
        onFiltersChange={handleFiltersChange}
        isExporting={isExporting}
        onAddToCalendar={handleAddToCalendar}
        isAddingToCalendar={isAddingToCalendar}
      />
    );
  };

  return (
    <div style={{ padding: pagePadding }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: isMobile ? 'flex-start' : 'center',
          flexDirection: isMobile ? 'column' : 'row',
          gap: isMobile ? 12 : 0,
          marginBottom: isMobile ? 12 : 24,
        }}
      >
        <Title level={isMobile ? 4 : 2} style={{ margin: 0 }}>
          公文管理
        </Title>

        <Space size={isMobile ? 'small' : 'middle'} wrap>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => forceRefresh()}
            loading={isLoading}
            size={isMobile ? 'small' : 'middle'}
          >
            {isMobile ? '' : '重新整理'}
          </Button>

          {canCreate && (
            <Button
              icon={<UploadOutlined />}
              onClick={() => setImportModalVisible(true)}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : '公文匯入'}
            </Button>
          )}

          {canCreate && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreateDocument}
              size={isMobile ? 'small' : 'middle'}
            >
              {isMobile ? '' : '新增公文'}
            </Button>
          )}
        </Space>
      </div>

      <DocumentFilter
        filters={filters}
        onFiltersChange={handleFiltersChange}
        onReset={handleResetFilters}
      />

      {renderMainContent()}

      <Modal
        title="確認刪除"
        open={deleteModal.open}
        onOk={handleConfirmDelete}
        onCancel={() => setDeleteModal({ open: false, document: null })}
        okText="刪除"
        cancelText="取消"
        okButtonProps={{ danger: true }}
        confirmLoading={deleteMutation.isPending}
      >
        <p>確定要刪除公文「{deleteModal.document?.doc_number}」嗎？此操作無法復原。</p>
      </Modal>

      <DocumentImport
        visible={importModalVisible}
        onClose={() => setImportModalVisible(false)}
        onSuccess={async () => {
          await forceRefresh();
        }}
      />
    </div>
  );
};
