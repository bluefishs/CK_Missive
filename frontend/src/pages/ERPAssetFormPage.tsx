/**
 * ERP 資產新增/編輯表單頁面
 *
 * 偵測 :id 參數區分新增 vs 編輯模式
 *
 * @version 1.0.0
 */
import React from 'react';
import {
  Card, Form, Input, InputNumber, Select, DatePicker, Button,
  Typography, Space, App,
} from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useNavigate, useParams } from 'react-router-dom';
import dayjs from 'dayjs';
import { useAssetDetail, useCreateAsset, useUpdateAsset } from '../hooks';
import { ROUTES } from '../router/types';

const { Title } = Typography;
const { TextArea } = Input;

// --- Constants (aligned with ERPAssetListPage) ---

const CATEGORY_LABELS: Record<string, string> = {
  equipment: '設備',
  vehicle: '車輛',
  instrument: '儀器',
  furniture: '家具',
  other: '其他',
};

const CATEGORY_OPTIONS = Object.entries(CATEGORY_LABELS).map(([value, label]) => ({
  value,
  label,
}));

const STATUS_LABELS: Record<string, string> = {
  in_use: '使用中',
  maintenance: '維修中',
  idle: '閒置',
  disposed: '已報廢',
  lost: '遺失',
};

const STATUS_OPTIONS = Object.entries(STATUS_LABELS).map(([value, label]) => ({
  value,
  label,
}));

const ERPAssetFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const isEdit = !!id;
  const [form] = Form.useForm();

  const { data: existingAsset, isLoading } = useAssetDetail(isEdit ? Number(id) : null);
  const createMutation = useCreateAsset();
  const updateMutation = useUpdateAsset();

  // Populate form on edit
  React.useEffect(() => {
    if (existingAsset && isEdit) {
      form.setFieldsValue({
        ...existingAsset,
        purchase_date: existingAsset.purchase_date
          ? dayjs(existingAsset.purchase_date)
          : undefined,
        purchase_amount: existingAsset.purchase_amount
          ? Number(existingAsset.purchase_amount)
          : undefined,
        depreciation_rate: existingAsset.depreciation_rate
          ? Number(existingAsset.depreciation_rate)
          : undefined,
      });
    }
  }, [existingAsset, isEdit, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();

      const payload = {
        ...values,
        purchase_date: values.purchase_date
          ? values.purchase_date.format('YYYY-MM-DD')
          : undefined,
      };

      if (isEdit) {
        await updateMutation.mutateAsync({ id: Number(id), ...payload });
        message.success('資產更新成功');
      } else {
        await createMutation.mutateAsync(payload);
        message.success('資產建立成功');
      }
      navigate(ROUTES.ERP_ASSETS);
    } catch {
      // validation or mutation error handled by antd / global error handler
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <ResponsiveContent>
      <Card
        loading={isEdit && isLoading}
        title={
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              type="text"
              onClick={() => navigate(ROUTES.ERP_ASSETS)}
            />
            <Title level={4} style={{ margin: 0 }}>
              {isEdit ? '編輯資產' : '新增資產'}
            </Title>
          </Space>
        }
        extra={
          <Space>
            <Button onClick={() => navigate(ROUTES.ERP_ASSETS)}>取消</Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              loading={isSaving}
              onClick={handleSubmit}
            >
              {isEdit ? '更新' : '建立'}
            </Button>
          </Space>
        }
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ category: 'equipment', status: 'in_use', depreciation_rate: 0 }}
          style={{ maxWidth: 800 }}
        >
          <Form.Item
            name="asset_code"
            label="資產編號"
            rules={[{ required: true, message: '請輸入資產編號' }]}
          >
            <Input placeholder="例: EQ-2026-001" disabled={isEdit} />
          </Form.Item>

          <Form.Item
            name="name"
            label="資產名稱"
            rules={[{ required: true, message: '請輸入資產名稱' }]}
          >
            <Input placeholder="例: ThinkPad X1 Carbon" />
          </Form.Item>

          <Form.Item name="category" label="類別">
            <Select options={CATEGORY_OPTIONS} placeholder="請選擇類別" />
          </Form.Item>

          <Form.Item name="brand" label="品牌">
            <Input placeholder="例: Lenovo" />
          </Form.Item>

          <Form.Item name="asset_model" label="型號">
            <Input placeholder="例: X1C Gen 11" />
          </Form.Item>

          <Form.Item name="serial_number" label="序號">
            <Input placeholder="例: SN12345678" />
          </Form.Item>

          <Form.Item name="purchase_date" label="購入日期">
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="purchase_amount" label="購入金額">
            <InputNumber
              style={{ width: '100%' }}
              min={0}
              prefix="NT$"
              formatter={(v) => `${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={(v) => Number(v!.replace(/,/g, '')) as unknown as 0}
            />
          </Form.Item>

          <Form.Item name="depreciation_rate" label="年折舊率">
            <InputNumber style={{ width: '100%' }} min={0} max={100} suffix="%" />
          </Form.Item>

          <Form.Item name="status" label="狀態">
            <Select options={STATUS_OPTIONS} placeholder="請選擇狀態" />
          </Form.Item>

          <Form.Item name="location" label="存放位置">
            <Input placeholder="例: 桃園辦公室 3F" />
          </Form.Item>

          <Form.Item name="custodian" label="保管人">
            <Input placeholder="例: 王大明" />
          </Form.Item>

          <Form.Item name="case_code" label="所屬案件">
            <Input placeholder="案件代碼" />
          </Form.Item>

          <Form.Item name="expense_invoice_id" label="關聯發票 ID">
            <InputNumber style={{ width: '100%' }} min={1} placeholder="關聯發票 ID" />
          </Form.Item>

          <Form.Item name="notes" label="備註">
            <TextArea rows={3} placeholder="備註說明" />
          </Form.Item>
        </Form>
      </Card>
    </ResponsiveContent>
  );
};

export default ERPAssetFormPage;
