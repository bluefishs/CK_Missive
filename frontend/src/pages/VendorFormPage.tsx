/**
 * 廠商表單頁
 *
 * 共享新增/編輯表單，根據路由參數自動切換模式
 * 導航模式：編輯模式支援刪除功能
 *
 * @version 1.1.0 - 整合刪除功能 (導航模式規範)
 * @date 2026-01-23
 */

import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Form, Input, Select, Row, Col, App, Rate, Modal } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FormPageLayout } from '../components/common/FormPage';
import { vendorsApi } from '../api';
import type { VendorCreate, VendorUpdate } from '../types/api';
import { ROUTES } from '../router/types';

// 營業項目選項
const BUSINESS_TYPE_OPTIONS = [
  { value: '測量業務', label: '測量業務' },
  { value: '資訊系統', label: '資訊系統' },
  { value: '查估業務', label: '查估業務' },
  { value: '不動產估價', label: '不動產估價' },
  { value: '大地工程', label: '大地工程' },
  { value: '其他類別', label: '其他類別' },
];

export const VendorFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const isEdit = Boolean(id);
  const title = isEdit ? '編輯廠商' : '新增廠商';
  const vendorId = id ? parseInt(id, 10) : undefined;

  // 編輯模式：載入廠商資料
  const { data: vendor, isLoading } = useQuery({
    queryKey: ['vendor', vendorId],
    queryFn: async () => {
      return await vendorsApi.getVendor(vendorId!);
    },
    enabled: isEdit && !!vendorId,
  });

  // 填入表單資料
  useEffect(() => {
    if (vendor) {
      form.setFieldsValue({
        vendor_name: vendor.vendor_name,
        vendor_code: vendor.vendor_code,
        contact_person: vendor.contact_person,
        phone: vendor.phone,
        email: vendor.email,
        address: vendor.address,
        business_type: vendor.business_type,
        rating: vendor.rating,
      });
    }
  }, [vendor, form]);

  // 新增 mutation
  const createMutation = useMutation({
    mutationFn: (data: VendorCreate) => vendorsApi.createVendor(data),
    onSuccess: () => {
      message.success('廠商建立成功');
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      navigate(ROUTES.VENDORS);
    },
    onError: (error: any) => {
      message.error(error?.message || '建立失敗');
    },
  });

  // 更新 mutation
  const updateMutation = useMutation({
    mutationFn: (data: VendorUpdate) =>
      vendorsApi.updateVendor(vendorId!, data),
    onSuccess: () => {
      message.success('廠商更新成功');
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      navigate(ROUTES.VENDORS);
    },
    onError: (error: any) => {
      message.error(error?.message || '更新失敗');
    },
  });

  // 刪除 mutation (導航模式：從列表頁移至此處)
  const deleteMutation = useMutation({
    mutationFn: () => vendorsApi.deleteVendor(vendorId!),
    onSuccess: () => {
      message.success('廠商刪除成功');
      queryClient.invalidateQueries({ queryKey: ['vendors'] });
      navigate(ROUTES.VENDORS);
    },
    onError: (error: any) => {
      message.error(error?.message || '刪除失敗');
    },
  });

  // 刪除確認
  const handleDelete = () => {
    Modal.confirm({
      title: '確定要刪除此廠商？',
      icon: <ExclamationCircleOutlined />,
      content: '刪除後將無法復原，請確保沒有關聯的專案。',
      okText: '確定刪除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => deleteMutation.mutate(),
    });
  };

  // 保存處理
  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (isEdit) {
        updateMutation.mutate(values);
      } else {
        createMutation.mutate(values);
      }
    } catch {
      message.error('請檢查表單欄位');
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;

  return (
    <FormPageLayout
      title={title}
      backPath={ROUTES.VENDORS}
      onSave={handleSave}
      onDelete={isEdit ? handleDelete : undefined}
      loading={isEdit && isLoading}
      saving={isSaving}
      deleting={deleteMutation.isPending}
    >
      <Form form={form} layout="vertical" size="large">
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item
              name="vendor_name"
              label="廠商名稱"
              rules={[{ required: true, message: '請輸入廠商名稱' }]}
            >
              <Input placeholder="請輸入廠商名稱" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="vendor_code" label="廠商代碼">
              <Input placeholder="請輸入廠商代碼" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item
              name="business_type"
              label="營業項目"
              rules={[{ required: true, message: '請選擇營業項目' }]}
            >
              <Select
                placeholder="請選擇營業項目"
                options={BUSINESS_TYPE_OPTIONS}
                allowClear
              />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="rating" label="評價">
              <Rate allowHalf />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item name="contact_person" label="聯絡人">
              <Input placeholder="請輸入聯絡人姓名" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="phone" label="電話">
              <Input placeholder="請輸入聯絡電話" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="email"
          label="Email"
          rules={[{ type: 'email', message: '請輸入有效的 Email' }]}
        >
          <Input placeholder="請輸入 Email" />
        </Form.Item>

        <Form.Item name="address" label="地址">
          <Input.TextArea rows={2} placeholder="請輸入地址" />
        </Form.Item>
      </Form>
    </FormPageLayout>
  );
};

export default VendorFormPage;
