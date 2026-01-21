/**
 * 桃園查估派工 - 契金管控 Tab
 *
 * 功能：
 * - 選擇派工單後顯示對應的契金紀錄
 * - 支援新增、編輯、刪除契金紀錄
 * - 顯示金額彙總統計
 *
 * @version 1.0.0
 * @date 2026-01-21
 */

import React, { useState } from 'react';
import {
  Typography,
  Button,
  Space,
  Modal,
  App,
  Card,
  Table,
  Select,
  Form,
  DatePicker,
  InputNumber,
  Statistic,
  Row,
  Col,
  Tooltip,
  Popconfirm,
  Input,
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  EditOutlined,
  DeleteOutlined,
  DollarOutlined,
} from '@ant-design/icons';
import { useQuery, useMutation } from '@tanstack/react-query';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

import {
  dispatchOrdersApi,
  contractPaymentsApi,
} from '../../api/taoyuanDispatchApi';
import type {
  ContractPayment,
  ContractPaymentCreate,
  ContractPaymentUpdate,
} from '../../types/api';

const { Title } = Typography;

export interface PaymentsTabProps {
  contractProjectId: number;
}

export const PaymentsTab: React.FC<PaymentsTabProps> = ({ contractProjectId }) => {
  const { message } = App.useApp();

  // 先查詢派工單列表以取得 dispatch_order_id
  const { data: ordersData } = useQuery({
    queryKey: ['dispatch-orders', contractProjectId],
    queryFn: () =>
      dispatchOrdersApi.getList({
        contract_project_id: contractProjectId,
        limit: 1000,
      }),
  });

  const orders = ordersData?.items ?? [];
  const [selectedOrderId, setSelectedOrderId] = useState<number | undefined>();

  const {
    data: paymentsData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ['contract-payments', selectedOrderId],
    queryFn: () => (selectedOrderId ? contractPaymentsApi.getList(selectedOrderId) : null),
    enabled: !!selectedOrderId,
  });

  const payments = paymentsData?.items ?? [];
  // 計算彙總金額
  const totalCurrentAmount = payments.reduce((sum, p) => sum + (p.current_amount ?? 0), 0);
  const totalCumulativeAmount = payments.reduce((sum, p) => sum + (p.cumulative_amount ?? 0), 0);
  const totalRemainingAmount = payments.reduce((sum, p) => sum + (p.remaining_amount ?? 0), 0);

  const [editingPayment, setEditingPayment] = useState<ContractPayment | null>(null);
  const [modalVisible, setModalVisible] = useState(false);
  const [form] = Form.useForm();

  const createMutation = useMutation({
    mutationFn: (data: ContractPaymentCreate) => contractPaymentsApi.create(data),
    onSuccess: () => {
      message.success('契金紀錄新增成功');
      refetch();
      setModalVisible(false);
      form.resetFields();
    },
    onError: () => message.error('新增失敗'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: ContractPaymentUpdate }) =>
      contractPaymentsApi.update(id, data),
    onSuccess: () => {
      message.success('契金紀錄更新成功');
      refetch();
      setModalVisible(false);
      setEditingPayment(null);
      form.resetFields();
    },
    onError: () => message.error('更新失敗'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => contractPaymentsApi.delete(id),
    onSuccess: () => {
      message.success('契金紀錄刪除成功');
      refetch();
    },
    onError: () => message.error('刪除失敗'),
  });

  const handleEdit = (payment: ContractPayment) => {
    setEditingPayment(payment);
    form.setFieldsValue({
      work_01_date: payment.work_01_date ? dayjs(payment.work_01_date) : null,
      work_01_amount: payment.work_01_amount,
      work_02_date: payment.work_02_date ? dayjs(payment.work_02_date) : null,
      work_02_amount: payment.work_02_amount,
      work_03_date: payment.work_03_date ? dayjs(payment.work_03_date) : null,
      work_03_amount: payment.work_03_amount,
      work_04_date: payment.work_04_date ? dayjs(payment.work_04_date) : null,
      work_04_amount: payment.work_04_amount,
      work_05_date: payment.work_05_date ? dayjs(payment.work_05_date) : null,
      work_05_amount: payment.work_05_amount,
      work_06_date: payment.work_06_date ? dayjs(payment.work_06_date) : null,
      work_06_amount: payment.work_06_amount,
      work_07_date: payment.work_07_date ? dayjs(payment.work_07_date) : null,
      work_07_amount: payment.work_07_amount,
      current_amount: payment.current_amount,
      cumulative_amount: payment.cumulative_amount,
      remaining_amount: payment.remaining_amount,
      acceptance_date: payment.acceptance_date ? dayjs(payment.acceptance_date) : null,
    });
    setModalVisible(true);
  };

  const handleCreate = () => {
    if (!selectedOrderId) {
      message.warning('請先選擇派工單');
      return;
    }
    setEditingPayment(null);
    form.resetFields();
    form.setFieldsValue({ dispatch_order_id: selectedOrderId });
    setModalVisible(true);
  };

  const handleSubmit = async () => {
    const values = await form.validateFields();
    const data: ContractPaymentCreate = {
      dispatch_order_id: selectedOrderId!,
      work_01_date: values.work_01_date?.format('YYYY-MM-DD'),
      work_01_amount: values.work_01_amount,
      work_02_date: values.work_02_date?.format('YYYY-MM-DD'),
      work_02_amount: values.work_02_amount,
      work_03_date: values.work_03_date?.format('YYYY-MM-DD'),
      work_03_amount: values.work_03_amount,
      work_04_date: values.work_04_date?.format('YYYY-MM-DD'),
      work_04_amount: values.work_04_amount,
      work_05_date: values.work_05_date?.format('YYYY-MM-DD'),
      work_05_amount: values.work_05_amount,
      work_06_date: values.work_06_date?.format('YYYY-MM-DD'),
      work_06_amount: values.work_06_amount,
      work_07_date: values.work_07_date?.format('YYYY-MM-DD'),
      work_07_amount: values.work_07_amount,
      current_amount: values.current_amount,
      cumulative_amount: values.cumulative_amount,
      remaining_amount: values.remaining_amount,
      acceptance_date: values.acceptance_date?.format('YYYY-MM-DD'),
    };

    if (editingPayment) {
      const { dispatch_order_id, ...updateData } = data;
      updateMutation.mutate({ id: editingPayment.id, data: updateData });
    } else {
      createMutation.mutate(data);
    }
  };

  const columns: ColumnsType<ContractPayment> = [
    {
      title: '派工單號',
      dataIndex: 'dispatch_no',
      width: 120,
    },
    {
      title: '工程名稱',
      dataIndex: 'project_name',
      width: 200,
      ellipsis: true,
    },
    {
      title: '本次派工金額',
      dataIndex: 'current_amount',
      width: 130,
      align: 'right',
      render: (val?: number) => (val ? `$${val.toLocaleString()}` : '-'),
    },
    {
      title: '累進派工金額',
      dataIndex: 'cumulative_amount',
      width: 130,
      align: 'right',
      render: (val?: number) => (val ? `$${val.toLocaleString()}` : '-'),
    },
    {
      title: '剩餘金額',
      dataIndex: 'remaining_amount',
      width: 130,
      align: 'right',
      render: (val?: number) => (val ? `$${val.toLocaleString()}` : '-'),
    },
    {
      title: '驗收日期',
      dataIndex: 'acceptance_date',
      width: 110,
      render: (val?: string) => (val ? dayjs(val).format('YYYY-MM-DD') : '-'),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="編輯">
            <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} />
          </Tooltip>
          <Popconfirm title="確定刪除?" onConfirm={() => deleteMutation.mutate(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* 統計卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="本次派工金額"
              value={totalCurrentAmount}
              prefix={<DollarOutlined />}
              precision={0}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="累進派工金額" value={totalCumulativeAmount} precision={0} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="剩餘金額"
              value={totalRemainingAmount}
              valueStyle={{ color: '#1890ff' }}
              precision={0}
            />
          </Card>
        </Col>
      </Row>

      {/* 工具列 */}
      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="選擇派工單"
          style={{ width: 300 }}
          value={selectedOrderId}
          onChange={setSelectedOrderId}
          allowClear
        >
          {orders.map((order) => (
            <Select.Option key={order.id} value={order.id}>
              {order.dispatch_no || `派工單 #${order.id}`} - {order.project_name || ''}
            </Select.Option>
          ))}
        </Select>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()} disabled={!selectedOrderId}>
          重新整理
        </Button>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate} disabled={!selectedOrderId}>
          新增契金紀錄
        </Button>
      </Space>

      <Table
        columns={columns}
        dataSource={payments}
        rowKey="id"
        loading={isLoading}
        pagination={{
          showSizeChanger: true,
          showTotal: (total) => `共 ${total} 筆`,
        }}
      />

      <Modal
        title={editingPayment ? '編輯契金紀錄' : '新增契金紀錄'}
        open={modalVisible}
        onOk={handleSubmit}
        onCancel={() => {
          setModalVisible(false);
          setEditingPayment(null);
          form.resetFields();
        }}
        width={800}
        confirmLoading={createMutation.isPending || updateMutation.isPending}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="dispatch_order_id" hidden>
            <Input />
          </Form.Item>

          <Title level={5}>作業類別派工</Title>
          {/* 01.地上物查估作業 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="work_01_date" label="01.地上物查估 - 派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="work_01_amount" label="01.地上物查估 - 金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          {/* 02.土地協議市價查估作業 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="work_02_date" label="02.土地協議市價查估 - 派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="work_02_amount" label="02.土地協議市價查估 - 金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          {/* 03.土地徵收市價查估作業 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="work_03_date" label="03.土地徵收市價查估 - 派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="work_03_amount" label="03.土地徵收市價查估 - 金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          {/* 04.相關計畫書製作 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="work_04_date" label="04.相關計畫書製作 - 派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="work_04_amount" label="04.相關計畫書製作 - 金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          {/* 05.測量作業 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="work_05_date" label="05.測量作業 - 派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="work_05_amount" label="05.測量作業 - 金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          {/* 06.樁位測釘作業 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="work_06_date" label="06.樁位測釘作業 - 派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="work_06_amount" label="06.樁位測釘作業 - 金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          {/* 07.辦理教育訓練 */}
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="work_07_date" label="07.辦理教育訓練 - 派工日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="work_07_amount" label="07.辦理教育訓練 - 金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>

          <Title level={5} style={{ marginTop: 16 }}>金額彙總</Title>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="current_amount" label="本次派工金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="cumulative_amount" label="累進派工金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item name="remaining_amount" label="剩餘金額">
                <InputNumber style={{ width: '100%' }} min={0} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item name="acceptance_date" label="完成驗收日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>
    </div>
  );
};

export default PaymentsTab;
