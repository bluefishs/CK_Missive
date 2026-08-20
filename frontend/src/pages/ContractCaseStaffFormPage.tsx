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
import { Form, Select, App, Button, Popconfirm, Alert } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { ROUTES } from '../router/types';
import { useResponsive } from '../hooks';
import { ErpFormPageShell } from '../components/erp/ErpFormPageShell';
import { projectStaffApi } from '../api/projectStaffApi';
import type { User } from '../types/api';
import { STAFF_ROLE_OPTIONS } from '../constants/staffOptions';
import { filterAssignableUsers, userDisplayName, assignableNotFound } from '../utils/assignableUsers';
import { apiClient } from '../api/client';
import { USERS_ENDPOINTS } from '../api/endpoints';

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
  //
  // ⚠️ queryKey 與 `useContractCaseData`（承攬案件詳情）**相同是刻意的**
  //    —— 同一份清單就該共用快取。但前提是**兩處的資料源也必須相同**：
  //    2026-08-20 之前詳情頁打 `users/list` 而這裡打別的，於是誰先載入誰
  //    就決定了快取內容，動線「詳情頁 → 新增承辦同仁」讓這一支的修改完全
  //    不會生效。兩處現在同源；`queryKey_drift_audit` 會擋住它再度分岔。
  const { data: allUsers = [], isError: userListFailed, isLoading: userListLoading } = useQuery({
    queryKey: ['contract-case-user-options'],
    queryFn: async () => {
      // ⚠️ 這裡原本打 `/users/list`，而它是 **require_admin** ——
      // 以 role='user' 的帳號登入會 403 ⇒ 選項為空，
      // 而 AntD Select 在 options 為空、value 有值時會顯示原始 value（數字 id），
      // 畫面上就是 owner 2026-08-20 回報的「只顯示代號無姓名」。
      //
      // 改打只需登入的 `/users/assignable`（只回 id/姓名/帳號/在職/分身欄位）。
      const response = await apiClient.post<{ items: User[] }>(USERS_ENDPOINTS.ASSIGNABLE, {});
      return response.items || [];
    },
    staleTime: 10 * 60 * 1000,
    enabled: !isEdit,
  });
  const userOptions = React.useMemo(() => {
    const taken = new Set(staffList.map((s) => Number(s.user_id)));
    // 排除已合併的分身帳號 —— 否則同一個人會出現兩次，
    // 其中張雅惠與李昭德兩筆**完全同名**，使用者無從分辨（見 utils/assignableUsers）
    return filterAssignableUsers(allUsers)
      .filter((u) => !taken.has(u.id))
      .map((u) => ({ value: u.id, label: userDisplayName(u) }));
  }, [allUsers, staffList]);

  useEffect(() => {
    if (record) form.setFieldsValue({ user_id: record.user_id, role: record.role });
  }, [record, form]);

  const backToCase = () =>
    navigate(`${ROUTES.CONTRACT_CASE_DETAIL.replace(':id', String(projectId))}?tab=staff`);

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['project-staff', projectId] });
    // ⚠️ 原本寫 `['contract-case', projectId]` —— 那個 key 不存在，
    //    詳情頁用的是 `contract-case-detail`（前綴比對是逐元素，不是字串開頭）。
    queryClient.invalidateQueries({ queryKey: ['contract-case-detail', projectId] });
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
            loading={!isEdit && userListLoading}
            // 清單載不到時要**說出來**，不能只是留一個空的下拉 ——
            // 「同仁變成代碼」這個症狀的成因不是誰有權限，而是清單空掉時
            // 畫面退化成顯示原始數字 id，看起來像資料壞了而不是載入失敗。
            notFoundContent={assignableNotFound({ isLoading: userListLoading, isError: userListFailed })}
            options={isEdit
              ? [{ value: uid as number, label: String(record?.user_name || `#${uid}`) }]
              : userOptions}
          />
        </Form.Item>
        {!isEdit && userListFailed && (
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
            message="同仁清單載入失敗"
            description="下拉選單目前是空的。這是清單取得失敗，不是系統裡沒有同仁 —— 請重新整理頁面再試。"
          />
        )}
        <Form.Item name="role" label="角色/職責" rules={[{ required: true, message: '請選擇角色' }]}>
          <Select placeholder="選擇角色" options={STAFF_ROLE_OPTIONS.map((r) => ({ value: r, label: r }))} />
        </Form.Item>
      </Form>
    </ErpFormPageShell>
  );
};

export default ContractCaseStaffFormPage;
