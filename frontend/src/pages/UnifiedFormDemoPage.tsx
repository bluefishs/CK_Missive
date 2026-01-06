import React, { useState } from 'react';
import {
  Card,
  Typography,
  Space,
  Form,
  Input,
  Button,
  Select,
  Row,
  Col,
  Divider,
  Alert,
  Tag,
  App
} from 'antd';
import {
  FormOutlined,
  TableOutlined,
  NumberOutlined,
  MessageOutlined,
  DatabaseOutlined
} from '@ant-design/icons';

import UnifiedTable, { FilterConfig } from '../components/common/UnifiedTable';
import SequenceNumberGenerator from '../components/common/SequenceNumberGenerator';
import RemarksField from '../components/common/RemarksField';

const { Title, Text } = Typography;
const { Option } = Select;

// 模擬數據接口
interface DemoRecord {
  id: number;
  sequence_number: string;
  title: string;
  category: string;
  status: string;
  priority: string;
  created_date: string;
  created_by: string;
  amount?: number;
  remarks?: string;
}

const UnifiedFormDemoPage: React.FC = () => {
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [demoData, setDemoData] = useState<DemoRecord[]>([
    {
      id: 1,
      sequence_number: 'DOC-20240912-0001',
      title: '系統需求分析文件',
      category: '技術文件',
      status: '進行中',
      priority: '高',
      created_date: '2024-09-12',
      created_by: '張三',
      amount: 50000,
      remarks: '需要在本月底前完成初稿'
    },
    {
      id: 2,
      sequence_number: 'DOC-20240912-0002',
      title: '用戶介面設計規範',
      category: '設計文件',
      status: '已完成',
      priority: '中',
      created_date: '2024-09-11',
      created_by: '李四',
      amount: 30000,
      remarks: '已通過設計審查'
    },
    {
      id: 3,
      sequence_number: 'DOC-20240912-0003',
      title: '資料庫架構設計',
      category: '技術文件',
      status: '待開始',
      priority: '高',
      created_date: '2024-09-10',
      created_by: '王五',
      amount: 80000,
      remarks: '等待前期需求確認完成'
    },
    {
      id: 4,
      sequence_number: 'PRJ-2024-001',
      title: 'CK Missive 專案管理系統',
      category: '軟體開發',
      status: '進行中',
      priority: '高',
      created_date: '2024-09-01',
      created_by: '陳六',
      amount: 500000,
      remarks: '主要功能模組開發中'
    },
    {
      id: 5,
      sequence_number: 'VEN-202409-001',
      title: '雲端服務供應商合作',
      category: '合作夥伴',
      status: '洽談中',
      priority: '中',
      created_date: '2024-09-05',
      created_by: '趙七',
      amount: 120000,
      remarks: '正在評估技術方案與成本'
    }
  ]);

  const [formSequenceNumber, setFormSequenceNumber] = useState('');
  const [formRemarks, setFormRemarks] = useState('');

  // 表格列配置
  const columns = [
    {
      title: '標題',
      dataIndex: 'title',
      key: 'title',
      render: (text: string) => <Text strong>{text}</Text>
    },
    {
      title: '流水號',
      dataIndex: 'sequence_number',
      key: 'sequence_number',
      width: 150,
      render: (text: string) => <Text code>{text}</Text>
    },
    {
      title: '類別',
      dataIndex: 'category',
      key: 'category',
      width: 120
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => {
        const colors = {
          '進行中': 'processing',
          '已完成': 'success',
          '待開始': 'default',
          '洽談中': 'warning'
        };
        return <Tag color={colors[status as keyof typeof colors]}>{status}</Tag>;
      }
    },
    {
      title: '優先級',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (priority: string) => {
        const colors = {
          '高': 'red',
          '中': 'orange',
          '低': 'green'
        };
        return <Tag color={colors[priority as keyof typeof colors]}>{priority}</Tag>;
      }
    },
    {
      title: '金額',
      dataIndex: 'amount',
      key: 'amount',
      width: 120,
      render: (amount: number) => amount ? `NT$ ${amount.toLocaleString()}` : '-'
    },
    {
      title: '建立日期',
      dataIndex: 'created_date',
      key: 'created_date',
      width: 120
    },
    {
      title: '建立者',
      dataIndex: 'created_by',
      key: 'created_by',
      width: 100
    }
  ];

  // 篩選配置
  const filterConfigs: FilterConfig[] = [
    {
      key: 'category',
      label: '類別',
      type: 'select',
      options: [
        { value: '技術文件', label: '技術文件' },
        { value: '設計文件', label: '設計文件' },
        { value: '軟體開發', label: '軟體開發' },
        { value: '合作夥伴', label: '合作夥伴' }
      ]
    },
    {
      key: 'status',
      label: '狀態',
      type: 'select',
      options: [
        { value: '進行中', label: '進行中' },
        { value: '已完成', label: '已完成' },
        { value: '待開始', label: '待開始' },
        { value: '洽談中', label: '洽談中' }
      ]
    },
    {
      key: 'priority',
      label: '優先級',
      type: 'select',
      options: [
        { value: '高', label: '高' },
        { value: '中', label: '中' },
        { value: '低', label: '低' }
      ]
    },
    {
      key: 'created_by',
      label: '建立者',
      type: 'autocomplete',
      autoCompleteOptions: ['張三', '李四', '王五', '陳六', '趙七']
    },
    {
      key: 'created_date',
      label: '建立日期',
      type: 'dateRange'
    }
  ];

  // 表單提交
  const handleFormSubmit = (values: any) => {
    const newRecord: DemoRecord = {
      id: demoData.length + 1,
      sequence_number: formSequenceNumber || '',
      title: values.title,
      category: values.category,
      status: values.status || '待開始',
      priority: values.priority || '中',
      created_date: new Date().toISOString().split('T')[0] ?? '',
      created_by: '當前使用者',
      amount: values.amount ? Number(values.amount) : undefined,
      remarks: formRemarks
    };

    setDemoData([...demoData, newRecord]);
    form.resetFields();
    setFormSequenceNumber('');
    setFormRemarks('');
    message.success('記錄已新增');
  };

  // 導出功能
  const handleExport = (filteredData: DemoRecord[]) => {
    const exportData = filteredData.map(item => ({
      流水號: item.sequence_number,
      標題: item.title,
      類別: item.category,
      狀態: item.status,
      優先級: item.priority,
      金額: item.amount || 0,
      建立日期: item.created_date,
      建立者: item.created_by,
      備註: item.remarks || ''
    }));

    if (exportData.length === 0) {
      message.warning('沒有數據可導出');
      return;
    }
    const csvContent = [
      Object.keys(exportData[0]!).join(','),
      ...exportData.map(row => Object.values(row).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `統一表單數據_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
    message.success('CSV 文件已導出');
  };

  return (
    <div style={{ padding: '24px' }}>
      <Space direction="vertical" style={{ width: '100%' }} size="large">
        {/* 頁面標題 */}
        <Card>
          <Space direction="vertical" style={{ width: '100%' }}>
            <Title level={2}>
              <FormOutlined style={{ marginRight: 8 }} />
              統一表單系統演示
            </Title>
            <Alert
              message="功能特色"
              description={
                <div>
                  <Text>此頁面展示了統一表單系統的核心功能：</Text>
                  <div style={{ marginTop: 8 }}>
                    <Tag color="blue">自動流水號生成</Tag>
                    <Tag color="green">智能篩選與排序</Tag>
                    <Tag color="orange">備註說明管理</Tag>
                    <Tag color="purple">數據導出功能</Tag>
                    <Tag color="red">響應式設計</Tag>
                  </div>
                </div>
              }
              type="info"
              showIcon
            />
          </Space>
        </Card>

        {/* 新增表單 */}
        <Card title={<><FormOutlined /> 新增記錄</>}>
          <Form
            form={form}
            layout="vertical"
            onFinish={handleFormSubmit}
          >
            <Row gutter={16}>
              <Col xs={24} md={8}>
                <Form.Item label="流水號" required>
                  <SequenceNumberGenerator
                    value={formSequenceNumber}
                    onChange={setFormSequenceNumber}
                    category="document"
                    autoGenerate={true}
                  />
                </Form.Item>
              </Col>
              <Col xs={24} md={16}>
                <Form.Item
                  name="title"
                  label="標題"
                  rules={[{ required: true, message: '請輸入標題' }]}
                >
                  <Input placeholder="請輸入記錄標題" />
                </Form.Item>
              </Col>
            </Row>

            <Row gutter={16}>
              <Col xs={24} sm={8}>
                <Form.Item
                  name="category"
                  label="類別"
                  rules={[{ required: true, message: '請選擇類別' }]}
                >
                  <Select placeholder="選擇類別">
                    <Option value="技術文件">技術文件</Option>
                    <Option value="設計文件">設計文件</Option>
                    <Option value="軟體開發">軟體開發</Option>
                    <Option value="合作夥伴">合作夥伴</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item name="priority" label="優先級" initialValue="中">
                  <Select>
                    <Option value="高">高</Option>
                    <Option value="中">中</Option>
                    <Option value="低">低</Option>
                  </Select>
                </Form.Item>
              </Col>
              <Col xs={24} sm={8}>
                <Form.Item name="amount" label="預算金額">
                  <Input type="number" placeholder="輸入金額" addonBefore="NT$" />
                </Form.Item>
              </Col>
            </Row>

            <Form.Item label="備註說明">
              <RemarksField
                value={formRemarks}
                onChange={setFormRemarks}
                placeholder="請輸入相關備註說明..."
                inline={true}
                maxLength={500}
              />
            </Form.Item>

            <Form.Item>
              <Button type="primary" htmlType="submit" size="large">
                <FormOutlined /> 新增記錄
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {/* 數據表格 */}
        <UnifiedTable
          title="記錄列表"
          subtitle="支持全文搜索、多欄位篩選、自定義排序等功能"
          columns={columns}
          data={demoData}
          filterConfigs={filterConfigs}
          enableExport={true}
          enableSequenceNumber={true}
          onExport={handleExport}
          onRefresh={() => {
            message.success('數據已刷新');
          }}
          rowKey="id"
          customActions={
            <Button type="dashed">
              <DatabaseOutlined /> 自定義操作
            </Button>
          }
        />

        {/* 功能說明 */}
        <Card title="功能詳細說明">
          <Row gutter={16}>
            <Col xs={24} md={12}>
              <Card size="small" title={<><NumberOutlined /> 流水號系統</>}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text>• 支持自定義前綴、日期格式、分隔符</Text>
                  <Text>• 自動生成唯一流水號</Text>
                  <Text>• 支持手動編輯和複製功能</Text>
                  <Text>• 提供格式預覽</Text>
                </Space>
              </Card>
            </Col>
            <Col xs={24} md={12}>
              <Card size="small" title={<><MessageOutlined /> 備註管理</>}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text>• 行內編輯模式</Text>
                  <Text>• 支持歷史記錄查看</Text>
                  <Text>• 快捷鍵操作 (Ctrl+Enter, Esc)</Text>
                  <Text>• 字數限制和統計</Text>
                </Space>
              </Card>
            </Col>
          </Row>
          
          <Divider />
          
          <Card size="small" title={<><TableOutlined /> 統一表格功能</>}>
            <Row gutter={16}>
              <Col xs={24} md={8}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text strong>篩選功能:</Text>
                  <Text>• 全文搜索</Text>
                  <Text>• 下拉選單篩選</Text>
                  <Text>• 日期區間篩選</Text>
                  <Text>• 自動完成輸入</Text>
                </Space>
              </Col>
              <Col xs={24} md={8}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text strong>排序功能:</Text>
                  <Text>• 多欄位排序</Text>
                  <Text>• 升序/降序切換</Text>
                  <Text>• 數字、日期、文字智能排序</Text>
                  <Text>• 排序狀態指示</Text>
                </Space>
              </Col>
              <Col xs={24} md={8}>
                <Space direction="vertical" style={{ width: '100%' }}>
                  <Text strong>其他功能:</Text>
                  <Text>• 數據導出 (CSV/JSON)</Text>
                  <Text>• 序號自動生成</Text>
                  <Text>• 響應式布局</Text>
                  <Text>• 篩選條件可視化</Text>
                </Space>
              </Col>
            </Row>
          </Card>
        </Card>
      </Space>
    </div>
  );
};

export default UnifiedFormDemoPage;