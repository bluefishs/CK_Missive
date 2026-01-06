import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Typography, 
  Row, 
  Col, 
  Statistic, 
  Select, 
  DatePicker, 
  Space,
  Table,
  Button,
  Spin,
  message
} from 'antd';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  ResponsiveContainer
} from 'recharts';
import { 
  FileTextOutlined, 
  ClockCircleOutlined, 
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  DownloadOutlined
} from '@ant-design/icons';

const { Title } = Typography;
const { Option } = Select;
const { RangePicker } = DatePicker;

const ReportsPage: React.FC = () => {
  const [selectedPeriod, setSelectedPeriod] = useState('month');
  const [loading, setLoading] = useState(false);
  const [monthlyData, setMonthlyData] = useState<any[]>([]);
  const [statusData, setStatusData] = useState<any[]>([]);
  const [departmentData, setDepartmentData] = useState<any[]>([]);
  const [totalStats, setTotalStats] = useState({
    total: 0,
    processed: 0,
    processing: 0,
    overdue: 0
  });

  useEffect(() => {
    loadReportData();
  }, [selectedPeriod]);

  const loadReportData = async () => {
    setLoading(true);
    try {
      // 載入文件統計數據 (暫時使用模擬數據)
      console.log('Loading reports data for period:', selectedPeriod);

      // 模擬 API 回應數據
      const mockData = {
        monthly_data: [
          { month: '2025-01', documents: 45, processed: 40, pending: 5 },
          { month: '2025-02', documents: 52, processed: 48, pending: 4 },
          { month: '2025-03', documents: 38, processed: 35, pending: 3 },
          { month: '2025-04', documents: 61, processed: 58, pending: 3 },
          { month: '2025-05', documents: 47, processed: 44, pending: 3 },
          { month: '2025-06', documents: 53, processed: 50, pending: 3 },
        ]
      };

      setMonthlyData(mockData.monthly_data);

      // 模擬狀態數據
      const mockStatusData = [
        { name: '已處理', value: 245, color: '#52c41a' },
        { name: '處理中', value: 28, color: '#faad14' },
        { name: '待處理', value: 15, color: '#ff4d4f' },
        { name: '已完成', value: 188, color: '#1890ff' }
      ];

      setStatusData(mockStatusData);

      // 模擬部門數據
      const mockDepartmentData = [
        { department: '資訊室', total: 48, completed: 45, rate: '94%' },
        { department: '人事室', total: 32, completed: 30, rate: '94%' },
        { department: '會計室', total: 25, completed: 24, rate: '96%' },
        { department: '總務處', total: 41, completed: 38, rate: '93%' },
        { department: '秘書室', total: 19, completed: 18, rate: '95%' }
      ];

      setDepartmentData(mockDepartmentData);

      // 模擬總計統計
      const mockTotalStats = {
        total: 476,
        processed: 355,
        processing: 95,
        overdue: 26
      };

      setTotalStats(mockTotalStats);

    } catch (error) {
      console.error('Failed to load report data:', error);
      message.error('載入報表數據失敗');

      // 設置空數據
      setMonthlyData([]);
      setStatusData([]);
      setDepartmentData([]);
      setTotalStats({ total: 0, processed: 0, processing: 0, overdue: 0 });
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    const colorMap: { [key: string]: string } = {
      'processed': '#52c41a',
      'processing': '#1890ff',
      'pending': '#faad14',
      'overdue': '#ff4d4f'
    };
    return colorMap[status] || '#d9d9d9';
  };

  const columns = [
    {
      title: '部門',
      dataIndex: 'department',
      key: 'department',
    },
    {
      title: '總公文數',
      dataIndex: 'total',
      key: 'total',
      sorter: (a: any, b: any) => a.total - b.total,
    },
    {
      title: '已完成',
      dataIndex: 'completed',
      key: 'completed',
      sorter: (a: any, b: any) => a.completed - b.completed,
    },
    {
      title: '完成率',
      dataIndex: 'rate',
      key: 'rate',
      sorter: (a: any, b: any) => parseFloat(a.rate) - parseFloat(b.rate),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Title level={2}>統計報表</Title>

      <Spin spinning={loading}>
      
      {/* 篩選器 */}
      <Card style={{ marginBottom: 16 }}>
        <Space size="large">
          <span>統計期間：</span>
          <Select
            value={selectedPeriod}
            onChange={(value) => {
              setSelectedPeriod(value);
              loadReportData();
            }}
            style={{ width: 120 }}
          >
            <Option value="week">本週</Option>
            <Option value="month">本月</Option>
            <Option value="quarter">本季</Option>
            <Option value="year">本年</Option>
          </Select>
          <RangePicker />
          <Button type="primary" icon={<DownloadOutlined />}>
            匯出報表
          </Button>
        </Space>
      </Card>

      {/* 統計卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="總公文數"
              value={totalStats.total}
              prefix={<FileTextOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已處理"
              value={totalStats.processed}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="處理中"
              value={totalStats.processing}
              prefix={<ClockCircleOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="逾期未處理"
              value={totalStats.overdue}
              prefix={<ExclamationCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 圖表區域 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="每月公文處理趨勢">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={monthlyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="documents" 
                  stroke="#1890ff" 
                  name="總公文數"
                />
                <Line 
                  type="monotone" 
                  dataKey="processed" 
                  stroke="#52c41a" 
                  name="已處理"
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="公文處理狀態分布">
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={statusData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry: any) => `${entry.name} ${(entry.percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {statusData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="各月公文數量統計">
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={monthlyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="documents" fill="#1890ff" name="總公文" />
                <Bar dataKey="processed" fill="#52c41a" name="已處理" />
                <Bar dataKey="pending" fill="#faad14" name="待處理" />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="各部門處理效率">
            <Table
              dataSource={departmentData}
              columns={columns}
              pagination={false}
              size="small"
              rowKey="department"
            />
          </Card>
        </Col>
      </Row>

      </Spin>
    </div>
  );
};

export default ReportsPage;