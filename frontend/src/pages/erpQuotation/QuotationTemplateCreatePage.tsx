/**
 * 新增報價 — 範本式一頁建單（2026-08-28 owner：「erp/quotations/create 仍是 mis 非 xls 樣板」）
 *
 * 版面依正式報價單範本（`backend/app/templates/quotation_template.xlsx`）的結構：
 * 案首（案名／委託單位／年度）→ 逐項明細（工作內容／單位／數量／單價／複價）
 * → 小計／營業稅 5%／總計 → 備註。**不是** MIS 欄位表單。
 *
 * 兩個入口共用本頁：
 *  · 列表頁「新增報價」（無參數）＝快速建單 —— 送出時**先走授權路徑建 PM 案件**
 *    （委託單位寫進 pm_cases.client_name，輸出文件的客戶欄才有來源；
 *    entity_creation_ssot：PMCase 只能經 /pm/cases/create 建構），
 *    再建報價、再存明細，最後導向該案件的報價單分頁（唯一輸出入口）。
 *  · PM 案件詳情頁「新增報價」（帶 case_code）＝案件已存在，只建報價＋明細。
 *
 * 財務成本欄位（外包費／人事費等）**刻意不在本頁** —— 那是 ERP 財務視角，
 * 編輯路徑仍在 `/erp/quotations/:id/edit`（ERPQuotationFormPage）。
 */
import React from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Card, Table, Button, Input, InputNumber, Space, Typography, App, Row, Col, Form, Modal,
  Select, Divider,
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, SaveOutlined, ArrowLeftOutlined, FileTextOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { apiClient } from '../../api/client';
import { ERP_ENDPOINTS, PM_ENDPOINTS, API_ENDPOINTS } from '../../api/endpoints';
import { erpQuotationsApi as quotationsApi } from '../../api/erp/quotationsApi';
import { ROUTES } from '../../router/types';
import { ResponsiveContent } from '@ck-shared/ui-components';
import type { SuccessResponse } from '../../api/types';
import type { PMCase } from '../../types/pm';
import { useClientOptions, useUsersDropdown } from '../../hooks/business/useDropdownData';
import { vendorsApi } from '../../api/vendorsApi';
import { authService } from '../../services/authService';
import { useQuery, useQueryClient } from '@tanstack/react-query';

const { Text, Title } = Typography;

const money = (n: number) => `NT$ ${Math.round(n).toLocaleString()}`;

/** 範本明細列（本頁為建立期的本地列，尚無 quotation_id） */
interface DraftItemRow {
  key: string;
  /** 項次（自填，如 1.1；空＝自動） */
  item_no?: string;
  item_name: string;
  spec?: string;
  unit?: string;
  qty: number;
  unit_price: number;
  /** 工項備註（正式文件 G 欄） */
  notes?: string;
  /** 複價覆寫（undefined＝數量×單價） */
  amount?: number;
}

/**
 * 正式範本的明細容量 —— **不在這裡寫死**。
 *
 * 2026-08-29：後端把上限從 5 提到 10，而這裡曾有一份手抄的 `= 5` 沒跟著改，
 * 於是第 6 項起畫面警告「僅容 5 項，超出的需先合併」——
 * **叫使用者去手動合併後端其實輸出得出來的工項**。tsc 檢查不出一個過期的字面值。
 *
 * ⇒ 改由 `/erp/quotations/template-meta` 取（來源＝ITEM_LAST_ROW - ITEM_FIRST_ROW + 1）。
 * 下面這個只是**取值失敗前的保守起始值**：取偏小只會多提醒一次，
 * 取偏大會讓人填到輸出才被 400 擋。
 */
const CAPACITY_FALLBACK = 5;

let _keySeq = 0;
const newRow = (): DraftItemRow => ({
  key: `draft-${++_keySeq}`, item_name: '', spec: '', unit: '式', qty: 1, unit_price: 0, notes: '',
});

