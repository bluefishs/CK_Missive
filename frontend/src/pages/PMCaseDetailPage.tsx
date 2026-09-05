/**
 * 邀標/報價詳情頁面 — 統一 DetailPageLayout + inline 編輯
 *
 * 與 documents、contract-cases 共用佈局/標頭/Tab/編輯模式。
 * 編輯：inline Form（非跳轉頁面），儲存/取消按鈕切換。
 *
 * @version 7.0.0 — inline 編輯 + 統一模板
 */
import { Suspense, lazy, useState, useEffect } from 'react';
import {
  Button, Spin, Descriptions, Tag, Typography, Popconfirm, App,
  Form, Input, Select, InputNumber, Divider, Space,
} from 'antd';
import {
  EditOutlined, DeleteOutlined, RocketOutlined, SaveOutlined, CloseOutlined,
  InfoCircleOutlined, TeamOutlined, BarChartOutlined, PlusOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { usePMCase, useAuthGuard } from '../hooks';
import { useClientOptions, useCaseNatureOptions } from '../hooks/business/useDropdownData';
import { vendorsApi } from '../api/vendorsApi';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { projectsApi } from '../api/projectsApi';
import { pmCasesApi } from '../api/pm/casesApi';
import { PM_CATEGORY_LABELS } from '../types/api';
import { PM_CASE_STATUS_LABELS, PM_CASE_STATUS_COLORS } from '../types/pm';
import type { PMCaseStatus } from '../types/pm';
import type { PMCaseUpdate } from '../types/api';
import { ROUTES } from '../router/types';

import { ContractCaseDetailContent } from './ContractCaseDetailPage';
import { DetailPageLayout } from '../components/common/DetailPage/DetailPageLayout';
import { createTabItem, getTagColor } from '../components/common/DetailPage/utils';
import { ExpenseQRButton } from '../components/common/ExpenseQRCode';
import { getErrorMessage } from '../utils/apiErrorParser';

const MilestonesGanttTab = lazy(() => import('./pmCase/MilestonesGanttTab'));
const PMStaffTab = lazy(() => import('./pmCase/StaffTab'));
const QuotationRecordsTab = lazy(() => import('./pmCase/QuotationRecordsTab'));
const ExpensesTab = lazy(() => import('./pmCase/ExpensesTab'));

// 承攬狀態：是否承作 → 是=已承攬, 否=未承攬, 其他=評估中
//
// 2026-08-10：改為由 types/pm.ts 的詞彙推導，不再手寫第二份。
// 原本這裡少了 `in_progress`（成案成功後由後端寫入），於是那個值被 fallback
// 顯示成「評估中」—— 使用者改成「已承攬」、成案其實成功了，畫面卻像沒反應。
const STATUS_OPTIONS = (Object.keys(PM_CASE_STATUS_LABELS) as PMCaseStatus[]).map((value) => ({
  value,
  label: PM_CASE_STATUS_LABELS[value],
  color: PM_CASE_STATUS_COLORS[value],
}));

const CATEGORY_OPTIONS = Object.entries(PM_CATEGORY_LABELS).map(([k, v]) => ({ value: k, label: v }));

export const PMCaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuthGuard();
  const { message } = App.useApp();
  const notifyError = (t: string) => { void message.error(t); };
  const queryClient = useQueryClient();
  const pmCaseId = id ? parseInt(id, 10) : null;

  const { data: pmCase, isLoading: pmLoading } = usePMCase(pmCaseId);
  const { clients, isLoading: clientsLoading } = useClientOptions();
  const { caseNatureOptions } = useCaseNatureOptions();
  const [newClientName, setNewClientName] = useState('');
  const handleAddClient = async () => {
    if (!newClientName.trim()) return;
    try {
      const created = await vendorsApi.createVendor({ vendor_name: newClientName.trim(), vendor_type: 'client' });
      message.success(`委託單位「${newClientName}」已建立`);
      setNewClientName('');
      queryClient.invalidateQueries({ queryKey: ['clients-dropdown'] });
      form.setFieldsValue({ client_vendor_id: created.id });
    } catch (e) { message.error(getErrorMessage(e, '建立失敗'), 8); }
  };

  // ── Inline 編輯 ──
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  // 表單只在「進入編輯模式」時灌入一次。
  //
  // 2026-08-10：原本的相依是 [pmCase, isEditing, form, clients] —— `clients` 是另一支
  // useQuery 的結果，refetch（視窗重新聚焦、快取過期、invalidate）就會回傳**新的陣列參考**，
  // 於是這個 effect 重跑、`setFieldsValue` 把使用者**正在編輯的整份表單重設回資料庫的值**。
  //
  // 症狀是「改了沒反應」：owner 把承攬狀態選成「已承攬」後按儲存，畫面顯示「儲存成功」
  // 但值沒變。後端 log 證實請求有送出且含 status —— 送的就是被重設回去的舊值。
  // 這不限於承攬狀態，**這一頁的每個欄位都可能被靜靜還原**，而且完全不報錯。
  //
  // 讀取模式渲染的是 Descriptions 不是 Form，所以「進入編輯時灌一次」已足夠；
  // 換一筆案件（id 變）也要重灌，故保留 pmCase?.id。
  useEffect(() => {
    if (!pmCase || !isEditing) return;
    form.setFieldsValue({
      ...pmCase,
      contract_amount: pmCase.contract_amount ? Number(pmCase.contract_amount) : null,
      start_date: pmCase.start_date ? dayjs(pmCase.start_date) : null,
      end_date: pmCase.end_date ? dayjs(pmCase.end_date) : null,
    });
    // 刻意不把 pmCase 物件本身放進相依 —— 放了就會在背景 refetch 時
    // 重設使用者正在編輯的內容，那正是本次要修的缺陷。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEditing, pmCase?.id]);

  const handleSave = async () => {
    if (!pmCase) return;
    try {
      setSaving(true);
      const values = await form.validateFields();
      // 同步 client_name 冗餘欄位
      const matchedClient = clients.find(c => c.id === values.client_vendor_id);
      const payload: PMCaseUpdate = {
        case_name: values.case_name,
        category: values.category,
        case_nature: values.case_nature,
        client_vendor_id: values.client_vendor_id,
        client_name: matchedClient?.vendor_name ?? pmCase.client_name,
        contract_amount: values.contract_amount != null ? Number(values.contract_amount) : undefined,
        status: values.status,
        location: values.location,
        notes: values.notes,
      };
      const resp = await pmCasesApi.updateWithMessage(pmCase.id, payload);
      // invalidate 所有 pm-cases 查詢 (key prefix match: 列表 + detail 全部刷新)
      await queryClient.invalidateQueries({ queryKey: ['pm-cases'] });
      // 2026-08-29（M1）：後端把「自動成案未完成」寫在 message 裡 ——
      // 硬編「儲存成功」會把它蓋掉，使用者以為流程走完了（08-27 在
      // /promote 按鈕修掉的同一件事，編輯路徑上還在）。
      if (resp.message && (resp.message.includes('未完成') || resp.message.includes('非預期錯誤'))) {
        message.warning(resp.message, 10);
      } else {
        message.success(resp.message || '儲存成功', resp.message?.includes('自動成案') ? 6 : 3);
      }
      setIsEditing(false);
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      console.error('[PM Save Error]', err);
      message.error(`儲存失敗: ${errMsg.slice(0, 100)}`);
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    if (pmCase) {
      form.setFieldsValue({
        ...pmCase,
        start_date: pmCase.start_date ? dayjs(pmCase.start_date) : null,
        end_date: pmCase.end_date ? dayjs(pmCase.end_date) : null,
      });
    }
  };

  // Find matching contract_project
  // 2026-09-04 owner：「/pm/cases/579 已有報價單但又可新增報價，邏輯不合理」——
  // 一案一張（版次在報價單分頁切換）；已有報價單就不再給表頭的「新增報價」，入口只剩分頁。
  const { data: quotationCountData } = useQuery({
    queryKey: ['erp-quotations', 'by-case', pmCase?.case_code, 'count'],
    queryFn: () => apiClient.post<{ pagination?: { total?: number }; items?: unknown[] }>(
      API_ENDPOINTS.ERP.QUOTATIONS_LIST, { case_code: pmCase!.case_code, page: 1, limit: 1, include_unawarded: true },
    ),
    enabled: !!pmCase?.case_code,
  });
  const quotationCount = quotationCountData?.pagination?.total ?? quotationCountData?.items?.length ?? 0;
  const [creatingQuotation, setCreatingQuotation] = useState(false);

  const { data: matchedProject, isLoading: matchLoading } = useQuery({
    queryKey: ['contract-project-by-code', pmCase?.case_code],
    queryFn: async () => {
      const result = await projectsApi.getProjects({ search: pmCase!.case_code, limit: 5 });
      return result.items?.find(p => p.project_code === pmCase!.case_code || p.case_code === pmCase!.case_code) ?? null;
    },
    enabled: !!pmCase?.case_code,
  });

  // ── Route A ──
  if (!pmLoading && !matchLoading && matchedProject?.id) {
    return <ContractCaseDetailContent projectId={matchedProject.id} backRoute={ROUTES.PM_CASES} />;
  }

  if (!pmCase && !pmLoading) {
    return <DetailPageLayout header={{ title: '案件不存在', backPath: ROUTES.PM_CASES }} tabs={[]} hasData={false} />;
  }

  // ── Route B: PM-only view ──
  const statusTag = STATUS_OPTIONS.find(o => o.value === pmCase?.status);
  // 2026-08-27：原本用 `projects:write` 守著，而那個名字**不存在於任何地方**
  //   （沒有角色擁有、兩份 SSOT 都沒有）⇒ 只有 superuser 看得到這些按鈕，
  //   admin 與業務同仁都看不到。
  //
  //   ⚠️ 改成 `projects:edit` **不會放寬任何 API 存取** ——
  //   這一頁對應的後端端點全部只有 `require_auth`（實測：quotations 5 支、
  //   pm/cases 1 支，零個 require_admin／require_permission）
  //   ⇒ 任何登入者本來就打得到那些 API。前端的守衛只是在隱藏入口，
  //   而它隱藏的對象包含本來就有權限的人。
  //
  //   為什麼是 `projects:edit`：它是最接近的**既有**權限（admin／staff／ops 擁有），
  //   而報價單與 PM 案件在資料模型上都掛在承攬案件之下（case_code 橋接）。
  //   「新增」動作刻意用同一個守衛而不是 `projects:create`（admin 專屬）——
  //   因為後端沒有做這個區分，前端多做一層會再製造一次「前後端不一致」。
  //
  //   ⚠️ 這是**過渡對齊**，不是最終答案。正解是 `quotations:*` / `pm:*` 自己的
  //   權限詞彙，那需要 owner 決定（A23 後續）。在那之前，這個對齊讓畫面
  //   與後端說同一件事。
  const canWrite = hasPermission('projects:edit');

  // 委辦招標（`01`）的報價單顯示規則變過兩次，都來自 owner：
  //   2026-08-27「委辦招標無須有報價單 tab」→ 按鈕與分頁都排除 01
  //   2026-08-28「委辦案件（即使無報價）仍呈現報價單」→ 取消排除
  // 現在按鈕與分頁對所有類別一致顯示；輸出文件時後端會對 01 自動加註
  // 「本案為委辦招標案，依招標文件所列項目辦理」（quotation_document.py）。

  const headerConfig = {
    title: pmCase?.case_name ?? '載入中...',
    subtitle: pmCase?.case_code,
    icon: <RocketOutlined />,
    backPath: ROUTES.PM_CASES,
    backText: '返回列表',
    tags: [
      ...(statusTag ? [{ text: statusTag.label, color: statusTag.color }] : []),
      ...(pmCase?.project_code ? [{ text: `成案: ${pmCase.project_code}`, color: 'success' }] : []),
    ],
    extra: isEditing ? (
      <>
        <Button icon={<CloseOutlined />} onClick={handleCancel}>取消</Button>
        <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>儲存</Button>
      </>
    ) : (
      <>
        {pmCase?.case_code && (
          <ExpenseQRButton caseCode={pmCase.case_code} caseName={pmCase.case_name} />
        )}
        {/* 2026-08-20 owner：「尚未看到新增報價單機制」
            「新增報價單應建構在 pm/cases（新增報價），目前為何在 erp/quotations/152?tab=info？」

            邀標案件是報價單的起點，但這一頁一直沒有通往報價單的入口 ——
            從案件出發的人得自己記住案號、切到 ERP 模組、再打一次。

            2026-08-28 owner 更新：委辦招標案件也呈現報價單（分頁已不再隱藏），
            按鈕同步放開 —— 分頁的空狀態叫人「用上方新增報價建立」，
            按鈕卻不存在，會把「刻意不給」與「壞了」混在一起。 */}
        {canWrite && pmCase?.case_code && quotationCount === 0 && (
          <Button
            icon={<FileTextOutlined />}
            loading={creatingQuotation}
            onClick={async () => {
              // 2026-09-04 owner「須同步整合 pm/cases/:id?tab=quotations 的填報機制（避免異質同工）」：
              // 從案件出發不再經過建立頁——直接建一張 draft，落到報價單分頁，明細／備註／抬頭都在那一份編輯器。
              setCreatingQuotation(true);
              try {
                await apiClient.post(API_ENDPOINTS.ERP.QUOTATIONS_CREATE, {
                  case_code: pmCase.case_code!, case_name: pmCase.case_name ?? '', year: pmCase.year ?? new Date().getFullYear(),
                });
                await queryClient.invalidateQueries({ queryKey: ['erp-quotations'] });
                navigate(`${ROUTES.PM_CASE_DETAIL.replace(':id', String(pmCase.id))}?tab=quotations`);
              } catch (e) {
                notifyError(getErrorMessage(e, '建立報價單失敗'));
              } finally {
                setCreatingQuotation(false);
              }
            }}
          >新增報價</Button>
        )}
        {/* 2026-09-04 owner「編輯鈕功能定位」：這顆只管「案件資訊」分頁的欄位；報價單分頁的明細／備註／抬頭
            各自有儲存鈕、不需要它。標題寫清楚範圍，避免在報價單分頁以為要先按它。 */}
        {canWrite && (
          <Button type="primary" icon={<EditOutlined />} onClick={() => setIsEditing(true)} title="編輯案件資訊分頁的欄位（案名、委託單位、金額、日期…）；報價單分頁的內容直接在分頁內儲存">編輯案件資訊</Button>
        )}
        {canWrite && !pmCase?.project_code && pmCase?.status === 'contracted' && (
          <Popconfirm
            title="確認成案？"
            description="將自動產生成案編號、建立承攬案件與 ERP 報價連結"
            okText="確認成案" cancelText="取消"
            onConfirm={async () => {
              try {
                const resp = await apiClient.post<{ success: boolean; data: { project_code: string } }>(
                  API_ENDPOINTS.PM.CASES_PROMOTE, { case_code: pmCase!.case_code }
                );
                message.success(`成案成功，成案編號: ${resp.data.project_code}`);
                // `pm-cases` 已經涵蓋詳情（真實 key 是 `['pm-cases','detail',id]`，
                // invalidate 是**前綴逐元素比對**）。
                // ⚠️ 我先前多加了一行 `['pm-case', id]` —— 那個 key 不存在，
                //    `queryKey_drift_audit` 當場把 dead invalidate 從 0 抓成 1。
                queryClient.invalidateQueries({ queryKey: ['pm-cases'] });
              } catch (e) {
                // 2026-08-27 owner：「承攬狀態已承攬，為何有『確認成案』按鈕，且無法正常執行」。
                //
                // 實測 `/pm/cases/promote` 對這個案子回 400，而**後端寫得很完整**：
                //   「同名承攬案件已存在：CK2026_01_01_008（…）。這件工作看起來已經建過案 ——
                //     若要沿用，請直接把 PM 案件的成案編號指向它；
                //     若確實是不同的兩案，請把名稱或年度改成能分辨的內容再成案。」
                //
                // 而原本是 `catch { message.error('成案失敗') }` —— **裸 catch 把整段丟掉**，
                // 使用者只看到四個字，於是「按了沒反應」與「有具體原因但你看不到」
                // 在畫面上長得一模一樣。後端做對了事，前端把它扔了。
                message.error(getErrorMessage(e, '成案失敗'), 10);
              }
            }}
          >
            <Button type="primary" style={{ background: '#52c41a', borderColor: '#52c41a' }} icon={<RocketOutlined />}>確認成案</Button>
          </Popconfirm>
        )}
        {canWrite && (
          <Popconfirm
            title="確定要刪除此案件嗎？"
            description="刪除後將無法復原"
            okText="確定刪除" cancelText="取消"
            okButtonProps={{ danger: true }}
            onConfirm={async () => {
              try {
                await pmCasesApi.delete(pmCase!.id);
                message.success('案件已刪除');
                queryClient.invalidateQueries({ queryKey: ['pm-cases'], refetchType: 'all' });
                navigate(ROUTES.PM_CASES);
              } catch (e) {
                const msg = e instanceof Error ? e.message : '刪除失敗';
                message.error(msg.includes('關聯') ? '此案件有關聯資料，請先解除關聯' : `刪除失敗: ${msg}`);
              }
            }}
          >
            <Button danger icon={<DeleteOutlined />}>刪除</Button>
          </Popconfirm>
        )}
      </>
    ),
  };

  // ── 案件資訊 Tab：view / edit 雙模式 ──
  // 欄位順序：年度、案號、專案名稱、委託單位、作業類別、報價金額、作業地點、承攬狀態、成案編號、備註
  const infoTabContent = pmCase ? (
    isEditing ? (
      <Form form={form} layout="vertical" size="small">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 16px' }}>
          <Form.Item label="年度"><Input value={pmCase.year ? `${pmCase.year} 年` : '-'} disabled /></Form.Item>
          <Form.Item label="案號"><Input value={pmCase.case_code} disabled /></Form.Item>
          <Form.Item name="case_name" label="專案名稱" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item name="client_vendor_id" label="委託單位">
            <Select showSearch allowClear placeholder="選擇或新增委託單位" optionFilterProp="label"
              loading={clientsLoading}
              options={(() => {
                const opts = clients.map(c => ({ value: c.id, label: c.vendor_name }));
                // clients 未載入時用 pmCase.client_name 作為暫時 option，避免顯示 raw ID
                if (opts.length === 0 && pmCase?.client_vendor_id && pmCase?.client_name) {
                  return [{ value: pmCase.client_vendor_id, label: pmCase.client_name }];
                }
                return opts;
              })()}
              dropdownRender={(menu) => (
                <>
                  {menu}
                  <Divider style={{ margin: '8px 0' }} />
                  <Space style={{ padding: '0 8px 4px' }}>
                    <Input placeholder="新委託單位" value={newClientName}
                      onChange={(e) => setNewClientName(e.target.value)}
                      onKeyDown={(e) => e.stopPropagation()} size="small" />
                    <Button type="link" icon={<PlusOutlined />} onClick={handleAddClient} size="small">新增</Button>
                  </Space>
                </>
              )}
            />
          </Form.Item>
          <Form.Item name="category" label="計畫類別"><Select options={CATEGORY_OPTIONS} allowClear /></Form.Item>
          <Form.Item name="case_nature" label="作業性質">
            <Select allowClear placeholder="選擇作業性質" options={caseNatureOptions} />
          </Form.Item>
          <Form.Item name="contract_amount" label="報價金額"><InputNumber style={{ width: '100%' }} min={0} /></Form.Item>
          <Form.Item name="location" label="作業地點" style={{ gridColumn: 'span 2' }}><Input /></Form.Item>
          <Form.Item name="status" label="承攬狀態">
            {/* 與上方 STATUS_OPTIONS 共用同一份詞彙 —— 原本這裡是第三份手寫清單，
                同樣少了 in_progress，於是成案後回來編輯會看到空白選項。 */}
            <Select options={STATUS_OPTIONS.map(({ value, label }) => ({ value, label }))} />
          </Form.Item>
          <Form.Item label="成案編號"><Input value={pmCase.project_code ?? '未成案'} disabled /></Form.Item>
          <Form.Item name="notes" label="備註" style={{ gridColumn: 'span 2' }}><Input.TextArea rows={2} /></Form.Item>
        </div>
      </Form>
    ) : (
      <Descriptions bordered column={{ xs: 1, sm: 2 }} size="small">
        <Descriptions.Item label="年度">{pmCase.year ? `${pmCase.year} 年` : '-'}</Descriptions.Item>
        {/* 2026-09-05 owner：以成案案號為主；未成案才只有建案案號 */}
        {pmCase.project_code && <Descriptions.Item label="成案編號">{pmCase.project_code}</Descriptions.Item>}
        <Descriptions.Item label="建案案號">{pmCase.case_code}</Descriptions.Item>
        <Descriptions.Item label="專案名稱">{pmCase.case_name}</Descriptions.Item>
        <Descriptions.Item label="委託單位">{pmCase.client_name || clients.find(c => c.id === pmCase.client_vendor_id)?.vendor_name || (clientsLoading ? '載入中...' : '-')}</Descriptions.Item>
        <Descriptions.Item label="計畫類別">{pmCase.category ? (PM_CATEGORY_LABELS[pmCase.category] ?? pmCase.category) : '-'}</Descriptions.Item>
        <Descriptions.Item label="作業性質">{pmCase.case_nature ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="報價金額">{pmCase.contract_amount ? `NT$${pmCase.contract_amount.toLocaleString()}` : '-'}</Descriptions.Item>
        <Descriptions.Item label="作業地點" span={2}>{pmCase.location ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="承攬狀態">
          {/* 2026-08-10：詞彙外的值**不再謊報成「評估中」**。
              案件 244 的 status 是 `in_progress`（那是里程碑的狀態詞彙，不是案件的），
              原本的 `?? '評估中'` 讓它顯示為評估中 —— 畫面說的與資料庫存的是兩件事，
              而使用者看到「評估中」就不會知道這筆資料其實是壞的。 */}
          {STATUS_OPTIONS.some(o => o.value === pmCase.status) ? (
            <Tag color={getTagColor(pmCase.status, STATUS_OPTIONS)}>
              {STATUS_OPTIONS.find(o => o.value === pmCase.status)!.label}
            </Tag>
          ) : (
            <Tag color="error">未知狀態：{pmCase.status ?? '(空)'}</Tag>
          )}
        </Descriptions.Item>
        <Descriptions.Item label="成案編號">{pmCase.project_code ?? <Typography.Text type="secondary">未成案</Typography.Text>}</Descriptions.Item>
        <Descriptions.Item label="備註" span={2}>{pmCase.notes ?? '-'}</Descriptions.Item>
      </Descriptions>
    )
  ) : null;

  const tabs = pmCase ? [
    createTabItem('info', { icon: <InfoCircleOutlined />, text: '案件資訊' }, infoTabContent),
    createTabItem('staff', { icon: <TeamOutlined />, text: '承辦同仁' }, (
      <Suspense fallback={<Spin />}><PMStaffTab caseCode={pmCase.case_code} /></Suspense>
    )),
    // 2026-08-26：分頁名由「報價紀錄」改為「報價單」——
    // 它現在是**線上明細編輯器**（嵌入 QuotationItemsTab），不是一份紀錄清單。
    //
    // 2026-08-28 owner 更新指示：委辦招標案件**也要呈現**報價單分頁
    // （即使通常沒有報價，也不隱藏）—— 取代 08-27「01 不掛分頁」的規則。
    createTabItem('quotations', { icon: <FileTextOutlined />, text: '報價單' }, (
      <Suspense fallback={<Spin />}>
        <QuotationRecordsTab
          caseCode={pmCase.case_code}
          caseName={pmCase.case_name}
          isEditing={isEditing}
        />
      </Suspense>
    )),
    createTabItem('milestones', { icon: <BarChartOutlined />, text: '里程碑/甘特圖' }, (
      <Suspense fallback={<Spin />}><MilestonesGanttTab pmCaseId={pmCase.id} /></Suspense>
    )),
    createTabItem('expenses', { icon: <FileTextOutlined />, text: '費用核銷' }, (
      <Suspense fallback={<Spin />}><ExpensesTab caseCode={pmCase.case_code} /></Suspense>
    )),
  ] : [];

  return (
    <DetailPageLayout
      header={headerConfig}
      tabs={tabs}
      loading={pmLoading || matchLoading}
      hasData={!!pmCase}
    />
  );
};

export default PMCaseDetailPage;
