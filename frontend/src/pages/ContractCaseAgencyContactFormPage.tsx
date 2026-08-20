/**
 * 承攬案件「機關承辦」填報頁（新增／編輯共用）
 *
 * 路由：/contract-cases/:caseId/agency-contacts/create
 *      /contract-cases/:caseId/agency-contacts/:contactId/edit
 *
 * 取代 `AgencyContactTab` 內的 Modal 填報（owner：填報參照公文設計、重點在行動裝置）。
 * 沿用 PMMilestoneFormPage 已確立的理由：返回時帶 `?tab=agency-contacts` 保留分頁，
 * 換到的是手機完整縱向空間、可分享網址、返回鍵正確、重整不丟填到一半的內容 ——
 * 7 個欄位的表單塞進 390px 的彈窗，正是最不好填的形狀。
 *
 * 刪除也在這一頁的標題列（詳情頁 tab 只呈現、不操作）。
 */
import React, { useEffect } from 'react';
import { Form, Input, Select, App, Button, Popconfirm } from 'antd';
import { DeleteOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import { ROUTES } from '../router/types';
import { useResponsive } from '../hooks';
import { ErpFormPageShell } from '../components/erp/ErpFormPageShell';
import {
  getAgencyContact,
  createAgencyContact,
  updateAgencyContact,
  deleteAgencyContact,
} from '../api/projectAgencyContacts';

const ContractCaseAgencyContactFormPage: React.FC = () => {
  const { caseId, contactId } = useParams<{ caseId: string; contactId?: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const { isMobile } = useResponsive();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const projectId = Number(caseId);
  const cid = contactId ? Number(contactId) : null;
  const isEdit = cid !== null;
  const [submitting, setSubmitting] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);

  // 用既有的單筆查詢 API（不另開端點）。
  // 初版寫成「撈清單再 find」——實測回傳是包了一層的物件不是陣列，
  // `Array.isArray` 直接為 false → 永遠找不到 → 頁面顯示「找不到這筆」。
  // 這種錯誤編譯得過、路由也對，只有真的打開頁面才看得到。
  const { data: record, isLoading } = useQuery({
    queryKey: ['project-agency-contact', cid],
    queryFn: () => getAgencyContact(cid as number),
    enabled: isEdit && Number.isFinite(cid),
  });

  useEffect(() => {
    if (record) form.setFieldsValue(record);
  }, [record, form]);

  const backToCase = () =>
    navigate(`${ROUTES.CONTRACT_CASE_DETAIL.replace(':id', String(projectId))}?tab=agency-contacts`);

  const invalidate = () => {
    // ⚠️ 這兩行原本是 `['project-agency-contacts', ...]` 與 `['contract-case', ...]`，
    //    **兩個都不存在** —— invalidateQueries 是逐元素比對，
    //    `'contract-case' !== 'contract-case-detail'`，所以存檔後詳情頁不會重載。
    //    機關承辦清單本來就是跟著 `contract-case-detail` 那一支一起撈回來的
    //    （useContractCaseData 的 Promise.all），所以 invalidate 它就夠。
    queryClient.invalidateQueries({ queryKey: ['contract-case-detail', projectId] });
  };

  const handleSubmit = async () => {
    let values;
    try {
      values = await form.validateFields();
    } catch {
      return; // 驗證訊息由 Form 自己顯示
    }
    setSubmitting(true);
    try {
      if (isEdit && cid) {
        await updateAgencyContact(cid, values);
        message.success('更新成功');
      } else {
        await createAgencyContact({ ...values, project_id: projectId });
        message.success('新增成功');
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
    if (!cid) return;
    setDeleting(true);
    try {
      await deleteAgencyContact(cid);
      message.success('刪除成功');
      invalidate();
      backToCase();
    } catch {
      message.error('刪除失敗');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <ErpFormPageShell
      title={isEdit ? '編輯機關承辦' : '新增機關承辦'}
      backText="返回案件"
      onBack={backToCase}
      onSubmit={handleSubmit}
      submitting={submitting}
      isEdit={isEdit}
      submitText={isEdit ? '儲存變更' : '新增承辦人'}
      loading={isEdit && isLoading}
      notFoundMessage={isEdit && !isLoading && !record ? '找不到這筆機關承辦（可能已被刪除）。' : undefined}
      headerExtra={isEdit ? (
        <Popconfirm
          title="確定要刪除此承辦人嗎？" okText="刪除" cancelText="取消"
          onConfirm={handleDelete}
        >
          <Button danger icon={<DeleteOutlined />} loading={deleting}>刪除</Button>
        </Popconfirm>
      ) : undefined}
    >
      <Form form={form} layout="vertical" size={isMobile ? 'large' : 'middle'} preserve={false}>
        <Form.Item name="contact_name" label="姓名" rules={[{ required: true, message: '請輸入姓名' }]}>
          <Input placeholder="請輸入承辦人姓名" />
        </Form.Item>
        <Form.Item name="position" label="職稱">
          <Input placeholder="請輸入職稱" />
        </Form.Item>
        <Form.Item name="department" label="單位/科室">
          <Input placeholder="請輸入單位或科室名稱" />
        </Form.Item>
        <Form.Item name="phone" label="電話">
          <Input placeholder="請輸入電話" inputMode="tel" />
        </Form.Item>
        <Form.Item name="mobile" label="手機">
          <Input placeholder="請輸入手機" inputMode="tel" />
        </Form.Item>
        <Form.Item name="email" label="電子郵件">
          <Input placeholder="請輸入電子郵件" inputMode="email" autoCapitalize="off" autoCorrect="off" />
        </Form.Item>
        <Form.Item name="is_primary" label="是否為主要承辦人">
          <Select
            placeholder="請選擇"
            allowClear
            options={[{ value: true, label: '是（主要承辦人）' }, { value: false, label: '否' }]}
          />
        </Form.Item>
        <Form.Item name="notes" label="備註">
          <Input.TextArea rows={isMobile ? 2 : 3} placeholder="請輸入備註" maxLength={500} />
        </Form.Item>
      </Form>
    </ErpFormPageShell>
  );
};

export default ContractCaseAgencyContactFormPage;
