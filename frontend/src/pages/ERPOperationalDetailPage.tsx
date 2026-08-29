/**
 * ERP 營運帳目詳情頁面 — DetailPageLayout
 *
 * Tab: 帳目資訊 / 費用明細 / 預算分析
 */
import React from 'react';
import {
  Descriptions, Tag, Button, Modal, Progress, Statistic, Row, Col, Card, Space, App,
  Alert, Typography,
} from 'antd';

const { Text } = Typography;
import { EnhancedTable } from '../components/common/EnhancedTable';
import {
  InfoCircleOutlined, FileTextOutlined, BarChartOutlined,
  PlusOutlined, EditOutlined, CheckOutlined, CloseOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import {
  useOperationalAccountDetail,
  useOperationalExpenses,
  useApproveOperationalExpense,
  useRejectOperationalExpense,
  useDeleteOperationalAccount,
} from '../hooks';
import {
  OPERATIONAL_CATEGORIES,
  OPERATIONAL_STATUS,
} from '../types/erp';
import type { OperationalExpense } from '../types/erp';
import type { ColumnsType } from 'antd/es/table';
import { ROUTES } from '../router/types';
import { useAuthGuard } from '../hooks';
import { DetailPageLayout } from '../components/common/DetailPage/DetailPageLayout';
import { createTabItem } from '../components/common/DetailPage/utils';

const STATUS_COLORS: Record<string, string> = {
  active: 'green', closed: 'default', frozen: 'blue',
};

const APPROVAL_COLORS: Record<string, string> = {
  pending: 'orange', approved: 'green', rejected: 'red',
};
const APPROVAL_LABELS: Record<string, string> = {
  pending: '待審核', approved: '已核准', rejected: '已駁回',
};

const ERPOperationalDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const accountId = id ? Number(id) : null;
  const { message } = App.useApp();

  const { data: account, isLoading } = useOperationalAccountDetail(accountId);
  const { data: expenseData, isLoading: expLoading } = useOperationalExpenses(accountId);
  const approveExpense = useApproveOperationalExpense();
  const rejectExpense = useRejectOperationalExpense();
  const deleteAccount = useDeleteOperationalAccount();

  const { hasPermission } = useAuthGuard();
  const canWrite = hasPermission('operational:write');
  const canApprove = hasPermission('operational:approve');

  // ⚠️ 2026-08-29 實測：`operational:write` 與 `operational:approve`
  // 在 `role_permissions` 裡**只掛在 `finance` 與 `ops` 兩個角色**，
  // 而**沒有任何在職使用者持有那兩個角色**（12 位：staff 6／admin 5／superuser 1）
  // ⇒ **0 人有這兩個權限**，`admin` 也沒有（`hasPermission` 只對 superuser 短路）。
  //
  // 也就是說：新增費用／編輯／審批這三顆按鈕，**12 個人裡只有 1 個看得到**。
  //
  // 原本它們是**靜靜消失**的 —— 使用者分不出「這個功能不存在」與
  // 「我沒有權限」，那兩件事在畫面上長得一模一樣
  // （同 B7 的 `/staff`「空表格 vs 載不到」）。
  //
  // ⚠️ **刻意不放寬權限**：要不要讓誰做這些動作是產品決策（待辦 A27，
  // owner 尚未決定是否開 finance／ops 角色）。這裡只治「看不出原因」。
  const missingOps: string[] = [
    !canWrite && 'operational:write',
    !canApprove && 'operational:approve',
  ].filter(Boolean) as string[];

  // 2026-08-16：新增費用已改為導覽頁（/erp/operational/:id/expenses/create）

  const expenses = expenseData?.items ?? [];
  const spent = account?.total_spent ?? 0;
  const budget = account?.budget_limit ?? 0;
  const usagePct = budget > 0 ? Math.round((spent / budget) * 100) : 0;
  const remaining = budget - spent;


  const handleDelete = () => {
    Modal.confirm({
      title: '確認刪除',
      content: `確定要刪除帳目「${account?.name}」嗎？`,
      okText: '刪除',
      okType: 'danger',
      onOk: async () => {
        await deleteAccount.mutateAsync(accountId!);
        message.success('帳目已刪除');
        navigate(ROUTES.ERP_OPERATIONAL);
      },
    });
  };

  const expenseColumns: ColumnsType<OperationalExpense> = [
    {
      title: '日期',
      dataIndex: 'expense_date',
      key: 'expense_date',
      width: 110,
      render: (val: string) => val ? dayjs(val).format('YYYY-MM-DD') : '-',
    },
    {
      title: '金額',
      dataIndex: 'amount',
      key: 'amount',
      width: 120,
      align: 'right',
      render: (val: number) => `NT$ ${val.toLocaleString()}`,
    },
    {
      title: '說明',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '類別',
      dataIndex: 'category',
      key: 'category',
      width: 100,
      render: (val?: string) => val ? <Tag>{val}</Tag> : '-',
    },
    {
      title: '狀態',
      dataIndex: 'approval_status',
      key: 'approval_status',
      width: 90,
      render: (val: string) => (
        <Tag color={APPROVAL_COLORS[val] ?? 'default'}>
          {APPROVAL_LABELS[val] ?? val}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: unknown, record: OperationalExpense) => {
        if (record.approval_status !== 'pending' || !canApprove) return null;
        return (
          <Button.Group size="small">
            <Button
              type="link"
              icon={<CheckOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                approveExpense.mutate(record.id, {
                  onSuccess: () => message.success('已核准'),
                });
              }}
            >
              核准
            </Button>
            <Button
              type="link"
              danger
              icon={<CloseOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                rejectExpense.mutate({ id: record.id }, {
                  onSuccess: () => message.success('已駁回'),
                });
              }}
            >
              駁回
            </Button>
          </Button.Group>
        );
      },
    },
  ];

  // --- Tab 1: Account Info ---
  const infoTab = (
    <Card>
      <Descriptions column={{ xs: 1, sm: 2 }} bordered size="small">
        <Descriptions.Item label="帳目編號">{account?.account_code}</Descriptions.Item>
        <Descriptions.Item label="名稱">{account?.name}</Descriptions.Item>
        <Descriptions.Item label="類別">
          <Tag>{OPERATIONAL_CATEGORIES[account?.category ?? ''] ?? account?.category}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="年度">{account?.fiscal_year}</Descriptions.Item>
        <Descriptions.Item label="部門">{account?.department ?? '-'}</Descriptions.Item>
        <Descriptions.Item label="狀態">
          <Tag color={STATUS_COLORS[account?.status ?? '']}>
            {OPERATIONAL_STATUS[account?.status ?? ''] ?? account?.status}
          </Tag>
        </Descriptions.Item>
        <Descriptions.Item label="備註" span={2}>{account?.notes ?? '-'}</Descriptions.Item>
      </Descriptions>
      <div style={{ marginTop: 16 }}>
        <Progress
          percent={usagePct}
          status={usagePct > 90 ? 'exception' : usagePct > 70 ? 'active' : 'normal'}
          format={() => `${usagePct}% (NT$ ${spent.toLocaleString()} / ${budget.toLocaleString()})`}
        />
      </div>
    </Card>
  );

  // --- Tab 2: Expenses ---
  const expensesTab = (
    <Card>
      {missingOps.length > 0 && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          message="部分操作未顯示：你的帳號沒有對應權限"
          description={
            <span>
              缺少 {missingOps.map((k, i) => (
                <React.Fragment key={k}>{i > 0 && '、'}<Text code>{k}</Text></React.Fragment>
              ))} ⇒ 新增費用／編輯／審批按鈕不會出現。
              <br />
              這兩個權限目前只掛在「finance」與「ops」角色上，而<strong>尚未有人被指派這兩個角色</strong> ——
              需要時請找系統管理員在 <Text code>/admin/permissions</Text> 調整。
            </span>
          }
        />
      )}
      <div style={{ marginBottom: 16, textAlign: 'right' }}>
        {canWrite && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => navigate(`/erp/operational/${accountId}/expenses/create`)}
          >
            新增費用
          </Button>
        )}
      </div>
      <EnhancedTable<OperationalExpense>
        columns={expenseColumns}
        dataSource={expenses}
        rowKey="id"
        loading={expLoading}
        pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 筆` }}
        size="middle"
      />
    </Card>
  );

  // --- Tab 3: Budget Analysis ---
  const analysisTab = (
    <Row gutter={[16, 16]}>
      <Col xs={24} sm={8}>
        <Card>
          <Statistic
            title="總預算"
            value={budget}
            precision={0}
            prefix="NT$"
          />
        </Card>
      </Col>
      <Col xs={24} sm={8}>
        <Card>
          <Statistic
            title="已支出"
            value={spent}
            precision={0}
            prefix="NT$"
            styles={{ content: { color: usagePct > 90 ? '#ff4d4f' : '#3f8600' } }}
          />
        </Card>
      </Col>
      <Col xs={24} sm={8}>
        <Card>
          <Statistic
            title="剩餘預算"
            value={remaining}
            precision={0}
            prefix="NT$"
            styles={{ content: { color: remaining < 0 ? '#ff4d4f' : '#1890ff' } }}
          />
        </Card>
      </Col>
      <Col span={24}>
        <Card>
          <Statistic title="預算使用率" value={usagePct} suffix="%" />
          <Progress
            percent={usagePct}
            status={usagePct > 90 ? 'exception' : usagePct > 70 ? 'active' : 'normal'}
            style={{ marginTop: 8 }}
          />
        </Card>
      </Col>
    </Row>
  );

  const tabs = [
    createTabItem('info', { icon: <InfoCircleOutlined />, text: '帳目資訊' }, infoTab),
    createTabItem('expenses', { icon: <FileTextOutlined />, text: '費用明細', count: expenses.length }, expensesTab),
    createTabItem('analysis', { icon: <BarChartOutlined />, text: '預算分析' }, analysisTab),
  ];

  return (
    <>
      <DetailPageLayout
        header={{
          title: account?.name ?? '營運帳目詳情',
          tags: account?.status
            ? [{ text: OPERATIONAL_STATUS[account.status] ?? account.status, color: STATUS_COLORS[account.status] ?? 'default' }]
            : [],
          backPath: ROUTES.ERP_OPERATIONAL,
          extra: canWrite ? (
            <Space>
              <Button
                icon={<EditOutlined />}
                onClick={() => navigate(`${ROUTES.ERP_OPERATIONAL}/${accountId}/edit`)}
              >
                編輯
              </Button>
              <Button danger onClick={handleDelete}>
                刪除
              </Button>
            </Space>
          ) : undefined,
        }}
        tabs={tabs}
        loading={isLoading}
        hasData={!!account}
      />

      {/* Create Expense Modal */}
    </>
  );
};

export default ERPOperationalDetailPage;
