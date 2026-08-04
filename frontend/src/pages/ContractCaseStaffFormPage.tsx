/**
 * 承攬案件「承辦同仁」填報頁（新增／編輯共用）
 *
 * 路由：/contract-cases/:caseId/staff/create
 *      /contract-cases/:caseId/staff/:userId/edit
 *
 * 取代 `StaffTab` 內的新增 Modal 與列內就地編輯／移除（owner 指示逐一辦理）。
 *
 * 誠實記錄：量測顯示原本的彈窗在 390px 下版面是好的（374×252、零溢出、2 欄位），
 * 因此這次改動的理由**不是量到的版面缺陷**，而是規範一致 ——
 * 詳情頁 tab 只呈現、狀態變更一律在自己的頁面。取捨寫在這裡，
 * 免得日後有人以為這是為了修某個 bug。
 */
import React, { useEffect } from 'react';
import { Form, Select, App, Button, Popconfirm } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { ROUTES } from '../router/types';
import { useResponsive } from '../hooks';
import { ErpFormPageShell } from '../components/erp/ErpFormPageShell';
import { projectStaffApi } from '../api/projectStaffApi';
import { usersApi } from '../api/usersApi';
import type { PaginatedResponse } from '../api/types';
import type { User } from '../types/api';
import { STAFF_ROLE_OPTIONS } from '../constants/staffOptions';

const ContractCaseStaffFormPage: React.FC = () => {
  const { caseId, userId } = useParams<{ caseId: string; userId?: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const { isMobile } = useResponsive();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const projectId = Number(caseId);
  const uid = userId ? Number(userId) : null;
  const isEdit = uid !== null;
  const [submitting, setSubmitting] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);

  // 既有清單 API：同仁關聯沒有「取單筆」端點，用清單找出這一筆。
  // 與機關承辦不同（那支有 DETAIL），這裡先確認過回傳是陣列才這樣寫。
  const { data: staffResp, isLoading } = useQuery({
    queryKey: ['project-staff', projectId],
    queryFn: () => projectStaffApi.getProjectStaff(projectId),
    enabled: Number.isFinite(projectId),
  });

  // 回傳形狀依型別定義是 { project_id, project_name, staff[], total } ——
  // 初版猜 data/items 全落空 → 找不到記錄、頁面顯示「找不到這位」。
  // 這是同一輪內第二次猜錯回傳形狀（機關承辦那支是 detail 端點），
  // 教訓：**不要猜 API 形狀，去看型別定義或實打一次**。
  const staffList = React.useMemo(() => staffResp?.staff ?? [], [staffResp]);

  const record = React.useMemo(
    () => (isEdit ? staffList.find((x) => x.user_id === uid) : undefined),
    [staffList, uid, isEdit],
  );

  // 新增時要挑人；編輯時人已定，不再讓改（改人＝換一筆關聯）
  // 沿用詳情頁本來就在用的那支（usersApi + 同一組查詢鍵），不另開資料來源
  const { data: allUsers = [] } = useQuery({
    queryKey: ['contract-case-user-options'],
    queryFn: async () => {
      const response = await usersApi.getUsers({ limit: 100 }) as PaginatedResponse<User>;
      return response.items || [];
    },
    staleTime: 10 * 60 * 1000,
    enabled: !isEdit,
  });
  const userOptions = React.useMemo(() => {
    const taken = new Set(staffList.map((s) => Number(s.user_id)));
    return allUsers
      .filter((u) => !taken.has(u.id))
      .map((u) => ({ value: u.id, label: u.full_name || u.username || `#${u.id}` }));
  }, [allUsers, staffList]);

  useEffect(() => {
    if (record) form.setFieldsValue({ user_id: record.user_id, role: record.role });
  }, [record, form]);

  const backToCase = () =>
    navigate(`${ROUTES.CONTRACT_CASE_DETAIL.replace(':id', String(projectId))}?tab=staff`);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['project-staff', projectId] });
    queryClient.invalidateQueries({ queryKey: ['contract-case', projectId] });
  };

  const handleSubmit = async () => {
    let values;
    try {
      values = await form.validateFields();
    } catch {
      return;
    }
    setSubmitting(true);
    try {
      if (isEdit && uid) {
        // 沿用原本就地編輯用的同一支：role 變更連動 is_primary，行為不變
        await projectStaffApi.updateStaff(projectId, uid, {
          role: values.role, is_primary: values.role === '計畫主持',
        });
        message.success('更新成功');
      } else {
        await projectStaffApi.addStaff({
          project_id: projectId,
          user_id: values.user_id,
          role: values.role,
          is_primary: values.role === '計畫主持',
          start_date: new Date().toISOString().slice(0, 10),
          status: 'active',
        });
        message.success('新增承辦同仁成功');
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
    if (!uid) return;
    setDeleting(true);
    try {
      await projectStaffApi.deleteStaff(projectId, uid);
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
      title={isEdit ? '編輯承辦同仁' : '新增承辦同仁'}
      backText="返回案件"
      onBack={backToCase}
      onSubmit={handleSubmit}
      submitting={submitting}
      isEdit={isEdit}
      submitText={isEdit ? '儲存變更' : '新增同仁'}
      loading={isEdit && isLoading}
      notFoundMessage={isEdit && !isLoading && !record ? '找不到這位承辦同仁（可能已被移除）。' : undefined}
      headerExtra={isEdit ? (
        <Popconfirm title="確定要移除此同仁？" okText="移除" cancelText="取消" onConfirm={handleDelete}>
          <Button danger icon={<DeleteOutlined />} loading={deleting}>移除</Button>
        </Popconfirm>
      ) : undefined}
    >
      <Form form={form} layout="vertical" size={isMobile ? 'large' : 'middle'} preserve={false}>
        <Form.Item
          name="user_id"
          label="同仁"
          rules={[{ required: true, message: '請選擇同仁' }]}
        >
          <Select
            showSearch
            optionFilterProp="label"
            placeholder="選擇同仁"
            disabled={isEdit}
            options={isEdit
              ? [{ value: uid as number, label: String(record?.user_name || `#${uid}`) }]
              : userOptions}
          />
        </Form.Item>
        <Form.Item name="role" label="角色/職責" rules={[{ required: true, message: '請選擇角色' }]}>
          <Select placeholder="選擇角色" options={STAFF_ROLE_OPTIONS.map((r) => ({ value: r, label: r }))} />
        </Form.Item>
      </Form>
    </ErpFormPageShell>
  );
};

export default ContractCaseStaffFormPage;
