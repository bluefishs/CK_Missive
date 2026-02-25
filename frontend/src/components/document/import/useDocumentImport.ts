/**
 * 公文匯入邏輯 Hook
 *
 * 管理 step state machine、預覽、匯入、範本下載。
 *
 * @version 1.1.0 - 統一使用 apiClient 取代 raw fetch
 * @date 2026-02-25
 */

import { useState } from 'react';
import { apiClient } from '../../../api/client';
import { API_ENDPOINTS } from '../../../api/endpoints';
import type { PreviewResult, ImportResult, ImportStep } from './types';

export interface UseDocumentImportReturn {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  uploading: boolean;
  importing: boolean;
  step: ImportStep;
  previewResult: PreviewResult | null;
  importResult: ImportResult | null;
  handleReset: () => void;
  handleClose: () => void;
  handleExcelPreview: (file: File) => Promise<false>;
  handleExcelImport: () => Promise<void>;
  handleCsvUpload: (file: File) => Promise<false>;
  handleDownloadTemplate: () => Promise<void>;
}

export function useDocumentImport(
  onClose: () => void,
  onSuccess?: () => void,
): UseDocumentImportReturn {
  const [activeTab, setActiveTab] = useState<string>('excel');
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [step, setStep] = useState<ImportStep>('upload');
  const [previewResult, setPreviewResult] = useState<PreviewResult | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [currentFile, setCurrentFile] = useState<File | null>(null);

  const handleReset = () => {
    setStep('upload');
    setPreviewResult(null);
    setImportResult(null);
    setCurrentFile(null);
  };

  const handleClose = () => {
    handleReset();
    onClose();
  };

  const handleImportSuccess = () => {
    if (onSuccess) {
      onSuccess();
    }
  };

  const handleExcelPreview = async (file: File): Promise<false> => {
    setUploading(true);
    setCurrentFile(file);

    try {
      const result = await apiClient.postForm<PreviewResult>(
        API_ENDPOINTS.DOCUMENTS.IMPORT_EXCEL_PREVIEW,
        (() => { const fd = new FormData(); fd.append('file', file); return fd; })()
      );
      setPreviewResult(result);
      setStep('preview');
    } catch (error) {
      setPreviewResult({
        success: false,
        filename: file.name,
        total_rows: 0,
        preview_rows: [],
        headers: [],
        validation: {
          missing_required_fields: [],
          invalid_categories: [],
          invalid_doc_types: [],
          duplicate_doc_numbers: [],
          existing_in_db: [],
          will_insert: 0,
          will_update: 0,
        },
        errors: [`預覽失敗: ${error}`],
      });
      setStep('preview');
    } finally {
      setUploading(false);
    }

    return false;
  };

  const handleExcelImport = async () => {
    if (!currentFile) return;

    setImporting(true);

    try {
      const result = await apiClient.postForm<ImportResult>(
        API_ENDPOINTS.DOCUMENTS.IMPORT_EXCEL,
        (() => { const fd = new FormData(); fd.append('file', currentFile); return fd; })()
      );
      setImportResult(result);
      setStep('result');

      if (result.success && (result.inserted > 0 || result.updated > 0)) {
        handleImportSuccess();
      }
    } catch (error) {
      setImportResult({
        success: false,
        filename: currentFile.name,
        total_rows: 0,
        inserted: 0,
        updated: 0,
        skipped: 0,
        errors: [`匯入失敗: ${error}`],
      });
      setStep('result');
    } finally {
      setImporting(false);
    }
  };

  const handleCsvUpload = async (file: File): Promise<false> => {
    setUploading(true);
    setCurrentFile(file);

    try {
      const result = await apiClient.postForm<ImportResult>(
        API_ENDPOINTS.CSV_IMPORT.UPLOAD_AND_IMPORT,
        (() => { const fd = new FormData(); fd.append('file', file); return fd; })()
      );
      setImportResult(result);
      setStep('result');

      if (result.success && result.inserted > 0) {
        handleImportSuccess();
      }
    } catch (error) {
      setImportResult({
        success: false,
        filename: file.name,
        total_rows: 0,
        inserted: 0,
        updated: 0,
        skipped: 0,
        errors: [`匯入失敗: ${error}`],
      });
      setStep('result');
    } finally {
      setUploading(false);
    }

    return false;
  };

  const handleDownloadTemplate = async () => {
    await apiClient.downloadPost(
      API_ENDPOINTS.DOCUMENTS.IMPORT_EXCEL_TEMPLATE,
      {},
      '公文匯入範本.xlsx'
    );
  };

  return {
    activeTab,
    setActiveTab,
    uploading,
    importing,
    step,
    previewResult,
    importResult,
    handleReset,
    handleClose,
    handleExcelPreview,
    handleExcelImport,
    handleCsvUpload,
    handleDownloadTemplate,
  };
}
