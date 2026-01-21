/**
 * 桃園查估派工 - 函文紀錄 Tab
 *
 * 使用原有的公文管理設計：
 * - 使用 DocumentTabs 組件呈現「全部公文/收文/發文」三個標籤頁
 * - 使用 DocumentFilter 組件進行篩選
 * - 點擊公文可導航至詳情頁，在「派工安排」Tab 進行派工管理
 *
 * @version 1.0.0
 * @date 2026-01-21
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Typography,
  Button,
  Space,
  Modal,
  App,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  UploadOutlined,
} from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';

import { DocumentTabs } from '../document/DocumentTabs';
import { DocumentFilter } from '../document/DocumentFilter';
import { DocumentOperations } from '../document/DocumentOperations';
import { DocumentImport } from '../document/DocumentImport';
import { exportDocumentsToExcel } from '../../utils/exportUtils';
import {
  useDocuments,
  useCreateDocument,
  useUpdateDocument,
  useDeleteDocument,
  useAuthGuard,
} from '../../hooks';
import { Document, DocumentFilter as IDocumentFilter } from '../../types';
import { calendarIntegrationService } from '../../services/calendarIntegrationService';
import { queryKeys } from '../../config/queryConfig';
import { logger } from '../../utils/logger';

const { Title } = Typography;

export interface DocumentsTabProps {
  contractCode: string;
}

export const DocumentsTab: React.FC<DocumentsTabProps> = ({ contractCode }) => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  const { hasPermission } = useAuthGuard();
  const canCreate = hasPermission('documents:create');
  const canEdit = hasPermission('documents:edit');
  const canDelete = hasPermission('documents:delete');

  // 篩選條件 - 預設帶入桃園專案的承攬案件代碼
  const [filters, setFilters] = useState<IDocumentFilter>({
    contract_case: contractCode,
  });
  const [pagination, setPagination] = useState({ page: 1, limit: 20 });

  // 排序狀態
  const [sortField, setSortField] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<'ascend' | 'descend' | null>(null);

  // Modal 狀態
  const [deleteModal, setDeleteModal] = useState<{ open: boolean; document: Document | null }>({
    open: false,
    document: null,
  });
  const [importModalVisible, setImportModalVisible] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isAddingToCalendar, setIsAddingToCalendar] = useState(false);

  const [documentOperation, setDocumentOperation] = useState<{
    type: 'view' | 'edit' | 'create' | 'copy' | null;
    document: Document | null;
    visible: boolean;
  }>({ type: null, document: null, visible: false });

  // 查詢公文列表
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

  const documents = documentsData?.items ?? [];
  const totalCount = documentsData?.pagination?.total ?? 0;

  const createMutation = useCreateDocument();
  const updateMutation = useUpdateDocument();
  const deleteMutation = useDeleteDocument();

  const forceRefresh = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
    await refetch();
  }, [queryClient, refetch]);

  useEffect(() => {
    if (queryError) {
      message.error(queryError instanceof Error ? queryError.message : '載入公文資料失敗');
    }
  }, [queryError, message]);

  // 篩選與分頁處理
  const handleFiltersChange = (newFilters: IDocumentFilter) => {
    // 保留桃園專案的 contract_case
    setPagination({ page: 1, limit: pagination.limit });
    setFilters({ ...newFilters, contract_case: contractCode });
  };

  const handleResetFilters = () => {
    setPagination({ page: 1, limit: 20 });
    setSortField('');
    setSortOrder(null);
    setFilters({ contract_case: contractCode });
  };

  const handleTableChange = (paginationInfo: any, _tableFilters: any, sorter: any) => {
    if (paginationInfo && (paginationInfo.current !== pagination.page || paginationInfo.pageSize !== pagination.limit)) {
      setPagination({
        page: paginationInfo.current || 1,
        limit: paginationInfo.pageSize || 20,
      });
    }

    if (sorter && sorter.field) {
      setSortField(sorter.field);
      setSortOrder(sorter.order);
    } else {
      setSortField('');
      setSortOrder(null);
    }
  };

  // 公文操作處理
  const handleViewDocument = (document: Document) => {
    // 導航到公文詳情頁，可在「派工安排」Tab 中進行派工管理
    navigate(`/documents/${document.id}`);
  };

  const handleEditDocument = (document: Document) => {
    // 導航到公文詳情頁進行編輯
    navigate(`/documents/${document.id}`);
  };

  const handleCreateDocument = () => {
    navigate('/documents/create');
  };

  const handleDeleteDocument = (document: Document) => {
    setDeleteModal({ open: true, document });
  };

  const handleConfirmDelete = async () => {
    if (deleteModal.document) {
      try {
        await deleteMutation.mutateAsync(deleteModal.document.id);
        message.success(`已刪除公文: ${deleteModal.document.doc_number}`);
        setDeleteModal({ open: false, document: null });
      } catch {
        message.error('刪除公文失敗');
      }
    }
  };

  const handleSaveDocument = async (documentData: Partial<Document>): Promise<Document | void> => {
    try {
      let result: Document;
      if (documentOperation.type === 'create' || documentOperation.type === 'copy') {
        result = await createMutation.mutateAsync(documentData as any);
        message.success('公文新增成功！');
      } else if (documentOperation.type === 'edit' && documentOperation.document?.id) {
        result = await updateMutation.mutateAsync({
          documentId: documentOperation.document.id,
          data: documentData as any,
        });
        message.success('公文更新成功！');
      } else {
        return;
      }
      setDocumentOperation({ type: null, document: null, visible: false });
      return result;
    } catch (error) {
      logger.error('Save document error:', error);
      throw error;
    }
  };

  const handleExportExcel = async () => {
    setIsExporting(true);
    try {
      const now = new Date();
      const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '');
      const filename = `桃園查估派工函文紀錄_${dateStr}`;
      await exportDocumentsToExcel(documents, filename, filters);
      message.success('文件已成功匯出');
    } catch {
      message.error('匯出 Excel 失敗');
    } finally {
      setIsExporting(false);
    }
  };

  const handleAddToCalendar = async (document: Document) => {
    setIsAddingToCalendar(true);
    try {
      await calendarIntegrationService.addDocumentToCalendar(document);
    } catch (error) {
      console.error('Calendar integration failed:', error);
    } finally {
      setIsAddingToCalendar(false);
    }
  };

  return (
    <div>
      {/* 標題列與工具按鈕 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>桃園查估派工 - 函文紀錄</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => forceRefresh()} loading={isLoading}>
            重新整理
          </Button>
          {canCreate && (
            <Button icon={<UploadOutlined />} onClick={() => setImportModalVisible(true)}>
              公文匯入
            </Button>
          )}
          {canCreate && (
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateDocument}>
              新增公文
            </Button>
          )}
        </Space>
      </div>

      {/* 篩選區 - 使用 DocumentFilter 組件 */}
      <DocumentFilter
        filters={filters}
        onFiltersChange={handleFiltersChange}
        onReset={handleResetFilters}
      />

      {/* 公文列表 - 使用 DocumentTabs 組件（全部公文/收文/發文） */}
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

      {/* 確認刪除 Modal */}
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

      {/* 公文匯入 */}
      <DocumentImport
        visible={importModalVisible}
        onClose={() => setImportModalVisible(false)}
        onSuccess={forceRefresh}
      />

      {/* 公文操作 Modal */}
      <DocumentOperations
        document={documentOperation.document}
        operation={documentOperation.type}
        visible={documentOperation.visible}
        onClose={() => setDocumentOperation({ type: null, document: null, visible: false })}
        onSave={handleSaveDocument}
      />
    </div>
  );
};

export default DocumentsTab;
