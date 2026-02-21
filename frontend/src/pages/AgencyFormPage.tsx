/**
 * 機關單位表單頁
 *
 * 共享新增/編輯表單，根據路由參數自動切換模式
 * 導航模式：編輯模式支援刪除功能
 *
 * @version 1.2.0 - 新增名稱標準化處理，避免重複資料
 * @date 2026-01-26
 */

import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Form, Input, Select, App, Modal } from 'antd';
import { ResponsiveFormRow } from '../components/common/ResponsiveFormRow';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FormPageLayout } from '../components/common/FormPage';
import { agenciesApi } from '../api';
import type { AgencyCreate, AgencyUpdate } from '../api';
import { ROUTES } from '../router/types';
import { AGENCY_CATEGORY_OPTIONS } from '../constants';

/**
 * 標準化名稱字串（與後端一致）
 * - 移除前後空白
 * - 移除全形空白
 * - 統一全形/半形括號
 * - 移除連續空白
 */
const normalizeName = (value: string | undefined | null): string | undefined => {
  if (!value) return undefined;
  return value
    .trim()
    .replace(/\u3000/g, '')        // 移除全形空白
    .replace(/（/g, '(')           // 統一全形括號
    .replace(/）/g, ')')
    .replace(/\s+/g, ' ')          // 移除連續空白
    || undefined;
};

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
      const response = await agenciesApi.getAgencies({ limit: 100 });
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
    onError: (error: Error) => {
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
    onError: (error: Error) => {
      message.error(error?.message || '更新失敗');
    },
  });

  // 刪除 mutation (導航模式：從列表頁移至此處)
  const deleteMutation = useMutation({
    mutationFn: () => agenciesApi.deleteAgency(agencyId!),
    onSuccess: () => {
      message.success('機關單位刪除成功');
      queryClient.invalidateQueries({ queryKey: ['agencies'] });
      navigate(ROUTES.AGENCIES);
    },
    onError: (error: Error) => {
      message.error(error?.message || '刪除失敗');
    },
  });

  // 刪除確認
  const handleDelete = () => {
    Modal.confirm({
      title: '確定要刪除此機關單位？',
      icon: <ExclamationCircleOutlined />,
      content: '刪除後將無法復原',
      okText: '確定刪除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => deleteMutation.mutate(),
    });
  };

  // 保存處理（含名稱標準化）
  const handleSave = async () => {
    try {
      const values = await form.validateFields();

      // 標準化名稱欄位
      const normalizedValues = {
        ...values,
        agency_name: normalizeName(values.agency_name),
        agency_short_name: normalizeName(values.agency_short_name),
      };

      if (isEdit) {
        updateMutation.mutate(normalizedValues);
      } else {
        createMutation.mutate(normalizedValues as AgencyCreate);
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
      onDelete={isEdit ? handleDelete : undefined}
      loading={isEdit && isLoading}
      saving={isSaving}
      deleting={deleteMutation.isPending}
    >
      <Form form={form} layout="vertical" size="large">
        <ResponsiveFormRow>
          <Form.Item
            name="agency_name"
            label="機關名稱"
            rules={[{ required: true, message: '請輸入機關名稱' }]}
          >
            <Input placeholder="請輸入機關全名" />
          </Form.Item>
          <Form.Item
            name="agency_short_name"
            label="機關簡稱"
            tooltip="可用於公文顯示的簡短名稱"
          >
            <Input placeholder="請輸入機關簡稱" />
          </Form.Item>
        </ResponsiveFormRow>

        <ResponsiveFormRow>
          <Form.Item name="agency_code" label="機關代碼">
            <Input placeholder="請輸入機關代碼" />
          </Form.Item>
          <Form.Item name="agency_type" label="機關類型">
            <Select
              placeholder="請選擇機關類型"
              options={[...AGENCY_CATEGORY_OPTIONS]}
              allowClear
            />
          </Form.Item>
        </ResponsiveFormRow>

        <Form.Item name="address" label="地址">
          <Input.TextArea rows={2} placeholder="請輸入地址" />
        </Form.Item>
      </Form>
    </FormPageLayout>
  );
};

export default AgencyFormPage;
