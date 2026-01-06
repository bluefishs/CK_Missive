import React, { useState, useEffect } from 'react';
import { Typography, Button, Space, Modal, App, Upload, Progress } from 'antd';
import { PlusOutlined, ReloadOutlined, UploadOutlined } from '@ant-design/icons';
import { DocumentList } from '../components/document/DocumentList';
import { DocumentFilter } from '../components/document/DocumentFilter';
import { DocumentTabs } from '../components/document/DocumentTabs';
import { DocumentPagination } from '../components/document/DocumentPagination';
import { DocumentOperations, DocumentSendModal } from '../components/document/DocumentOperations';
import { exportDocumentsToExcel } from '../utils/exportUtils';
import { useDocuments } from '../hooks';
import { useDocumentsStore } from '../stores';
import { Document, DocumentFilter as IDocumentFilter } from '../types';
import { API_BASE_URL } from '../api/client';
import { documentsApi } from '../api/documentsApi';
import { calendarIntegrationService } from '../services/calendarIntegrationService';

const { Title } = Typography;

export const DocumentPage: React.FC = () => {
  const { message } = App.useApp();

  const { documents, filters, pagination, setFilters, setPagination } = useDocumentsStore();

  const [deleteModal, setDeleteModal] = useState<{
    open: boolean;
    document: Document | null;
  }>({ open: false, document: null });

  const [sortField, setSortField] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<'ascend' | 'descend' | null>(null);
  const [useTabView, setUseTabView] = useState(true);

  // CSV匯入相關狀態
  const [csvImportModal, setCsvImportModal] = useState(false);
  const [csvImporting, setCsvImporting] = useState(false);
  const [importProgress, setImportProgress] = useState(0);
  const [isExporting, setIsExporting] = useState(false); // 新增匯出狀態
  const [isAddingToCalendar, setIsAddingToCalendar] = useState(false); // 新增日曆狀態

  // 公文操作相關狀態
  const [documentOperation, setDocumentOperation] = useState<{
    type: 'view' | 'edit' | 'create' | 'copy' | null;
    document: Document | null;
    visible: boolean;
  }>({ type: null, document: null, visible: false });

  const [sendModal, setSendModal] = useState<{
    visible: boolean;
    document: Document | null;
  }>({ visible: false, document: null });

  // 使用 React Query 獲取公文資料
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

  // 更新本地狀態
  useEffect(() => {
    if (documentsData) {
      useDocumentsStore.getState().setDocuments([...documentsData.items]);
      // 正確訪問 pagination 物件中的分頁資料
      useDocumentsStore.getState().setPagination({
        total: documentsData.pagination?.total ?? 0,
        totalPages: documentsData.pagination?.total_pages ?? 0,
        page: documentsData.pagination?.page ?? 1,
        limit: documentsData.pagination?.limit ?? 20,
      });
    }
  }, [documentsData]);

  // 顯示錯誤訊息
  useEffect(() => {
    if (queryError) {
      message.error(queryError instanceof Error ? queryError.message : '載入公文資料失敗');
    }
  }, [queryError]);

  const handleFiltersChange = (newFilters: IDocumentFilter) => {
    setPagination({ page: 1 });
    setFilters(newFilters);
  };

  const handleResetFilters = () => {
    setPagination({ page: 1 });
    setSortField('');
    setSortOrder(null);
    useDocumentsStore.getState().resetFilters();
  };

  const handlePageChange = (newPage: number) => {
    setPagination({ page: newPage });
  };

  const handleLimitChange = (newLimit: number) => {
    setPagination({ page: 1, limit: newLimit });
  };

  // 公文操作處理函數
  const handleViewDocument = (document: Document) => {
    setDocumentOperation({ type: 'view', document, visible: true });
  };

  const handleEditDocument = (document: Document) => {
    setDocumentOperation({ type: 'edit', document, visible: true });
  };

  const handleCreateDocument = () => {
    setDocumentOperation({ type: 'create', document: null, visible: true });
  };

  const handleCopyDocument = (document: Document) => {
    setDocumentOperation({ type: 'copy', document, visible: true });
  };

  const handleDeleteDocument = (document: Document) => {
    setDeleteModal({ open: true, document });
  };

  const handleSendDocument = (document: Document) => {
    setSendModal({ visible: true, document });
  };

  const handleArchiveDocument = async (document: Document) => {
    try {
      // 實際的歸檔 API 呼叫
      message.success(`公文 ${document.doc_number} 已歸檔`);
      refetch();
    } catch (error) {
      message.error('歸檔失敗');
    }
  };

  const handleExportPdf = async (document: Document) => {
    try {
      message.success(`正在匯出公文 ${document.doc_number} 的PDF...`);
      // 這裡實作PDF匯出邏輯
    } catch (error) {
      message.error('PDF匯出失敗');
    }
  };

  const handleAddToCalendar = async (document: Document) => {
    setIsAddingToCalendar(true);
    try {
      await calendarIntegrationService.addDocumentToCalendar(document);
    } catch (error) {
      // 錯誤處理已在服務中完成
      console.error('Calendar integration failed:', error);
    } finally {
      setIsAddingToCalendar(false);
    }
  };

  // 批量操作處理函數
  const handleBatchExport = async (selectedDocuments: Document[]) => {
    setIsExporting(true);
    try {
      await exportDocumentsToExcel(selectedDocuments);
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
      // 實際的批量刪除 API 呼叫
      console.log('批量刪除 IDs:', ids);
      message.success(`已刪除 ${selectedDocuments.length} 個公文`);
      refetch();
    } catch (error) {
      message.error('批量刪除失敗');
    }
  };

  const handleBatchArchive = async (selectedDocuments: Document[]) => {
    try {
      const ids = selectedDocuments.map(d => d.id);
      // 實際的批量歸檔 API 呼叫
      console.log('批量歸檔 IDs:', ids);
      message.success(`已歸檔 ${selectedDocuments.length} 個公文`);
      refetch();
    } catch (error) {
      message.error('批量歸檔失敗');
    }
  };

  // 儲存公文 (使用統一 API 服務)
  const handleSaveDocument = async (documentData: Partial<Document>) => {
    try {
      let updatedDocument: Document;

      if (documentOperation.type === 'create' || documentOperation.type === 'copy') {
        // 使用 documentsApi 建立公文
        updatedDocument = await documentsApi.createDocument(documentData as any);
        message.success('公文新增成功！');
        refetch();
      } else if (documentOperation.type === 'edit' && documentOperation.document?.id) {
        // 使用 documentsApi 更新公文
        updatedDocument = await documentsApi.updateDocument(
          documentOperation.document.id,
          documentData as any
        );
        message.success('公文更新成功！');
        // 刷新列表以確保顯示最新資料
        refetch();
      }

      setDocumentOperation({ type: null, document: null, visible: false });
    } catch (error) {
      console.error('Save document error:', error);
      throw error;
    }
  };

  // 發送公文
  const handleSend = async () => {
    try {
      message.success('公文發送成功！');
      setSendModal({ visible: false, document: null });
      refetch();
    } catch (error) {
      throw error;
    }
  };

  const handleRefresh = () => {
    refetch();
  };

  const handleConfirmDelete = async () => {
    if (deleteModal.document) {
      try {
        // 使用統一 API 服務刪除公文 (POST-only 資安機制)
        await documentsApi.deleteDocument(deleteModal.document.id);

        message.success(`已刪除公文: ${deleteModal.document.doc_number}`);
        refetch();
        setDeleteModal({ open: false, document: null });
      } catch (error) {
        console.error('刪除公文失敗:', error);
        message.error('刪除公文失敗');
      }
    }
  };

  const handleCancelDelete = () => {
    setDeleteModal({ open: false, document: null });
  };

  const handleTableChange = (pagination: any, __: any, sorter: any) => {
    // Handle pagination changes
    if (pagination && (pagination.current !== pagination.page || pagination.pageSize !== pagination.limit)) {
      const newPagination = {
        page: pagination.current || 1,
        limit: pagination.pageSize || 10,
        total: pagination.total || 0
      };
      setPagination(newPagination);
    }

    // Handle sorting changes
    if (sorter && sorter.field) {
      setSortField(sorter.field);
      setSortOrder(sorter.order);
    } else {
      setSortField('');
      setSortOrder(null);
    }
  };

  const handleExportExcel = async () => {
    setIsExporting(true);
    try {
      // 匯出所有當前篩選條件下的文件
      await exportDocumentsToExcel(documents, 'documents.xlsx', filters);
      message.success('文件已成功匯出');
    } catch (error) {
      console.error('匯出失敗:', error);
      message.error('匯出 Excel 失敗');
    } finally {
      setIsExporting(false);
    }
  };

  // 渲染主內容
  const renderMainContent = () => {
    if (useTabView) {
      return (
        <DocumentTabs
          documents={documents}
          loading={isLoading}
          filters={{ ...filters, page: pagination.page, limit: pagination.limit }}
          total={pagination.total}
          onEdit={handleEditDocument}
          onDelete={handleDeleteDocument}
          onView={handleViewDocument}
          onExport={handleExportExcel}
          onTableChange={handleTableChange}
          onFiltersChange={handleFiltersChange}
          isExporting={isExporting}
          onAddToCalendar={handleAddToCalendar}
          isAddingToCalendar={isAddingToCalendar}
        />
      );
    }
    return (
      <>
        <DocumentList
          documents={documents}
          loading={isLoading}
          total={pagination.total}
          pagination={{ current: pagination.page, pageSize: pagination.limit }}
          sortField={sortField}
          sortOrder={sortOrder}
          onTableChange={handleTableChange}
          onEdit={handleEditDocument}
          onDelete={handleDeleteDocument}
          onView={handleViewDocument}
          onCopy={handleCopyDocument}
          onExportPdf={handleExportPdf}
          onSend={handleSendDocument}
          onArchive={handleArchiveDocument}
          onExport={handleExportExcel}
          onAddToCalendar={handleAddToCalendar}
          onBatchExport={handleBatchExport}
          onBatchDelete={handleBatchDelete}
          onBatchArchive={handleBatchArchive}
          enableBatchOperations
          isExporting={isExporting}
          isAddingToCalendar={isAddingToCalendar}
        />
        <DocumentPagination
          page={pagination.page}
          limit={pagination.limit}
          total={pagination.total}
          totalPages={pagination.totalPages}
          onPageChange={handlePageChange}
          onLimitChange={handleLimitChange}
        />
      </>
    );
  };

  // CSV匯入處理
  const handleCSVImport = () => {
    setCsvImportModal(true);
  };

  const handleCSVUpload = async (file: any) => {
    setCsvImporting(true);
    setImportProgress(0);

    const formData = new FormData();
    formData.append('file', file);

    try {
      const progressInterval = setInterval(() => {
        setImportProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      const response = await fetch(`${API_BASE_URL}/documents/import`, {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);
      setImportProgress(100);

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`匯入失敗 (${response.status}): ${errorText}`);
      }

      const result = await response.json();

      if (result.success_count > 0) {
        message.success(`CSV匯入成功！共 ${result.total_rows} 筆，成功 ${result.success_count} 筆`);
      } else {
        message.warning(
          `CSV匯入完成，但無資料成功匯入。共 ${result.total_rows} 筆，${result.error_count} 筆錯誤`
        );
      }

      if (result.errors && result.errors.length > 0) {
        const errorSample = result.errors.slice(0, 3).join('; ');
        message.error(`匯入錯誤: ${errorSample}${result.errors.length > 3 ? '...' : ''}`);
      }

      refetch();
      setCsvImportModal(false);
    } catch (error) {
      message.error(`CSV匯入失敗: ${error instanceof Error ? error.message : '網路錯誤'}`);
    } finally {
      setCsvImporting(false);
      setImportProgress(0);
    }

    return false;
  };

  return (
    <div style={{ padding: '24px' }}>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 24,
        }}
      >
        <Title level={2} style={{ margin: 0 }}>
          公文管理
        </Title>

        <Space>
          <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={isLoading}>
            重新整理
          </Button>

          <Button onClick={() => setUseTabView(!useTabView)}>
            {useTabView ? '列表視圖' : '分頁視圖'}
          </Button>

          <Button icon={<UploadOutlined />} onClick={handleCSVImport} loading={csvImporting}>
            匯入 CSV
          </Button>

          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreateDocument}>
            新增公文
          </Button>
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
        onCancel={handleCancelDelete}
        okText="刪除"
        cancelText="取消"
        okButtonProps={{ danger: true }}
      >
        <p>確定要刪除公文「{deleteModal.document?.doc_number}」嗎？此操作無法復原。</p>
      </Modal>

      <Modal
        title="匯入 CSV 檔案"
        open={csvImportModal}
        onCancel={() => setCsvImportModal(false)}
        footer={null}
        width={600}
      >
        <div style={{ padding: '20px 0' }}>
          {csvImporting ? (
            <div style={{ textAlign: 'center' }}>
              <Progress type="circle" percent={importProgress} />
              <p style={{ marginTop: 16 }}>匯入中...</p>
            </div>
          ) : (
            <Upload.Dragger
              name="file"
              multiple={false}
              accept=".csv"
              beforeUpload={handleCSVUpload}
              showUploadList={false}
            >
              <p className="ant-upload-drag-icon">
                <UploadOutlined />
              </p>
              <p className="ant-upload-text">點選或拖曳 CSV 檔案到此區域</p>
              <p className="ant-upload-hint">支援單檔上傳。欄位將自動對應。</p>
            </Upload.Dragger>
          )}
        </div>
      </Modal>

      <DocumentOperations
        document={documentOperation.document}
        operation={documentOperation.type}
        visible={documentOperation.visible}
        onClose={() => setDocumentOperation({ type: null, document: null, visible: false })}
        onSave={handleSaveDocument}
      />

      <DocumentSendModal
        document={sendModal.document}
        visible={sendModal.visible}
        onClose={() => setSendModal({ visible: false, document: null })}
        onSend={handleSend}
      />
    </div>
  );
};
