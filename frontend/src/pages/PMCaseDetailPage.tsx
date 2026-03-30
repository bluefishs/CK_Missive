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
  InfoCircleOutlined, TeamOutlined, PaperClipOutlined, BarChartOutlined, PlusOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { usePMCase, useAuthGuard } from '../hooks';
import { useClientOptions, useCaseNatureOptions } from '../hooks/business/useDropdownData';
import { vendorsApi } from '../api/vendorsApi';
import { apiClient } from '../api/client';
import { projectsApi } from '../api/projectsApi';
import { pmCasesApi } from '../api/pm/casesApi';
import { PM_CATEGORY_LABELS } from '../types/api';
import type { PMCaseUpdate } from '../types/api';
import { ROUTES } from '../router/types';

import { ContractCaseDetailContent } from './ContractCaseDetailPage';
import { DetailPageLayout } from '../components/common/DetailPage/DetailPageLayout';
import { createTabItem, getTagColor } from '../components/common/DetailPage/utils';

const MilestonesGanttTab = lazy(() => import('./pmCase/MilestonesGanttTab'));
const PMStaffTab = lazy(() => import('./pmCase/StaffTab'));
const QuotationRecordsTab = lazy(() => import('./pmCase/QuotationRecordsTab'));

// 承攬狀態：是否承作 → 是=已承攬, 否=未承攬, 其他=評估中
const STATUS_OPTIONS = [
  { value: 'planning', label: '評估中', color: 'default' },
  { value: 'contracted', label: '已承攬', color: 'blue' },
  { value: 'completed', label: '已結案', color: 'success' },
  { value: 'closed', label: '未得標', color: 'error' },
];

const CATEGORY_OPTIONS = Object.entries(PM_CATEGORY_LABELS).map(([k, v]) => ({ value: k, label: v }));

export const PMCaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { hasPermission } = useAuthGuard();
  const { message } = App.useApp();
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
    } catch { message.error('建立失敗'); }
  };

  // ── Inline 編輯 ──
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    if (pmCase) {
      form.setFieldsValue({
        ...pmCase,
        contract_amount: pmCase.contract_amount ? Number(pmCase.contract_amount) : null,
        start_date: pmCase.start_date ? dayjs(pmCase.start_date) : null,
        end_date: pmCase.end_date ? dayjs(pmCase.end_date) : null,
      });
    }
  }, [pmCase, isEditing, form, clients]);

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
      await pmCasesApi.update(pmCase.id, payload);
      // invalidate 所有 pm-cases 查詢 (key prefix match: 列表 + detail 全部刷新)
      await queryClient.invalidateQueries({ queryKey: ['pm-cases'] });
      message.success('儲存成功');
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
  const canWrite = hasPermission('projects:write');

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
        {canWrite && (
          <Button type="primary" icon={<EditOutlined />} onClick={() => setIsEditing(true)}>編輯</Button>
        )}
        {canWrite && !pmCase?.project_code && pmCase?.status === 'contracted' && (
          <Popconfirm
            title="確認成案？"
            description="將自動產生成案編號、建立承攬案件與 ERP 報價連結"
            okText="確認成案" cancelText="取消"
            onConfirm={async () => {
              try {
                const resp = await apiClient.post<{ success: boolean; data: { project_code: string } }>(
                  '/pm/cases/promote', { case_code: pmCase!.case_code }
                );
                message.success(`成案成功，成案編號: ${resp.data.project_code}`);
                queryClient.invalidateQueries({ queryKey: ['pm-cases'] });
              } catch { message.error('成案失敗'); }
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
                navigate(ROUTES.PM_CASES);
              } catch { message.error('刪除失敗'); }
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
            <Select options={[
              { value: 'planning', label: '評估中' },
              { value: 'contracted', label: '已承攬' },
              { value: 'completed', label: '已結案' },
              { value: 'closed', label: '未得標' },
            ]} />
          </Form.Item>
          <Form.Item label="成案編號"><Input value={pmCase.project_code ?? '未成案'} disabled /></Form.Item>
          <Form.Item name="notes" label="備註" style={{ gridColumn: 'span 2' }}><Input.TextArea rows={2} /></Form.Item>
        </div>
      </Form>
    ) : (
      <Descriptions bordered column={{ xs: 1, sm: 2 }} size="small">
        <Descriptions.Item label="年度">{pmCase.year ? `${pmCase.year} 年` : '-'}</Descriptions.Item>
        <Descriptions.Item label="案號">{pmCase.case_code}</Descriptions.Item>
        <Descriptions.Item label="專案名稱">{pmCase.case_name}</Descriptions.Item>
        <Descriptions.Item label="委託單位">{pmCase.client_name || clients.find(c => c.id === pmCase.client_vendor_id)?.vendor_name || (clientsLoading ? '載入中...' : '-')}</Descriptions.Item>
        <Descriptions.Item label="計畫類別">{pmCase.category ? (PM_CATEGORY_LABELS[pmCase.category] ?? pmCase.category) : '-'}</Descriptions.Item>
        <Descriptions.Item label="作業性質">{pmCase.case_nature ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="報價金額">{pmCase.contract_amount ? `NT$${pmCase.contract_amount.toLocaleString()}` : '-'}</Descriptions.Item>
        <Descriptions.Item label="作業地點" span={2}>{pmCase.location ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="承攬狀態">
          <Tag color={getTagColor(pmCase.status, STATUS_OPTIONS)}>
            {STATUS_OPTIONS.find(o => o.value === pmCase.status)?.label ?? '評估中'}
          </Tag>
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
    createTabItem('quotations', { icon: <PaperClipOutlined />, text: '報價紀錄' }, (
      <Suspense fallback={<Spin />}><QuotationRecordsTab caseCode={pmCase.case_code} isEditing={isEditing} /></Suspense>
    )),
    createTabItem('milestones', { icon: <BarChartOutlined />, text: '里程碑/甘特圖' }, (
      <Suspense fallback={<Spin />}><MilestonesGanttTab pmCaseId={pmCase.id} /></Suspense>
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
