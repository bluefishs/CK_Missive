/**
 * PM 里程碑填報頁（新增／編輯共用）
 *
 * 路由：/pm/cases/:caseId/milestones/create
 *      /pm/cases/:caseId/milestones/:milestoneId/edit
 *
 * 取代 `MilestonesTab` 內的 Modal 填報（owner：填報參考公文設計、減少彈跳視窗）。
 * 原 ACCEPTED EXCEPTION 的理由是「導頁會失去詳情頁捲動位置與 tab 狀態」——
 * 返回時已帶 `?tab=milestones` 保留分頁，而換到的是手機完整縱向空間、
 * 可分享網址、返回鍵正確、重整不丟填到一半的內容。
 */

import React, { useEffect, useMemo } from 'react';
import { Form, Input, Select, DatePicker, App } from 'antd';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';

import { ROUTES } from '../router/types';
import { useResponsive } from '../hooks';
import { ErpFormPageShell } from '../components/erp/ErpFormPageShell';
import { Button, Popconfirm } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import {
  usePMMilestones,
  useCreatePMMilestone,
  useUpdatePMMilestone,
  useDeletePMMilestone,
} from '../hooks/business/usePMCases';
import { PM_MILESTONE_TYPE_LABELS, PM_MILESTONE_STATUS_LABELS } from '../types/pm';


const PMMilestoneFormPage: React.FC = () => {
  const { caseId, milestoneId } = useParams<{ caseId: string; milestoneId?: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const { isMobile } = useResponsive();

  const pmCaseId = Number(caseId);
  const mid = milestoneId ? Number(milestoneId) : null;
  const isEdit = mid !== null;

  const { data: milestones, isLoading } = usePMMilestones(pmCaseId);
  const record = useMemo(
    () => (isEdit && Array.isArray(milestones) ? milestones.find((m) => m.id === mid) : undefined),
    [milestones, mid, isEdit],
  );

  const createMutation = useCreatePMMilestone();
  const updateMutation = useUpdatePMMilestone();
  const deleteMutation = useDeletePMMilestone();

  useEffect(() => {
    if (!record) return;
    form.setFieldsValue({
      milestone_name: record.milestone_name,
      milestone_type: record.milestone_type,
      planned_date: record.planned_date ? dayjs(record.planned_date) : null,
      actual_date: record.actual_date ? dayjs(record.actual_date) : null,
      status: record.status,
      sort_order: record.sort_order,
      notes: record.notes,
    });
  }, [record, form]);

  const backToCase = () =>
    navigate(`${ROUTES.PM_CASE_DETAIL.replace(':id', String(pmCaseId))}?tab=milestones`);

  const handleSubmit = async () => {
    let values;
    try {
      values = await form.validateFields();
    } catch {
      return; // 欄位已自行標紅
    }
    const payload = {
      milestone_name: values.milestone_name,
      milestone_type: values.milestone_type,
      planned_date: values.planned_date?.format('YYYY-MM-DD'),
      actual_date: values.actual_date?.format('YYYY-MM-DD'),
      status: values.status,
      sort_order: values.sort_order,
      notes: values.notes,
    };

    try {
      if (isEdit && mid) {
        await updateMutation.mutateAsync({ id: mid, pmCaseId, data: payload });
        message.success('里程碑已更新');
      } else {
        await createMutation.mutateAsync({ ...payload, pm_case_id: pmCaseId });
        message.success('里程碑已新增');
      }
      backToCase();
    } catch {
      message.error(isEdit ? '更新失敗' : '新增失敗');
    }
  };

  const typeOptions = Object.entries(PM_MILESTONE_TYPE_LABELS).map(([value, label]) => ({ value, label }));
  const statusOptions = Object.entries(PM_MILESTONE_STATUS_LABELS).map(([value, label]) => ({ value, label }));

  return (
    <ErpFormPageShell
      title={isEdit ? '編輯里程碑' : '新增里程碑'}
      backText="返回案件"
      onBack={backToCase}
      onSubmit={handleSubmit}
      submitting={createMutation.isPending || updateMutation.isPending}
      isEdit={isEdit}
      submitText={isEdit ? '儲存變更' : '新增里程碑'}
      loading={isEdit && isLoading}
      notFoundMessage={isEdit && !isLoading && !record ? '找不到這筆里程碑（可能已被刪除）。' : undefined}
      /* 刪除原本在案件頁的表格操作欄。該欄依「詳情頁 tab 只呈現不操作」移除後，
         刪除若不搬到這裡就沒有任何入口了。 */
      headerExtra={isEdit ? (
        <Popconfirm
          title="確定刪除此里程碑？" okText="刪除" cancelText="取消"
          onConfirm={() => deleteMutation.mutate({ id: mid!, pmCaseId }, {
            onSuccess: () => { message.success('里程碑已刪除'); backToCase(); },
          })}
        >
          <Button danger icon={<DeleteOutlined />} loading={deleteMutation.isPending}>刪除</Button>
        </Popconfirm>
      ) : undefined}
    >
      <Form form={form} layout="vertical" size={isMobile ? 'middle' : 'large'} preserve={false}>
        <Form.Item
          name="milestone_name"
          label="里程碑名稱"
          rules={[{ required: true, message: '請輸入里程碑名稱' }]}
        >
          <Input placeholder="請輸入名稱" />
        </Form.Item>

        <Form.Item name="milestone_type" label="類型">
          <Select placeholder="請選擇類型" allowClear options={typeOptions} />
        </Form.Item>

        <Form.Item name="planned_date" label="預計日期">
          <DatePicker style={{ width: '100%' }} inputReadOnly={isMobile} />
        </Form.Item>

        <Form.Item name="actual_date" label="實際日期">
          <DatePicker style={{ width: '100%' }} inputReadOnly={isMobile} />
        </Form.Item>

        <Form.Item name="status" label="狀態">
          <Select placeholder="請選擇狀態" allowClear options={statusOptions} />
        </Form.Item>

        <Form.Item name="sort_order" label="排序">
          <Input type="number" inputMode="numeric" placeholder="排序值" />
        </Form.Item>

        <Form.Item name="notes" label="備註">
          <Input.TextArea rows={3} placeholder="備註" />
        </Form.Item>
      </Form>
    </ErpFormPageShell>
  );
};

export default PMMilestoneFormPage;
