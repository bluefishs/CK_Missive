/**
 * ERP 營運帳目詳情頁面 — DetailPageLayout
 *
 * Tab: 帳目資訊 / 費用明細 / 預算分析
 */
import React, { useState } from 'react';
import {
  Descriptions, Tag, Table, Button, Modal, Form, Input, InputNumber,
  DatePicker, Select, Progress, Statistic, Row, Col, Card, Space, App,
} from 'antd';
import {
  InfoCircleOutlined, FileTextOutlined, BarChartOutlined,
  PlusOutlined, EditOutlined, CheckOutlined, CloseOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';
import {
  useOperationalAccountDetail,
  useOperationalExpenses,
  useCreateOperationalExpense,
  useApproveOperationalExpense,
  useRejectOperationalExpense,
  useDeleteOperationalAccount,
} from '../hooks';
import {
  OPERATIONAL_CATEGORIES,
  OPERATIONAL_STATUS,
} from '../types/erp';
import type { OperationalExpense, OperationalExpenseCreate } from '../types/erp';
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
  const createExpense = useCreateOperationalExpense();
  const approveExpense = useApproveOperationalExpense();
  const rejectExpense = useRejectOperationalExpense();
  const deleteAccount = useDeleteOperationalAccount();

  const { hasPermission } = useAuthGuard();
  const canWrite = hasPermission('operational:write');
  const canApprove = hasPermission('operational:approve');

  const [showExpenseModal, setShowExpenseModal] = useState(false);
  const [form] = Form.useForm();

  const expenses = expenseData?.items ?? [];
  const spent = account?.total_spent ?? 0;
  const budget = account?.budget_limit ?? 0;
  const usagePct = budget > 0 ? Math.round((spent / budget) * 100) : 0;
  const remaining = budget - spent;

  const handleCreateExpense = async () => {
    try {
      const values = await form.validateFields();
      const payload: OperationalExpenseCreate = {
        account_id: accountId!,
        expense_date: values.expense_date.format('YYYY-MM-DD'),
        amount: values.amount,
        description: values.description,
        category: values.category,
        notes: values.notes,
      };
      await createExpense.mutateAsync(payload);
      message.success('費用已新增');
      setShowExpenseModal(false);
      form.resetFields();
    } catch {
      // validation or API error
    }
  };

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
      <div style={{ marginBottom: 16, textAlign: 'right' }}>
        {canWrite && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => setShowExpenseModal(true)}
          >
            新增費用
          </Button>
        )}
      </div>
      <Table<OperationalExpense>
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
      <Modal
        title="新增費用"
        open={showExpenseModal}
        onOk={handleCreateExpense}
        onCancel={() => { setShowExpenseModal(false); form.resetFields(); }}
        confirmLoading={createExpense.isPending}
        destroyOnClose
      >
        <Form form={form} layout="vertical">
          <Form.Item name="expense_date" label="日期" rules={[{ required: true, message: '請選擇日期' }]}>
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="amount" label="金額" rules={[{ required: true, message: '請輸入金額' }]}>
            <InputNumber style={{ width: '100%' }} min={0} prefix="NT$" />
          </Form.Item>
          <Form.Item name="description" label="說明">
            <Input />
          </Form.Item>
          <Form.Item name="category" label="費用類別">
            <Select
              placeholder="選擇類別"
              allowClear
              options={Object.entries(OPERATIONAL_CATEGORIES).map(([v, l]) => ({ value: v, label: l }))}
            />
          </Form.Item>
          <Form.Item name="notes" label="備註">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default ERPOperationalDetailPage;
