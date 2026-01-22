/**
 * 承辦同仁管理頁面
 * @description 提供承辦同仁的列表與導航管理功能
 * @version 2.0.0 - 移除 Modal，改用導航模式
 * @date 2026-01-22
 */
import React, { useState, useEffect, useCallback } from 'react';
import type { TableColumnType } from 'antd';
import {
  Table,
  Button,
  Input,
  Space,
  Card,
  Select,
  Typography,
  Popconfirm,
  Row,
  Col,
  Statistic,
  App,
  Tooltip,
  Switch,
  Tag,
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
  BankOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { useTableColumnSearch, useResponsive } from '../hooks';
import { ROUTES } from '../router/types';

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

export const StaffPage: React.FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { getColumnSearchProps } = useStaffTableSearch();
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });

  // 列表狀態
  const [staffList, setStaffList] = useState<Staff[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [current, setCurrent] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // 篩選狀態
  const [searchText, setSearchText] = useState('');
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>();

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

  // 導航至詳情頁
  const handleEdit = (staff: Staff) => {
    navigate(ROUTES.STAFF_DETAIL.replace(':id', String(staff.id)));
  };

  // 導航至新增頁
  const handleAdd = () => {
    navigate(ROUTES.STAFF_CREATE);
  };

  // 響應式表格欄位定義
  const columns: TableColumnType<Staff>[] = isMobile
    ? [
        {
          title: '同仁',
          dataIndex: 'full_name',
          key: 'full_name',
          render: (text: string, record: Staff) => (
            <Space direction="vertical" size={0}>
              <strong><UserOutlined /> {text || record.username}</strong>
              {record.department && <Tag color="blue" style={{ fontSize: 12 }}>{record.department}</Tag>}
              <small style={{ color: '#666' }}>{record.email}</small>
            </Space>
          ),
        },
        {
          title: '狀態',
          dataIndex: 'is_active',
          key: 'is_active',
          width: 70,
          render: (isActive: boolean, record: Staff) => (
            <Switch
              size="small"
              checked={isActive}
              onChange={(checked) => handleToggleActive(record.id, checked)}
            />
          ),
        },
        {
          title: '',
          key: 'action',
          width: 50,
          render: (_, record: Staff) => (
            <Popconfirm
              title="刪除此同仁？"
              onConfirm={(e) => { e?.stopPropagation(); handleDelete(record.id); }}
              onCancel={(e) => e?.stopPropagation()}
              okText="確定"
              cancelText="取消"
            >
              <Button type="link" size="small" danger icon={<DeleteOutlined />} onClick={(e) => e.stopPropagation()} />
            </Popconfirm>
          ),
        },
      ]
    : [
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
    <div style={{ padding: pagePadding }}>
      {/* 頁面標題 */}
      <Title level={isMobile ? 4 : 3} style={{ marginBottom: isMobile ? 12 : 16 }}>
        <TeamOutlined style={{ marginRight: 8 }} />
        {isMobile ? '同仁管理' : '承辦同仁管理'}
      </Title>

      {/* 統計卡片 */}
      <Row gutter={[8, 8]} style={{ marginBottom: isMobile ? 12 : 16 }}>
        <Col xs={8} sm={8}>
          <Card size="small">
            <Statistic
              title={isMobile ? '總數' : '總人數'}
              value={stats.total}
              prefix={<TeamOutlined />}
              valueStyle={{ fontSize: isMobile ? 18 : 24 }}
            />
          </Card>
        </Col>
        <Col xs={8} sm={8}>
          <Card size="small">
            <Statistic
              title={isMobile ? '啟用' : '啟用中'}
              value={stats.active}
              valueStyle={{ color: '#3f8600', fontSize: isMobile ? 18 : 24 }}
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={8} sm={8}>
          <Card size="small">
            <Statistic
              title={isMobile ? '停用' : '已停用'}
              value={stats.inactive}
              valueStyle={{ color: '#999', fontSize: isMobile ? 18 : 24 }}
              prefix={<CloseCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 主要內容卡片 */}
      <Card size={isMobile ? 'small' : 'default'}>
        {/* 工具列 */}
        <Row gutter={[8, 8]} style={{ marginBottom: isMobile ? 12 : 16 }}>
          <Col xs={24} sm={16}>
            <Space wrap size={isMobile ? 'small' : 'middle'}>
              <Input
                placeholder={isMobile ? '搜尋同仁...' : '搜尋姓名、帳號、Email...'}
                prefix={<SearchOutlined />}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                style={{ width: isMobile ? '100%' : 250 }}
                size={isMobile ? 'small' : 'middle'}
                allowClear
              />
              {!isMobile && (
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
              )}
            </Space>
          </Col>
          <Col xs={24} sm={8} style={{ textAlign: isMobile ? 'left' : 'right' }}>
            <Space size={isMobile ? 'small' : 'middle'}>
              <Button
                icon={<ReloadOutlined />}
                onClick={loadStaffList}
                size={isMobile ? 'small' : 'middle'}
              >
                {isMobile ? '' : '重新整理'}
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleAdd}
                size={isMobile ? 'small' : 'middle'}
              >
                {isMobile ? '' : '新增同仁'}
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
          size={isMobile ? 'small' : 'middle'}
          scroll={{ x: isMobile ? 300 : 1000 }}
          onRow={(record) => ({
            onClick: () => handleEdit(record),
            style: { cursor: 'pointer' },
          })}
          pagination={{
            current,
            pageSize: isMobile ? 10 : pageSize,
            total,
            showSizeChanger: !isMobile,
            showQuickJumper: !isMobile,
            showTotal: isMobile ? undefined : (t) => `共 ${t} 筆`,
            onChange: (page, size) => {
              setCurrent(page);
              setPageSize(size);
            },
            size: isMobile ? 'small' : 'default',
          }}
        />
      </Card>
    </div>
  );
};

export default StaffPage;
