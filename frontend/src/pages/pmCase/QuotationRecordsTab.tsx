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
import { Suspense, lazy, useState, useEffect } from 'react';
import { Card, Empty, Space, Spin, Alert, Select, Typography, Input, Button, App, Descriptions } from 'antd';
import { useQuotationExport } from '../erpQuotation/useQuotationExport';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AttachmentPanel } from '../../components/common/AttachmentPanel';
import { apiClient } from '../../api/client';
import { ERP_ENDPOINTS, PM_ENDPOINTS } from '../../api/endpoints';
import { useNavigate } from 'react-router-dom';
import { ROUTES } from '../../router/types';
import { defaultQueryOptions, queryKeys } from '../../config/queryConfig';
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
      // 2026-09-04 owner「新增報價單也無看到紀錄」：列表端點預設只回成案的報價單（include_unawarded=false），
      // 剛建的 draft 永遠不在裡面 ⇒ 分頁顯示「尚無報價單」。本案範圍要看全部版次。
      ERP_ENDPOINTS.QUOTATIONS_LIST, { case_code: caseCode, page: 1, limit: 10, include_unawarded: true },
    ),
    enabled: !!caseCode,
    ...defaultQueryOptions.list,
  });

  const quotations = data?.items ?? [];
  // 2026-09-04：一案多張報價單時可切換（此前只顯示第一張，其餘要跳去 ERP 列表）。
  // 列表由後端 id desc 排序 ⇒ 預設是最新一張，也就是使用者剛建立的那張。
  const [selectedId, setSelectedId] = useState<number | undefined>();
  const primary = quotations.find((q) => q.id === selectedId) ?? quotations[0];

  // 明細筆數：與 `QuotationItemsTab` **共用同一個 queryKey**，
  // 所以嵌入的編輯器已經取過時這裡不會多打一次。
  const { data: itemsData } = useQuery({
    // 與 QuotationItemsTab 完全相同的 key + queryFn ——
    // 形狀必須一致，否則就是今天修過的那個「同 key 不同形狀」的坑。
    queryKey: queryKeys.erpQuotations.items(primary?.id ?? 0),
    queryFn: async () => {
      const res = await apiClient.post<{ data: { items?: unknown[] } }>(
        ERP_ENDPOINTS.QUOTATION_ITEMS_DETAIL, { quotation_id: primary!.id },
      );
      return res?.data;
    },
    enabled: !!primary?.id,
  });

  // 2026-08-27 owner：「為何 /erp/quotations/150 會輸出報價單與輸出 pdf 功能鈕，
  //   此機制應在 /pm/cases 新增報價作業機制」。
  //
  // 複查：新增報價（08-20）與線上填明細（08-26）都已經在 PM 案件頁了，
  // **只有「輸出」還留在 ERP 側** ⇒ 流程走到一半得跳模組。
  // 用共用 hook 而不是把按鈕複製一份 —— 那個流程裡有四件容易各自演化的東西
  // （空工項提醒、後端給的檔名、PDF 預覽、blob 釋放時機）。
  //
  // 2026-08-28 owner 更新：委辦招標（`01`）**也呈現**報價單與輸出 ——
  //   取代 08-27「01 不顯示」的規則。後端 `quotation_document.py` 本來就
  //   不擋 01，只在文件上加註「本案為委辦招標案，依招標文件所列項目辦理」。
  // 2026-09-04 owner「編輯頁面無法編輯備註，但新增報價時有」：備註印在正式文件第 29 列，
  // 建立頁填得到、這裡（唯一的輸出入口）卻改不了。同一個欄位、同一個更新端點。
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [notes, setNotes] = useState('');
  useEffect(() => { setNotes(primary?.notes ?? ''); }, [primary?.id, primary?.notes]);
  const saveNotes = useMutation({
    mutationFn: () => apiClient.post(ERP_ENDPOINTS.QUOTATIONS_UPDATE, { id: primary!.id, data: { notes: notes.trim() || null } }),
    onSuccess: () => {
      message.success('備註已更新（已輸出的檔要重新輸出才會帶到）');
      void qc.invalidateQueries({ queryKey: ['erp-quotations', 'by-case', caseCode] });
    },
    onError: () => message.error('備註更新失敗'),
  });
  const notesDirty = (primary?.notes ?? '') !== notes;

  // 2026-09-04 owner「報價單無法編輯客戶資訊等」：文件抬頭欄位不在報價單上（客戶＝委託單位主檔、
  // 工作地點＝PM 案、服務人員＝承辦指派）。這張卡把「文件會印什麼」攤開，每一欄旁邊就是改它的入口。
  const navigate = useNavigate();
  interface DocHeader {
    client_name?: string | null; client_tax_id?: string | null; client_phone?: string | null; client_address?: string | null;
    contact_person?: string | null; contact_phone?: string | null; contact_mobile?: string | null; contact_email?: string | null;
    location?: string | null; staff_name?: string | null; staff_email?: string | null;
    pm_case_id?: number | null; client_vendor_id?: number | null;
  }
  const { data: docHeader } = useQuery({
    queryKey: ['erp-quotations', 'document-data', primary?.id],
    queryFn: async () => (await apiClient.post<{ data: DocHeader }>(ERP_ENDPOINTS.QUOTATION_DOCUMENT_DATA, { erp_quotation_id: primary!.id })).data,
    enabled: !!primary?.id,
  });
  const [locationDraft, setLocationDraft] = useState('');
  useEffect(() => { setLocationDraft(docHeader?.location ?? ''); }, [docHeader?.location]);
  const saveLocation = useMutation({
    mutationFn: () => apiClient.post(PM_ENDPOINTS.CASES_UPDATE, { id: docHeader!.pm_case_id, data: { location: locationDraft.trim() || null } }),
    onSuccess: () => { message.success('工作地點已更新'); void qc.invalidateQueries({ queryKey: ['erp-quotations', 'document-data'] }); },
    onError: () => message.error('工作地點更新失敗'),
  });
  const dash = (v?: string | null) => v || <Text type="secondary">—</Text>;

  const { exportButtons, pdfPreview } = useQuotationExport({
    quotationId: primary?.id,
    quotationNo: primary?.quotation_no,
    itemCount: itemsData?.items?.length,
    // 明細編輯器就嵌在這一頁下方，不需要導航 —— 不給 onGoToItems
    // 等於略過「前往填寫」那個選項，但仍會照常輸出。
  });

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
          <Card size="small" styles={{ body: { padding: '8px 12px' } }}>
            <Space wrap>
              <Text type="secondary">產出正式文件：</Text>
              {exportButtons}
              <Text type="secondary" style={{ fontSize: 12 }}>
                （輸出後自動存入本案附件，只保留最新一份）
              </Text>
            </Space>
          </Card>
          <Card size="small" title="文件抬頭資訊（正式報價單會印出來的）" styles={{ body: { padding: '8px 12px' } }}
            extra={<Space size={4}>
              {docHeader?.client_vendor_id ? (
                <Button size="small" onClick={() => navigate(ROUTES.CLIENT_EDIT.replace(':id', String(docHeader.client_vendor_id)))}>編輯委託單位（客戶／聯絡人／統編／地址）</Button>
              ) : (
                <Text type="secondary" style={{ fontSize: 12 }}>此案未連結委託單位主檔，請到案件資訊分頁選擇委託單位</Text>
              )}
              <Button size="small" onClick={() => navigate(`?tab=staff`)}>承辦同仁（服務人員）</Button>
            </Space>}>
            <Descriptions size="small" column={{ xs: 1, sm: 2, md: 3 }} colon
              items={[
                { key: 'client', label: '客戶名稱', children: dash(docHeader?.client_name) },
                { key: 'tax', label: '統一編號', children: dash(docHeader?.client_tax_id) },
                { key: 'contact', label: '聯絡人', children: dash(docHeader?.contact_person) },
                { key: 'phone', label: '聯絡電話', children: dash(docHeader?.contact_phone ?? docHeader?.client_phone) },
                { key: 'mobile', label: '手機', children: dash(docHeader?.contact_mobile) },
                { key: 'email', label: 'E-mail', children: dash(docHeader?.contact_email) },
                { key: 'addr', label: '聯絡地址', children: dash(docHeader?.client_address), span: 2 },
                { key: 'staff', label: '服務人員', children: dash(docHeader?.staff_name) },
                { key: 'loc', label: '工作地點', span: 3, children: isEditing || !primary.project_code ? (
                  <Space.Compact style={{ width: '100%', maxWidth: 560 }}>
                    <Input value={locationDraft} onChange={(e) => setLocationDraft(e.target.value)} placeholder="例：西區後壠子段199-44地號" maxLength={300} />
                    <Button type="primary" disabled={(docHeader?.location ?? '') === locationDraft || !docHeader?.pm_case_id} loading={saveLocation.isPending} onClick={() => saveLocation.mutate()}>儲存</Button>
                  </Space.Compact>
                ) : dash(docHeader?.location) },
              ]} />
          </Card>
          <Suspense fallback={<div style={{ textAlign: 'center', padding: 24 }}><Spin /></div>}>
            <QuotationItemsTab
              quotationId={primary.id}
              caseName={caseName ?? primary.case_name ?? undefined}
              caseCode={caseCode}
            />
          </Suspense>
          {!primary.project_code && (
            <Card size="small" title="整張報價單的備註（印在明細區工項下方，可多行）" styles={{ body: { padding: '8px 12px' } }}
              extra={<Button size="small" type="primary" disabled={!notesDirty} loading={saveNotes.isPending} onClick={() => saveNotes.mutate()}>儲存備註</Button>}>
              <Input.TextArea value={notes} onChange={(e) => setNotes(e.target.value)} autoSize={{ minRows: 2, maxRows: 5 }}
                placeholder="例：本案已領得使用執照，如經審視發現與法規不符需協助修改者，費用另計。" maxLength={500} showCount />
            </Card>
          )}
          {quotations.length > 1 && (
            <Card size="small" styles={{ body: { padding: '8px 12px' } }}>
              <Space wrap>
                <Text type="secondary">此案有 {quotations.length} 張報價單，切換：</Text>
                <Select
                  size="small"
                  style={{ minWidth: 260 }}
                  value={primary.id}
                  onChange={(v: number) => setSelectedId(v)}
                  options={quotations.map((q) => ({
                    value: q.id,
                    label: `${q.quotation_no || `#${q.id}`} ／ NT$${Number(q.total_price ?? 0).toLocaleString()} ／ ${q.status ?? ''}`,
                  }))}
                />
              </Space>
            </Card>
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

      {pdfPreview}
    </Space>
  );
}
