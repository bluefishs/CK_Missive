/**
 * ERP 資產新增/編輯表單頁面
 *
 * 偵測 :id 參數區分新增 vs 編輯模式
 *
 * @version 2.0.0
 */
import React, { useMemo } from 'react';
import {
  Card, Form, Input, InputNumber, Select, DatePicker, Button,
  Typography, Space, App, Upload, Image,
} from 'antd';
import { ArrowLeftOutlined, SaveOutlined, CameraOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useNavigate, useParams } from 'react-router-dom';
import dayjs from 'dayjs';
import { useAssetDetail, useCreateAsset, useUpdateAsset, useCaseCodeMap } from '../hooks';
import { useUsersDropdown } from '../hooks/business/useDropdownData';
import { ROUTES } from '../router/types';
import { ERP_ENDPOINTS } from '../api/endpoints';
import apiClient from '../api/client';

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
  const { users, isLoading: usersLoading } = useUsersDropdown();
  const { data: caseCodeMap } = useCaseCodeMap();

  // 保管人下拉選項 (存名字字串，相容現有資料)
  const custodianOptions = useMemo(
    () => users.map(u => ({
      value: u.full_name || u.username,
      label: `${u.full_name || u.username}${u.email ? ` (${u.email})` : ''}`,
    })),
    [users],
  );

  // 成案編號下拉選項
  const projectCodeOptions = useMemo(() => {
    if (!caseCodeMap) return [];
    return Object.entries(caseCodeMap).map(([caseCode, projectCode]) => ({
      value: caseCode,
      label: projectCode || caseCode,
    }));
  }, [caseCodeMap]);

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

  // 照片上傳
  const handlePhotoUpload = async (file: File) => {
    if (!isEdit) {
      message.info('請先建立資產後再上傳照片');
      return false;
    }
    const formData = new FormData();
    formData.append('asset_id', String(id));
    formData.append('file', file);
    try {
      await apiClient.postForm(ERP_ENDPOINTS.ASSETS_UPLOAD_PHOTO, formData);
      message.success('照片上傳成功');
      // Refresh asset detail
      window.location.reload();
    } catch {
      message.error('照片上傳失敗');
    }
    return false;
  };

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
  const photoUrl = existingAsset?.photo_path
    ? `/${existingAsset.photo_path}`
    : null;

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
          {/* 資產照片 */}
          {isEdit && (
            <Form.Item label="資產照片">
              <Space orientation="vertical" align="center" style={{ width: '100%' }}>
                {photoUrl ? (
                  <Image
                    src={photoUrl}
                    alt="資產照片"
                    width={200}
                    style={{ borderRadius: 8, objectFit: 'cover' }}
                    fallback="data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2YwZjBmMCIvPjx0ZXh0IHg9IjUwJSIgeT0iNTAlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBmaWxsPSIjY2NjIiBmb250LXNpemU9IjE0Ij7nhKfniYc8L3RleHQ+PC9zdmc+"
                  />
                ) : null}
                <Upload
                  accept="image/*"
                  showUploadList={false}
                  beforeUpload={(file) => handlePhotoUpload(file as File)}
                >
                  <Button icon={<CameraOutlined />}>
                    {photoUrl ? '更換照片' : '上傳照片'}
                  </Button>
                </Upload>
              </Space>
            </Form.Item>
          )}

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
            <Select
              showSearch
              allowClear
              optionFilterProp="label"
              options={custodianOptions}
              loading={usersLoading}
              placeholder="請選擇保管人"
            />
          </Form.Item>

          <Form.Item name="case_code" label="成案編號">
            <Select
              showSearch
              allowClear
              optionFilterProp="label"
              options={projectCodeOptions}
              placeholder="請選擇成案編號"
            />
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
