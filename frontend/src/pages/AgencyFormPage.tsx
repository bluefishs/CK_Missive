/**
 * 機關單位表單頁
 *
 * 共享新增/編輯表單，根據路由參數自動切換模式
 *
 * @version 1.0.0
 * @date 2026-01-22
 */

import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Form, Input, Select, Row, Col, App } from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FormPageLayout } from '../components/common/FormPage';
import { agenciesApi } from '../api';
import type { AgencyCreate, AgencyUpdate } from '../api';
import { ROUTES } from '../router/types';

// 機關類型選項
const AGENCY_TYPE_OPTIONS = [
  { value: '政府機關', label: '政府機關' },
  { value: '民間企業', label: '民間企業' },
  { value: '其他單位', label: '其他單位' },
];

export const AgencyFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const isEdit = Boolean(id);
  const title = isEdit ? '編輯機關單位' : '新增機關單位';
  const agencyId = id ? parseInt(id, 10) : undefined;

  // 編輯模式：載入機關資料
  const { data: agency, isLoading } = useQuery({
    queryKey: ['agency', agencyId],
    queryFn: async () => {
      const response = await agenciesApi.getAgencies({ limit: 1000 });
      return response.items.find(a => a.id === agencyId);
    },
    enabled: isEdit && !!agencyId,
  });

  // 填入表單資料
  useEffect(() => {
    if (agency) {
      form.setFieldsValue({
        agency_name: agency.agency_name,
        agency_short_name: agency.agency_short_name,
        agency_code: agency.agency_code,
        agency_type: agency.agency_type,
        address: agency.address,
      });
    }
  }, [agency, form]);

  // 新增 mutation
  const createMutation = useMutation({
    mutationFn: (data: AgencyCreate) => agenciesApi.createAgency(data),
    onSuccess: () => {
      message.success('機關單位建立成功');
      queryClient.invalidateQueries({ queryKey: ['agencies'] });
      navigate(ROUTES.AGENCIES);
    },
    onError: (error: any) => {
      message.error(error?.message || '建立失敗');
    },
  });

  // 更新 mutation
  const updateMutation = useMutation({
    mutationFn: (data: AgencyUpdate) =>
      agenciesApi.updateAgency(agencyId!, data),
    onSuccess: () => {
      message.success('機關單位更新成功');
      queryClient.invalidateQueries({ queryKey: ['agencies'] });
      navigate(ROUTES.AGENCIES);
    },
    onError: (error: any) => {
      message.error(error?.message || '更新失敗');
    },
  });

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
      backPath={ROUTES.AGENCIES}
      onSave={handleSave}
      loading={isEdit && isLoading}
      saving={isSaving}
    >
      <Form form={form} layout="vertical" size="large">
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item
              name="agency_name"
              label="機關名稱"
              rules={[{ required: true, message: '請輸入機關名稱' }]}
            >
              <Input placeholder="請輸入機關全名" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item
              name="agency_short_name"
              label="機關簡稱"
              tooltip="可用於公文顯示的簡短名稱"
            >
              <Input placeholder="請輸入機關簡稱" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item name="agency_code" label="機關代碼">
              <Input placeholder="請輸入機關代碼" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="agency_type" label="機關類型">
              <Select
                placeholder="請選擇機關類型"
                options={AGENCY_TYPE_OPTIONS}
                allowClear
              />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="address" label="地址">
          <Input.TextArea rows={2} placeholder="請輸入地址" />
        </Form.Item>
      </Form>
    </FormPageLayout>
  );
};

export default AgencyFormPage;
