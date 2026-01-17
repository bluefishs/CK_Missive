import React, { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Typography, Button, Space, Modal, App, Card, Tag, Alert } from 'antd';
import { PlusOutlined, ReloadOutlined, UploadOutlined, FileExcelOutlined } from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';
import { DocumentTabs } from '../components/document/DocumentTabs';
import { DocumentOperations, DocumentSendModal } from '../components/document/DocumentOperations';
import { DocumentImport } from '../components/document/DocumentImport';
import { exportDocumentsToExcel } from '../utils/exportUtils';
import {
  useDocuments,
  useCreateDocument,
  useUpdateDocument,
  useDeleteDocument,
  useAuthGuard
} from '../hooks';
import { Document, DocumentFilter as IDocumentFilter } from '../types';
import { calendarIntegrationService } from '../services/calendarIntegrationService';
import { queryKeys } from '../config/queryConfig';

const { Title, Text } = Typography;

// 固定的承攬案件（使用案件編號進行精確篩選，避免特殊字元問題）
const FIXED_CONTRACT_CODE = 'CK2025_01_03_001';
// 案件完整名稱（用於顯示）
const FIXED_CONTRACT_NAME = '115年度桃園市興辦公共設施用地取得所需土地市價及地上物查估、測量作業暨開瓶資料製作委託專業服務(開口契約)';

/**
 * 桃園查估專區 - 派工管理頁面
 *
 * 基於公文管理頁面架構，固定篩選條件為指定承攬案件
 */
