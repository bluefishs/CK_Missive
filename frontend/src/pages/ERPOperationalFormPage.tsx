/**
 * ERP 營運帳目表單頁面 (新增/編輯共用)
 *
 * 路由: /erp/operational/create 或 /erp/operational/:id/edit
 */
import React, { useEffect } from 'react';
import { Card, Form, Input, InputNumber, Select, Button, Space, App, Typography } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useParams, useNavigate } from 'react-router-dom';
import { ROUTES } from '../router/types';
import {
  useOperationalAccountDetail,
  useCreateOperationalAccount,
  useUpdateOperationalAccount,
} from '../hooks';
import { OPERATIONAL_CATEGORIES } from '../types/erp';
import type { OperationalAccountCreate, OperationalAccountUpdate } from '../types/erp';

const { Title } = Typography;

const currentYear = new Date().getFullYear();
const YEAR_OPTIONS = Array.from({ length: 10 }, (_, i) => {
  const y = currentYear - i + 1;
  return { value: y, label: String(y) };
});

const CATEGORY_OPTIONS = Object.entries(OPERATIONAL_CATEGORIES).map(
  ([value, label]) => ({ value, label })
);

const ERPOperationalFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();

  const isEdit = !!id;
  const accountId = id ? Number(id) : null;
  const { data: account, isLoading } = useOperationalAccountDetail(accountId);
  const createMutation = useCreateOperationalAccount();
  const updateMutation = useUpdateOperationalAccount();

  useEffect(() => {
    if (account && isEdit) {
      form.setFieldsValue({
        name: account.name,
        category: account.category,
        fiscal_year: account.fiscal_year,
        budget_limit: account.budget_limit,
        department: account.department,
        notes: account.notes,
      });
    }
  }, [account, isEdit, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      if (isEdit && accountId) {
        const payload: { id: number } & OperationalAccountUpdate = {
          id: accountId,
          ...values,
        };
        await updateMutation.mutateAsync(payload);
        message.success('帳目已更新');
        navigate(`${ROUTES.ERP_OPERATIONAL}/${accountId}`);
      } else {
        const payload: OperationalAccountCreate = values;
        await createMutation.mutateAsync(payload);
        message.success('帳目已建立');
        navigate(ROUTES.ERP_OPERATIONAL);
      }
    } catch {
      // validation or API error
    }
  };

  const isPending = createMutation.isPending || updateMutation.isPending;

  return (
    <ResponsiveContent maxWidth={800} padding="medium">
      <Card loading={isEdit && isLoading}>
        <Space orientation="vertical" size="large" style={{ width: '100%' }}>
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate(isEdit ? `${ROUTES.ERP_OPERATIONAL}/${accountId}` : ROUTES.ERP_OPERATIONAL)}
            >
              返回
            </Button>
            <Title level={4} style={{ margin: 0 }}>
              {isEdit ? '編輯營運帳目' : '新增營運帳目'}
            </Title>
          </Space>

          <Form
            form={form}
            layout="vertical"
            initialValues={{ fiscal_year: currentYear }}
          >
            <Form.Item
              name="name"
              label="帳目名稱"
              rules={[{ required: true, message: '請輸入帳目名稱' }]}
            >
              <Input placeholder="例：辦公室租金" />
            </Form.Item>

            <Form.Item
              name="category"
              label="類別"
              rules={[{ required: true, message: '請選擇類別' }]}
            >
              <Select placeholder="選擇類別" options={CATEGORY_OPTIONS} />
            </Form.Item>

            <Form.Item
              name="fiscal_year"
              label="會計年度"
              rules={[{ required: true, message: '請選擇年度' }]}
            >
              <Select placeholder="選擇年度" options={YEAR_OPTIONS} />
            </Form.Item>

            <Form.Item
              name="budget_limit"
              label="預算上限"
              rules={[{ required: true, message: '請輸入預算金額' }]}
            >
              <InputNumber
                style={{ width: '100%' }}
                min={0}
                prefix="NT$"
                placeholder="0"
              />
            </Form.Item>

            <Form.Item name="department" label="部門">
              <Input placeholder="例：管理部" />
            </Form.Item>

            <Form.Item name="notes" label="備註">
              <Input.TextArea rows={3} placeholder="備註說明..." />
            </Form.Item>

            <Form.Item>
              <Space>
                <Button
                  type="primary"
                  icon={<SaveOutlined />}
                  onClick={handleSubmit}
                  loading={isPending}
                >
                  {isEdit ? '更新' : '建立'}
                </Button>
                <Button onClick={() => navigate(ROUTES.ERP_OPERATIONAL)}>
                  取消
                </Button>
              </Space>
            </Form.Item>
          </Form>
        </Space>
      </Card>
    </ResponsiveContent>
  );
};

export default ERPOperationalFormPage;
