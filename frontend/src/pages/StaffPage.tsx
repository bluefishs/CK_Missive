/**
 * 承辦同仁管理頁面
 * @description 提供承辦同仁的 CRUD 維護功能
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
} from '@ant-design/icons';
import { apiClient } from '../api/client';
import { useTableColumnSearch } from '../hooks/useTableColumnSearch';

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

// 使用表格搜尋 Hook
const useStaffTableSearch = () => useTableColumnSearch<Staff>();

// 承辦同仁資料類型
interface Staff {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  last_login?: string;
  created_at?: string;
}

// 表單資料類型 (專案角色在承攬案件詳情頁管理)
interface StaffFormData {
  username: string;
  email: string;
  full_name: string;
  is_active: boolean;
  password?: string;
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
      const response = await apiClient.post('/users/list', requestBody);
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

  // 新增或編輯承辦同仁 (POST-only 資安機制)
  const handleSubmit = async (values: StaffFormData) => {
    setSubmitLoading(true);
    try {
      if (editingStaff) {
        // 更新 (POST-only)
        await apiClient.post(`/users/${editingStaff.id}/update`, values);
        message.success('承辦同仁更新成功');
      } else {
        // 新增 (POST-only)
        await apiClient.post('/users', values);
        message.success('承辦同仁建立成功');
      }

      setModalVisible(false);
      setEditingStaff(null);
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
      await apiClient.post(`/users/${id}/delete`);
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
      await apiClient.post(`/users/${id}/status`, { is_active: isActive });
      message.success(isActive ? '已啟用' : '已停用');
      loadStaffList();
    } catch (error: any) {
      console.error('狀態更新失敗:', error);
      message.error('狀態更新失敗');
    }
  };

  // 開啟編輯模態框
  const handleEdit = (staff: Staff) => {
    setEditingStaff(staff);
    setModalVisible(true);
  };

  // 開啟新增模態框
  const handleAdd = () => {
    setEditingStaff(null);
    setModalVisible(true);
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
      width: 120,
      sorter: (a, b) => a.username.localeCompare(b.username),
      ...getColumnSearchProps('username'),
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
        title={editingStaff ? '編輯承辦同仁' : '新增承辦同仁'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingStaff(null);
        }}
        footer={null}
        width={600}
        destroyOnHidden
      >
        <Form
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={editingStaff ? {
            username: editingStaff.username,
            email: editingStaff.email,
            full_name: editingStaff.full_name,
            is_active: editingStaff.is_active,
          } : {
            is_active: true,
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
                rules={[
                  { required: true, message: '請輸入帳號' },
                  { min: 3, message: '帳號至少3個字元' },
                ]}
              >
                <Input placeholder="請輸入帳號" disabled={!!editingStaff} />
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

          {!editingStaff && (
            <Form.Item
              name="password"
              label="密碼"
              rules={[
                { required: !editingStaff, message: '請輸入密碼' },
                { min: 6, message: '密碼至少6個字元' },
              ]}
            >
              <Input.Password placeholder="請輸入密碼" />
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
              <Button onClick={() => setModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={submitLoading}>
                {editingStaff ? '更新' : '建立'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default StaffPage;
