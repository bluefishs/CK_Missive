/**
 * useDocumentAttachments - 附件操作 Hook
 *
 * 從 useDocumentDetail 提取，封裝附件下載、預覽、刪除。
 *
 * @version 1.0.0
 * @date 2026-03-10
 */

import { useState, useCallback } from 'react';
import { App } from 'antd';
import { filesApi } from '../../../api/filesApi';
import type { DocumentAttachment } from '../../../types/document';
import { logger } from '../../../utils/logger';

export interface UseDocumentAttachmentsReturn {
  attachments: DocumentAttachment[];
  attachmentsLoading: boolean;
  loadAttachments: (docId: number) => Promise<DocumentAttachment[]>;
  handleDownload: (attachmentId: number, filename: string) => Promise<void>;
  handlePreview: (attachmentId: number, filename: string) => Promise<void>;
  handleDeleteAttachment: (attachmentId: number, docId: number) => Promise<void>;
}

export function useDocumentAttachments(): UseDocumentAttachmentsReturn {
  const { message } = App.useApp();
  const [attachments, setAttachments] = useState<DocumentAttachment[]>([]);
  const [attachmentsLoading, setAttachmentsLoading] = useState(false);

  const loadAttachments = useCallback(async (docId: number): Promise<DocumentAttachment[]> => {
    setAttachmentsLoading(true);
    try {
      const atts = await filesApi.getDocumentAttachments(docId);
      setAttachments(atts);
      return atts;
    } catch (error) {
      logger.warn('載入附件失敗:', error);
      return [];
    } finally {
      setAttachmentsLoading(false);
    }
  }, []);

  const handleDownload = useCallback(async (attachmentId: number, filename: string) => {
    try {
      await filesApi.downloadAttachment(attachmentId, filename);
    } catch (error) {
      logger.error('下載附件失敗:', error);
      message.error('下載附件失敗');
    }
  }, [message]);

  const handlePreview = useCallback(async (attachmentId: number, filename: string) => {
    try {
      const blob = await filesApi.getAttachmentBlob(attachmentId);
      const previewUrl = window.URL.createObjectURL(blob);
      window.open(previewUrl, '_blank');
      setTimeout(() => window.URL.revokeObjectURL(previewUrl), 10000);
    } catch (error) {
      logger.error('預覽附件失敗:', error);
      message.error(`預覽 ${filename} 失敗`);
    }
  }, [message]);

  const handleDeleteAttachment = useCallback(async (attachmentId: number, docId: number) => {
    try {
      await filesApi.deleteAttachment(attachmentId);
      message.success('附件刪除成功');
      const atts = await filesApi.getDocumentAttachments(docId);
      setAttachments(atts);
    } catch (error) {
      logger.error('刪除附件失敗:', error);
      message.error('附件刪除失敗');
    }
  }, [message]);

  return {
    attachments,
    attachmentsLoading,
    loadAttachments,
    handleDownload,
    handlePreview,
    handleDeleteAttachment,
  };
}
