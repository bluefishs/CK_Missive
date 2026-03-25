/**
 * 承辦同仁詳情頁面
 * @description 顯示同仁詳情，含 Tab 分頁（基本資料、證照紀錄）
 * @version 3.0.0 - 拆分子元件 (StaffDetailHeader, StaffBasicInfoTab, StaffCertificationsTab)
 * @date 2026-03-16
 */
import React, { useState, useCallback } from 'react';
import { Form, App, Button, Popconfirm } from 'antd';
import { UserOutlined, SafetyCertificateOutlined, EditOutlined, DeleteOutlined, SaveOutlined, CloseOutlined } from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { DetailPageLayout } from '../components/common/DetailPage/DetailPageLayout';
import { createTabItem } from '../components/common/DetailPage/utils';
import { apiClient, SERVER_BASE_URL } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { ROUTES } from '../router/types';
import { certificationsApi, Certification } from '../api/certificationsApi';
import type { User } from '../types/api';
import { useDepartments } from '../hooks/system';
import { StaffBasicInfoTab } from './staffDetail/StaffBasicInfoTab';
import { StaffCertificationsTab } from './staffDetail/StaffCertificationsTab';
import { extractErrorMessage } from './staffDetail/staffDetailUtils';

type Staff = User;

export const StaffDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();

  const staffId = id ? parseInt(id, 10) : undefined;

  const { data: departmentOptions = [] } = useDepartments();
  const queryClient = useQueryClient();

  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showPasswordChange, setShowPasswordChange] = useState(false);

  // Load staff data
  const { data: staff = null, isLoading: loading } = useQuery({
    queryKey: ['staff-detail', staffId],
    queryFn: async () => {
      const user = await apiClient.post(API_ENDPOINTS.USERS.DETAIL(staffId!));
      const response: { items: Staff[]; users?: Staff[] } = { items: [user as Staff] };
      const items = response.items || response.users || [];
      const found = items.find((s: Staff) => s.id === staffId);
      if (found) {
        form.setFieldsValue({
          username: found.username,
          email: found.email,
          full_name: found.full_name,
          is_active: found.is_active,
          department: found.department,
          position: found.position,
        });
        return found as Staff;
      }
      message.error('找不到此承辦同仁');
      navigate(ROUTES.STAFF);
      return null;
    },
    enabled: !!staffId,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  // Load certifications
  const { data: certifications = [], isLoading: certLoading } = useQuery({
    queryKey: ['staff-certifications', staffId],
    queryFn: async () => {
      const response = await certificationsApi.getUserCertifications(staffId!);
      return response.items;
    },
    enabled: !!staffId,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const loadStaff = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['staff-detail', staffId] });
  }, [queryClient, staffId]);

  const loadCertifications = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['staff-certifications', staffId] });
  }, [queryClient, staffId]);

  // Save basic info
  const handleSave = async () => {
    if (!staffId) return;
    try {
      const values = await form.validateFields();
      setSaving(true);

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const updateData: Record<string, any> = {
        email: values.email,
        full_name: values.full_name,
        is_active: values.is_active,
        department: values.department,
        position: values.position,
      };

      if (showPasswordChange && values.password) {
        updateData.password = values.password;
      }

      await apiClient.post(API_ENDPOINTS.USERS.UPDATE(staffId), updateData);
      message.success(showPasswordChange ? '資料與密碼已更新' : '資料更新成功');
      setIsEditing(false);
      setShowPasswordChange(false);
      loadStaff();
    } catch (error: unknown) {
      message.error(extractErrorMessage(error));
    } finally {
      setSaving(false);
    }
  };

  // Cancel edit
  const handleCancelEdit = () => {
    setIsEditing(false);
    setShowPasswordChange(false);
    if (staff) {
      form.setFieldsValue({
        username: staff.username,
        email: staff.email,
        full_name: staff.full_name,
        is_active: staff.is_active,
        department: staff.department,
        position: staff.position,
      });
    }
  };

  // Delete staff
  const handleDelete = async () => {
    if (!staffId) return;
    try {
      await apiClient.post(API_ENDPOINTS.USERS.DELETE(staffId));
      message.success('承辦同仁已刪除');
      navigate(ROUTES.STAFF);
    } catch (error: unknown) {
      message.error(extractErrorMessage(error));
    }
  };

  // Certification navigation handlers
  const handleAddCert = () => {
    navigate(`/staff/${staffId}/certifications/create`);
  };

  const handleEditCert = (cert: Certification) => {
    navigate(`/staff/${staffId}/certifications/${cert.id}/edit`);
  };

  const handleDeleteCert = async (certId: number) => {
    try {
      await certificationsApi.delete(certId);
      message.success('證照刪除成功');
      loadCertifications();
    } catch (error: unknown) {
      message.error(extractErrorMessage(error));
    }
  };

  const handlePreviewAttachment = (cert: Certification) => {
    if (cert.attachment_path) {
      const attachmentUrl = `${SERVER_BASE_URL}/uploads/${cert.attachment_path}`;
      window.open(attachmentUrl, '_blank');
    } else {
      message.info('此證照沒有附件');
    }
  };

  if (!staff && !loading) {
    return <DetailPageLayout header={{ title: '找不到此承辦同仁', backPath: ROUTES.STAFF }} tabs={[]} hasData={false} />;
  }

  const headerConfig = {
    title: staff?.full_name ?? staff?.username ?? '載入中...',
    icon: <UserOutlined />,
    backPath: ROUTES.STAFF,
    tags: staff ? [
      { text: staff.is_active ? '啟用' : '停用', color: staff.is_active ? 'success' : 'default' },
      ...(staff.department ? [{ text: staff.department, color: 'blue' }] : []),
    ] : [],
    extra: isEditing ? (
      <>
        <Button icon={<CloseOutlined />} onClick={handleCancelEdit}>取消</Button>
        <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>儲存</Button>
      </>
    ) : (
      <>
        <Button type="primary" icon={<EditOutlined />} onClick={() => setIsEditing(true)}>編輯</Button>
        <Popconfirm title="確定刪除此同仁？" okText="確定" cancelText="取消" okButtonProps={{ danger: true }} onConfirm={handleDelete}>
          <Button danger icon={<DeleteOutlined />}>刪除</Button>
        </Popconfirm>
      </>
    ),
  };

  const tabs = staff ? [
    createTabItem('basic', { icon: <UserOutlined />, text: '基本資料' },
      <StaffBasicInfoTab staff={staff} form={form} isEditing={isEditing} isMobile={false}
        saving={saving} showPasswordChange={showPasswordChange} departmentOptions={departmentOptions}
        onShowPasswordChange={setShowPasswordChange} onSave={handleSave} onCancel={handleCancelEdit} />
    ),
    createTabItem('certifications', { icon: <SafetyCertificateOutlined />, text: '證照紀錄', count: certifications.length },
      <StaffCertificationsTab certifications={certifications} certLoading={certLoading} isMobile={false}
        onAdd={handleAddCert} onEdit={handleEditCert} onDelete={handleDeleteCert} onPreview={handlePreviewAttachment} />
    ),
  ] : [];

  return <DetailPageLayout header={headerConfig} tabs={tabs} loading={loading} hasData={!!staff} />;
};

export default StaffDetailPage;
