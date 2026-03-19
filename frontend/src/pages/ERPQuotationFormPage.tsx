/**
 * ERP 報價新增/編輯表單頁面
 */
import React from 'react';
import { Card, Form, Input, InputNumber, Select, Button, Typography, message, Space } from 'antd';
import { ArrowLeftOutlined, SaveOutlined, ThunderboltOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useNavigate, useParams } from 'react-router-dom';
import { useERPQuotation, useCreateERPQuotation, useUpdateERPQuotation } from '../hooks';
import { ERP_QUOTATION_STATUS_LABELS, ERP_CATEGORY_CODES } from '../types/erp';
import type { ERPQuotationCreate } from '../types/erp';
import { erpQuotationsApi } from '../api/erp';
import { ROUTES } from '../router/types';

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
      navigate(ROUTES.ERP_QUOTATIONS);
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
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(ROUTES.ERP_QUOTATIONS)}>返回</Button>
        <Title level={4} style={{ margin: 0 }}>{isEdit ? '編輯報價' : '新增報價'}</Title>
      </div>

      <Card>
        <Form form={form} layout="vertical" onFinish={handleSubmit} style={{ maxWidth: 800 }}>
          <Space style={{ display: 'flex', gap: 16 }} align="start">
            <Form.Item name="case_code" label="案號" style={{ flex: 1 }} tooltip="格式: CK{年度}_FN_{類別}_{流水號}，例如 CK2025_FN_01_001" extra="留空可自動產生">
              <Input
                placeholder="例: CK2025_FN_01_001"
                addonAfter={
                  !isEdit && (
                    <Button
                      type="link"
                      size="small"
                      icon={<ThunderboltOutlined />}
                      loading={generating}
                      onClick={handleGenerateCode}
                      style={{ padding: 0, height: 'auto' }}
                    >
                      產生
                    </Button>
                  )
                }
              />
            </Form.Item>
            <Form.Item name="case_name" label="案名" style={{ flex: 2 }}>
              <Input placeholder="案名" />
            </Form.Item>
          </Space>

          <Space style={{ display: 'flex', gap: 16 }} align="start">
            <Form.Item name="year" label="年度" style={{ flex: 1 }}>
              <InputNumber placeholder="民國年" style={{ width: '100%' }} />
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
