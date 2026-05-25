/**
 * 契金管控 - Excel 匯出邏輯
 *
 * 從 PaymentsTab.tsx 提取，負責產生完整的 .xlsx 檔案。
 * 使用動態 import('exceljs') 延遲載入，減少初始 bundle 大小。
 *
 * @version 2.0.0 — 2026-05-21 從 xlsx (SheetJS) 遷至 ExcelJS（修 GHSA-4r6h-8v6p-xvw6 prototype pollution / GHSA-5pgg-2g8v-p4x9 ReDoS）
 * @date 2026-02-27
 */

import dayjs from 'dayjs';
import { logger } from '../../../services/logger';
import { formatDate } from './usePaymentColumns';

import type { PaymentControlItem } from '../../../types/api';

/**
 * 匯出契金管控資料為 Excel 檔案
 *
 * @param items - 契金管控資料列表
 * @param totalBudget - 總預算金額（用於檔案名稱參考）
 * @param contractTitle - 契約標題（預留，目前未用於工作表）
 * @throws 匯出失敗時拋出錯誤
 */
export const exportPaymentExcel = async (
  items: PaymentControlItem[],
  _totalBudget: number,
  _contractTitle: string
): Promise<void> => {
  // 第一行：主標題 (對應 Excel 工作表 4 的欄位結構)
  const headers1 = [
    '序',
    '派工單號',
    '工程名稱/派工事項',
    '作業類別',
    '分案名稱/派工備註',
    '案件承辦',
    '查估單位',
    '雲端資料夾',
    '專案資料夾',
    '機關函文歷程',
    '乾坤函文紀錄',
    '01.地上物查估作業',
    '',
    '02.土地協議市價查估作業',
    '',
    '03.土地徵收市價查估作業',
    '',
    '04.相關計畫書製作',
    '',
    '05.測量作業',
    '',
    '06.樁位測釘作業',
    '',
    '07.辦理教育訓練',
    '',
    '本次派工總金額',
    '累進派工金額',
    '剩餘金額',
  ];

  // 第二行：子標題
  const headers2 = [
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '',
    '派工日期',
    '派工金額',
    '派工日期',
    '派工金額',
    '派工日期',
    '派工金額',
    '派工日期',
    '派工金額',
    '派工日期',
    '派工金額',
    '派工日期',
    '派工金額',
    '派工日期',
    '派工金額',
    '',
    '',
    '',
  ];

  const rows = items.map((item, index) => [
    index + 1,
    item.dispatch_no || '',
    item.project_name || '',
    item.work_type || '',
    item.sub_case_name || '',
    item.case_handler || '',
    item.survey_unit || '',
    item.cloud_folder || '',
    item.project_folder || '',
    item.agency_doc_history || '',
    item.company_doc_history || '',
    formatDate(item.work_01_date),
    item.work_01_amount ? Math.round(item.work_01_amount) : '',
    formatDate(item.work_02_date),
    item.work_02_amount ? Math.round(item.work_02_amount) : '',
    formatDate(item.work_03_date),
    item.work_03_amount ? Math.round(item.work_03_amount) : '',
    formatDate(item.work_04_date),
    item.work_04_amount ? Math.round(item.work_04_amount) : '',
    formatDate(item.work_05_date),
    item.work_05_amount ? Math.round(item.work_05_amount) : '',
    formatDate(item.work_06_date),
    item.work_06_amount ? Math.round(item.work_06_amount) : '',
    formatDate(item.work_07_date),
    item.work_07_amount ? Math.round(item.work_07_amount) : '',
    item.current_amount ? Math.round(item.current_amount) : '',
    item.cumulative_amount ? Math.round(item.cumulative_amount) : '',
    item.remaining_amount ? Math.round(item.remaining_amount) : '',
  ]);

  // 動態載入 exceljs + file-saver（減少初始 bundle）
  const ExcelJS = (await import('exceljs')).default;
  const { saveAs } = await import('file-saver');

  const workbook = new ExcelJS.Workbook();
  const worksheet = workbook.addWorksheet('契金管控總表');

  // 加入兩行表頭
  worksheet.addRow(headers1);
  worksheet.addRow(headers2);

  // 加入資料列
  rows.forEach(row => worksheet.addRow(row));

  // 設定欄寬（對應原 wch）
  const colWidths = [
    4, 12, 25, 20, 15, 10, 10, 30, 30, 20, 20, 10, 12, 10, 12, 10, 12, 10, 12, 10, 12, 10, 12, 10,
    12, 14, 14, 14,
  ];
  colWidths.forEach((width, idx) => {
    worksheet.getColumn(idx + 1).width = width;
  });

  // 下載檔案
  const filename = `契金管控總表_${dayjs().format('YYYYMMDD')}.xlsx`;
  const buffer = await workbook.xlsx.writeBuffer();
  saveAs(
    new Blob([buffer], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    }),
    filename
  );

  logger.info(`契金管控 Excel 匯出完成: ${filename}, ${items.length} 筆`);
};
