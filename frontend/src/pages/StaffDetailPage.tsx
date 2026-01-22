/**
 * 承辦同仁詳情頁面
 * @description 顯示同仁詳情，含 Tab 分頁（基本資料、證照紀錄）
 * @version 1.0.0
 * @date 2026-01-22
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
  Tooltip,
  Modal,
  DatePicker,
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
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { ROUTES } from '../router/types';
import {
  certificationsApi,
  Certification,
  CertificationCreate,
  CertificationUpdate,
  CERT_TYPES,
  CERT_STATUS,
} from '../api/certificationsApi';
import type { User } from '../types/api';

const { Title, Text } = Typography;
const { Option } = Select;

type Staff = User;

// 部門選項
const DEPARTMENT_OPTIONS = ['空間資訊部', '測量部', '管理部'];

// 輔助函數：提取錯誤訊息
const extractErrorMessage = (error: any): string => {
  const detail = error?.response?.data?.detail;
  if (!detail) return '操作失敗，請稍後再試';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
  }
  return JSON.stringify(detail);
};

export const StaffDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [certForm] = Form.useForm();

  const staffId = id ? parseInt(id, 10) : undefined;

  // 狀態
  const [staff, setStaff] = useState<Staff | null>(null);
  const [loading, setLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [showPasswordChange, setShowPasswordChange] = useState(false);

  // 證照狀態
  const [certifications, setCertifications] = useState<Certification[]>([]);
  const [certLoading, setCertLoading] = useState(false);
  const [certModalVisible, setCertModalVisible] = useState(false);
  const [editingCert, setEditingCert] = useState<Certification | null>(null);

  // 載入同仁資料
  const loadStaff = useCallback(async () => {
    if (!staffId) return;
    setLoading(true);
    try {
      // 使用 detail API 直接取得指定 ID 的使用者
      const user = await apiClient.post(API_ENDPOINTS.USERS.DETAIL(staffId));
      const response = { items: [user] };
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
      console.error('載入同仁資料失敗:', error);
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
      console.error('載入證照列表失敗:', error);
      setCertifications([]);
    } finally {
      setCertLoading(false);
    }
  }, [staffId]);

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

      const updateData = { ...values };
      if (!showPasswordChange) {
        delete updateData.password;
      }

      await apiClient.post(API_ENDPOINTS.USERS.UPDATE(staffId), updateData);
      message.success(showPasswordChange ? '資料與密碼已更新' : '資料更新成功');
      setIsEditing(false);
      setShowPasswordChange(false);
      loadStaff();
    } catch (error: any) {
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

  // === 證照操作 ===
  const handleAddCert = () => {
    setEditingCert(null);
    certForm.resetFields();
    certForm.setFieldsValue({ status: '有效' });
    setCertModalVisible(true);
  };

  const handleEditCert = (cert: Certification) => {
    setEditingCert(cert);
    certForm.setFieldsValue({
      ...cert,
      issue_date: cert.issue_date ? dayjs(cert.issue_date) : undefined,
      expiry_date: cert.expiry_date ? dayjs(cert.expiry_date) : undefined,
    });
    setCertModalVisible(true);
  };

  const handleDeleteCert = async (certId: number) => {
    try {
      await certificationsApi.delete(certId);
      message.success('證照刪除成功');
      loadCertifications();
    } catch (error) {
      message.error('刪除證照失敗');
    }
  };

  const handleCertSubmit = async (values: any) => {
    if (!staffId) return;
    try {
      const certData = {
        ...values,
        issue_date: values.issue_date?.format('YYYY-MM-DD'),
        expiry_date: values.expiry_date?.format('YYYY-MM-DD'),
      };

      if (editingCert) {
        await certificationsApi.update(editingCert.id, certData as CertificationUpdate);
        message.success('證照更新成功');
      } else {
        await certificationsApi.create({
          ...certData,
          user_id: staffId,
        } as CertificationCreate);
        message.success('證照新增成功');
      }

      setCertModalVisible(false);
      setEditingCert(null);
      certForm.resetFields();
      loadCertifications();
    } catch (error) {
      message.error(extractErrorMessage(error));
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
      <div style={{ padding: 24, textAlign: 'center' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!staff) {
    return (
      <div style={{ padding: 24 }}>
        <Empty description="找不到此承辦同仁" />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      {/* 頁面標題 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Space>
            <Button
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate(ROUTES.STAFF)}
            >
              返回列表
            </Button>
            <Title level={4} style={{ margin: 0 }}>
              <UserOutlined style={{ marginRight: 8 }} />
              {staff.full_name || staff.username}
            </Title>
            <Tag color={staff.is_active ? 'success' : 'default'}>
              {staff.is_active ? '啟用中' : '已停用'}
            </Tag>
          </Space>
          {!isEditing && (
            <Button type="primary" icon={<EditOutlined />} onClick={() => setIsEditing(true)}>
              編輯
            </Button>
          )}
        </div>
      </Card>

      {/* Tab 分頁 */}
      <Card>
        <Tabs
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

                  <div style={{ textAlign: 'right' }}>
                    <Space>
                      <Button icon={<CloseOutlined />} onClick={handleCancelEdit}>
                        取消
                      </Button>
                      <Button
                        type="primary"
                        icon={<SaveOutlined />}
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
                  <div style={{ marginBottom: 16 }}>
                    <Button type="primary" icon={<PlusOutlined />} onClick={handleAddCert}>
                      新增證照
                    </Button>
                  </div>

                  {certLoading ? (
                    <div style={{ textAlign: 'center', padding: 40 }}>
                      <Spin />
                    </div>
                  ) : certifications.length === 0 ? (
                    <Empty description="尚無證照紀錄" />
                  ) : (
                    <Table
                      dataSource={certifications}
                      rowKey="id"
                      size="small"
                      pagination={false}
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
                          title: '操作',
                          key: 'action',
                          width: 100,
                          render: (_: any, record: Certification) => (
                            <Space size="small">
                              <Tooltip title="編輯">
                                <Button
                                  type="link"
                                  size="small"
                                  icon={<EditOutlined />}
                                  onClick={() => handleEditCert(record)}
                                />
                              </Tooltip>
                              <Popconfirm
                                title="確定要刪除此證照？"
                                onConfirm={() => handleDeleteCert(record.id)}
                                okText="確定"
                                cancelText="取消"
                              >
                                <Tooltip title="刪除">
                                  <Button
                                    type="link"
                                    size="small"
                                    danger
                                    icon={<DeleteOutlined />}
                                  />
                                </Tooltip>
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

      {/* 證照新增/編輯 Modal */}
      <Modal
        title={editingCert ? '編輯證照' : '新增證照'}
        open={certModalVisible}
        onCancel={() => {
          setCertModalVisible(false);
          setEditingCert(null);
          certForm.resetFields();
        }}
        footer={null}
        width={500}
        destroyOnHidden
      >
        <Form form={certForm} layout="vertical" onFinish={handleCertSubmit}>
          <Form.Item
            name="cert_type"
            label="證照類型"
            rules={[{ required: true, message: '請選擇證照類型' }]}
          >
            <Select placeholder="請選擇證照類型">
              {CERT_TYPES.map(type => (
                <Option key={type} value={type}>{type}</Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="cert_name"
            label="證照名稱"
            rules={[{ required: true, message: '請輸入證照名稱' }]}
          >
            <Input placeholder="請輸入證照名稱" />
          </Form.Item>

          <Form.Item name="issuing_authority" label="核發機關">
            <Input placeholder="請輸入核發機關" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="cert_number" label="證照編號">
                <Input placeholder="請輸入證照編號" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="status" label="狀態">
                <Select placeholder="請選擇狀態">
                  {CERT_STATUS.map(s => (
                    <Option key={s} value={s}>{s}</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="issue_date" label="核發日期">
                <DatePicker style={{ width: '100%' }} placeholder="請選擇核發日期" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="expiry_date" label="有效期限">
                <DatePicker style={{ width: '100%' }} placeholder="永久有效可不填" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} placeholder="請輸入備註" />
          </Form.Item>

          <div style={{ textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setCertModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                {editingCert ? '更新' : '新增'}
              </Button>
            </Space>
          </div>
        </Form>
      </Modal>
    </div>
  );
};

export default StaffDetailPage;
