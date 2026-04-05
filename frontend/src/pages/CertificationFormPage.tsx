/**
 * 證照表單頁
 *
 * 共享新增/編輯表單，根據路由參數自動切換模式
 * 導航模式：編輯模式支援刪除功能
 * 支援附件上傳（圖片、PDF）
 *
 * @version 2.1.0 (refactored: extracted attachment hook + preview component)
 * @date 2026-01-26
 */

import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Form, Input, Select, Row, Col, App, DatePicker } from 'antd';
import { ExclamationCircleOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FormPageLayout } from '../components/common/FormPage';
import {
  certificationsApi,
  CERT_TYPES,
  CERT_STATUS,
} from '../api/certificationsApi';
import type { CertificationCreate, CertificationUpdate } from '../types/api';
import dayjs from 'dayjs';
import { useCertificationAttachment } from './certification/useCertificationAttachment';
import AttachmentPreview from './certification/AttachmentPreview';

const { Option } = Select;

export const CertificationFormPage: React.FC = () => {
  const { userId, certId } = useParams<{ userId: string; certId: string }>();
  const navigate = useNavigate();
  const { message, modal } = App.useApp();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const staffId = userId ? parseInt(userId, 10) : undefined;
  const certificationId = certId ? parseInt(certId, 10) : undefined;

  const isEdit = Boolean(certificationId);
  const title = isEdit ? '編輯證照' : '新增證照';
  const backPath = staffId ? `/staff/${staffId}` : '/staff';

  // 編輯模式：載入證照資料
  const { data: certification, isLoading } = useQuery({
    queryKey: ['certification', certificationId],
    queryFn: () => certificationsApi.getDetail(certificationId!),
    enabled: isEdit && !!certificationId,
  });

  // 附件管理
  const attachment = useCertificationAttachment({
    certificationId,
    existingAttachmentPath: certification?.attachment_path ?? null,
    messageApi: message,
    modalApi: modal,
  });

  // 填入表單資料
  useEffect(() => {
    if (certification) {
      form.setFieldsValue({
        cert_type: certification.cert_type,
        cert_name: certification.cert_name,
        issuing_authority: certification.issuing_authority,
        cert_number: certification.cert_number,
        status: certification.status,
        issue_date: certification.issue_date ? dayjs(certification.issue_date) : undefined,
        expiry_date: certification.expiry_date ? dayjs(certification.expiry_date) : undefined,
        notes: certification.notes,
      });
      attachment.initPreview(certification.attachment_path);
    } else if (!isEdit) {
      form.setFieldsValue({ status: '有效' });
    }
  }, [certification, form, isEdit]); // eslint-disable-line react-hooks/exhaustive-deps

  // 新增 mutation
  const createMutation = useMutation({
    mutationFn: (data: CertificationCreate) => certificationsApi.create(data),
    onSuccess: async (newCert) => {
      if (attachment.attachmentFile && newCert.id) {
        const ok = await attachment.uploadAttachment(newCert.id);
        message.success(ok ? '證照及附件建立成功' : '證照已建立，但附件上傳失敗');
      } else {
        message.success('證照建立成功');
      }
      queryClient.invalidateQueries({ queryKey: ['certifications', staffId] });
      navigate(backPath);
    },
    onError: (error: Error) => {
      message.error(error?.message || '建立失敗');
    },
  });

  // 更新 mutation
  const updateMutation = useMutation({
    mutationFn: (data: CertificationUpdate) =>
      certificationsApi.update(certificationId!, data),
    onSuccess: async () => {
      if (attachment.attachmentFile && certificationId) {
        const ok = await attachment.uploadAttachment(certificationId);
        message.success(ok ? '證照及附件更新成功' : '證照已更新，但附件上傳失敗');
      } else {
        message.success('證照更新成功');
      }
      queryClient.invalidateQueries({ queryKey: ['certifications', staffId] });
      queryClient.invalidateQueries({ queryKey: ['certification', certificationId] });
      navigate(backPath);
    },
    onError: (error: Error) => {
      message.error(error?.message || '更新失敗');
    },
  });

  // 刪除 mutation (導航模式)
  const deleteMutation = useMutation({
    mutationFn: () => certificationsApi.delete(certificationId!),
    onSuccess: () => {
      message.success('證照刪除成功');
      queryClient.invalidateQueries({ queryKey: ['certifications', staffId] });
      navigate(backPath);
    },
    onError: (error: Error) => {
      message.error(error?.message || '刪除失敗');
    },
  });

  // 刪除確認
  const handleDelete = () => {
    modal.confirm({
      title: '確定要刪除此證照？',
      icon: <ExclamationCircleOutlined />,
      content: '刪除後將無法復原。',
      okText: '確定刪除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => deleteMutation.mutate(),
    });
  };

  // 保存處理
  const handleSave = async () => {
    if (!staffId) {
      message.error('缺少使用者 ID');
      return;
    }
    try {
      const values = await form.validateFields();
      const certData = {
        ...values,
        issue_date: values.issue_date?.format('YYYY-MM-DD'),
        expiry_date: values.expiry_date?.format('YYYY-MM-DD'),
      };
      if (isEdit) {
        updateMutation.mutate(certData);
      } else {
        createMutation.mutate({ ...certData, user_id: staffId });
      }
    } catch {
      message.error('請檢查表單欄位');
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending || attachment.uploading;

  return (
    <FormPageLayout
      title={title}
      backPath={backPath}
      onSave={handleSave}
      onDelete={isEdit ? handleDelete : undefined}
      loading={isEdit && isLoading}
      saving={isSaving}
      deleting={deleteMutation.isPending}
    >
      <Form form={form} layout="vertical" size="large">
        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item
              name="cert_type"
              label="證照類型"
              rules={[{ required: true, message: '請選擇證照類型' }]}
            >
              <Select placeholder="請選擇證照類型">
                {CERT_TYPES.map((type) => (
                  <Option key={type} value={type}>{type}</Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="status" label="狀態">
              <Select placeholder="請選擇狀態">
                {CERT_STATUS.map((s) => (
                  <Option key={s} value={s}>{s}</Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
        </Row>

        <Form.Item
          name="cert_name"
          label="證照名稱"
          rules={[{ required: true, message: '請輸入證照名稱' }]}
        >
          <Input placeholder="請輸入證照名稱" />
        </Form.Item>

        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item name="issuing_authority" label="核發機關">
              <Input placeholder="請輸入核發機關" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="cert_number" label="證照編號">
              <Input placeholder="請輸入證照編號" />
            </Form.Item>
          </Col>
        </Row>

        <Row gutter={16}>
          <Col xs={24} sm={12}>
            <Form.Item name="issue_date" label="核發日期">
              <DatePicker style={{ width: '100%' }} placeholder="請選擇核發日期" />
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="expiry_date" label="有效期限">
              <DatePicker style={{ width: '100%' }} placeholder="永久有效可不填" />
            </Form.Item>
          </Col>
        </Row>

        <Form.Item name="notes" label="備註">
          <Input.TextArea rows={3} placeholder="請輸入備註" />
        </Form.Item>

        {/* 附件上傳區域 */}
        <Form.Item label="證照掃描檔">
          <AttachmentPreview
            attachmentPreview={attachment.attachmentPreview}
            attachmentFile={attachment.attachmentFile}
            isEdit={isEdit}
            hasExistingAttachment={!!certification?.attachment_path}
            deleteAttachmentPending={attachment.deleteAttachmentMutation.isPending}
            onClearFile={attachment.handleClearFile}
            onDeleteAttachment={attachment.handleDeleteAttachment}
            onFileSelect={attachment.handleFileSelect}
          />
        </Form.Item>
      </Form>
    </FormPageLayout>
  );
};

export default CertificationFormPage;
