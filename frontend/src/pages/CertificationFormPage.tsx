/**
 * 證照表單頁
 *
 * 共享新增/編輯表單，根據路由參數自動切換模式
 * 導航模式：編輯模式支援刪除功能
 * 支援附件上傳（圖片、PDF）
 *
 * @version 2.0.0
 * @date 2026-01-26
 */

import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Form, Input, Select, Row, Col, App, DatePicker, Modal, Upload, Button, Space, Image } from 'antd';
import { ExclamationCircleOutlined, UploadOutlined, DeleteOutlined, EyeOutlined, FileOutlined } from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FormPageLayout } from '../components/common/FormPage';
import {
  certificationsApi,
  CERT_TYPES,
  CERT_STATUS,
} from '../api/certificationsApi';
import type { CertificationCreate, CertificationUpdate } from '../types/api';
import { SERVER_BASE_URL } from '../api/client';
import dayjs from 'dayjs';

const { Option } = Select;

// 允許的附件格式
const ALLOWED_FILE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'application/pdf'];
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export const CertificationFormPage: React.FC = () => {
  const { userId, certId } = useParams<{ userId: string; certId: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const queryClient = useQueryClient();

  const staffId = userId ? parseInt(userId, 10) : undefined;
  const certificationId = certId ? parseInt(certId, 10) : undefined;

  const isEdit = Boolean(certificationId);
  const title = isEdit ? '編輯證照' : '新增證照';
  const backPath = staffId ? `/staff/${staffId}` : '/staff';

  // 附件狀態
  const [attachmentFile, setAttachmentFile] = useState<File | null>(null);
  const [attachmentPreview, setAttachmentPreview] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  // 編輯模式：載入證照資料
  const { data: certification, isLoading } = useQuery({
    queryKey: ['certification', certificationId],
    queryFn: async () => {
      return await certificationsApi.getDetail(certificationId!);
    },
    enabled: isEdit && !!certificationId,
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
      // 設定現有附件預覽
      if (certification.attachment_path) {
        setAttachmentPreview(certification.attachment_path);
      }
    } else if (!isEdit) {
      // 新增模式：設定預設值
      form.setFieldsValue({ status: '有效' });
    }
  }, [certification, form, isEdit]);

  // 新增 mutation
  const createMutation = useMutation({
    mutationFn: (data: CertificationCreate) => certificationsApi.create(data),
    onSuccess: async (newCert) => {
      // 如果有選擇附件，上傳附件
      if (attachmentFile && newCert.id) {
        try {
          setUploading(true);
          await certificationsApi.uploadAttachment(newCert.id, attachmentFile);
          message.success('證照及附件建立成功');
        } catch (uploadError) {
          const errMsg = uploadError instanceof Error ? uploadError.message : '未知錯誤';
          message.warning(`證照已建立，但附件上傳失敗: ${errMsg}`);
        } finally {
          setUploading(false);
        }
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
      // 如果有選擇新附件，上傳附件
      if (attachmentFile && certificationId) {
        try {
          setUploading(true);
          await certificationsApi.uploadAttachment(certificationId, attachmentFile);
          message.success('證照及附件更新成功');
        } catch (uploadError) {
          const errMsg = uploadError instanceof Error ? uploadError.message : '未知錯誤';
          message.warning(`證照已更新，但附件上傳失敗: ${errMsg}`);
        } finally {
          setUploading(false);
        }
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

  // 刪除附件 mutation
  const deleteAttachmentMutation = useMutation({
    mutationFn: () => certificationsApi.deleteAttachment(certificationId!),
    onSuccess: () => {
      message.success('附件刪除成功');
      setAttachmentPreview(null);
      queryClient.invalidateQueries({ queryKey: ['certification', certificationId] });
    },
    onError: (error: Error) => {
      message.error(error?.message || '刪除附件失敗');
    },
  });

  // 刪除確認
  const handleDelete = () => {
    Modal.confirm({
      title: '確定要刪除此證照？',
      icon: <ExclamationCircleOutlined />,
      content: '刪除後將無法復原。',
      okText: '確定刪除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => deleteMutation.mutate(),
    });
  };

  // 刪除附件確認
  const handleDeleteAttachment = () => {
    Modal.confirm({
      title: '確定要刪除附件？',
      icon: <ExclamationCircleOutlined />,
      content: '刪除後將無法復原。',
      okText: '確定刪除',
      okType: 'danger',
      cancelText: '取消',
      onOk: () => deleteAttachmentMutation.mutate(),
    });
  };

  // 檔案選擇處理
  const handleFileSelect = (file: File): boolean => {
    // 驗證檔案類型
    if (!ALLOWED_FILE_TYPES.includes(file.type)) {
      message.error('不支援的檔案格式，請上傳 JPG、PNG、GIF、BMP 或 PDF 檔案');
      return false;
    }
    // 驗證檔案大小
    if (file.size > MAX_FILE_SIZE) {
      message.error('檔案大小超過限制（最大 10MB）');
      return false;
    }
    setAttachmentFile(file);
    // 產生本地預覽
    if (file.type.startsWith('image/')) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setAttachmentPreview(e.target?.result as string);
      };
      reader.readAsDataURL(file);
    } else {
      // PDF 顯示檔名
      setAttachmentPreview(`file:${file.name}`);
    }
    return false; // 阻止自動上傳
  };

  // 清除選擇的檔案
  const handleClearFile = () => {
    setAttachmentFile(null);
    // 如果有原始附件，恢復原始預覽
    if (certification?.attachment_path) {
      setAttachmentPreview(certification.attachment_path);
    } else {
      setAttachmentPreview(null);
    }
  };

  // 取得附件完整 URL
  const getAttachmentUrl = (path: string): string => {
    if (path.startsWith('file:') || path.startsWith('data:')) {
      return path;
    }
    // 將相對路徑轉換為完整 URL
    return `${SERVER_BASE_URL}/uploads/${path}`;
  };

  // 判斷是否為圖片
  const isImageAttachment = (path: string): boolean => {
    if (path.startsWith('data:image')) return true;
    const ext = path.split('.').pop()?.toLowerCase();
    return ['jpg', 'jpeg', 'png', 'gif', 'bmp'].includes(ext || '');
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
        createMutation.mutate({
          ...certData,
          user_id: staffId,
        });
      }
    } catch {
      message.error('請檢查表單欄位');
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending || uploading;

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
                  <Option key={type} value={type}>
                    {type}
                  </Option>
                ))}
              </Select>
            </Form.Item>
          </Col>
          <Col xs={24} sm={12}>
            <Form.Item name="status" label="狀態">
              <Select placeholder="請選擇狀態">
                {CERT_STATUS.map((s) => (
                  <Option key={s} value={s}>
                    {s}
                  </Option>
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {/* 現有附件預覽 */}
            {attachmentPreview && (
              <div style={{
                border: '1px solid #d9d9d9',
                borderRadius: 8,
                padding: 12,
                background: '#fafafa',
              }}>
                {attachmentPreview.startsWith('file:') ? (
                  // PDF 檔案顯示
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <FileOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                    <span>{attachmentPreview.replace('file:', '')}</span>
                    {attachmentFile && (
                      <Button
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={handleClearFile}
                        danger
                      >
                        取消選擇
                      </Button>
                    )}
                  </div>
                ) : isImageAttachment(attachmentPreview) ? (
                  // 圖片預覽
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    <Image
                      src={attachmentPreview.startsWith('data:')
                        ? attachmentPreview
                        : getAttachmentUrl(attachmentPreview)
                      }
                      alt="證照掃描檔"
                      style={{ maxWidth: 300, maxHeight: 200 }}
                      preview={{
                        mask: <EyeOutlined />,
                      }}
                    />
                    <Space>
                      {attachmentFile ? (
                        <Button
                          size="small"
                          icon={<DeleteOutlined />}
                          onClick={handleClearFile}
                          danger
                        >
                          取消選擇
                        </Button>
                      ) : isEdit && certification?.attachment_path && (
                        <Button
                          size="small"
                          icon={<DeleteOutlined />}
                          onClick={handleDeleteAttachment}
                          loading={deleteAttachmentMutation.isPending}
                          danger
                        >
                          刪除附件
                        </Button>
                      )}
                    </Space>
                  </div>
                ) : (
                  // PDF 或其他檔案
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <FileOutlined style={{ fontSize: 24, color: '#1890ff' }} />
                    <a
                      href={getAttachmentUrl(attachmentPreview)}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      查看附件
                    </a>
                    {isEdit && certification?.attachment_path && (
                      <Button
                        size="small"
                        icon={<DeleteOutlined />}
                        onClick={handleDeleteAttachment}
                        loading={deleteAttachmentMutation.isPending}
                        danger
                      >
                        刪除
                      </Button>
                    )}
                  </div>
                )}
              </div>
            )}

            {/* 上傳按鈕 */}
            <Upload
              accept=".jpg,.jpeg,.png,.gif,.bmp,.pdf"
              beforeUpload={handleFileSelect}
              showUploadList={false}
              maxCount={1}
            >
              <Button icon={<UploadOutlined />}>
                {attachmentPreview ? '更換附件' : '選擇檔案'}
              </Button>
            </Upload>
            <div style={{ color: '#999', fontSize: 12 }}>
              支援格式: JPG、PNG、GIF、BMP、PDF，檔案大小限制 10MB
            </div>
          </div>
        </Form.Item>
      </Form>
    </FormPageLayout>
  );
};

export default CertificationFormPage;
