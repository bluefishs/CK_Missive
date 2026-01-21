/**
 * 承辦同仁管理頁面
 * @description 提供承辦同仁的 CRUD 維護功能，含證照紀錄管理
 */
import React, { useState, useEffect, useCallback } from 'react';
import type { TableColumnType } from 'antd';
import {
  Table,
  Button,
  Input,
  Space,
  Card,
  Modal,
  Form,
  Select,
  Typography,
  Popconfirm,
  Row,
  Col,
  Statistic,
  App,
  Tooltip,
  Switch,
  Tabs,
  DatePicker,
  Tag,
  Empty,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  DeleteOutlined,
  UserOutlined,
  MailOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  LockOutlined,
  KeyOutlined,
  EditOutlined,
  SafetyCertificateOutlined,
  BankOutlined,
  IdcardOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { useTableColumnSearch } from '../hooks';
import { certificationsApi, Certification, CertificationCreate, CertificationUpdate, CERT_TYPES, CERT_STATUS } from '../api/certificationsApi';

const { Title } = Typography;
const { Option } = Select;

// 注意：專案角色在「承攬案件詳情頁」中管理
// 同一位同仁可在不同專案擔任不同角色 (計畫主持、計畫協同、專案PM、職安主管)
// 此頁面僅管理基本帳號資訊，不顯示專案角色

// 輔助函數：提取錯誤訊息
const extractErrorMessage = (error: any): string => {
  const detail = error?.response?.data?.detail;
  if (!detail) return '操作失敗，請稍後再試';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    // Pydantic 驗證錯誤格式
    return detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
  }
  return JSON.stringify(detail);
};

// ---[型別定義]---
import type { User } from '../types/api';

/**
 * Staff 型別別名 - 使用 User 作為統一型別來源
 * 承辦同仁本質上是系統使用者，使用相同的資料結構
 */
type Staff = User;

// 使用表格搜尋 Hook
const useStaffTableSearch = () => useTableColumnSearch<Staff>();

// 部門選項
const DEPARTMENT_OPTIONS = ['空間資訊部', '測量部', '管理部'];

/**
 * 表單資料類型 (專案角色在承攬案件詳情頁管理)
 * 僅包含表單編輯所需的欄位
 */
interface StaffFormData {
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  password?: string;
  department?: string;
  position?: string;
}

