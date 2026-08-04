/**
 * 承攬案件「協力廠商」關聯填報頁（新增／編輯共用）
 *
 * 路由：/contract-cases/:caseId/vendors/create
 *      /contract-cases/:caseId/vendors/:vendorId/edit
 *
 * 取代 `VendorsTab` 內的新增 Modal 與列內就地編輯／移除（owner 指示逐一辦理）。
 * 「下拉內即時新增廠商」是專案既有規約，原樣保留在這一頁。
 */
import React, { useEffect, useState } from 'react';
import {
  Form, Select, InputNumber, DatePicker, Input, Button, Popconfirm, Space, Divider, Row, Col, App,
} from 'antd';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';

import { ROUTES } from '../router/types';
import { useResponsive } from '../hooks';
import { ErpFormPageShell } from '../components/erp/ErpFormPageShell';
import { projectVendorsApi } from '../api/projectVendorsApi';
import { vendorsApi } from '../api/vendorsApi';
import type { PaginatedResponse } from '../api/types';
import type { Vendor } from '../types/api';
import { VENDOR_ROLE_OPTIONS } from './contractCase/tabs/constants';
import { parseCurrencyInput } from '../utils/format';

const ContractCaseVendorFormPage: React.FC = () => {
  const { caseId, vendorId } = useParams<{ caseId: string; vendorId?: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const { isMobile } = useResponsive();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const projectId = Number(caseId);
  const vid = vendorId ? Number(vendorId) : null;
  const isEdit = vid !== null;
  const [submitting, setSubmitting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [newVendorName, setNewVendorName] = useState('');

  const { data: assocResp, isLoading } = useQuery({
    queryKey: ['project-vendors', projectId],
    queryFn: () => projectVendorsApi.getProjectVendors(projectId),
    enabled: Number.isFinite(projectId),
  });

  // 依型別定義回傳是 { project_id, project_name, associations[], total }
  const assocList = React.useMemo(() => assocResp?.associations ?? [], [assocResp]);

  const record = React.useMemo(
    () => (isEdit ? assocList.find((v) => v.vendor_id === vid) : undefined),
    [assocList, vid, isEdit],
  );

  // 廠商清單沿用詳情頁本來就在用的那支與查詢鍵
  const { data: vendorOptions = [], refetch: reloadVendors } = useQuery({
    queryKey: ['contract-case-vendor-options'],
    queryFn: async () => {
      const response = await vendorsApi.getVendors({ vendor_type: 'subcontractor', limit: 100 }) as PaginatedResponse<Vendor>;
      return (response.items || []).map((v) => ({
        value: v.id,
        label: `${v.vendor_name}${v.vendor_code ? ` (${v.vendor_code})` : ''}`,
      }));
    },
    staleTime: 10 * 60 * 1000,
  });

  useEffect(() => {
    if (record) {
      form.setFieldsValue({
        vendor_id: record.vendor_id,
        role: record.role,
        contract_amount: record.contract_amount,
        start_date: record.start_date ? dayjs(record.start_date) : undefined,
        end_date: record.end_date ? dayjs(record.end_date) : undefined,
      });
    }
  }, [record, form]);

  const backToCase = () =>
    navigate(`${ROUTES.CONTRACT_CASE_DETAIL.replace(':id', String(projectId))}?tab=vendors`);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['project-vendors', projectId] });
    queryClient.invalidateQueries({ queryKey: ['contract-case', projectId] });
  };

  // 下拉內即時新增廠商：專案既有規約（Select 找不到選項時 dropdownRender 提供新增）
  const handleAddNewVendor = async () => {
    if (!newVendorName.trim()) return;
    try {
      const created = await vendorsApi.createVendor({
        vendor_name: newVendorName.trim(), vendor_type: 'subcontractor',
      });
      message.success(`廠商「${newVendorName}」已建立`);
      setNewVendorName('');
      await reloadVendors();
      form.setFieldsValue({ vendor_id: created.id });
    } catch {
      message.error('建立失敗');
    }
  };

  const handleSubmit = async () => {
    let values;
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    const payload = {
      role: values.role,
      contract_amount: values.contract_amount,
      start_date: values.start_date ? dayjs(values.start_date).format('YYYY-MM-DD') : undefined,
      end_date: values.end_date ? dayjs(values.end_date).format('YYYY-MM-DD') : undefined,
    };
    setSubmitting(true);
    try {
      if (isEdit && vid) {
        await projectVendorsApi.updateVendor(projectId, vid, payload);
        message.success('更新成功');
      } else {
        await projectVendorsApi.addVendor({
          project_id: projectId, vendor_id: values.vendor_id, ...payload,
        });
        message.success('新增協力廠商成功');
      }
      invalidate();
      backToCase();
    } catch {
      message.error(isEdit ? '更新失敗' : '新增失敗');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!vid) return;
    setDeleting(true);
    try {
      await projectVendorsApi.deleteVendor(projectId, vid);
      message.success('已移除');
      invalidate();
      backToCase();
    } catch {
      message.error('移除失敗');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <ErpFormPageShell
      title={isEdit ? '編輯協力廠商' : '新增協力廠商'}
      backText="返回案件"
      onBack={backToCase}
      onSubmit={handleSubmit}
      submitting={submitting}
      isEdit={isEdit}
      submitText={isEdit ? '儲存變更' : '新增廠商'}
      loading={isEdit && isLoading}
      notFoundMessage={isEdit && !isLoading && !record ? '找不到這筆協力廠商關聯（可能已被移除）。' : undefined}
      headerExtra={isEdit ? (
        <Popconfirm title="確定要移除此廠商？" okText="移除" cancelText="取消" onConfirm={handleDelete}>
          <Button danger icon={<DeleteOutlined />} loading={deleting}>移除</Button>
        </Popconfirm>
      ) : undefined}
    >
      <Form form={form} layout="vertical" size={isMobile ? 'large' : 'middle'} preserve={false}>
        <Form.Item name="vendor_id" label="廠商" rules={[{ required: true, message: '請選擇廠商' }]}>
          <Select
            placeholder="選擇或新增廠商"
            showSearch
            optionFilterProp="label"
            disabled={isEdit}
            options={vendorOptions}
            dropdownRender={isEdit ? undefined : (menu) => (
              <>
                {menu}
                <Divider style={{ margin: '8px 0' }} />
                <Space style={{ padding: '0 8px 4px' }}>
                  <Input
                    placeholder="輸入新廠商名稱"
                    value={newVendorName}
                    onChange={(e) => setNewVendorName(e.target.value)}
                    onKeyDown={(e) => e.stopPropagation()}
                    size="small"
                  />
                  <Button type="link" icon={<PlusOutlined />} onClick={handleAddNewVendor} size="small">
                    新增
                  </Button>
                </Space>
              </>
            )}
          />
        </Form.Item>
        <Form.Item name="role" label="業務類別" rules={[{ required: true, message: '請選擇業務類別' }]}>
          <Select placeholder="請選擇業務類別" options={VENDOR_ROLE_OPTIONS} />
        </Form.Item>
        <Form.Item name="contract_amount" label="合約金額">
          <InputNumber
            style={{ width: '100%' }}
            placeholder="請輸入合約金額"
            inputMode="decimal"
            formatter={(value) => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
            parser={parseCurrencyInput}
          />
        </Form.Item>
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item name="start_date" label="合作開始日期">
              <DatePicker style={{ width: '100%' }} inputReadOnly={isMobile} />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="end_date" label="合作結束日期">
              <DatePicker style={{ width: '100%' }} inputReadOnly={isMobile} />
            </Form.Item>
          </Col>
        </Row>
      </Form>
    </ErpFormPageShell>
  );
};

export default ContractCaseVendorFormPage;
