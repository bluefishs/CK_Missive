/**
 * 桃園查估派工 - 函文紀錄 Tab
 *
 * 使用原有的公文管理設計：
 * - 使用 DocumentTabs 組件呈現「全部公文/收文/發文」三個標籤頁
 * - 使用 DocumentFilter 組件進行篩選
 * - 桌面版：點擊公文開啟預覽抽屜，可快速查看摘要
 * - 手機版：直接導航至詳情頁
 *
 * @version 1.2.0 - 新增預覽抽屜功能
 * @date 2026-01-26
 */

import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Typography,
  Button,
  Space,
  Modal,
  App,
  Row,
  Col,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  UploadOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useResponsive } from '../../hooks';
import { useQueryClient, useQuery } from '@tanstack/react-query';

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
import { documentsApi } from '../../api/documentsApi';
import { filesApi } from '../../api/filesApi';
import { PreviewDrawer, DocumentPreview } from '../common/PreviewDrawer';

const { Title } = Typography;

export interface DocumentsTabProps {
  contractCode: string;
}

export const DocumentsTab: React.FC<DocumentsTabProps> = ({ contractCode }) => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  // RWD 響應式
  const { isMobile } = useResponsive();

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

  // 預覽抽屜狀態
  const [previewDrawer, setPreviewDrawer] = useState<{
    open: boolean;
    documentId: number | null;
  }>({ open: false, documentId: null });

  // 預覽公文資料查詢
  const { data: previewDocument, isLoading: previewLoading } = useQuery({
    queryKey: ['document-preview', previewDrawer.documentId],
    queryFn: () => documentsApi.getDocument(previewDrawer.documentId!),
    enabled: previewDrawer.open && previewDrawer.documentId !== null,
  });

  // 預覽公文附件數量查詢
  const { data: previewAttachments } = useQuery({
    queryKey: ['document-attachments-preview', previewDrawer.documentId],
    queryFn: () => filesApi.getDocumentAttachments(previewDrawer.documentId!),
    enabled: previewDrawer.open && previewDrawer.documentId !== null,
  });

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
    // 手機版：直接跳轉詳情頁
    // 桌面版：開啟預覽抽屜
    if (isMobile) {
      navigate(`/documents/${document.id}`);
    } else {
      setPreviewDrawer({ open: true, documentId: document.id });
    }
  };

  const handleClosePreview = () => {
    setPreviewDrawer({ open: false, documentId: null });
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
      {/* 標題列與工具按鈕 - RWD 響應式 */}
      <Row gutter={[8, 8]} style={{ marginBottom: isMobile ? 12 : 16 }} align="middle">
        <Col xs={24} sm={12}>
          <Title level={isMobile ? 5 : 4} style={{ margin: 0 }}>
            {isMobile ? '函文紀錄' : '桃園查估派工 - 函文紀錄'}
          </Title>
        </Col>
        <Col xs={24} sm={12} style={{ textAlign: isMobile ? 'left' : 'right' }}>
          <Space wrap size={isMobile ? 'small' : 'middle'}>
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
        </Col>
      </Row>

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

      {/* 公文預覽抽屜 */}
      <PreviewDrawer
        open={previewDrawer.open}
        onClose={handleClosePreview}
        title={
          <Space>
            <FileTextOutlined />
            公文預覽
          </Space>
        }
        subtitle={previewDocument?.doc_number}
        detailPath={previewDrawer.documentId ? `/documents/${previewDrawer.documentId}` : undefined}
        loading={previewLoading}
      >
        <DocumentPreview
          document={previewDocument || null}
          attachmentCount={previewAttachments?.length || 0}
        />
      </PreviewDrawer>
    </div>
  );
};

export default DocumentsTab;
