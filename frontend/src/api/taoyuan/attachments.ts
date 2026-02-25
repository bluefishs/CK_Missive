/**
 * 桃園查估派工 - 派工單附件 API
 *
 * @version 2.0.0
 * @date 2026-01-23
 */

import { apiClient } from '../client';
import { API_ENDPOINTS } from '../endpoints';
import type {
  DispatchAttachment,
  DispatchAttachmentListResponse,
  DispatchAttachmentUploadResult,
  DispatchAttachmentDeleteResult,
  DispatchAttachmentVerifyResult,
} from '../../types/api';

/**
 * 派工單附件 API 服務
 */
export const dispatchAttachmentsApi = {
  /**
   * 上傳派工單附件
   */
  async uploadFiles(
    dispatchOrderId: number,
    files: File[],
    onProgress?: (percent: number) => void
  ): Promise<DispatchAttachmentUploadResult> {
    return apiClient.uploadWithProgress<DispatchAttachmentUploadResult>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ATTACHMENTS_UPLOAD(dispatchOrderId),
      files,
      'files',
      onProgress
    );
  },

  /**
   * 取得派工單附件列表
   */
  async getAttachments(dispatchOrderId: number): Promise<DispatchAttachment[]> {
    const response = await apiClient.post<DispatchAttachmentListResponse>(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ATTACHMENTS_LIST(dispatchOrderId),
      {}
    );
    return response.attachments || [];
  },

  /**
   * 下載附件
   */
  async downloadAttachment(attachmentId: number, filename: string): Promise<void> {
    await apiClient.downloadPost(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ATTACHMENT_DOWNLOAD(attachmentId),
      {},
      filename
    );
  },

  /**
   * 取得附件 Blob（用於預覽）
   *
   * @param attachmentId 附件 ID
   * @returns Blob 資料
   */
  async getAttachmentBlob(attachmentId: number): Promise<Blob> {
    return apiClient.postBlob(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ATTACHMENT_DOWNLOAD(attachmentId)
    );
  },

  /**
   * 刪除附件
   */
  async deleteAttachment(attachmentId: number): Promise<DispatchAttachmentDeleteResult> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ATTACHMENT_DELETE(attachmentId),
      {}
    );
  },

  /**
   * 驗證附件完整性
   */
  async verifyAttachment(attachmentId: number): Promise<DispatchAttachmentVerifyResult> {
    return apiClient.post(
      API_ENDPOINTS.TAOYUAN_DISPATCH.DISPATCH_ATTACHMENT_VERIFY(attachmentId),
      {}
    );
  },
};

// 重新匯出附件型別
export type {
  DispatchAttachment,
  DispatchAttachmentListResponse,
  DispatchAttachmentUploadResult,
  DispatchAttachmentDeleteResult,
  DispatchAttachmentVerifyResult,
};
