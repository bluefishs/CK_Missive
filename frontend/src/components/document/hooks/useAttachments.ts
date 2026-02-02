/**
 * useAttachments Hook
 * 附件管理邏輯，從 DocumentList.tsx 拆分
 */

import { useState, useCallback } from 'react';
import { App } from 'antd';
import { filesApi, type DocumentAttachment } from '../../../api/filesApi';
import { logger } from '../../../services/logger';

interface UseAttachmentsReturn {
  attachmentCache: Record<number, DocumentAttachment[]>;
  loadingAttachments: Record<number, boolean>;
  loadAttachments: (documentId: number) => Promise<void>;
  handleDownloadAttachment: (attachment: DocumentAttachment, e: React.MouseEvent) => Promise<void>;
  handlePreviewAttachment: (attachment: DocumentAttachment, e: React.MouseEvent) => Promise<void>;
  formatFileSize: (bytes: number) => string;
  isPreviewable: (contentType?: string) => boolean;
}

export const useAttachments = (): UseAttachmentsReturn => {
  const [attachmentCache, setAttachmentCache] = useState<Record<number, DocumentAttachment[]>>({});
  const [loadingAttachments, setLoadingAttachments] = useState<Record<number, boolean>>({});
  const { message } = App.useApp();

  // 載入附件列表
  const loadAttachments = useCallback(async (documentId: number) => {
    if (attachmentCache[documentId]) {
      return; // 已載入過，直接使用快取
    }

    setLoadingAttachments(prev => ({ ...prev, [documentId]: true }));
    try {
      const attachments = await filesApi.getDocumentAttachments(documentId);
      setAttachmentCache(prev => ({ ...prev, [documentId]: attachments }));
    } catch (error) {
      logger.error('載入附件失敗:', error);
      message.error('載入附件列表失敗');
    } finally {
      setLoadingAttachments(prev => ({ ...prev, [documentId]: false }));
    }
  }, [attachmentCache, message]);

  // 下載附件
  const handleDownloadAttachment = useCallback(async (
    attachment: DocumentAttachment,
    e: React.MouseEvent
  ) => {
    e.stopPropagation();
    try {
      await filesApi.downloadAttachment(attachment.id, attachment.filename);
      message.success(`下載 ${attachment.filename} 成功`);
    } catch (error) {
      message.error(`下載 ${attachment.filename} 失敗`);
    }
  }, [message]);

  // 預覽附件
  const handlePreviewAttachment = useCallback(async (
    attachment: DocumentAttachment,
    e: React.MouseEvent
  ) => {
    e.stopPropagation();
    try {
      const blob = await filesApi.getAttachmentBlob(attachment.id);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch (error) {
      message.error(`預覽 ${attachment.filename} 失敗`);
    }
  }, [message]);

  // 格式化檔案大小
  const formatFileSize = useCallback((bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }, []);

  // 判斷是否可預覽
  const isPreviewable = useCallback((contentType?: string): boolean => {
    if (!contentType) return false;
    return contentType.startsWith('image/') ||
           contentType === 'application/pdf' ||
           contentType.startsWith('text/');
  }, []);

  return {
    attachmentCache,
    loadingAttachments,
    loadAttachments,
    handleDownloadAttachment,
    handlePreviewAttachment,
    formatFileSize,
    isPreviewable,
  };
};

export default useAttachments;
