/**
 * 承辦同仁詳情頁面
 * @description 顯示同仁詳情，含 Tab 分頁（基本資料、證照紀錄）
 * @version 2.1.0 - 導航模式設計，整合編輯/新增按鈕
 * @date 2026-01-26
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Button,
  Space,
  Typography,
  Tabs,
  Form,
  Input,
  Select,
  Switch,
  Row,
  Col,
  Table,
  Tag,
  Empty,
  App,
  Popconfirm,
  Spin,
  Descriptions,
} from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  UserOutlined,
  MailOutlined,
  LockOutlined,
  IdcardOutlined,
  SafetyCertificateOutlined,
  PlusOutlined,
  DeleteOutlined,
  KeyOutlined,
  BankOutlined,
  EyeOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import { useResponsive } from '../hooks';
import { apiClient, SERVER_BASE_URL } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { ROUTES } from '../router/types';
import { certificationsApi, Certification } from '../api/certificationsApi';
import type { User } from '../types/api';
import { DEPARTMENT_OPTIONS } from '../constants';
import { logger } from '../services/logger';

const { Title, Text } = Typography;
const { Option } = Select;

type Staff = User;

// 輔助函數：提取錯誤訊息
const extractErrorMessage = (error: unknown): string => {
  // 定義錯誤響應的型別
  interface ErrorDetail {
    msg?: string;
  }
  interface ApiErrorResponse {
    response?: {
      data?: {
        detail?: string | ErrorDetail[];
      };
    };
  }

  const apiError = error as ApiErrorResponse;
  const detail = apiError?.response?.data?.detail;
  if (!detail) return '操作失敗，請稍後再試';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((e: ErrorDetail) => e.msg || JSON.stringify(e)).join(', ');
  }
  return JSON.stringify(detail);
};

export const StaffDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();

  const staffId = id ? parseInt(id, 10) : undefined;

  // RWD 響應式
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  // 狀態
  const [staff, setStaff] = useState<Staff | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showPasswordChange, setShowPasswordChange] = useState(false);

  // 證照狀態
  const [certifications, setCertifications] = useState<Certification[]>([]);
  const [certLoading, setCertLoading] = useState(false);

  // 載入同仁資料
  const loadStaff = useCallback(async () => {
    if (!staffId) return;
    setLoading(true);
    try {
      const user = await apiClient.post(API_ENDPOINTS.USERS.DETAIL(staffId));
      const response = { items: [user] };
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const data = response as any;
      const items = data.items || data.users || [];
      const found = items.find((s: Staff) => s.id === staffId);
      if (found) {
        setStaff(found);
        form.setFieldsValue({
          username: found.username,
          email: found.email,
          full_name: found.full_name,
          is_active: found.is_active,
          department: found.department,
          position: found.position,
        });
      } else {
        message.error('找不到此承辦同仁');
        navigate(ROUTES.STAFF);
      }
    } catch (error) {
      logger.error('載入同仁資料失敗:', error);
      message.error('載入資料失敗');
    } finally {
      setLoading(false);
    }
  }, [staffId, form, message, navigate]);

  // 載入證照
  const loadCertifications = useCallback(async () => {
    if (!staffId) return;
    setCertLoading(true);
    try {
      const response = await certificationsApi.getUserCertifications(staffId);
      setCertifications(response.items);
    } catch (error) {
      logger.error('載入證照列表失敗:', error);
      // 重要：錯誤時不清空現有列表，避免「紀錄消失」問題
      // setCertifications([]);
      message.error('載入證照列表失敗');
    } finally {
      setCertLoading(false);
    }
  }, [staffId, message]);

  useEffect(() => {
    loadStaff();
    loadCertifications();
  }, [loadStaff, loadCertifications]);

  // 儲存基本資料
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

  // 取消編輯
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

  // 刪除同仁
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

  // === 證照操作（導航模式） ===
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

  // 預覽附件
  const handlePreviewAttachment = (cert: Certification) => {
    if (cert.attachment_path) {
      // 使用 uploads 目錄路徑
      const attachmentUrl = `${SERVER_BASE_URL}/uploads/${cert.attachment_path}`;
      window.open(attachmentUrl, '_blank');
    } else {
      message.info('此證照沒有附件');
    }
  };

  // 顏色映射
  const getCertTypeColor = (type: string) => {
    switch (type) {
      case '核發證照': return 'blue';
      case '評量證書': return 'green';
      case '訓練證明': return 'orange';
      default: return 'default';
    }
  };

  const getCertStatusColor = (status: string) => {
    switch (status) {
      case '有效': return 'success';
      case '已過期': return 'error';
      case '已撤銷': return 'default';
      default: return 'default';
    }
  };

  if (loading) {
    return (
      <div style={{ padding: pagePadding, textAlign: 'center' }}>
        <Spin size={isMobile ? 'default' : 'large'} />
      </div>
    );
  }

  if (!staff) {
    return (
      <div style={{ padding: pagePadding }}>
        <Empty description="找不到此承辦同仁" />
      </div>
    );
  }

  return (
    <div style={{ padding: pagePadding }}>
      {/* 頁面標題 */}
      <Card size={isMobile ? 'small' : 'default'} style={{ marginBottom: isMobile ? 8 : 16 }}>
        <div style={{
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          justifyContent: 'space-between',
          alignItems: isMobile ? 'stretch' : 'center',
          gap: isMobile ? 8 : 0
        }}>
          <Space wrap size={isMobile ? 'small' : 'middle'}>
            <Button
              icon={<ArrowLeftOutlined />}
              size={isMobile ? 'small' : 'middle'}
              onClick={() => navigate(ROUTES.STAFF)}
            >
              {isMobile ? '返回' : '返回列表'}
            </Button>
            <Title level={isMobile ? 5 : 4} style={{ margin: 0 }}>
              <UserOutlined style={{ marginRight: 8 }} />
              {staff.full_name || staff.username}
            </Title>
            <Tag color={staff.is_active ? 'success' : 'default'}>
              {staff.is_active ? '啟用中' : '已停用'}
            </Tag>
          </Space>
          {!isEditing && (
            <Space size={isMobile ? 'small' : 'middle'} style={{ width: isMobile ? '100%' : 'auto' }}>
              <Button
                type="primary"
                icon={<EditOutlined />}
                size={isMobile ? 'small' : 'middle'}
                onClick={() => setIsEditing(true)}
                style={isMobile ? { flex: 1 } : undefined}
              >
                編輯
              </Button>
              <Popconfirm
                title="確定要刪除此承辦同仁？"
                description="刪除後將無法復原"
                onConfirm={handleDelete}
                okText="確定"
                cancelText="取消"
                okButtonProps={{ danger: true }}
              >
                <Button
                  danger
                  icon={<DeleteOutlined />}
                  size={isMobile ? 'small' : 'middle'}
                  style={isMobile ? { flex: 1 } : undefined}
                >
                  {isMobile ? '' : '刪除'}
                </Button>
              </Popconfirm>
            </Space>
          )}
        </div>
      </Card>

      {/* Tab 分頁 */}
      <Card size={isMobile ? 'small' : 'default'}>
        <Tabs
          size={isMobile ? 'small' : 'middle'}
          items={[
            {
              key: 'basic',
              label: (
                <span>
                  <UserOutlined /> 基本資料
                </span>
              ),
              children: isEditing ? (
                // 編輯模式
                <Form form={form} layout="vertical">
                  <Row gutter={16}>
                    <Col xs={24} sm={12}>
                      <Form.Item
                        name="full_name"
                        label="姓名"
                        rules={[{ required: true, message: '請輸入姓名' }]}
                      >
                        <Input prefix={<UserOutlined />} placeholder="請輸入姓名" />
                      </Form.Item>
                    </Col>
                    <Col xs={24} sm={12}>
                      <Form.Item name="username" label="帳號">
                        <Input disabled />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Form.Item
                    name="email"
                    label="Email"
                    rules={[
                      { required: true, message: '請輸入 Email' },
                      { type: 'email', message: '請輸入有效的 Email' },
                    ]}
                  >
                    <Input prefix={<MailOutlined />} placeholder="請輸入 Email" />
                  </Form.Item>

                  <Row gutter={16}>
                    <Col xs={24} sm={12}>
                      <Form.Item name="department" label="部門">
                        <Select placeholder="請選擇部門" allowClear>
                          {DEPARTMENT_OPTIONS.map(dept => (
                            <Option key={dept} value={dept}>{dept}</Option>
                          ))}
                        </Select>
                      </Form.Item>
                    </Col>
                    <Col xs={24} sm={12}>
                      <Form.Item name="position" label="職稱">
                        <Input prefix={<IdcardOutlined />} placeholder="請輸入職稱" />
                      </Form.Item>
                    </Col>
                  </Row>

                  <Form.Item label="密碼管理">
                    <Space>
                      <Switch
                        checked={showPasswordChange}
                        onChange={setShowPasswordChange}
                        checkedChildren="修改密碼"
                        unCheckedChildren="保持不變"
                      />
                      {!showPasswordChange && (
                        <Text type="secondary">
                          <KeyOutlined /> 如需修改密碼請開啟此選項
                        </Text>
                      )}
                    </Space>
                  </Form.Item>

                  {showPasswordChange && (
                    <Form.Item
                      name="password"
                      label="新密碼"
                      rules={[
                        { required: true, message: '請輸入新密碼' },
                        { min: 6, message: '密碼至少 6 個字元' },
                      ]}
                    >
                      <Input.Password prefix={<LockOutlined />} placeholder="請輸入新密碼" />
                    </Form.Item>
                  )}

                  <Form.Item name="is_active" label="狀態" valuePropName="checked">
                    <Switch checkedChildren="啟用" unCheckedChildren="停用" />
                  </Form.Item>

                  <div style={{ textAlign: isMobile ? 'center' : 'right' }}>
                    <Space size={isMobile ? 'small' : 'middle'}>
                      <Button
                        icon={<CloseOutlined />}
                        size={isMobile ? 'small' : 'middle'}
                        onClick={handleCancelEdit}
                      >
                        取消
                      </Button>
                      <Button
                        type="primary"
                        icon={<SaveOutlined />}
                        size={isMobile ? 'small' : 'middle'}
                        onClick={handleSave}
                        loading={saving}
                      >
                        儲存
                      </Button>
                    </Space>
                  </div>
                </Form>
              ) : (
                // 檢視模式
                <Descriptions column={{ xs: 1, sm: 2 }} bordered>
                  <Descriptions.Item label="姓名">{staff.full_name || '-'}</Descriptions.Item>
                  <Descriptions.Item label="帳號">{staff.username}</Descriptions.Item>
                  <Descriptions.Item label="Email">
                    <a href={`mailto:${staff.email}`}>{staff.email}</a>
                  </Descriptions.Item>
                  <Descriptions.Item label="部門">
                    {staff.department ? (
                      <Tag icon={<BankOutlined />} color="blue">{staff.department}</Tag>
                    ) : '-'}
                  </Descriptions.Item>
                  <Descriptions.Item label="職稱">{staff.position || '-'}</Descriptions.Item>
                  <Descriptions.Item label="狀態">
                    <Tag color={staff.is_active ? 'success' : 'default'}>
                      {staff.is_active ? '啟用中' : '已停用'}
                    </Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="最後登入" span={2}>
                    {staff.last_login ? new Date(staff.last_login).toLocaleString('zh-TW') : '尚未登入'}
                  </Descriptions.Item>
                </Descriptions>
              ),
            },
            {
              key: 'certifications',
              label: (
                <span>
                  <SafetyCertificateOutlined /> 證照紀錄 ({certifications.length})
                </span>
              ),
              children: (
                <div>
                  {certLoading ? (
                    <div style={{ textAlign: 'center', padding: isMobile ? 20 : 40 }}>
                      <Spin size={isMobile ? 'default' : 'large'} />
                    </div>
                  ) : certifications.length === 0 ? (
                    <Empty description="尚無證照紀錄">
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        size={isMobile ? 'small' : 'middle'}
                        onClick={handleAddCert}
                      >
                        新增證照
                      </Button>
                    </Empty>
                  ) : (
                    <Table
                      dataSource={certifications}
                      rowKey="id"
                      size="small"
                      scroll={{ x: isMobile ? 500 : undefined }}
                      pagination={false}
                      title={() => (
                        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                          <Button
                            type="primary"
                            icon={<PlusOutlined />}
                            size="small"
                            onClick={handleAddCert}
                          >
                            新增證照
                          </Button>
                        </div>
                      )}
                      columns={[
                        {
                          title: '類型',
                          dataIndex: 'cert_type',
                          key: 'cert_type',
                          width: 90,
                          render: (type: string) => (
                            <Tag color={getCertTypeColor(type)}>{type}</Tag>
                          ),
                        },
                        {
                          title: '證照名稱',
                          dataIndex: 'cert_name',
                          key: 'cert_name',
                          ellipsis: true,
                        },
                        {
                          title: '核發機關',
                          dataIndex: 'issuing_authority',
                          key: 'issuing_authority',
                          width: 120,
                          ellipsis: true,
                          render: (text: string) => text || '-',
                        },
                        {
                          title: '狀態',
                          dataIndex: 'status',
                          key: 'status',
                          width: 70,
                          render: (status: string) => (
                            <Tag color={getCertStatusColor(status)}>{status}</Tag>
                          ),
                        },
                        {
                          title: '附件',
                          dataIndex: 'attachment_path',
                          key: 'attachment',
                          width: 60,
                          render: (path: string, record: Certification) => (
                            path ? (
                              <Button
                                type="link"
                                size="small"
                                icon={<EyeOutlined />}
                                onClick={() => handlePreviewAttachment(record)}
                              />
                            ) : (
                              <Text type="secondary">-</Text>
                            )
                          ),
                        },
                        {
                          title: '操作',
                          key: 'action',
                          width: 120,
                          render: (_: unknown, record: Certification) => (
                            <Space size="small">
                              <Button
                                type="link"
                                size="small"
                                icon={<EditOutlined />}
                                onClick={() => handleEditCert(record)}
                              >
                                編輯
                              </Button>
                              <Popconfirm
                                title="確定要刪除此證照？"
                                onConfirm={() => handleDeleteCert(record.id)}
                                okText="確定"
                                cancelText="取消"
                                okButtonProps={{ danger: true }}
                              >
                                <Button
                                  type="link"
                                  size="small"
                                  danger
                                  icon={<DeleteOutlined />}
                                />
                              </Popconfirm>
                            </Space>
                          ),
                        },
                      ]}
                    />
                  )}
                </div>
              ),
            },
          ]}
        />
      </Card>
    </div>
  );
};

export default StaffDetailPage;
