/**
 * ERP 報價新增/編輯表單頁面
 */
import React from 'react';
import { Card, Form, Input, InputNumber, Select, Button, Typography, message, Space } from 'antd';
import { ArrowLeftOutlined, SaveOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { useERPQuotation, useCreateERPQuotation, useUpdateERPQuotation } from '../hooks';
import { ERP_QUOTATION_STATUS_LABELS, ERP_CATEGORY_CODES } from '../types/erp';
import type { ERPQuotationCreate } from '../types/erp';
import { erpQuotationsApi } from '../api/erp';
import { ROUTES } from '../router/types';
import { toADYear } from '../utils/yearOptions';

const { Title } = Typography;

const categoryOptions = Object.entries(ERP_CATEGORY_CODES).map(([value, label]) => ({
  value,
  label: `${value} - ${label}`,
}));

export const ERPQuotationFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const isEdit = !!id;
  const [form] = Form.useForm();
  const [generating, setGenerating] = React.useState(false);

  const { data: existingQuotation, isLoading } = useERPQuotation(isEdit ? Number(id) : null);
  const createMutation = useCreateERPQuotation();
  const updateMutation = useUpdateERPQuotation();

  /**
   * 2026-07-29：由承攬案件「財務紀錄 → 建立報價並綁定此案」帶入的預填參數。
   * 存檔後 project_code 即成為兩模組的關聯鍵（cross_module_lookup 有 fallback）。
   */
  const [searchParams] = useSearchParams();
  // 從哪個 PM 案件進來的 —— 決定存檔與返回要回哪裡（見下方 onFinish 註解）
  const pmCaseId = searchParams.get('pm_case_id');
  React.useEffect(() => {
    if (isEdit) return;
    const prefill: Record<string, string | number> = {};
    const pc = searchParams.get('project_code');
    const cn = searchParams.get('case_name');
    if (pc) prefill.project_code = pc;
    if (cn) prefill.case_name = cn;
    // 2026-08-20：從邀標案件（/pm/cases）點「新增報價」帶進來的。
    // owner：「新增報價單應建構在 pm/cases，目前為何在 erp/quotations/152?tab=info？」
    // case_code 是 PM 案件與報價單之間的鍵 —— 不帶進來，使用者得自己回頭抄一次案號，
    // 抄錯就是一張掛不到案件上的報價單。
    const cc = searchParams.get('case_code');
    const yr = searchParams.get('year');
    if (cc) prefill.case_code = cc;
    if (yr && /^\d{4}$/.test(yr)) prefill.year = Number(yr);
    // 2026-07-31 L4 財務接續：若該案有來源標案，把標案預算帶進「預算上限」。
    // 原本從標案來的預算/機關/案名全部要人工重打 —— 資料明明就在系統裡。
    const bl = searchParams.get('budget_limit');
    if (bl) {
      const n = Number(String(bl).replace(/[^\d.]/g, ''));
      if (Number.isFinite(n) && n > 0) prefill.budget_limit = n;
    }
    if (Object.keys(prefill).length) form.setFieldsValue(prefill);
  }, [searchParams, isEdit, form]);

  React.useEffect(() => {
    if (existingQuotation && isEdit) {
      form.setFieldsValue({
        ...existingQuotation,
        total_price: existingQuotation.total_price ? Number(existingQuotation.total_price) : undefined,
        tax_amount: Number(existingQuotation.tax_amount),
        outsourcing_fee: Number(existingQuotation.outsourcing_fee),
        personnel_fee: Number(existingQuotation.personnel_fee),
        overhead_fee: Number(existingQuotation.overhead_fee),
        other_cost: Number(existingQuotation.other_cost),
        budget_limit: existingQuotation.budget_limit ? Number(existingQuotation.budget_limit) : undefined,
      });
    }
  }, [existingQuotation, isEdit, form]);

  const handleGenerateCode = async () => {
    const year = form.getFieldValue('year') as number | undefined;
    const category = (form.getFieldValue('erp_category') as string | undefined) ?? '01';
    if (!year) {
      message.warning('請先填寫年度');
      return;
    }
    setGenerating(true);
    try {
      const code = await erpQuotationsApi.generateCode({ year, category });
      form.setFieldValue('case_code', code);
      message.success(`已產生案號: ${code}`);
    } catch {
      message.error('案號產生失敗');
    } finally {
      setGenerating(false);
    }
  };

  const handleSubmit = async (values: Record<string, unknown>) => {
    const data: ERPQuotationCreate = {
      case_code: values.case_code as string | undefined,
      // 2026-07-29：成案編號 — 讓「先成案、後補報價」也能綁定既有承攬案件
      project_code: (values.project_code as string | undefined)?.trim() || undefined,
      case_name: values.case_name as string | undefined,
      year: values.year as number | undefined,
      total_price: values.total_price != null ? String(values.total_price) : undefined,
      tax_amount: values.tax_amount != null ? String(values.tax_amount) : undefined,
      outsourcing_fee: values.outsourcing_fee != null ? String(values.outsourcing_fee) : undefined,
      personnel_fee: values.personnel_fee != null ? String(values.personnel_fee) : undefined,
      overhead_fee: values.overhead_fee != null ? String(values.overhead_fee) : undefined,
      other_cost: values.other_cost != null ? String(values.other_cost) : undefined,
      budget_limit: values.budget_limit != null ? String(values.budget_limit) : undefined,
      status: values.status as ERPQuotationCreate['status'],
      notes: values.notes as string | undefined,
    };

    try {
      if (isEdit) {
        await updateMutation.mutateAsync({ id: Number(id), data });
        message.success('報價已更新');
      } else {
        await createMutation.mutateAsync(data);
        message.success('報價已建立');
      }
      // 2026-08-27 owner：「新增『邀標報價』不是已建構線上 xls 填報機制，為何一直無法整合」
      //
      // 這裡就是斷點。08-20 把「新增報價」加到 PM 案件頁，**入口換了、回程沒換** ——
      // 存檔後一律 `navigate(ROUTES.ERP_QUOTATIONS)`，也就是把人丟回 ERP 列表。
      // 於是流程在第一步就離開了邀標報價程序，而下一步（線上填明細）
      // **就嵌在剛剛那個 PM 案件的報價單分頁裡**，使用者卻已經被帶走了。
      // 同族：L81「換了出口沒換整條鏈」。
      //
      // 帶著來源回去，讓三段接成一條：新增報價 → 線上填明細 → 輸出。
      navigate(pmCaseId
        ? `${ROUTES.PM_CASE_DETAIL.replace(':id', pmCaseId)}?tab=quotations`
        : ROUTES.ERP_QUOTATIONS);
    } catch {
      message.error(isEdit ? '更新失敗' : '建立失敗');
    }
  };

  if (isEdit && isLoading) return null;

  const numberFormatter = (v: number | string | undefined) =>
    `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',');

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(pmCaseId
          ? `${ROUTES.PM_CASE_DETAIL.replace(':id', pmCaseId)}?tab=quotations`
          : ROUTES.ERP_QUOTATIONS)}>返回</Button>
        <Title level={4} style={{ margin: 0 }}>{isEdit ? '編輯報價' : '新增報價'}</Title>
      </div>

      <Card>
        <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ maxWidth: 800 }}>
          <Space style={{ display: 'flex', gap: 16 }} align="start">
            <Form.Item name="case_code" label="案號" style={{ flex: 1 }} tooltip="格式: CK{年度}_FN_{類別}_{流水號}，例如 CK2025_FN_01_001" extra="留空可自動產生">
              <Space.Compact style={{ width: '100%' }}>
                <Input placeholder="例: CK2025_FN_01_001" />
                {!isEdit && (
                  <Button
                    icon={<ThunderboltOutlined />}
                    loading={generating}
                    onClick={handleGenerateCode}
                  >
                    產生
                  </Button>
                )}
              </Space.Compact>
            </Form.Item>
            <Form.Item
              name="project_code"
              label="成案編號"
              style={{ flex: 1 }}
              tooltip="對應承攬案件的 project_code。填入後，該承攬案件詳情頁的「財務紀錄」分頁即可讀到本報價（適用於先成案、後補報價的案件）。"
              extra="可留空"
            >
              <Input placeholder="例: CK2026_01_01_006" allowClear />
            </Form.Item>
            <Form.Item name="case_name" label="案名" style={{ flex: 2 }}>
              <Input placeholder="案名" />
            </Form.Item>
          </Space>

          <Space style={{ display: 'flex', gap: 16 }} align="start">
            {/* 2026-08-20：placeholder 原本寫「民國年」，而全系統規範與實際資料都是西元
                （owner：「之前有標註統一西元年為主」）—— 使用者照著提示填民國並不是填錯。
                除了改提示，離開欄位時把民國值轉成西元：只改提示的話，
                習慣填民國的人還是會產生錯資料，而那個錯要等到有人用年度篩選才看得出來。 */}
            <Form.Item name="year" label="年度" style={{ flex: 1 }}
              normalize={(v) => toADYear(v as number)}
            >
              <InputNumber placeholder={`西元年，如 ${new Date().getFullYear()}`} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name="erp_category" label="報價類別" style={{ flex: 1 }}>
              <Select placeholder="選擇類別" options={categoryOptions} allowClear />
            </Form.Item>
            <Form.Item name="status" label="狀態" initialValue="draft" style={{ flex: 1 }}>
              <Select options={Object.entries(ERP_QUOTATION_STATUS_LABELS).map(([value, label]) => ({ value, label }))} />
            </Form.Item>
            <Form.Item name="total_price" label="總價 (含稅)" style={{ flex: 1 }}>
              <InputNumber placeholder="總價" style={{ width: '100%' }} formatter={numberFormatter} />
            </Form.Item>
          </Space>

          <Space style={{ display: 'flex', gap: 16 }} align="start">
            <Form.Item name="tax_amount" label="稅額" initialValue={0} style={{ flex: 1 }}>
              <InputNumber placeholder="稅額" style={{ width: '100%' }} formatter={numberFormatter} />
            </Form.Item>
            <Form.Item name="outsourcing_fee" label="外包費" initialValue={0} style={{ flex: 1 }}>
              <InputNumber placeholder="外包費" style={{ width: '100%' }} formatter={numberFormatter} />
            </Form.Item>
            <Form.Item name="personnel_fee" label="人事費" initialValue={0} style={{ flex: 1 }}>
              <InputNumber placeholder="人事費" style={{ width: '100%' }} formatter={numberFormatter} />
            </Form.Item>
          </Space>

          <Space style={{ display: 'flex', gap: 16 }} align="start">
            <Form.Item name="overhead_fee" label="管銷費" initialValue={0} style={{ flex: 1 }}>
              <InputNumber placeholder="管銷費" style={{ width: '100%' }} formatter={numberFormatter} />
            </Form.Item>
            <Form.Item name="other_cost" label="其他成本" initialValue={0} style={{ flex: 1 }}>
              <InputNumber placeholder="其他成本" style={{ width: '100%' }} formatter={numberFormatter} />
            </Form.Item>
            <Form.Item name="budget_limit" label="預算上限" style={{ flex: 1 }}>
              <InputNumber
                style={{ width: '100%' }}
                placeholder="預算上限 (選填)"
                formatter={numberFormatter}
                parser={(value) => value?.replace(/,/g, '') ?? ''}
              />
            </Form.Item>
          </Space>

          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={3} placeholder="備註" />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              icon={<SaveOutlined />}
              loading={createMutation.isPending || updateMutation.isPending}
            >
              {isEdit ? '更新' : '建立'}
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </ResponsiveContent>
  );
};

export default ERPQuotationFormPage;
