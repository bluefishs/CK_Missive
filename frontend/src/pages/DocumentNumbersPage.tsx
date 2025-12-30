import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Space,
  Table,
  Tag,
  Statistic,
  Row,
  Col,
  Input,
  Select,
  DatePicker,
  Modal,
  Form,
  message,
  Typography,
  Badge,
  Tooltip,
  Divider
} from 'antd';
import {
  PlusOutlined,
  ReloadOutlined,
  EyeOutlined,
  EditOutlined,
  FileTextOutlined,
  NumberOutlined,
  CalendarOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';

const { Title, Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface DocumentNumber {
  id: number;
  doc_prefix: string;
  year: number;
  sequence_number: number;
  full_number: string;
  subject: string;
  contract_case: string;
  receiver: string;
  send_date: string;
  status: string;
  created_by: string;
  created_at: string;
}

interface NextNumber {
  year: number;
  roc_year: number;
  sequence_number: number;
  full_number: string;
  previous_max: number;
}

interface Stats {
  total_count: number;
  draft_count: number;
  sent_count: number;
  max_sequence: number;
  year_range: {
    min_year: number | null;
    max_year: number | null;
  };
  yearly_stats: Array<{ year: number; count: number }>;
}

export const DocumentNumbersPage: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<DocumentNumber[]>([]);
  const [total, setTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [stats, setStats] = useState<Stats | null>(null);
  const [nextNumber, setNextNumber] = useState<NextNumber | null>(null);

  // 篩選條件
  const [filters, setFilters] = useState({
    year: undefined as number | undefined,
    status: undefined as string | undefined,
    keyword: undefined as string | undefined,
  });

  // 新增/編輯模態框
  const [modalOpen, setModalOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<DocumentNumber | null>(null);
  const [form] = Form.useForm();

  // 載入數據
  const loadData = async () => {
    setLoading(true);
    try {
      // 載入發文字號列表
      const params = new URLSearchParams({
        page: currentPage.toString(),
        per_page: pageSize.toString(),
      });

      if (filters.year) params.append('year', filters.year.toString());
      if (filters.status) params.append('status', filters.status);
      if (filters.keyword) params.append('keyword', filters.keyword);

      const response = await fetch(`/api/document-numbers/?${params}`);
      const result = await response.json();

      if (response.ok) {
        setData(result.items);
        setTotal(result.total);
      } else {
        message.error('載入發文字號列表失敗');
      }

      // 載入統計資料
      const statsResponse = await fetch('/api/document-numbers/stats');
      if (statsResponse.ok) {
        const statsResult = await statsResponse.json();
        setStats(statsResult);
      }

      // 載入下一個可用字號
      const nextResponse = await fetch('/api/document-numbers/next-number');
      if (nextResponse.ok) {
        const nextResult = await nextResponse.json();
        setNextNumber(nextResult);
      }

    } catch (error) {
      console.error('載入資料失敗:', error);
      message.error('載入資料失敗');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [currentPage, pageSize, filters]);

  // 處理篩選變更
  const handleFilterChange = (key: string, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value
    }));
    setCurrentPage(1); // 重置到第一頁
  };

  // 重置篩選
  const handleResetFilters = () => {
    setFilters({
      year: undefined,
      status: undefined,
      keyword: undefined,
    });
    setCurrentPage(1);
  };

  // 新增發文字號
  const handleCreate = () => {
    setEditingRecord(null);
    form.resetFields();
    if (nextNumber) {
      form.setFieldsValue({
        full_number: nextNumber.full_number,
        year: nextNumber.year,
        send_date: dayjs().format('YYYY-MM-DD')
      });
    }
    setModalOpen(true);
  };

  // 編輯發文字號
  const handleEdit = (record: DocumentNumber) => {
    setEditingRecord(record);
    form.setFieldsValue({
      ...record,
      send_date: record.send_date ? dayjs(record.send_date) : undefined
    });
    setModalOpen(true);
  };

  // 儲存發文字號
  const handleSave = async (values: any) => {
    try {
      const payload = {
        ...values,
        send_date: values.send_date ? dayjs(values.send_date).format('YYYY-MM-DD') : null
      };

      const url = editingRecord 
        ? `/api/document-numbers/${editingRecord.id}`
        : '/api/document-numbers/';

      const method = editingRecord ? 'PUT' : 'POST';

      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload)
      });

      const result = await response.json();

      if (response.ok) {
        message.success(editingRecord ? '更新成功' : '新增成功');
        setModalOpen(false);
        loadData(); // 重新載入資料
      } else {
        message.error(result.detail || '操作失敗');
      }
    } catch (error) {
      console.error('儲存失敗:', error);
      message.error('儲存失敗');
    }
  };

  // 排序狀態
  const [sortField, setSortField] = useState<string>('');
  const [sortOrder, setSortOrder] = useState<'ascend' | 'descend' | null>(null);

  // 處理表格變更（排序）
  const handleTableChange = (pagination: any, filters: any, sorter: any) => {
    if (sorter && sorter.field) {
      setSortField(sorter.field);
      setSortOrder(sorter.order);
    }
  };

  // 表格欄位定義
  const columns: ColumnsType<DocumentNumber> = [
    {
      title: '發文字號',
      dataIndex: 'full_number',
      key: 'full_number',
      width: 200,
      sorter: true,
      sortOrder: sortField === 'full_number' ? sortOrder : null,
      render: (text) => <Text strong copyable>{text}</Text>
    },
    {
      title: '年度',
      dataIndex: 'year',
      key: 'year',
      width: 80,
      align: 'center',
      sorter: true,
      sortOrder: sortField === 'year' ? sortOrder : null,
      render: (year) => <Tag color="blue">{year}</Tag>
    },
    {
      title: '流水號',
      dataIndex: 'sequence_number',
      key: 'sequence_number',
      width: 100,
      align: 'center',
      sorter: true,
      sortOrder: sortField === 'sequence_number' ? sortOrder : null,
      render: (num) => <Text code>{num ? num.toString().padStart(6, '0') : '000000'}</Text>
    },
    {
      title: '公文主旨',
      dataIndex: 'subject',
      key: 'subject',
      ellipsis: true,
      sorter: true,
      sortOrder: sortField === 'subject' ? sortOrder : null,
      render: (text) => text || <Text type="secondary">未填寫</Text>
    },
    {
      title: '承攬案件',
      dataIndex: 'contract_case',
      key: 'contract_case',
      width: 200,
      ellipsis: true,
      sorter: true,
      sortOrder: sortField === 'contract_case' ? sortOrder : null,
      render: (text) => text || <Text type="secondary">無</Text>
    },
    {
      title: '受文單位',
      dataIndex: 'receiver',
      key: 'receiver',
      width: 180,
      ellipsis: true,
      sorter: true,
      sortOrder: sortField === 'receiver' ? sortOrder : null,
      render: (text) => text || <Text type="secondary">未填寫</Text>
    },
    {
      title: '發文日期',
      dataIndex: 'send_date',
      key: 'send_date',
      width: 120,
      align: 'center',
      sorter: true,
      sortOrder: sortField === 'send_date' ? sortOrder : null,
      render: (date) => date ? dayjs(date).format('YYYY-MM-DD') : <Text type="secondary">未設定</Text>
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      align: 'center',
      sorter: true,
      sortOrder: sortField === 'status' ? sortOrder : null,
      render: (status) => {
        const statusConfig = {
          'draft': { color: 'orange', text: '草稿' },
          'sent': { color: 'green', text: '已發文' },
          'archived': { color: 'gray', text: '已歸檔' }
        };
        const config = statusConfig[status as keyof typeof statusConfig] || { color: 'default', text: status };
        return <Tag color={config.color}>{config.text}</Tag>;
      }
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space>
          <Tooltip title="檢視">
            <Button
              type="text"
              size="small"
              icon={<EyeOutlined />}
            />
          </Tooltip>
          <Tooltip title="編輯">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* 頁面標題與統計 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={24}>
          <Title level={2} style={{ margin: 0, display: 'flex', alignItems: 'center' }}>
            <FileTextOutlined style={{ marginRight: 8 }} />
            發文字號管理
          </Title>
        </Col>
      </Row>

      {/* 統計卡片 */}
      {stats && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="總發文數"
                value={stats.total_count}
                prefix={<NumberOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="草稿"
                value={stats.draft_count}
                valueStyle={{ color: '#faad14' }}
                prefix={<EditOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="已發文"
                value={stats.sent_count}
                valueStyle={{ color: '#52c41a' }}
                prefix={<FileTextOutlined />}
              />
            </Card>
          </Col>
          <Col xs={24} sm={6}>
            <Card>
              <Statistic
                title="最大流水號"
                value={stats.max_sequence}
                formatter={(value) => value ? value.toString().padStart(6, '0') : '000000'}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 下一個字號預覽 */}
      {nextNumber && (
        <Card style={{ marginBottom: 24, background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
          <Row gutter={16} align="middle">
            <Col flex="1">
              <Space direction="vertical" size={0}>
                <Text style={{ color: 'white', opacity: 0.8 }}>下一個可用發文字號</Text>
                <Title level={3} style={{ margin: 0, color: 'white' }}>
                  {nextNumber.full_number}
                </Title>
                <Text style={{ color: 'white', opacity: 0.9 }}>
                  {nextNumber?.year}年 (民國{nextNumber?.roc_year}年) • 流水號 {nextNumber?.sequence_number ? nextNumber.sequence_number.toString().padStart(6, '0') : '000000'}
                </Text>
              </Space>
            </Col>
            <Col>
              <Button
                type="primary"
                size="large"
                icon={<PlusOutlined />}
                onClick={handleCreate}
                style={{ background: 'rgba(255,255,255,0.2)', borderColor: 'white' }}
              >
                建立新發文
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {/* 篩選與操作區 */}
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]} align="middle">
          <Col xs={24} sm={8} md={5}>
            <Input
              placeholder="搜尋主旨、受文單位、案件"
              prefix={<SearchOutlined />}
              value={filters.keyword}
              onChange={(e) => handleFilterChange('keyword', e.target.value)}
            />
          </Col>
          <Col xs={12} sm={4} md={3}>
            <Select
              placeholder="年度"
              value={filters.year}
              onChange={(value) => handleFilterChange('year', value)}
              allowClear
              style={{ width: '100%' }}
            >
              {stats?.yearly_stats?.map(stat => (
                <Option key={stat.year} value={stat.year}>
                  {stat.year}年 ({stat.count})
                </Option>
              )) || []}
            </Select>
          </Col>
          <Col xs={12} sm={4} md={3}>
            <Select
              placeholder="狀態"
              value={filters.status}
              onChange={(value) => handleFilterChange('status', value)}
              allowClear
              style={{ width: '100%' }}
            >
              <Option value="draft">草稿</Option>
              <Option value="sent">已發文</Option>
              <Option value="archived">已歸檔</Option>
            </Select>
          </Col>
          <Col xs={24} sm={8} md={13}>
            <Space>
              <Button onClick={handleResetFilters}>重置篩選</Button>
              <Button icon={<ReloadOutlined />} onClick={loadData} loading={loading}>
                重新整理
              </Button>
              <Divider type="vertical" />
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleCreate}
              >
                新增發文字號
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 資料表格 */}
      <Card>
        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          onChange={handleTableChange}
          pagination={{
            current: currentPage,
            pageSize: pageSize,
            total: total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 項，共 ${total} 項`,
            onChange: (page, size) => {
              setCurrentPage(page);
              setPageSize(size);
            },
          }}
          scroll={{ x: 1200 }}
          showSorterTooltip={{
            title: '點擊排序'
          }}
        />
      </Card>

      {/* 新增/編輯模態框 */}
      <Modal
        title={editingRecord ? '編輯發文字號' : '新增發文字號'}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={null}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSave}
        >
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                label="發文字號"
                name="full_number"
              >
                <Input disabled />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="狀態"
                name="status"
                rules={[{ required: true, message: '請選擇狀態' }]}
              >
                <Select>
                  <Option value="draft">草稿</Option>
                  <Option value="sent">已發文</Option>
                  <Option value="archived">已歸檔</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="公文主旨"
            name="subject"
            rules={[{ required: true, message: '請輸入公文主旨' }]}
          >
            <TextArea rows={2} placeholder="請輸入公文主旨" />
          </Form.Item>

          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Form.Item
                label="承攬案件名稱"
                name="contract_case"
              >
                <Input placeholder="請輸入承攬案件名稱" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                label="發文日期"
                name="send_date"
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            label="受文單位"
            name="receiver"
            rules={[{ required: true, message: '請輸入受文單位' }]}
          >
            <Input placeholder="請輸入受文單位" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setModalOpen(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                {editingRecord ? '更新' : '新增'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DocumentNumbersPage;