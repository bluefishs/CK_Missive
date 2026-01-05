import { Document, DocumentFilter } from '../types';
import { API_BASE_URL } from '../api/client';

/**
 * 匯出文件到 Excel（非同步版本，呼叫後端 API）
 * @param documents 要匯出的文件列表
 * @param filename 檔案名稱
 * @param filters 當前篩選條件（用於檔案命名）
 */
export const exportDocumentsToExcel = async (
  documents: Document[],
  filename?: string,
  filters?: DocumentFilter
): Promise<void> => {
  if (!documents || documents.length === 0) {
    console.warn('沒有文件可以匯出');
    throw new Error('沒有可匯出的文件。');
  }

  const documentIds = documents.map(doc => doc.id);

  try {
    const response = await fetch(`${API_BASE_URL}/documents/export/excel`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // 如果需要，加入授權 token
        // 'Authorization': `Bearer ${your_token_here}`
      },
      body: JSON.stringify(documentIds),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: '無法解析錯誤回應' }));
      throw new Error(`API 請求失敗: ${response.status} - ${errorData.detail || '未知錯誤'}`);
    }

    const blob = await response.blob();

    // 從 Content-Disposition 標頭獲取檔名 (如果後端有設定)
    const disposition = response.headers.get('Content-Disposition');
    let finalFilename = filename || generateFilename(filters);
    if (disposition && disposition.indexOf('attachment') !== -1) {
      const filenameRegex = /filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/;
      const matches = filenameRegex.exec(disposition);
      if (matches != null && matches[1]) {
        finalFilename = matches[1].replace(/['"]/g, '');
      }
    }

    // 建立 URL 並觸發下載
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${finalFilename}.xlsx`;
    document.body.appendChild(a);
    a.click();

    // 清理
    a.remove();
    window.URL.revokeObjectURL(url);

    console.log(`已成功請求匯出 ${documents.length} 筆文件到 ${finalFilename}.xlsx`);
  } catch (error) {
    console.error('匯出 Excel 失敗:', error);
    // 將錯誤向上拋出，以便 UI 層可以捕獲並顯示訊息
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

  let prefix = '乾坤測繪公文清單';

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

  // 改為呼叫非同步版本的 exportDocumentsToExcel
  await exportDocumentsToExcel(filteredDocs, finalFilename);
};
