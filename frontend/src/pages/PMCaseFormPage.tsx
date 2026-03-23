/**
 * PM 案件新增/編輯表單頁面
 *
 * 根據路由參數 id 自動切換建立 / 編輯模式。
 *
 * @version 2.0.0
 */
import React, { useEffect } from 'react';
import {
  Form,
  Input,
  InputNumber,
  Select,
  DatePicker,
  Button,
  Space,
  Flex,
  Card,
  Typography,
  App,
} from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { usePMCase, useCreatePMCase, useUpdatePMCase } from '../hooks';
import { PM_CASE_STATUS_LABELS, PM_CATEGORY_LABELS } from '../types/api';
import type { PMCaseCreate, PMCaseUpdate } from '../types/api';
import { ROUTES } from '../router/types';

export const PMCaseFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const isEdit = !!id;
  const caseId = id ? parseInt(id, 10) : null;

  // usePMCase returns PMCase directly (not wrapped)
  const { data: existingCase, isLoading: loadingCase } = usePMCase(caseId);
  const createMutation = useCreatePMCase();
  const updateMutation = useUpdatePMCase();

  useEffect(() => {
    if (existingCase) {
      form.setFieldsValue({
        ...existingCase,
        start_date: existingCase.start_date ? dayjs(existingCase.start_date) : undefined,
        end_date: existingCase.end_date ? dayjs(existingCase.end_date) : undefined,
      });
    }
  }, [existingCase, form]);

  const handleSubmit = async (values: Record<string, unknown>) => {
    const payload = {
      ...values,
      start_date: values.start_date
        ? (values.start_date as dayjs.Dayjs).format('YYYY-MM-DD')
        : undefined,
      end_date: values.end_date
        ? (values.end_date as dayjs.Dayjs).format('YYYY-MM-DD')
        : undefined,
    };

    try {
      if (isEdit && caseId) {
        await updateMutation.mutateAsync({ id: caseId, data: payload as PMCaseUpdate });
        message.success('案件已更新');
      } else {
        await createMutation.mutateAsync(payload as PMCaseCreate);
        message.success('案件已建立');
      }
      navigate(ROUTES.PM_CASES);
    } catch {
      message.error(isEdit ? '更新失敗' : '建立失敗');
    }
  };

  return (
    <ResponsiveContent>
      <Flex vertical gap={8} style={{ width: '100%' }}>
        <Space>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate(ROUTES.PM_CASES)}
          >
            返回
          </Button>
          <Typography.Title level={4} style={{ margin: 0 }}>
            {isEdit ? '編輯案件' : '新增案件'}
          </Typography.Title>
        </Space>

        <Card loading={isEdit && loadingCase}>
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            initialValues={{ status: 'planning', year: 114 }}
            style={{ maxWidth: 800 }}
          >
            <Form.Item
              name="case_name"
              label="案名"
              rules={[{ required: true, message: '請輸入案名' }]}
            >
              <Input placeholder="輸入案名" />
            </Form.Item>

            <Form.Item name="case_code" label="案號">
              <Input placeholder="自動產生或手動輸入" />
            </Form.Item>

            <Space size="middle" wrap>
              <Form.Item name="year" label="年度">
                <InputNumber style={{ width: 100 }} placeholder="民國年" />
              </Form.Item>
              <Form.Item name="category" label="類別">
                <Select
                  style={{ width: 160 }}
                  allowClear
                  placeholder="選擇類別"
                  options={Object.entries(PM_CATEGORY_LABELS).map(([k, v]) => ({
                    value: k,
                    label: v,
                  }))}
                />
              </Form.Item>
              <Form.Item name="status" label="狀態">
                <Select
                  style={{ width: 120 }}
                  options={Object.entries(PM_CASE_STATUS_LABELS).map(([k, v]) => ({
                    value: k,
                    label: v,
                  }))}
                />
              </Form.Item>
            </Space>

            <Form.Item name="client_name" label="委託單位">
              <Input placeholder="委託單位名稱" />
            </Form.Item>

            <Form.Item name="contract_amount" label="合約金額">
              <InputNumber
                style={{ width: 220 }}
                placeholder="金額"
                formatter={(v) =>
                  `NT$ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
                }
              />
            </Form.Item>

            <Space size="middle">
              <Form.Item name="start_date" label="開始日期">
                <DatePicker />
              </Form.Item>
              <Form.Item name="end_date" label="結束日期">
                <DatePicker />
              </Form.Item>
            </Space>

            <Form.Item name="description" label="說明">
              <Input.TextArea rows={3} />
            </Form.Item>

            <Form.Item name="notes" label="備註">
              <Input.TextArea rows={2} />
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
      </Flex>
    </ResponsiveContent>
  );
};

export default PMCaseFormPage;
