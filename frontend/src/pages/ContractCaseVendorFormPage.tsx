/**
 * 承攬案件「協力廠商」關聯填報頁（新增／編輯共用）
 *
 * 路由：/contract-cases/:caseId/vendors/create
 *      /contract-cases/:caseId/vendors/:vendorId/edit
 *
 * 取代 `VendorsTab` 內的新增 Modal 與列內就地編輯／移除（owner 指示逐一辦理）。
 * 「下拉內即時新增廠商」是專案既有規約，原樣保留在這一頁。
 */
import React, { useEffect, useMemo, useState } from 'react';
import {
  Form, Select, InputNumber, DatePicker, Input, Button, Popconfirm, Space, Divider, Row, Col, App,
} from 'antd';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';

import { ROUTES } from '../router/types';
import { useResponsive } from '../hooks';
import { usePermissions } from '../hooks/utility/usePermissions';
import { useSubcontractorOptions } from '../hooks/business/useDropdownData';
import { ErpFormPageShell } from '../components/erp/ErpFormPageShell';
import { projectVendorsApi } from '../api/projectVendorsApi';
import { vendorsApi } from '../api/vendorsApi';
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

  // ⚠️ 2026-08-27 —— 原本這裡自己開一支 useQuery，註解寫著
  //    「廠商清單沿用詳情頁本來就在用的那支與查詢鍵」。**key 確實沿用了，
  //    形狀沒有**：詳情頁回 `{id,name,code}`、這裡回 `{value,label}`，
  //    共用同一個 cache key ⇒ 誰先載入誰就決定內容。動線
  //    「詳情頁 → 新增協力廠商」會讓 Select 拿到 `{id,name,code}`，
  //    `value` 與 `label` 雙雙 undefined。
  //
  //    與同日修的人員下拉是同一個家族（同 key、同源、**不同形狀**）。
  //    改用既有共用 hook 回原始 `Vendor[]`，呈現形狀在這裡自己組。
  const { hasPermission } = usePermissions();
  const canCreateVendor = hasPermission('vendors:create');
  const { subcontractors, isLoading: vendorsLoading, isError: vendorsFailed } = useSubcontractorOptions();
  const vendorOptions = useMemo(
    () => subcontractors.map((v) => ({
      value: v.id,
      label: `${v.vendor_name}${v.vendor_code ? ` (${v.vendor_code})` : ''}`,
    })),
    [subcontractors],
  );

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
    // ⚠️ 原本寫 `['contract-case', projectId]` —— 那個 key 不存在（見 L39）。
    queryClient.invalidateQueries({ queryKey: ['contract-case-detail', projectId] });
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
      // 清單改由共用 hook 提供，這裡讓它重取 —— 用 invalidate 而不是本地 refetch，
      // 新建的廠商在**所有**用到這份清單的地方都會立刻出現。
      await queryClient.invalidateQueries({ queryKey: ['subcontractors-dropdown'] });
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
            // 載不到時要說出來 —— 空下拉會讓人以為「系統裡沒有協力廠商」，
            // 那與「這次沒載到」在畫面上長得一模一樣（同人員下拉的判準）
            notFoundContent={
              vendorsFailed ? '廠商清單載入失敗，請重新整理'
                : vendorsLoading ? '載入中…'
                : canCreateVendor ? '沒有可選的協力廠商'
                : '找不到這家廠商，請洽管理員建立'
            }
                // 2026-08-27：一般同仁看得到這個「新增廠商」，按下去必然 403
                // （`POST /api/vendors` 要 `vendors:create`；owner 實測 uid=7 連按三次全 403）。
                // 08-26 已立的判準：**不給一般同仁一個必然失敗的按鈕**。
                // 刻意不放寬端點權限 —— 誰能建廠商是產品決策，不是這一頁能決定的。
            dropdownRender={(isEdit || !canCreateVendor) ? undefined : (menu) => (
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
