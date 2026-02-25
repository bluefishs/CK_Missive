import { Document, DocumentFilter } from '../types';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { logger } from './logger';

/**
 * 匯出文件到 Excel（非同步版本，呼叫後端 API）
 * @param documents 要匯出的文件列表
 * @param filename 檔案名稱
 * @param filters 當前篩選條件（用於檔案命名）
 */
export const exportDocumentsToExcel = async (
  documents: Document[],
  filename?: string,
  filters?: DocumentFilter,
  exportAll: boolean = true  // 預設匯出全部
): Promise<void> => {
  // 構建請求體
  const requestBody: {
    document_ids?: number[];
    category?: string;
    year?: number;
    keyword?: string;
    status?: string;
    contract_case?: string;
    sender?: string;
    receiver?: string;
  } = {};

  // 如果不是匯出全部，才傳入 document_ids（用於批次匯出選定項目）
  if (!exportAll && documents && documents.length > 0) {
    requestBody.document_ids = documents.map(doc => doc.id);
  }

  // 加入篩選條件（讓後端根據篩選條件匯出全部符合的資料）
  // category 對應收文/發文（支援 doc_type 和 category 兩種欄位名稱）
  if (filters?.doc_type) {
    requestBody.category = filters.doc_type;
  }
  if (filters?.category) {
    requestBody.category = filters.category;
  }
  if (filters?.year) {
    requestBody.year = filters.year;
  }
  // 支援 keyword 和 search 兩種欄位名稱
  if (filters?.keyword || filters?.search) {
    requestBody.keyword = filters.keyword || filters.search;
  }
  if (filters?.status) {
    requestBody.status = filters.status;
  }
  // 新增：承攬案件、發文單位、受文單位篩選
  if (filters?.contract_case) {
    requestBody.contract_case = filters.contract_case;
  }
  if (filters?.sender) {
    requestBody.sender = filters.sender;
  }
  if (filters?.receiver) {
    requestBody.receiver = filters.receiver;
  }

  const finalFilename = (filename || generateFilename(filters)).replace(/\.xlsx$/i, '') + '.xlsx';

  try {
    await apiClient.downloadPost(
      API_ENDPOINTS.DOCUMENTS.EXPORT_EXCEL,
      requestBody,
      finalFilename
    );
    logger.debug(`已成功請求匯出 ${documents.length} 筆文件到 ${finalFilename}`);
  } catch (error) {
    logger.error('匯出 Excel 失敗:', error);
    throw error;
  }
};

/**
 * 生成檔案名稱
 */
function generateFilename(filters?: DocumentFilter): string {
  const now = new Date();
  const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '');
  const timeStr = now.toTimeString().slice(0, 5).replace(':', '');

  let prefix = '乾坤測繪公文紀錄';

  // 根據篩選條件調整檔案名稱
  if (filters) {
    if (filters.doc_type === '收文') {
      prefix = '收文記錄';
    } else if (filters.doc_type === '發文') {
      prefix = '發文記錄';
    } else if (filters.year) {
      prefix = `${filters.year}年度公文清單`;
    }
  }

  return `${prefix}_${dateStr}_${timeStr}`;
}

/**
 * 匯出特定類型的文件 (已更新為非同步)
 */
export const exportDocumentsByType = async (
  documents: Document[],
  type: 'received' | 'sent' | 'all'
): Promise<void> => {
  let filteredDocs = documents;
  let filename = '';

  switch (type) {
    case 'received':
      filteredDocs = documents.filter(
        doc =>
          doc.doc_type === '收文' || doc.receive_date || (doc.doc_type !== '發文' && doc.receiver)
      );
      filename = '收文記錄';
      break;

    case 'sent':
      filteredDocs = documents.filter(
        doc =>
          doc.doc_type === '發文' ||
          doc.send_date ||
          (doc.doc_type !== '收文' && doc.sender && !doc.receiver)
      );
      filename = '發文記錄';
      break;

    case 'all':
    default:
      filteredDocs = documents;
      filename = '公文總彙整';
      break;
  }

  const now = new Date();
  const dateStr = now.toISOString().slice(0, 10).replace(/-/g, '');
  const finalFilename = `${filename}_${dateStr}`;

  // 批次匯出選定的文件 (exportAll: false)
  await exportDocumentsToExcel(filteredDocs, finalFilename, undefined, false);
};