const QuotationTemplateCreatePage: React.FC = () => {
  const navigate = useNavigate();
  const { message, modal } = App.useApp();
  const [searchParams] = useSearchParams();
  const qc = useQueryClient();
  const { clients } = useClientOptions();
  const { users: staffUsers, isError: staffLoadError } = useUsersDropdown();

  // owner 2026-08-29：「線上建單可對應登入帳號使用者」——
  // 預設帶登入者。多數情況建單的人就是承辦的人，讓他**改**比讓他**填**省一步；
  // 而預設值錯了看得見（名字就在畫面上），預設空白錯了看不見（就是那 122 張的來源）。
  const { data: me } = useQuery({
    queryKey: ['current-user-for-quotation-staff'],
    queryFn: () => authService.getCurrentUser(),
    staleTime: 30 * 60 * 1000,
  });

  // 入口 2（PM 案件詳情頁）帶進來的既有案件
  const presetCaseCode = searchParams.get('case_code') || undefined;
  const presetPmCaseId = searchParams.get('pm_case_id') || undefined;

  const [caseName, setCaseName] = React.useState(searchParams.get('case_name') ?? '');
  // 2026-08-29：委託單位改用**主檔 Select**（原本是自由文字，只送
  // `client_name` 不送 `client_vendor_id`）—— 那會讓這個入口持續產生
  // 「只有文字沒有連結」的案件，而全庫已有 145 筆是這個狀態。
  // 與 PMCaseFormPage 同一套控件（Select + dropdownRender inline 新增）。
  const [clientVendorId, setClientVendorId] = React.useState<number | undefined>();
  const [newClientName, setNewClientName] = React.useState('');
  const [year, setYear] = React.useState<number>(
    Number(searchParams.get('year')) || new Date().getFullYear(),
  );
  const [notes, setNotes] = React.useState('');
  // 承辦同仁 —— 2026-08-29 實查：257 張報價單有 **122 張**全庫查不到任何指派
  // 紀錄，正式報價單的「服務人員」（範本 E12/E13）因此空白。
  // ⚠️ 那不是查詢寫錯：取料的 JOIN 早在 08-21 就同時吃 project_id 與 case_code，
  // 改 JOIN 只救得回 7 張。**122 張是資料從來沒有被建立** ——
  // 因為在此之前，建單這條路徑上根本沒有地方可以指派。
  const [staffUserId, setStaffUserId] = React.useState<number | undefined>();
  // 只在使用者還沒動過這一欄時帶入預設 —— 否則清空選擇會被自動填回去
  const [staffTouched, setStaffTouched] = React.useState(false);
  const [rows, setRows] = React.useState<DraftItemRow[]>([newRow(), newRow(), newRow()]);
  const [saving, setSaving] = React.useState(false);
  const [tplUrl, setTplUrl] = React.useState<string | null>(null);
  const [tplLoading, setTplLoading] = React.useState(false);

  // 容量取自後端（見 CAPACITY_FALLBACK 的說明）
  const { data: tplMeta } = useQuery({
    queryKey: ['quotation-template-meta'],
    queryFn: () => quotationsApi.getTemplateMeta(),
    staleTime: 60 * 60 * 1000,  // 版面容量只有換範本時才變
  });
  const capacity = tplMeta?.item_capacity ?? CAPACITY_FALLBACK;

  // owner 2026-08-29：「xls 樣本報價單無法呈現嗎」——可以：
  // 空白範本經後端同一條 LibreOffice 鏈轉 PDF，建單前就能看到正式版面
  // （輸出 PDF 的預覽要先有單，這顆不用）。
  const showTemplate = async () => {
    setTplLoading(true);
    try {
      const res = await apiClient.post(
        ERP_ENDPOINTS.QUOTATION_TEMPLATE_PREVIEW, {}, { responseType: 'blob' },
      );
      const raw = res as unknown as { data?: Blob } | Blob;
      const blob = raw instanceof Blob ? raw : (raw.data as Blob);
      setTplUrl(URL.createObjectURL(blob));
    } catch {
      message.error('範本預覽產生失敗，請稍後再試');
    } finally {
      setTplLoading(false);
    }
  };

  // 下拉找不到時就地新增（與 PMCaseFormPage 同一套流程）
  const handleAddClient = async () => {
    if (!newClientName.trim()) return;
    try {
      const created = await vendorsApi.createVendor({
        vendor_name: newClientName.trim(), vendor_type: 'client',
      });
      message.success(`委託單位「${newClientName}」已建立`);
      setNewClientName('');
      qc.invalidateQueries({ queryKey: ['clients-dropdown'] });
      setClientVendorId(created.id);
    } catch {
      message.error('建立失敗');
    }
  };

  React.useEffect(() => {
    if (staffTouched || staffUserId !== undefined || !me?.id) return;
    // 登入者必須真的在可指派清單裡才帶入 —— 不在清單裡代表他不是可指派的對象，
    // 硬塞會送出一個後端接不到的 user_id
    if (staffUsers.some(u => u.id === me.id)) setStaffUserId(me.id);
  }, [me, staffUsers, staffTouched, staffUserId]);

  const patch = (key: string, part: Partial<DraftItemRow>) =>
    setRows(rs => rs.map(r => (r.key === key ? { ...r, ...part } : r)));

  const filled = rows.filter(r => r.item_name.trim());
  const subtotal = filled.reduce((s, r) => s + (r.amount ?? r.qty * r.unit_price), 0);
  const tax = Math.round(subtotal * 0.05);
  const total = subtotal + tax;

  const addRow = () => {
    if (rows.length >= capacity) {
      // 不擋（資料層存得下），但要在**填的當下**說，不是輸出那一步才 400
      message.warning(
        `正式文件範本目前僅容 ${capacity} 項，超出的項目輸出時需先合併`,
      );
    }
    setRows(rs => [...rs, newRow()]);
  };

  const handleSubmit = async () => {
    if (!caseName.trim()) { message.error('請填寫案名'); return; }
    if (!presetCaseCode && !clientVendorId) {
      message.error('請選擇委託單位 —— 輸出的報價單需要客戶抬頭，且案件要能關聯到單位主檔');
      return;
    }
    // 2026-09-04：從案件頁進來時先看這個案已有幾張報價單 —— owner 測試時一個案建出三張 draft
    // （每次「新增報價」都是新的一張，而分頁又看不到未成案的那幾張）。不擋，但要先說。
    if (presetCaseCode) {
      try {
        const existing = await apiClient.post<{ items?: Array<{ id: number; quotation_no?: string | null; total_price?: number | string | null }> }>(
          ERP_ENDPOINTS.QUOTATIONS_LIST, { case_code: presetCaseCode, page: 1, limit: 10, include_unawarded: true },
        );
        const n = existing?.items?.length ?? 0;
        if (n > 0) {
          const go = await new Promise<boolean>((resolve) => {
            modal.confirm({
              title: `此案已有 ${n} 張報價單`,
              content: `${existing.items!.map((q) => q.quotation_no || `#${q.id}`).join('、')}。再建一張會成為新的版次；若只是要編輯明細或輸出，請回案件頁的「報價單」分頁。`,
              okText: '仍要新建一張', cancelText: '回報價單分頁',
              onOk: () => resolve(true), onCancel: () => resolve(false),
            });
          });
          if (!go) {
            navigate(presetPmCaseId ? `${ROUTES.PM_CASE_DETAIL.replace(':id', presetPmCaseId)}?tab=quotations` : ROUTES.ERP_QUOTATIONS);
            return;
          }
        }
      } catch { /* 查不到就照常建，不因防呆本身失敗而擋住建單 */ }
    }
    setSaving(true);
    try {
      // ① 案件：入口 1 需先建案（授權路徑），入口 2 已有
      let caseCode = presetCaseCode;
      let pmCaseId = presetPmCaseId;
      if (!caseCode) {
        const res = await apiClient.post<SuccessResponse<PMCase>>(PM_ENDPOINTS.CASES_CREATE, {
          case_name: caseName.trim(),
          // 送 FK（案件關聯的單一事實），client_name 由後端從 FK 推導
          client_vendor_id: clientVendorId,
          year,
          category: '02', // 承攬報價 —— 本頁就是報價流程的入口
          status: 'planning',
        });
        const created = res.data!;
        caseCode = created.case_code ?? undefined;
        pmCaseId = String(created.id);
        if (!caseCode) throw new Error('建案成功但未取得建案案號');
      }

      // ② 報價單
      const quotation = await quotationsApi.create({
        case_code: caseCode,
        case_name: caseName.trim(),
        year,
        notes: notes.trim() || undefined,
      });

      // ③ 明細（有填才存；total_price 由後端小計回寫，不另填第二份事實）
      if (filled.length > 0) {
        await apiClient.post(ERP_ENDPOINTS.QUOTATION_ITEMS_REPLACE, {
          quotation_id: quotation.id,
          items: filled.map((r, i) => ({
            item_no: r.item_no?.trim() || undefined, item_name: r.item_name.trim(), spec: r.spec?.trim() || undefined,
            unit: r.unit?.trim() || undefined, qty: r.qty, unit_price: r.unit_price,
            sort_order: i, notes: r.notes?.trim() || undefined, amount: r.amount,
          })),
        });
      }

      // ④ 承辦同仁指派（選填）
      //
      // 刻意**不放進上面的 try 主線**：報價單與明細已經寫進去了，
      // 這一步失敗時整個 catch 會顯示「建立失敗」，而使用者會以為
      // 什麼都沒建成、回頭再建一次 —— 那會產生重複的報價單。
      // 失敗就明講「單建好了、指派沒成功、去哪裡補」。
      let staffWarn = '';
      if (staffUserId) {
        try {
          await apiClient.post(API_ENDPOINTS.PROJECT_STAFF.CREATE, {
            case_code: caseCode,
            user_id: staffUserId,
            role: '主辦',
            is_primary: true,   // 報價單只印一個服務人員，取 is_primary 優先
          });
        } catch {
          staffWarn = '（承辦同仁指派失敗，請於案件詳情頁的人員分頁補上）';
        }
      }

      message.success(`報價單已建立（${caseCode}）${staffWarn}`);
      // ④ 直達唯一的輸出入口 —— 該案件的報價單分頁（明細編輯器＋輸出 PDF 都在那裡）
      if (pmCaseId) {
        navigate(`${ROUTES.PM_CASE_DETAIL.replace(':id', pmCaseId)}?tab=quotations`);
      } else {
        navigate(ROUTES.ERP_QUOTATION_DETAIL.replace(':id', String(quotation.id)));
      }
    } catch (e) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      message.error(detail || (e as Error).message || '建立失敗');
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    {
      title: '項次', width: 72, align: 'center' as const,
      render: (_: unknown, r: DraftItemRow, i: number) => (
        <Input value={r.item_no} placeholder={`${i + 1}`} onChange={e => patch(r.key, { item_no: e.target.value })} />
      ),
    },
    {
      title: '工作內容', dataIndex: 'item_name',
      render: (_: unknown, r: DraftItemRow) => (
        <Input value={r.item_name} placeholder="例：地上物查估作業"
          onChange={e => patch(r.key, { item_name: e.target.value })} />
      ),
    },
    {
      title: '規格', dataIndex: 'spec', width: 140,
      render: (_: unknown, r: DraftItemRow) => (
        <Input value={r.spec} onChange={e => patch(r.key, { spec: e.target.value })} />
      ),
    },
    {
      title: '單位', dataIndex: 'unit', width: 80,
      render: (_: unknown, r: DraftItemRow) => (
        <Input value={r.unit} onChange={e => patch(r.key, { unit: e.target.value })} />
      ),
    },
    {
      title: '數量', dataIndex: 'qty', width: 90,
      render: (_: unknown, r: DraftItemRow) => (
        <InputNumber min={0} value={r.qty} style={{ width: '100%' }}
          onChange={v => patch(r.key, { qty: Number(v ?? 0) })} />
      ),
    },
    {
      title: '單價', dataIndex: 'unit_price', width: 120,
      render: (_: unknown, r: DraftItemRow) => (
        <InputNumber min={0} value={r.unit_price} style={{ width: '100%' }}
          formatter={v => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
          onChange={v => patch(r.key, { unit_price: Number(v ?? 0) })} />
      ),
    },
    {
      title: '複價', width: 120, align: 'right' as const,
      render: (_: unknown, r: DraftItemRow) => (
        <InputNumber min={0} value={r.amount ?? r.qty * r.unit_price} style={{ width: '100%' }}
          formatter={v => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
          onChange={v => patch(r.key, { amount: v === null || v === undefined ? undefined : Number(v) })} />
      ),
    },
    {
      title: '備註', dataIndex: 'notes', width: 150,
      render: (_: unknown, r: DraftItemRow) => (
        <Input value={r.notes} placeholder="選填" onChange={e => patch(r.key, { notes: e.target.value })} />
      ),
    },
    {
      title: '', width: 44,
      render: (_: unknown, r: DraftItemRow) => (
        <Button type="text" danger icon={<DeleteOutlined />} size="small"
          onClick={() => setRows(rs => rs.filter(x => x.key !== r.key))} />
      ),
    },
  ];

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(-1)}>返回</Button>
            <Title level={4} style={{ margin: 0 }}>
              <FileTextOutlined style={{ marginRight: 8 }} />新增報價單
            </Title>
          </Space>
          <Button icon={<EyeOutlined />} loading={tplLoading} onClick={showTemplate}>
            檢視 XLS 範本樣式
          </Button>
        </Space>

        <Modal
          title="報價單範本樣式（輸出時即為此版面）"
          open={!!tplUrl}
          onCancel={() => { if (tplUrl) URL.revokeObjectURL(tplUrl); setTplUrl(null); }}
          footer={null}
          width="80%"
        >
          {tplUrl && (
            <iframe src={tplUrl} title="quotation-template-preview"
              style={{ width: '100%', height: '70vh', border: 'none' }} />
          )}
        </Modal>

        {/* 案首 —— 對應範本抬頭下方的案件資訊區 */}
        <Card size="small" title="案件資訊">
          <Form layout="vertical">
            <Row gutter={16}>
              <Col xs={24} md={presetCaseCode ? 16 : 10}>
                <Form.Item label="案名" required style={{ marginBottom: 8 }}>
                  <Input value={caseName} placeholder="工程／作業名稱"
                    onChange={e => setCaseName(e.target.value)} />
                </Form.Item>
              </Col>
              {!presetCaseCode && (
                <Col xs={24} md={8}>
                  <Form.Item label="委託單位（客戶抬頭）" required style={{ marginBottom: 8 }}>
                    <Select
                      showSearch allowClear
                      placeholder="選擇或新增委託單位"
                      optionFilterProp="label"
                      value={clientVendorId}
                      onChange={(v) => setClientVendorId(v)}
                      options={clients.map(c => ({ value: c.id, label: c.vendor_name }))}
                      dropdownRender={(menu) => (
                        <>
                          {menu}
                          <Divider style={{ margin: '8px 0' }} />
                          <Space style={{ padding: '0 8px 4px' }}>
                            <Input
                              placeholder="輸入新委託單位名稱"
                              value={newClientName}
                              onChange={(e) => setNewClientName(e.target.value)}
                              onKeyDown={(e) => e.stopPropagation()}
                            />
                            <Button type="text" icon={<PlusOutlined />} onClick={handleAddClient}>
                              新增
                            </Button>
                          </Space>
                        </>
                      )}
                    />
                  </Form.Item>
                </Col>
              )}
              <Col xs={24} md={5}>
                <Form.Item
                  label="承辦同仁"
                  style={{ marginBottom: 8 }}
                  // 選單載不到時要說出來 —— 空的 options 與「沒有同仁」長得一樣
                  validateStatus={staffLoadError ? 'warning' : undefined}
                  help={staffLoadError ? '同仁清單載入失敗，可稍後於案件詳情頁指派' : undefined}
                >
                  <Select
                    allowClear
                    showSearch
                    optionFilterProp="label"
                    placeholder="選填 —— 印在報價單的服務人員欄"
                    value={staffUserId}
                    onChange={(v) => { setStaffTouched(true); setStaffUserId(v); }}
                    options={staffUsers.map(u => ({
                      value: u.id,
                      label: u.full_name || u.username,
                    }))}
                  />
                </Form.Item>
              </Col>
              <Col xs={12} md={4}>
                <Form.Item label="年度" style={{ marginBottom: 8 }}>
                  <InputNumber value={year} style={{ width: '100%' }}
                    onChange={v => setYear(Number(v ?? new Date().getFullYear()))} />
                </Form.Item>
              </Col>
              {presetCaseCode && (
                <Col xs={12} md={4}>
                  <Form.Item label="建案案號" style={{ marginBottom: 8 }}>
                    <Text code>{presetCaseCode}</Text>
                  </Form.Item>
                </Col>
              )}
            </Row>
          </Form>
          {!presetCaseCode && (
            <Text type="secondary" style={{ fontSize: 12 }}>
              送出時會自動建立邀標案件並產生建案案號（CK{'{'}年{'}'}_PM_02_…），
              後續成案、附件、費用都掛在同一個案號下。
            </Text>
          )}
        </Card>

        {/* 明細 —— 對應範本第 16~20 列 */}
        <Card size="small" title="報價明細"
          extra={<Button icon={<PlusOutlined />} size="small" onClick={addRow}>新增項目</Button>}>
          <Table<DraftItemRow>
            columns={columns} dataSource={rows} rowKey="key"
            size="small" pagination={false}
            scroll={{ x: 760 }}
          />
          <Row justify="end" style={{ marginTop: 12 }}>
            <Col>
              <Space direction="vertical" size={2} style={{ textAlign: 'right' }}>
                <Text>小計：{money(subtotal)}</Text>
                <Text>營業稅 5%：{money(tax)}</Text>
                <Title level={5} style={{ margin: 0 }}>總計：{money(total)}</Title>
              </Space>
            </Col>
          </Row>
        </Card>

        <Card size="small" title="備註">
          <Input.TextArea rows={2} value={notes} placeholder="付款條件、有效期限等"
            onChange={e => setNotes(e.target.value)} />
        </Card>

        <Space>
          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSubmit}>
            建立報價單
          </Button>
          <Text type="secondary" style={{ fontSize: 12 }}>
            建立後即進入報價單分頁，可繼續編輯明細並輸出正式 XLS／PDF（自動存入本案附件）
          </Text>
        </Space>
      </Space>
    </ResponsiveContent>
  );
};

export default QuotationTemplateCreatePage;
