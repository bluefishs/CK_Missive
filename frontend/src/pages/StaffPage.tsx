/**
 * 承辦同仁管理頁面
 * @description 提供承辦同仁的列表與導航管理功能
 * @version 2.1.0 - 移除列表刪除按鈕，整合至詳情頁 (導航模式規範)
 * @date 2026-01-22
 */
import React, { useState, useMemo } from 'react';
import { ClickableStatCard } from '../components/common';
import type { TableColumnType } from 'antd';
import {
  Button,
  Input,
  Space,
  Card,
  Select,
  Typography,
  Row,
  Col,
  App,
  Switch,
  Tag,
  Tooltip,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  UserOutlined,
  MailOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  BankOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ResponsiveTable } from '../components/common';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import { useTableColumnSearch, useResponsive } from '../hooks';
import { defaultQueryOptions } from '../config/queryConfig';
import { ROUTES } from '../router/types';
import { useDepartments } from '../hooks/system';
import { useAuthGuard } from '../hooks/utility/useAuthGuard';
import { logger } from '../services/logger';

const { Title } = Typography;
const { Option } = Select;

// 注意：專案角色在「承攬案件詳情頁」中管理
// 同一位同仁可在不同專案擔任不同角色 (計畫主持、計畫協同、專案PM、職安主管)
// 此頁面僅管理基本帳號資訊，不顯示專案角色

// ---[型別定義]---
import type { User } from '../types/api';

/**
 * Staff 型別別名 - 使用 User 作為統一型別來源
 * 承辦同仁本質上是系統使用者，使用相同的資料結構
 */
type Staff = User;

// 使用表格搜尋 Hook
const useStaffTableSearch = () => useTableColumnSearch<Staff>();

