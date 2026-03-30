/**
 * 邀標/報價 新增/編輯表單頁面
 *
 * 欄位順序與 PMCaseDetailPage 案件資訊 Tab 一致：
 * 年度、案號、專案名稱、委託單位、作業類別、報價金額、作業地點、承攬狀態、備註
 *
 * @version 3.0.0
 */
import React, { useEffect, useState } from 'react';
import {
  Form, Input, InputNumber, Select, Button, Card, Typography, App, Row, Col, Space, Divider,
} from 'antd';
import { ArrowLeftOutlined, SaveOutlined, RocketOutlined, PlusOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { usePMCase, useCreatePMCase, useUpdatePMCase } from '../hooks';
import { useClientOptions } from '../hooks/business/useDropdownData';
import { useQueryClient } from '@tanstack/react-query';
import { vendorsApi } from '../api/vendorsApi';
import { PM_CATEGORY_LABELS } from '../types/api';
import type { PMCaseCreate, PMCaseUpdate } from '../types/api';
import { ROUTES } from '../router/types';

const CATEGORY_OPTIONS = Object.entries(PM_CATEGORY_LABELS).map(([k, v]) => ({ value: k, label: v }));

const STATUS_OPTIONS = [
  { value: 'planning', label: '評估中' },
  { value: 'in_progress', label: '已承攬' },
  { value: 'completed', label: '未承攬' },
  { value: 'closed', label: '未得標' },
];

export const PMCaseFormPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const isEdit = !!id;
  const caseId = id ? parseInt(id, 10) : null;

  const { data: existingCase, isLoading: loadingCase } = usePMCase(caseId);
  const { clients } = useClientOptions();
  const qc = useQueryClient();
  const [newClientName, setNewClientName] = useState('');

  const handleAddClient = async () => {
    if (!newClientName.trim()) return;
    try {
      const created = await vendorsApi.createVendor({
        vendor_name: newClientName.trim(),
        vendor_type: 'client',
      });
      message.success(`委託單位「${newClientName}」已建立`);
      setNewClientName('');
      qc.invalidateQueries({ queryKey: ['clients-dropdown'] });
      form.setFieldsValue({ client_vendor_id: created.id });
    } catch {
      message.error('建立失敗');
    }
  };
  const createMutation = useCreatePMCase();
  const updateMutation = useUpdatePMCase();

  useEffect(() => {
    if (existingCase) {
      form.setFieldsValue(existingCase);
    }
  }, [existingCase, form]);

  const handleSubmit = async (values: Record<string, unknown>) => {
    // 同步 client_name 冗餘欄位（從 client_vendor_id 查找名稱）
    if (values.client_vendor_id) {
      const matched = clients.find(c => c.id === values.client_vendor_id);
      if (matched) values.client_name = matched.vendor_name;
    }
    try {
      if (isEdit && caseId) {
        await updateMutation.mutateAsync({ id: caseId, data: values as PMCaseUpdate });
        message.success('案件已更新');
      } else {
        await createMutation.mutateAsync(values as unknown as PMCaseCreate);
        message.success('案件已建立');
      }
      navigate(ROUTES.PM_CASES);
    } catch {
      message.error(isEdit ? '更新失敗' : '建立失敗');
    }
  };

  return (
    <ResponsiveContent>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(ROUTES.PM_CASES)}>返回</Button>
          <Typography.Title level={4} style={{ margin: 0 }}>
            <RocketOutlined style={{ marginRight: 8 }} />
            {isEdit ? '編輯邀標案件' : '新增邀標案件'}
          </Typography.Title>
        </div>

        <Card loading={isEdit && loadingCase}>
          <Form
            form={form}
            layout="vertical"
            onFinish={handleSubmit}
            initialValues={{ status: 'planning', year: 114 }}
            style={{ maxWidth: 800 }}
          >
            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item name="year" label="年度">
                  <InputNumber style={{ width: '100%' }} placeholder="民國年" />
                </Form.Item>
              </Col>
              <Col xs={24} sm={16}>
                <Form.Item name="case_code" label="案號">
                  <Input placeholder="自動產生或手動輸入" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="case_name" label="專案名稱"
              rules={[{ required: true, message: '請輸入專案名稱' }]}
            >
              <Input placeholder="輸入專案名稱" />
            </Form.Item>

            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item name="client_vendor_id" label="委託單位">
                  <Select
                    showSearch
                    allowClear
                    placeholder="選擇或新增委託單位"
                    optionFilterProp="label"
                    options={clients.map(c => ({ value: c.id, label: c.vendor_name }))}
                    dropdownRender={(menu) => (
                      <>
                        {menu}
                        <Divider style={{ margin: '8px 0' }} />
                        <Space style={{ padding: '0 8px 4px' }}>
                          <Input
                            placeholder="輸入新委託單位名稱"
                            value={newClientName}
                            onChange={(e) => setNewClientName(e.target.value)}
                            onKeyDown={(e) => e.stopPropagation()}
                            size="small"
                          />
                          <Button type="link" icon={<PlusOutlined />} onClick={handleAddClient} size="small">
                            新增
                          </Button>
                        </Space>
                      </>
                    )}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item name="category" label="計畫類別">
                  <Select allowClear placeholder="選擇類別" options={CATEGORY_OPTIONS} />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item name="case_nature" label="作業性質">
                  <Select allowClear placeholder="選擇作業性質" options={[
                    { value: '01地面測量', label: '01地面測量' },
                    { value: '02LiDAR掃描', label: '02LiDAR掃描' },
                    { value: '03UAV空拍', label: '03UAV空拍' },
                    { value: '04航空測量', label: '04航空測量' },
                    { value: '05安全檢測', label: '05安全檢測' },
                    { value: '06建物保存', label: '06建物保存' },
                    { value: '07建築線測量', label: '07建築線測量' },
                    { value: '08透地雷達', label: '08透地雷達' },
                    { value: '09資訊系統', label: '09資訊系統' },
                    { value: '10技師簽證', label: '10技師簽證' },
                    { value: '11其他類別', label: '11其他類別' },
                  ]} />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col xs={24} sm={12}>
                <Form.Item name="contract_amount" label="報價金額">
                  <InputNumber
                    style={{ width: '100%' }}
                    placeholder="金額"
                    min={0}
                    formatter={(v) => `NT$ ${v}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} sm={12}>
                <Form.Item name="location" label="作業地點">
                  <Input placeholder="作業地點" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item name="status" label="承攬狀態">
              <Select style={{ width: 200 }} options={STATUS_OPTIONS} />
            </Form.Item>

            <Form.Item name="notes" label="備註">
              <Input.TextArea rows={2} placeholder="備註說明" />
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
      </div>
    </ResponsiveContent>
  );
};

export default PMCaseFormPage;
