/**
 * 報價單輸出（xlsx / PDF）—— **兩個入口共用同一份實作**。
 *
 * ## 為什麼抽出來
 *
 * 2026-08-27 owner：「為何 /erp/quotations/150 會輸出報價單與輸出 pdf 功能鈕，
 * 此機制應在 /pm/cases 新增報價作業機制（邀標報價、線上報價單填寫、
 * 輸出報價單 pdf、頁面新增報價案件）」。
 *
 * 複查後三段裡只有「輸出」還留在 ERP 側：
 *
 *     新增報價      PM 案件頁 ✅（2026-08-20）
 *     線上填明細    PM 案件頁 ✅（2026-08-26 嵌入 QuotationItemsTab）
 *     輸出 / PDF    **只有 ERP 頁有** ⇒ 流程走到一半得跳模組
 *
 * 修法**不是把按鈕複製一份到 PM 頁** —— 這個流程裡有四件容易各自演化的東西：
 *   1. 沒有工項時的提醒與「去填明細」的出口
 *   2. 檔名取自後端 `Content-Disposition`（RFC 5987 中文檔名）
 *   3. PDF 先在畫面上開起來預覽（不只下載）
 *   4. blob URL 的釋放時機（iframe 還在用時不能 revoke）
 *
 * 複製一份等於承諾「以後兩邊都要記得改」，而本專案今天已經在
 * 好幾個地方付過這個代價（同一判準兩份、同一邏輯兩份實作）。
 */
import { useState } from 'react';
import { App, Button, Modal } from 'antd';
import { FileExcelOutlined, FilePdfOutlined } from '@ant-design/icons';
import { apiClient } from '../../api/client';
import { ERP_ENDPOINTS } from '../../api/endpoints';
import { extractApiMessage } from '../../utils/apiMessage';

interface UseQuotationExportOptions {
  quotationId?: number | null;
  quotationNo?: string | null;
  /** 目前的工項數；`undefined` = 呼叫端不知道（略過「沒有工項」提醒，但**不阻擋**輸出） */
  itemCount?: number;
  /** 使用者選擇「前往填寫明細」時做什麼。不給就不顯示那個選項。 */
  onGoToItems?: () => void;
}

export function useQuotationExport({
  quotationId, quotationNo, itemCount, onGoToItems,
}: UseQuotationExportOptions) {
  const { message, modal } = App.useApp();
  const [exporting, setExporting] = useState(false);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [pdfName, setPdfName] = useState('');

  const exportDocument = async (format: 'xlsx' | 'pdf' = 'xlsx') => {
    if (!quotationId) return;

    // 沒有明細就直接產出，會得到一張只有抬頭與客戶、工項全空的報價單 ——
    // 而那是要寄給客戶的文件。先講清楚，並給一條去填的路；
    // 但**不阻擋**（有人就是要一張空白表格去手寫，那是他的判斷）。
    if (itemCount === 0 && onGoToItems) {
      const go = await new Promise<boolean>((resolve) => {
        modal.confirm({
          title: '這張報價單還沒有工項',
          content: '直接產出的話，「項次／工作內容／數量／單價」會是空白的。'
            + '要先去填寫明細嗎？（明細可以像 Excel 一樣直接在頁面上編輯）',
          okText: '前往填寫明細',
          cancelText: '仍要產出空白表',
          onOk: () => resolve(true),
          onCancel: () => resolve(false),
        });
      });
      if (go) { onGoToItems(); return; }
    }

    setExporting(true);
    try {
      // 走 `apiClient` 而不是 `window.open`：這支端點需要認證標頭與 CSRF，
      // 直接開新視窗會變成未帶憑證的請求（公網實測回 401）。
      const res = await apiClient.post(
        ERP_ENDPOINTS.EXPORT_DOCUMENT,
        // PDF 由後端從**同一份 xlsx 範本**轉出（LibreOffice），版面只有一份來源。
        // archive 預設 true：輸出即存進系統（只保留最新一份）。
        { erp_quotation_id: quotationId, format },
        { responseType: 'blob' },
      );
      const raw = res as unknown as { data?: Blob } | Blob;
      const blob = raw instanceof Blob ? raw : (raw.data as Blob);

      // 檔名取自後端的 `Content-Disposition`（RFC 5987 編碼的中文檔名）——
      // 前端自己拼檔名會與後端各自演化，而檔名裡有單號，
      // 兩邊不一致時使用者會拿到一個對不上系統的檔案。
      const cd = (res as unknown as { headers?: Record<string, string> })?.headers?.[
        'content-disposition'
      ] || '';
      const m = /filename\*=UTF-8''([^;]+)/i.exec(cd);
      const filename = m?.[1]
        ? decodeURIComponent(m[1])
        : `報價單_${quotationNo || quotationId}.${format}`;

      const url = URL.createObjectURL(blob);
      if (format === 'pdf') {
        // 報價單是要寄給客戶的文件，「看一眼再送出」本來就是這個動作的一部分。
        // ⚠️ 不 revoke URL —— iframe 還在用它，關閉 Modal 時才釋放。
        setPdfUrl(url);
        setPdfName(filename);
      } else {
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (e) {
      message.error(extractApiMessage(e, '報價單輸出失敗'), 8);
    } finally {
      setExporting(false);
    }
  };

  /** 兩個輸出按鈕。呼叫端自行決定要不要顯示（例如委辦招標不顯示）。 */
  const exportButtons = (
    <>
      <Button icon={<FileExcelOutlined />} loading={exporting} onClick={() => exportDocument('xlsx')}>
        輸出報價單
      </Button>
      <Button icon={<FilePdfOutlined />} loading={exporting} onClick={() => exportDocument('pdf')}>
        輸出 PDF
      </Button>
    </>
  );

  /** PDF 預覽 Modal，呼叫端要把它掛進畫面裡。
   *  樣式沿用 ERP 詳情頁原本那一份（960 寬 / 78vh）—— 抽共用時
   *  刻意不「順便簡化」，那會讓既有頁面在使用者眼裡變差。 */
  const pdfPreview = (
    <Modal
      title={`報價單預覽 — ${pdfName}`}
      open={!!pdfUrl}
      width={960}
      onCancel={() => {
        // iframe 用完才釋放 —— 提早 revoke 會讓預覽變成空白頁
        if (pdfUrl) URL.revokeObjectURL(pdfUrl);
        setPdfUrl(null);
      }}
      footer={[
        <Button key="dl" type="primary" icon={<FilePdfOutlined />} onClick={() => {
          if (!pdfUrl) return;
          const a = document.createElement('a');
          a.href = pdfUrl;
          a.download = pdfName;
          a.click();
        }}>下載 PDF</Button>,
      ]}
      styles={{ body: { padding: 0, height: '78vh' } }}
    >
      {pdfUrl && (
        <iframe src={pdfUrl} title={pdfName}
          style={{ width: '100%', height: '100%', border: 'none' }} />
      )}
    </Modal>
  );

  return { exporting, exportDocument, exportButtons, pdfPreview };
}
