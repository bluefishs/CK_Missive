/**
 * 證照附件管理 Hook
 *
 * 管理附件上傳、預覽、刪除邏輯
 * 從 CertificationFormPage 提取
 *
 * @version 1.0.0
 */
import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { certificationsApi } from '../../api/certificationsApi';
import { SERVER_BASE_URL } from '../../api/client';

/** 允許的附件格式 */
export const ALLOWED_FILE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'application/pdf'];
/** 最大檔案大小 10MB */
export const MAX_FILE_SIZE = 10 * 1024 * 1024;

/** 取得附件完整 URL */
export function getAttachmentUrl(path: string): string {
  if (path.startsWith('file:') || path.startsWith('data:')) {
    return path;
  }
  return `${SERVER_BASE_URL}/uploads/${path}`;
}

/** 判斷是否為圖片附件 */
export function isImageAttachment(path: string): boolean {
  if (path.startsWith('data:image')) return true;
  const ext = path.split('.').pop()?.toLowerCase();
  return ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext || '');
}

interface UseCertificationAttachmentOptions {
  certificationId?: number;
  existingAttachmentPath?: string | null;
  messageApi: {
    success: (msg: string) => void;
    error: (msg: string) => void;
  };
  modalApi: {
    confirm: (config: Record<string, unknown>) => unknown;
  };
}

export function useCertificationAttachment({
  certificationId,
  existingAttachmentPath,
  messageApi,
  modalApi,
}: UseCertificationAttachmentOptions) {
  const queryClient = useQueryClient();
  const [attachmentFile, setAttachmentFile] = useState<File | null>(null);
  const [attachmentPreview, setAttachmentPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  // 刪除附件 mutation
  const deleteAttachmentMutation = useMutation({
    mutationFn: () => certificationsApi.deleteAttachment(certificationId!),
    onSuccess: () => {
      messageApi.success('附件刪除成功');
      setAttachmentPreview(null);
      queryClient.invalidateQueries({ queryKey: ['certification', certificationId] });
    },
    onError: (error: Error) => {
      messageApi.error(error?.message || '刪除附件失敗');
    },
  });

  /** 初始化已有附件預覽 */
  const initPreview = (path: string | null | undefined) => {
    if (path) {
      setAttachmentPreview(path);
    }
  };

  /** 檔案選擇處理 */
  const handleFileSelect = (file: File): boolean => {
    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      messageApi.error('不支援的檔案格式，請上傳 JPG、PNG、GIF、BMP 或 PDF 檔案');
      return false;
    }
    if (file.size > MAX_FILE_SIZE) {
      messageApi.error('檔案大小超過限制（最大 10MB）');
      return false;
    }
    setAttachmentFile(file);
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setAttachmentPreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    } else {
      setAttachmentPreview(`file:${file.name}`);
    }
    return false; // 阻止自動上傳
  };

  /** 清除選擇的檔案 */
  const handleClearFile = () => {
    setAttachmentFile(null);
    if (existingAttachmentPath) {
      setAttachmentPreview(existingAttachmentPath);
    } else {
      setAttachmentPreview(null);
    }
  };

  /** 刪除附件確認 */
  const handleDeleteAttachment = () => {
    modalApi.confirm({
      title: '確定要刪除附件？',
      icon: null as unknown as React.ReactNode, // caller provides icon
      content: '刪除後將無法復原。',
      okText: '確定刪除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => deleteAttachmentMutation.mutate(),
    });
  };

  /** 上傳附件（在 create/update 成功後呼叫） */
  const uploadAttachment = async (targetId: number): Promise<boolean> => {
    if (!attachmentFile) return true;
    try {
      setUploading(true);
      await certificationsApi.uploadAttachment(targetId, attachmentFile);
      return true;
    } catch (uploadError) {
      const errMsg = uploadError instanceof Error ? uploadError.message : '未知錯誤';
      messageApi.error(`附件上傳失敗: ${errMsg}`);
      return false;
    } finally {
      setUploading(false);
    }
  };

  return {
    attachmentFile,
    attachmentPreview,
    uploading,
    deleteAttachmentMutation,
    initPreview,
    handleFileSelect,
    handleClearFile,
    handleDeleteAttachment,
    uploadAttachment,
  };
}
