/**
 * 報價單 Tab — **直接嵌入線上報價明細編輯器**
 *
 * 2026-08-26 owner：
 *   「其 tab 分頁有承辦同仁、報價紀錄（又有包含承辦同仁）…
 *    報價單已有提供範本，需要如 Google Sheet 線上編輯報價單機制，
 *    **目前非依原提及需求設計**，請再複查」
 *   「設計是否重疊，如 /pm/cases/526」
 *
 * ## 複查結果：要的東西 08-16 就做好了，但在使用者到不了的地方
 *
 * `QuotationItemsTab` **已經是**那個編輯器 —— 可編輯儲存格、整批儲存、
 * 空白列自動略過、總價由小計加總、可列印。它掛在 **ERP 側**
 * （`/erp/quotations/:id`），而 PM 案件頁看不到它。
 *
 * 結果：`erp_quotation_items` **0 筆 / 256 張報價單**。
 * 能力存在、範本存在（`quotation_template.xlsx`，r15 表頭正是
 * 項次｜工作內容｜數量｜單位｜單價｜複價），**中間的入口不存在**。
 *
 * ## 兩處重疊，都已消除
 *
 * 1. **承辦同仁**：我 8/26 稍早加的清單裡有「承辦同仁」欄，
 *    而隔壁就是「承辦同仁」分頁 ⇒ 同一份資訊兩個地方，已移除該欄。
 * 2. **報價編輯能力**：ERP 側有編輯器、PM 側有清單 ⇒ **入口分裂**。
 *    改為**直接嵌入同一個元件**，不是再做一份。
 *
 * ## 為什麼是「嵌入」而不是「清單再點進去」
 *
 * 實測：**256 個案件全部都只有 1 張報價單**（每案張數分布 1 張=256 案）。
 * 一案一張的情況下，清單只是多一次點擊；使用者要的是打開就能填。
 *
 * @version 5.0.0 — 嵌入 QuotationItemsTab（4.0.0 的清單是錯的方向）
 */
import { Suspense, lazy } from 'react';
import { Card, Empty, Space, Spin, Alert, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { AttachmentPanel } from '../../components/common/AttachmentPanel';
import { apiClient } from '../../api/client';
import { ERP_ENDPOINTS } from '../../api/endpoints';
import { defaultQueryOptions } from '../../config/queryConfig';
import type { ERPQuotation } from '../../types/erp';

const QuotationItemsTab = lazy(() =>
  import('../erpQuotation/QuotationItemsTab').then(m => ({ default: m.QuotationItemsTab })),
);

const { Text } = Typography;

interface QuotationRecordsTabProps {
  caseCode: string;
  caseName?: string;
  isEditing?: boolean;
}

export default function QuotationRecordsTab({
  caseCode, caseName, isEditing = false,
}: QuotationRecordsTabProps) {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['erp-quotations', 'by-case', caseCode],
    queryFn: () => apiClient.post<{ items?: ERPQuotation[] }>(
      ERP_ENDPOINTS.QUOTATIONS_LIST, { case_code: caseCode, page: 1, limit: 10 },
    ),
    enabled: !!caseCode,
    ...defaultQueryOptions.list,
  });

  const quotations = data?.items ?? [];
  const primary = quotations[0];

  return (
    <Space direction="vertical" size={16} style={{ width: '100%' }}>
      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>
      ) : isError ? (
        // ⚠️「載不到」與「還沒建報價單」意思完全相反，不能共用一個空畫面
        <Alert type="warning" showIcon message="報價單載入失敗，請重新整理" />
      ) : !primary ? (
        <Card size="small">
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="尚無報價單 —— 請用上方「新增報價」建立，建立後即可在此線上填寫明細"
          />
        </Card>
      ) : (
        <>
          <Suspense fallback={<div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>}>
            <QuotationItemsTab
              quotationId={primary.id}
              caseName={caseName ?? primary.case_name ?? undefined}
              caseCode={caseCode}
            />
          </Suspense>
          {quotations.length > 1 && (
            // 實測 256 案全部一案一張；真的出現多張時要說出來而不是靜靜只顯示第一張
            <Alert
              type="info"
              showIcon
              message={`此案有 ${quotations.length} 張報價單，目前顯示的是第一張（${primary.quotation_no || `#${primary.id}`}）`}
              description={<Text type="secondary">其餘可從 ERP 報價單列表開啟。</Text>}
            />
          )}
        </>
      )}

      {/* 上傳的檔案（客戶回簽、掃描件）—— 與線上明細是兩回事，兩者都要 */}
      <AttachmentPanel
        caseCode={caseCode}
        isEditing={isEditing}
        title="報價單檔案"
        uploadTitle="上傳報價單檔案"
        emptyText={isEditing ? '尚無檔案，可上傳客戶回簽或掃描件' : '尚無檔案'}
        showDocType
      />
    </Space>
  );
}