export const StaffPage: React.FC = () => {
  const { message } = App.useApp();
  const { getColumnSearchProps } = useStaffTableSearch();

  // 列表狀態
  const [staffList, setStaffList] = useState<Staff[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [current, setCurrent] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // 篩選狀態
  const [searchText, setSearchText] = useState('');
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>();

  // Modal 狀態
  const [modalVisible, setModalVisible] = useState(false);
  const [editingStaff, setEditingStaff] = useState<Staff | null>(null);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [showPasswordChange, setShowPasswordChange] = useState(false);
  const [activeTab, setActiveTab] = useState('basic');

  // 證照狀態
  const [certifications, setCertifications] = useState<Certification[]>([]);
  const [certLoading, setCertLoading] = useState(false);
  const [certModalVisible, setCertModalVisible] = useState(false);
  const [editingCert, setEditingCert] = useState<Certification | null>(null);
  const [certForm] = Form.useForm();

  // 統計資料
  const [stats, setStats] = useState({
    total: 0,
    active: 0,
    inactive: 0,
  });

  // 載入承辦同仁列表 (POST-only 資安機制)
  const loadStaffList = useCallback(async () => {
    setLoading(true);
    try {
      const requestBody: Record<string, any> = {
        skip: (current - 1) * pageSize,
        limit: pageSize,
      };

      if (searchText) requestBody.search = searchText;
      if (activeFilter !== undefined) requestBody.is_active = activeFilter;

      // POST-only: 使用 POST /users/list 端點
      const response = await apiClient.post(API_ENDPOINTS.USERS.LIST, requestBody);
      const data = response as any;

      // API 回傳 items 欄位
      const items = data.items || data.users || [];
      setStaffList(Array.isArray(items) ? items : []);
      setTotal(data.total || 0);

      // 更新統計
      const activeCount = items.filter((s: Staff) => s.is_active).length;
      setStats({
        total: data.total || items.length,
        active: activeCount,
        inactive: (data.total || items.length) - activeCount,
      });
    } catch (error) {
      console.error('載入承辦同仁列表失敗:', error);
      message.error('載入資料失敗，請稍後再試');
    } finally {
      setLoading(false);
    }
  }, [current, pageSize, searchText, activeFilter, message]);

  useEffect(() => {
    loadStaffList();
  }, [loadStaffList]);

  // 載入證照列表
  const loadCertifications = useCallback(async (userId: number) => {
    setCertLoading(true);
    try {
      const response = await certificationsApi.getUserCertifications(userId);
      setCertifications(response.items);
    } catch (error) {
      console.error('載入證照列表失敗:', error);
      setCertifications([]);
    } finally {
      setCertLoading(false);
    }
  }, []);

  // 當編輯的同仁變更時，載入其證照
  useEffect(() => {
    if (editingStaff) {
      loadCertifications(editingStaff.id);
    } else {
      setCertifications([]);
    }
  }, [editingStaff, loadCertifications]);

  // 新增或編輯承辦同仁 (POST-only 資安機制)
  const handleSubmit = async (values: StaffFormData) => {
    setSubmitLoading(true);
    try {
      if (editingStaff) {
        // 更新 (POST-only)
        // 如果沒有選擇修改密碼，則移除 password 欄位
        const updateData = { ...values };
        if (!showPasswordChange) {
          delete updateData.password;
        }
        await apiClient.post(API_ENDPOINTS.USERS.UPDATE(editingStaff.id), updateData);
        message.success(showPasswordChange ? '承辦同仁資料與密碼已更新' : '承辦同仁更新成功');
      } else {
        // 新增 (POST-only)
        await apiClient.post(API_ENDPOINTS.USERS.CREATE, values);
        message.success('承辦同仁建立成功');
      }

      setModalVisible(false);
      setEditingStaff(null);
      setShowPasswordChange(false);
      loadStaffList();
    } catch (error: any) {
      console.error('操作失敗:', error);
      message.error(extractErrorMessage(error));
    } finally {
      setSubmitLoading(false);
    }
  };

  // 刪除承辦同仁 (POST 機制)
  const handleDelete = async (id: number) => {
    try {
      await apiClient.post(API_ENDPOINTS.USERS.DELETE(id));
      message.success('承辦同仁刪除成功');
      loadStaffList();
    } catch (error: any) {
      console.error('刪除失敗:', error);
      message.error(extractErrorMessage(error));
    }
  };

  // 切換啟用狀態 (POST 機制)
  const handleToggleActive = async (id: number, isActive: boolean) => {
    try {
      await apiClient.post(API_ENDPOINTS.USERS.STATUS(id), { is_active: isActive });
      message.success(isActive ? '已啟用' : '已停用');
      loadStaffList();
    } catch (error: any) {
      console.error('狀態更新失敗:', error);
      message.error('狀態更新失敗');
    }
  };

  // === 證照相關操作 ===
  // 新增證照
  const handleAddCert = () => {
    setEditingCert(null);
    certForm.resetFields();
    certForm.setFieldsValue({ status: '有效' });
    setCertModalVisible(true);
  };

  // 編輯證照
  const handleEditCert = (cert: Certification) => {
    setEditingCert(cert);
    certForm.setFieldsValue({
      ...cert,
      issue_date: cert.issue_date ? dayjs(cert.issue_date) : undefined,
      expiry_date: cert.expiry_date ? dayjs(cert.expiry_date) : undefined,
    });
    setCertModalVisible(true);
  };

  // 刪除證照
  const handleDeleteCert = async (certId: number) => {
    try {
      await certificationsApi.delete(certId);
      message.success('證照刪除成功');
      if (editingStaff) {
        loadCertifications(editingStaff.id);
      }
    } catch (error: any) {
      console.error('刪除證照失敗:', error);
      message.error('刪除證照失敗');
    }
  };

  // 提交證照表單
  const handleCertSubmit = async (values: any) => {
    if (!editingStaff) return;

    try {
      const certData = {
        ...values,
        issue_date: values.issue_date?.format('YYYY-MM-DD'),
        expiry_date: values.expiry_date?.format('YYYY-MM-DD'),
      };

      if (editingCert) {
        // 更新
        await certificationsApi.update(editingCert.id, certData as CertificationUpdate);
        message.success('證照更新成功');
      } else {
        // 新增
        await certificationsApi.create({
          ...certData,
          user_id: editingStaff.id,
        } as CertificationCreate);
        message.success('證照新增成功');
      }

      setCertModalVisible(false);
      setEditingCert(null);
      certForm.resetFields();
      loadCertifications(editingStaff.id);
    } catch (error: any) {
      console.error('證照操作失敗:', error);
      message.error(extractErrorMessage(error));
    }
  };

  // 開啟編輯模態框
  const handleEdit = (staff: Staff) => {
    setEditingStaff(staff);
    setShowPasswordChange(false);
    setActiveTab('basic');
    setModalVisible(true);
  };

  // 開啟新增模態框
  const handleAdd = () => {
    setEditingStaff(null);
    setShowPasswordChange(false);
    setActiveTab('basic');
    setModalVisible(true);
  };

  // 證照類型顏色映射
  const getCertTypeColor = (type: string) => {
    switch (type) {
      case '核發證照': return 'blue';
      case '評量證書': return 'green';
      case '訓練證明': return 'orange';
      default: return 'default';
    }
  };

  // 證照狀態顏色映射
  const getCertStatusColor = (status: string) => {
    switch (status) {
      case '有效': return 'success';
      case '已過期': return 'error';
      case '已撤銷': return 'default';
      default: return 'default';
    }
  };

  // 表格欄位定義
  const columns: TableColumnType<Staff>[] = [
    {
      title: '姓名',
      dataIndex: 'full_name',
      key: 'full_name',
      width: 150,
      sorter: (a, b) => (a.full_name || '').localeCompare(b.full_name || '', 'zh-TW'),
      ...getColumnSearchProps('full_name'),
      render: (text: string, record: Staff) => (
        <Space>
          <UserOutlined />
          <span>{text || record.username}</span>
        </Space>
      ),
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      width: 220,
      sorter: (a, b) => a.email.localeCompare(b.email),
      ...getColumnSearchProps('email'),
      render: (email: string) => (
        <Space>
          <MailOutlined />
          <a href={`mailto:${email}`}>{email}</a>
        </Space>
      ),
    },
    {
      title: '帳號',
      dataIndex: 'username',
      key: 'username',
      width: 100,
      sorter: (a, b) => a.username.localeCompare(b.username),
      ...getColumnSearchProps('username'),
    },
    {
      title: '部門',
      dataIndex: 'department',
      key: 'department',
      width: 110,
      sorter: (a, b) => (a.department || '').localeCompare(b.department || '', 'zh-TW'),
      filters: DEPARTMENT_OPTIONS.map(d => ({ text: d, value: d })),
      onFilter: (value, record) => record.department === value,
      render: (dept: string) => dept ? (
        <Tag icon={<BankOutlined />} color="blue">{dept}</Tag>
      ) : '-',
    },
    {
      title: '職稱',
      dataIndex: 'position',
      key: 'position',
      width: 100,
      sorter: (a, b) => (a.position || '').localeCompare(b.position || '', 'zh-TW'),
      render: (pos: string) => pos || '-',
    },
    {
      title: '狀態',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 100,
      sorter: (a, b) => Number(a.is_active) - Number(b.is_active),
      filters: [
        { text: '啟用中', value: true },
        { text: '已停用', value: false },
      ],
      onFilter: (value, record) => record.is_active === value,
      render: (isActive: boolean, record: Staff) => (
        <Switch
          checked={isActive}
          onChange={(checked) => handleToggleActive(record.id, checked)}
          checkedChildren={<CheckCircleOutlined />}
          unCheckedChildren={<CloseCircleOutlined />}
        />
      ),
    },
    {
      title: '最後登入',
      dataIndex: 'last_login',
      key: 'last_login',
      width: 160,
      sorter: (a, b) => {
        if (!a.last_login) return 1;
        if (!b.last_login) return -1;
        return new Date(a.last_login).getTime() - new Date(b.last_login).getTime();
      },
      render: (date: string) => date ? new Date(date).toLocaleString('zh-TW') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      fixed: 'right',
      render: (_, record: Staff) => (
        <Popconfirm
          title="確定要刪除此承辦同仁？"
          description="刪除後將無法復原"
          onConfirm={(e) => {
            e?.stopPropagation();
            handleDelete(record.id);
          }}
          onCancel={(e) => e?.stopPropagation()}
          okText="確定"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Tooltip title="刪除">
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => e.stopPropagation()}
            />
          </Tooltip>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div style={{ padding: 24 }}>
      {/* 頁面標題 */}
      <Title level={3}>
        <TeamOutlined style={{ marginRight: 8 }} />
        承辦同仁管理
      </Title>

      {/* 統計卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic title="總人數" value={stats.total} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="啟用中"
              value={stats.active}
              valueStyle={{ color: '#3f8600' }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="已停用"
              value={stats.inactive}
              valueStyle={{ color: '#999' }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 主要內容卡片 */}
      <Card>
        {/* 工具列 */}
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col flex="auto">
            <Space wrap>
              <Input
                placeholder="搜尋姓名、帳號、Email..."
                prefix={<SearchOutlined />}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                style={{ width: 250 }}
                allowClear
              />
              <Select
                placeholder="狀態篩選"
                value={activeFilter}
                onChange={(v) => setActiveFilter(v)}
                style={{ width: 120 }}
                allowClear
              >
                <Option value={true}>啟用中</Option>
                <Option value={false}>已停用</Option>
              </Select>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={loadStaffList}
              >
                重新整理
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleAdd}
              >
                新增同仁
              </Button>
            </Space>
          </Col>
        </Row>

        {/* 資料表格 */}
        <Table
          columns={columns}
          dataSource={staffList}
          rowKey="id"
          loading={loading}
          scroll={{ x: 1000 }}
          onRow={(record) => ({
            onClick: () => handleEdit(record),
            style: { cursor: 'pointer' },
          })}
          pagination={{
            current,
            pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (t) => `共 ${t} 筆`,
            onChange: (page, size) => {
              setCurrent(page);
              setPageSize(size);
            },
          }}
        />
      </Card>

      {/* 新增/編輯 Modal */}
      <Modal
        key={editingStaff?.id ?? 'new'}
        title={editingStaff ? `編輯承辦同仁 - ${editingStaff.full_name || editingStaff.username}` : '新增承辦同仁'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingStaff(null);
          setShowPasswordChange(false);
          setActiveTab('basic');
        }}
        footer={null}
        width={700}
        destroyOnHidden
      >
        {editingStaff ? (
          // 編輯模式：顯示 Tab
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              {
                key: 'basic',
                label: (
                  <span>
                    <UserOutlined /> 基本資料
                  </span>
                ),
                children: (
                  <Form
                    layout="vertical"
                    onFinish={handleSubmit}
                    initialValues={{
                      username: editingStaff.username,
                      email: editingStaff.email,
                      full_name: editingStaff.full_name,
                      is_active: editingStaff.is_active,
                      department: editingStaff.department,
                      position: editingStaff.position,
                    }}
                  >
                    <Row gutter={16}>
                      <Col span={12}>
                        <Form.Item
                          name="full_name"
                          label="姓名"
                          rules={[{ required: true, message: '請輸入姓名' }]}
                        >
                          <Input prefix={<UserOutlined />} placeholder="請輸入姓名" />
                        </Form.Item>
                      </Col>
                      <Col span={12}>
                        <Form.Item
                          name="username"
                          label="帳號"
                          rules={[{ required: true, message: '請輸入帳號' }]}
                        >
                          <Input placeholder="請輸入帳號" disabled />
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
                      <Col span={12}>
                        <Form.Item name="department" label="部門">
                          <Select placeholder="請選擇部門" allowClear>
                            {DEPARTMENT_OPTIONS.map(dept => (
                              <Option key={dept} value={dept}>{dept}</Option>
                            ))}
                          </Select>
                        </Form.Item>
                      </Col>
                      <Col span={12}>
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
                          <Typography.Text type="secondary">
                            <KeyOutlined /> 如需修改密碼請開啟此選項
                          </Typography.Text>
                        )}
                      </Space>
                    </Form.Item>

                    {showPasswordChange && (
                      <Form.Item
                        name="password"
                        label="新密碼"
                        rules={[
                          { required: showPasswordChange, message: '請輸入新密碼' },
                          { min: 6, message: '密碼至少6個字元' },
                        ]}
                      >
                        <Input.Password prefix={<LockOutlined />} placeholder="請輸入新密碼" />
                      </Form.Item>
                    )}

                    <Form.Item
                      name="is_active"
                      label="狀態"
                      valuePropName="checked"
                    >
                      <Switch checkedChildren="啟用" unCheckedChildren="停用" />
                    </Form.Item>

                    <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
                      <Space>
                        <Button onClick={() => setModalVisible(false)}>取消</Button>
                        <Button type="primary" htmlType="submit" loading={submitLoading}>
                          更新
                        </Button>
                      </Space>
                    </Form.Item>
                  </Form>
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
                      <div style={{ textAlign: 'center', padding: 40 }}>載入中...</div>
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
        ) : (
          // 新增模式：只顯示基本表單
          <Form
            layout="vertical"
            onFinish={handleSubmit}
            initialValues={{ is_active: true }}
          >
            <Row gutter={16}>
              <Col span={12}>
                <Form.Item
                  name="full_name"
                  label="姓名"
                  rules={[{ required: true, message: '請輸入姓名' }]}
                >
                  <Input prefix={<UserOutlined />} placeholder="請輸入姓名" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item
                  name="username"
                  label="帳號"
                  rules={[
                    { required: true, message: '請輸入帳號' },
                    { min: 3, message: '帳號至少3個字元' },
                  ]}
                >
                  <Input placeholder="請輸入帳號" />
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
              <Col span={12}>
                <Form.Item name="department" label="部門">
                  <Select placeholder="請選擇部門" allowClear>
                    {DEPARTMENT_OPTIONS.map(dept => (
                      <Option key={dept} value={dept}>{dept}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="position" label="職稱">
                  <Input prefix={<IdcardOutlined />} placeholder="請輸入職稱" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item
              name="password"
              label="密碼"
              rules={[
                { required: true, message: '請輸入密碼' },
                { min: 6, message: '密碼至少6個字元' },
              ]}
            >
              <Input.Password prefix={<LockOutlined />} placeholder="請輸入密碼" />
            </Form.Item>

            <Form.Item
              name="is_active"
              label="狀態"
              valuePropName="checked"
            >
              <Switch checkedChildren="啟用" unCheckedChildren="停用" />
            </Form.Item>

            <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
              <Space>
                <Button onClick={() => setModalVisible(false)}>取消</Button>
                <Button type="primary" htmlType="submit" loading={submitLoading}>
                  建立
                </Button>
              </Space>
            </Form.Item>
          </Form>
        )}
      </Modal>

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
        <Form
          form={certForm}
          layout="vertical"
          onFinish={handleCertSubmit}
        >
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

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setCertModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">
                {editingCert ? '更新' : '新增'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default StaffPage;