export const StaffPage: React.FC = () => {
  const { message } = App.useApp();
  const navigate = useNavigate();
  const { getColumnSearchProps } = useStaffTableSearch();
  const { isMobile, responsiveValue } = useResponsive();
  const pagePadding = responsiveValue({ mobile: 12, tablet: 16, desktop: 24 });
  const queryClient = useQueryClient();
  const { data: departmentOptions = [] } = useDepartments();

  // 2026-08-26（C4）：這一頁的內容**全部需要管理員**（清單 USERS.LIST、
  // 啟用停用 USERS.STATUS），而 `/staff` 的導覽權限是 `projects:read`
  // ⇒ 一般同仁看得到選單、點進來看到**空表格 + 統計全 0**，
  // 看起來像「公司沒有同仁」——而那與「你沒有權限看」意思完全相反。
  //
  // 這一頁該不該對一般同仁開放是**產品決策**，這裡不改權限
  // （08-20 立過：那些 403 部分是刻意的，不擅自放寬），只治兩件事 ——
  // 載不到要說出來，且不給一個必然失敗的按鈕。
  const { isAdmin } = useAuthGuard();

  // 分頁狀態
  const [current, setCurrent] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  // 篩選狀態
  const [searchText, setSearchText] = useState('');
  const [activeFilter, setActiveFilter] = useState<boolean | undefined>();
  const [departmentFilter, setDepartmentFilter] = useState<string>('');

  // 使用 React Query 載入承辦同仁列表
  const { data: staffData, isLoading: loading, isError } = useQuery({
    queryKey: ['users', 'list', { page: current, limit: pageSize, search: searchText, is_active: activeFilter, department: departmentFilter }],
    queryFn: async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const requestBody: Record<string, any> = {
        page: current,
        limit: pageSize,
      };

      if (searchText) requestBody.search = searchText;
      if (activeFilter !== undefined) requestBody.is_active = activeFilter;
      if (departmentFilter) requestBody.department = departmentFilter;

      const response = await apiClient.post(API_ENDPOINTS.USERS.LIST, requestBody);
      return response as { items?: Staff[]; users?: Staff[]; total?: number };
    },
    ...defaultQueryOptions.list,
  });

  // 從 React Query 資料推導列表與統計
  const staffList = useMemo(() => {
    const items = staffData?.items || staffData?.users || [];
    return Array.isArray(items) ? items : [];
  }, [staffData]);
  const total = staffData?.total || 0;
  const stats = useMemo(() => {
    const activeCount = staffList.filter((s) => s.is_active).length;
    return {
      total,
      active: activeCount,
      inactive: total - activeCount,
    };
  }, [staffList, total]);

  const loadStaffList = () => {
    queryClient.invalidateQueries({ queryKey: ['users', 'list'] });
  };

  // 刪除功能已移至 StaffDetailPage (導航模式規範)

  // 切換啟用狀態 (useMutation)
  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, isActive }: { id: number; isActive: boolean }) =>
      apiClient.post(API_ENDPOINTS.USERS.STATUS(id), { is_active: isActive }),
    onSuccess: (_data, variables) => {
      message.success(variables.isActive ? '已啟用' : '已停用');
      loadStaffList();
    },
    onError: (error: unknown) => {
      logger.error('狀態更新失敗:', error);
      message.error('狀態更新失敗');
    },
  });

  const handleToggleActive = (id: number, isActive: boolean) => {
    toggleActiveMutation.mutate({ id, isActive });
  };

  // 導航至詳情頁
  const handleEdit = (staff: Staff) => {
    navigate(ROUTES.STAFF_DETAIL.replace(':id', String(staff.id)));
  };

  // 導航至新增頁
  const handleAdd = () => {
    navigate(ROUTES.STAFF_CREATE);
  };

  // 響應式表格欄位定義 (導航模式：刪除功能整合至詳情頁)
  // ADR-0025：同一個人可能有兩個登入帳號（例如業務用與管理用各一）。
  //
  // ⚠️ 標籤刻意用「同一人」而非「分身」：owner 2026-08-19 指出
  // `jujuiacc`（canonical）其實是**管理員身分**，而 `aaronfly1978`
  // （被標成 alias 的那個）才是**實際業務身分**、6 個專案指派都掛在它上面。
  // 「分身」這個詞暗示了誰主誰次，而在這個案例裡方向是反的。
  // 合併之後權限與 RLS 都以 canonical 為準，但這一頁是**人員管理**，
  // 兩個帳號都該看得到 —— 缺的是「看得出它們是同一個人」。
  // 2026-08-19 owner 回報：/staff 出現「王駿穠」與「王駿穠(fly)」兩列，
  // 分不出關係；而 /admin/user-management 有帶 canonical_only 所以只有一列。
  const renderNameWithAlias = (text: string, record: Staff) => {
    const canonicalId = (record as Staff & { canonical_user_id?: number }).canonical_user_id;
    if (!canonicalId) return <span>{text || record.username}</span>;
    const canonical = staffList.find((u) => u.id === canonicalId);
    return (
      <Space size={4}>
        <span>{text || record.username}</span>
        <Tooltip
          title={`與「${canonical?.full_name || canonical?.username || `使用者 #${canonicalId}`}」是同一個人（同仁可能有兩個登入帳號，例如業務用與管理用各一）。資料可見範圍會涵蓋兩個帳號。`}
        >
          <Tag color="orange" style={{ marginInlineEnd: 0 }}>同一人</Tag>
        </Tooltip>
      </Space>
    );
  };

  const columns: TableColumnType<Staff>[] = isMobile
    ? [
        {
          title: '同仁',
          dataIndex: 'full_name',
          key: 'full_name',
          render: (text: string, record: Staff) => (
            <Space vertical size={0}>
              <strong><UserOutlined /> {renderNameWithAlias(text, record)}</strong>
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
              onChange={(checked, e) => {
                e.stopPropagation();
                handleToggleActive(record.id, checked);
              }}
              onClick={(_, e) => e.stopPropagation()}
            />
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
              {renderNameWithAlias(text, record)}
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
          filters: departmentOptions.map(d => ({ text: d, value: d })),
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
        // 導航模式：刪除功能整合至詳情頁，列表頁不顯示刪除按鈕
      ];

  // ⚠️ 「載不到」與「沒有資料」必須看得出差別 —— 空表格會被讀成
  // 「公司沒有同仁」（08-20 的判準：空清單不得退化成看起來像真的答案）。
  if (isError && !isAdmin) {
    return (
      <div style={{ padding: pagePadding }}>
        <Title level={isMobile ? 4 : 3} style={{ marginBottom: 16 }}>
          <TeamOutlined style={{ marginRight: 8 }} />
          {isMobile ? '同仁管理' : '承辦同仁管理'}
        </Title>
        <Alert
          type="info"
          showIcon
          message="這一頁需要管理員權限"
          description="承辦同仁的帳號管理（啟用停用、部門、最後登入）屬於管理功能。若你要指派工作給同仁，請直接在案件或派工的「承辦同仁」欄位選擇。"
        />
      </div>
    );
  }

  return (
    <div style={{ padding: pagePadding }}>
      {/* 頁面標題 */}
      <Title level={isMobile ? 4 : 3} style={{ marginBottom: isMobile ? 12 : 16 }}>
        <TeamOutlined style={{ marginRight: 8 }} />
        {isMobile ? '同仁管理' : '承辦同仁管理'}
      </Title>

      {/* 統計卡片 —— development-rules §2.6 ②：卡片可點擊篩選列表，再點一次取消。
          2026-08-29：`activeFilter` 狀態**本來就存在**（下方篩選列在用），
          只是卡片沒有接上去 —— 使用者看到「啟用中 12」的下一個動作必然是
          「哪 12 個」，而先前那是一個看得到、點不動的數字。 */}
      <Row gutter={[8, 8]} style={{ marginBottom: isMobile ? 12 : 16 }}>
        <Col xs={8} sm={8}>
          <ClickableStatCard
            title={isMobile ? '總數' : '總人數'}
            value={stats.total}
            icon={<TeamOutlined />}
            active={activeFilter === undefined}
            onClick={() => { setActiveFilter(undefined); setCurrent(1); }}
          />
        </Col>
        <Col xs={8} sm={8}>
          <ClickableStatCard
            title={isMobile ? '啟用' : '啟用中'}
            value={stats.active}
            color="#3f8600"
            icon={<CheckCircleOutlined />}
            active={activeFilter === true}
            onClick={() => { setActiveFilter(activeFilter === true ? undefined : true); setCurrent(1); }}
          />
        </Col>
        <Col xs={8} sm={8}>
          <ClickableStatCard
            title={isMobile ? '停用' : '已停用'}
            value={stats.inactive}
            color="#999"
            icon={<CloseCircleOutlined />}
            active={activeFilter === false}
            onClick={() => { setActiveFilter(activeFilter === false ? undefined : false); setCurrent(1); }}
          />
        </Col>
      </Row>

      {/* 主要內容卡片 */}
      <Card size={isMobile ? 'small' : undefined}>
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
                <>
                  <Select
                    placeholder="部門篩選"
                    value={departmentFilter || undefined}
                    onChange={(v) => {
                      setDepartmentFilter(v || '');
                      setCurrent(1);
                    }}
                    style={{ width: 150 }}
                    allowClear
                    options={departmentOptions.map(d => ({ label: d, value: d }))}
                  />
                  <Select
                    placeholder="狀態篩選"
                    value={activeFilter}
                    onChange={(v) => {
                      setActiveFilter(v);
                      setCurrent(1);  // 切換篩選時重置頁碼
                    }}
                    style={{ width: 120 }}
                    allowClear
                  >
                    <Option value={true}>啟用中</Option>
                    <Option value={false}>已停用</Option>
                  </Select>
                </>
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
        <ResponsiveTable
          columns={columns}
          dataSource={staffList}
          rowKey="id"
          loading={loading}
          scroll={{ x: isMobile ? 300 : 1000 }}
          mobileHiddenColumns={['username', 'position', 'last_login']}
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
            showTotal: isMobile ? undefined : (t: number) => `共 ${t} 筆`,
            onChange: (page: number, size: number) => {
              setCurrent(page);
              setPageSize(size);
            },
            size: isMobile ? 'small' : undefined,
          }}
        />
      </Card>
    </div>
  );
};

export default StaffPage;