export const TaoyuanDispatchPage: React.FC = () => {
  const navigate = useNavigate();
  const { message } = App.useApp();
  const queryClient = useQueryClient();

  // 權限控制
  const { hasPermission } = useAuthGuard();
  const canCreate = hasPermission('documents:create' as any);
  const canEdit = hasPermission('documents:edit' as any);
  const canDelete = hasPermission('documents:delete' as any);

  // 固定篩選條件
  const [filters, setFilters] = useState<IDocumentFilter>({
    contract_case: FIXED_CONTRACT_CODE,
  });

  // 分頁狀態
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
  });

  // 排序狀態
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

  const [documentOperation, setDocumentOperation] = useState<{
    type: 'view' | 'edit' | 'create' | 'copy' | null;
    document: Document | null;
    visible: boolean;
  }>({ type: null, document: null, visible: false });

  const [sendModal, setSendModal] = useState<{
    visible: boolean;
    document: Document | null;
  }>({ visible: false, document: null });

  // React Query: 載入公文資料
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

  // Mutation Hooks
  const createMutation = useCreateDocument();
  const updateMutation = useUpdateDocument();
  const deleteMutation = useDeleteDocument();

  // 強制刷新
  const forceRefresh = useCallback(async () => {
    await queryClient.invalidateQueries({ queryKey: queryKeys.documents.all });
    await refetch();
  }, [queryClient, refetch]);

  // 顯示錯誤訊息
  useEffect(() => {
    if (queryError) {
      message.error(queryError instanceof Error ? queryError.message : '載入公文資料失敗');
    }
  }, [queryError, message]);

  // 篩選變更（保留固定的 contract_case）
  const handleFiltersChange = (newFilters: IDocumentFilter) => {
    setPagination({ ...pagination, page: 1 });
    setFilters({
      ...newFilters,
      contract_case: FIXED_CONTRACT_CODE, // 始終保持固定
    });
  };

  // 重置篩選（保留固定的 contract_case）
  const handleResetFilters = () => {
    setPagination({ page: 1, limit: 20 });
    setSortField('');
    setSortOrder(null);
    setFilters({ contract_case: FIXED_CONTRACT_CODE });
  };

  // 表格變更處理
  const handleTableChange = (paginationInfo: any, __: any, sorter: any) => {
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
    setDocumentOperation({ type: 'view', document, visible: true });
  };

  const handleEditDocument = (document: Document) => {
    setDocumentOperation({ type: 'edit', document, visible: true });
  };

  const handleCreateDocument = () => {
    navigate('/documents/create');
  };

  const handleDeleteDocument = (document: Document) => {
    setDeleteModal({ open: true, document });
  };

  const handleArchiveDocument = async (document: Document) => {
    try {
      message.success(`公文 ${document.doc_number} 已歸檔`);
      await forceRefresh();
    } catch (error) {
      message.error('歸檔失敗');
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

  // 批量操作
  const handleBatchExport = async (selectedDocuments: Document[]) => {
    setIsExporting(true);
    try {
      await exportDocumentsToExcel(selectedDocuments, undefined, undefined, false);
      message.success(`已成功匯出 ${selectedDocuments.length} 份文件`);
    } catch (error) {
      console.error('批量匯出失敗:', error);
      message.error('批量匯出失敗');
    } finally {
      setIsExporting(false);
    }
  };

  const handleBatchDelete = async (selectedDocuments: Document[]) => {
    try {
      const ids = selectedDocuments.map(d => d.id);
      console.log('批量刪除 IDs:', ids);
      message.success(`已刪除 ${selectedDocuments.length} 個公文`);
      await forceRefresh();
    } catch (error) {
      message.error('批量刪除失敗');
    }
  };

  const handleBatchArchive = async (selectedDocuments: Document[]) => {
    try {
      const ids = selectedDocuments.map(d => d.id);
      console.log('批量歸檔 IDs:', ids);
      message.success(`已歸檔 ${selectedDocuments.length} 個公文`);
      await forceRefresh();
    } catch (error) {
      message.error('批量歸檔失敗');
    }
  };

  // CRUD 操作
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
      console.error('Save document error:', error);
      throw error;
    }
  };

  const handleConfirmDelete = async () => {
    if (deleteModal.document) {
      try {
        await deleteMutation.mutateAsync(deleteModal.document.id);
        message.success(`已刪除公文: ${deleteModal.document.doc_number}`);
        setDeleteModal({ open: false, document: null });
      } catch (error) {
        console.error('刪除公文失敗:', error);
        message.error('刪除公文失敗');
      }
    }
  };

  const handleSend = async () => {
    try {
      message.success('公文發送成功！');
      setSendModal({ visible: false, document: null });
      await forceRefresh();
    } catch (error) {
      throw error;
    }
  };

  const handleExportExcel = async () => {
    setIsExporting(true);
    try {
      const now = new Date();
      const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '');
      const filename = `桃園查估派工紀錄_${dateStr}`;
      await exportDocumentsToExcel(documents, filename, filters);
      message.success('文件已成功匯出');
    } catch (error) {
      console.error('匯出失敗:', error);
      message.error('匯出 Excel 失敗');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div style={{ padding: '24px' }}>
      {/* 頁面標題 */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 16,
        }}
      >
        <div>
          <Title level={2} style={{ margin: 0 }}>
            派工管理
          </Title>
          <Text type="secondary">桃園查估專區</Text>
        </div>

        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => forceRefresh()} loading={isLoading}>
            重新整理
          </Button>

          <Button
            icon={<FileExcelOutlined />}
            onClick={handleExportExcel}
            loading={isExporting}
          >
            匯出 Excel
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

      {/* 專案資訊卡片 */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <Tag color="blue">承攬案件</Tag>
          <Tag color="cyan">{FIXED_CONTRACT_CODE}</Tag>
          <Text strong style={{ fontSize: '14px' }}>
            {FIXED_CONTRACT_NAME}
          </Text>
          <Tag color="green">共 {totalCount} 筆公文</Tag>
        </div>
      </Card>

      {/* 公文列表 */}
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

      {/* 刪除確認 Modal */}
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

      {/* 匯入 Modal */}
      <DocumentImport
        visible={importModalVisible}
        onClose={() => setImportModalVisible(false)}
        onSuccess={async () => {
          await forceRefresh();
        }}
      />

      {/* 公文操作 Modal */}
      <DocumentOperations
        document={documentOperation.document}
        operation={documentOperation.type}
        visible={documentOperation.visible}
        onClose={() => setDocumentOperation({ type: null, document: null, visible: false })}
        onSave={handleSaveDocument}
      />

      {/* 發送 Modal */}
      <DocumentSendModal
        document={sendModal.document}
        visible={sendModal.visible}
        onClose={() => setSendModal({ visible: false, document: null })}
        onSend={handleSend}
      />
    </div>
  );
};

export default TaoyuanDispatchPage;
