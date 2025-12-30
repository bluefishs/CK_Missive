import React, { useState, useEffect } from 'react';
import {
  Card,
  Descriptions,
  Tag,
  Button,
  Space,
  Typography,
  Spin,
  message,
  Row,
  Col,
  Progress,
  Tabs,
  Table,
  Timeline,
  Upload,
  Empty,
  Tooltip,
  Popconfirm,
} from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
  CalendarOutlined,
  PaperClipOutlined,
  InfoCircleOutlined,
  UploadOutlined,
  DownloadOutlined,
  EyeOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import {
  ContractCase,
  ContractCaseType,
  CONTRACT_CASE_TYPE_LABELS,
  CONTRACT_CASE_TYPE_COLORS,
  CONTRACT_CASE_STATUS_LABELS,
  CONTRACT_CASE_STATUS_COLORS,
} from '../types/contractCase';
import { ROUTES } from '../router/types';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

// 里程碑類型
interface Milestone {
  id: number;
  title: string;
  description?: string;
  due_date: string;
  status: 'pending' | 'in_progress' | 'completed' | 'overdue';
  completed_date?: string;
}

// 附件類型
interface Attachment {
  id: number;
  filename: string;
  file_size: number;
  file_type: string;
  uploaded_at: string;
  uploaded_by: string;
}

// 關聯文件類型
interface RelatedDocument {
  id: number;
  doc_number: string;
  doc_type: string;
  subject: string;
  doc_date: string;
  sender: string;
}

// 模擬數據
const mockData: ContractCase = {
  id: 1,
  year: '2024',
  project_name: '數位測繪技術創新專案',
  client_unit: '內政部國土測繪中心',
  contract_period_start: '2024-01-15',
  contract_period_end: '2024-12-31',
  responsible_staff: '王小明',
  partner_vendor: '精密測量科技有限公司',
  case_type: ContractCaseType.INNOVATION,
  case_status: 'in_progress',
  contract_amount: 5000000,
  description: '開發新一代數位測繪技術，包含點雲資料處理、三維建模、精度驗證等功能模組。本專案旨在提升測繪作業效率與精度，降低人力成本，建立智慧化測繪作業流程。',
  notes: '需要配合新採購的測繪設備進行整合測試。',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

// 模擬里程碑數據
const mockMilestones: Milestone[] = [
  {
    id: 1,
    title: '專案啟動會議',
    description: '召開專案啟動會議，確認專案範圍與時程',
    due_date: '2024-01-20',
    status: 'completed',
    completed_date: '2024-01-18',
  },
  {
    id: 2,
    title: '需求分析與規劃',
    description: '完成需求訪談與系統分析',
    due_date: '2024-02-28',
    status: 'completed',
    completed_date: '2024-02-25',
  },
  {
    id: 3,
    title: '系統設計審查',
    description: '完成系統架構設計並通過審查',
    due_date: '2024-04-15',
    status: 'completed',
    completed_date: '2024-04-12',
  },
  {
    id: 4,
    title: '第一階段開發完成',
    description: '完成核心功能模組開發',
    due_date: '2024-07-31',
    status: 'in_progress',
  },
  {
    id: 5,
    title: '整合測試',
    description: '進行系統整合測試與效能驗證',
    due_date: '2024-10-31',
    status: 'pending',
  },
  {
    id: 6,
    title: '專案結案',
    description: '完成驗收與結案報告',
    due_date: '2024-12-31',
    status: 'pending',
  },
];

// 模擬關聯文件
const mockRelatedDocuments: RelatedDocument[] = [
  {
    id: 1,
    doc_number: '乾坤測字第1140000145號',
    doc_type: '函',
    subject: '檢送「數位測繪技術創新專案」契約書乙份',
    doc_date: '2024-01-10',
    sender: '內政部國土測繪中心',
  },
  {
    id: 2,
    doc_number: '乾坤測字第1140000230號',
    doc_type: '函',
    subject: '有關本專案第一期款撥付案',
    doc_date: '2024-02-15',
    sender: '內政部國土測繪中心',
  },
  {
    id: 3,
    doc_number: '乾坤測字第1140000456號',
    doc_type: '函',
    subject: '有關本專案期中報告審查意見回覆說明',
    doc_date: '2024-05-20',
    sender: '乾坤測量有限公司',
  },
];

// 模擬附件
const mockAttachments: Attachment[] = [
  {
    id: 1,
    filename: '專案契約書.pdf',
    file_size: 2048576,
    file_type: 'application/pdf',
    uploaded_at: '2024-01-15',
    uploaded_by: '王小明',
  },
  {
    id: 2,
    filename: '需求規格書v1.0.docx',
    file_size: 512000,
    file_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    uploaded_at: '2024-02-28',
    uploaded_by: '李小華',
  },
  {
    id: 3,
    filename: '系統架構設計圖.pptx',
    file_size: 3145728,
    file_type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    uploaded_at: '2024-04-10',
    uploaded_by: '王小明',
  },
];

export const ContractCaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ContractCase | null>(null);
  const [activeTab, setActiveTab] = useState('basic');
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [relatedDocs, setRelatedDocs] = useState<RelatedDocument[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    setLoading(true);
    try {
      // 模擬API調用
      await new Promise(resolve => setTimeout(resolve, 500));
      // 這裡未來會替換為真實的API調用
      setData(mockData);
      setMilestones(mockMilestones);
      setRelatedDocs(mockRelatedDocuments);
      setAttachments(mockAttachments);
    } catch (error) {
      message.error('載入數據失敗');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = () => {
    navigate(ROUTES.CONTRACT_CASE_EDIT.replace(':id', id!));
  };

  const handleDelete = () => {
    message.success('刪除成功');
    navigate(ROUTES.CONTRACT_CASES);
  };

  const handleBack = () => {
    navigate(ROUTES.CONTRACT_CASES);
  };

  // 計算項目進度
  const calculateProgress = () => {
    if (!data) return 0;

    const startDate = new Date(data.contract_period_start);
    const endDate = new Date(data.contract_period_end);
    const currentDate = new Date();

    if (currentDate < startDate) return 0;
    if (currentDate > endDate) return 100;

    const totalDays = endDate.getTime() - startDate.getTime();
    const passedDays = currentDate.getTime() - startDate.getTime();

    return Math.round((passedDays / totalDays) * 100);
  };

  // 格式化檔案大小
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  };

  // 獲取里程碑狀態圖示和顏色
  const getMilestoneIcon = (status: Milestone['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'in_progress':
        return <ClockCircleOutlined style={{ color: '#1890ff' }} />;
      case 'overdue':
        return <ExclamationCircleOutlined style={{ color: '#ff4d4f' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  const getMilestoneColor = (status: Milestone['status']) => {
    switch (status) {
      case 'completed': return 'green';
      case 'in_progress': return 'blue';
      case 'overdue': return 'red';
      default: return 'gray';
    }
  };

  // 關聯文件表格欄位
  const documentColumns: ColumnsType<RelatedDocument> = [
    {
      title: '文號',
      dataIndex: 'doc_number',
      key: 'doc_number',
      render: (text) => <Text strong style={{ color: '#1890ff' }}>{text}</Text>,
    },
    {
      title: '類型',
      dataIndex: 'doc_type',
      key: 'doc_type',
      width: 80,
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
    {
      title: '主旨',
      dataIndex: 'subject',
      key: 'subject',
      ellipsis: true,
    },
    {
      title: '日期',
      dataIndex: 'doc_date',
      key: 'doc_date',
      width: 120,
    },
    {
      title: '發文單位',
      dataIndex: 'sender',
      key: 'sender',
      width: 180,
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Button
          type="primary"
          size="small"
          icon={<EyeOutlined />}
          onClick={() => navigate(`/documents/${record.id}`)}
        >
          檢視
        </Button>
      ),
    },
  ];

  // 附件表格欄位
  const attachmentColumns: ColumnsType<Attachment> = [
    {
      title: '檔案名稱',
      dataIndex: 'filename',
      key: 'filename',
      render: (text) => (
        <Space>
          <PaperClipOutlined />
          <Text>{text}</Text>
        </Space>
      ),
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 100,
      render: (size) => formatFileSize(size),
    },
    {
      title: '上傳時間',
      dataIndex: 'uploaded_at',
      key: 'uploaded_at',
      width: 120,
    },
    {
      title: '上傳者',
      dataIndex: 'uploaded_by',
      key: 'uploaded_by',
      width: 100,
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space>
          <Tooltip title="下載">
            <Button size="small" icon={<DownloadOutlined />} />
          </Tooltip>
          <Tooltip title="預覽">
            <Button size="small" icon={<EyeOutlined />} />
          </Tooltip>
          <Popconfirm title="確定要刪除此附件？" okText="確定" cancelText="取消">
            <Tooltip title="刪除">
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 50 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!data) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: 50 }}>
          <Title level={4}>案件不存在</Title>
          <Button type="primary" onClick={handleBack}>
            返回列表
          </Button>
        </div>
      </Card>
    );
  }

  const progress = calculateProgress();

  // TAB 1: 基本資訊
  const renderBasicInfo = () => (
    <div>
      {/* 進度顯示 */}
      {data.case_status === 'in_progress' && (
        <Card title="執行進度" style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            <Col span={18}>
              <Progress
                percent={progress}
                status={progress === 100 ? "success" : "active"}
              />
            </Col>
            <Col span={6} style={{ textAlign: 'right' }}>
              <div>完成度: {progress}%</div>
              <div style={{ color: '#666', fontSize: '12px' }}>
                根據契約期程計算
              </div>
            </Col>
          </Row>
        </Card>
      )}

      {/* 基本資訊 */}
      <Card title="基本資訊" style={{ marginBottom: 16 }}>
        <Descriptions column={2} bordered>
          <Descriptions.Item label="專案名稱" span={2}>
            {data.project_name}
          </Descriptions.Item>
          <Descriptions.Item label="年度別">
            {data.year}年
          </Descriptions.Item>
          <Descriptions.Item label="案件性質">
            <Tag color={CONTRACT_CASE_TYPE_COLORS[data.case_type]}>
              {CONTRACT_CASE_TYPE_LABELS[data.case_type]}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="委託單位">
            {data.client_unit}
          </Descriptions.Item>
          <Descriptions.Item label="案件狀態">
            <Tag color={CONTRACT_CASE_STATUS_COLORS[data.case_status]}>
              {CONTRACT_CASE_STATUS_LABELS[data.case_status]}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="承辦同仁">
            {data.responsible_staff}
          </Descriptions.Item>
          <Descriptions.Item label="協力廠商">
            {data.partner_vendor}
          </Descriptions.Item>
          <Descriptions.Item label="契約金額">
            {data.contract_amount ? `NT$ ${data.contract_amount.toLocaleString()}` : '未填寫'}
          </Descriptions.Item>
          <Descriptions.Item label="契約期程" span={2}>
            {data.contract_period_start} ~ {data.contract_period_end}
          </Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 詳細說明 */}
      {data.description && (
        <Card title="案件說明" style={{ marginBottom: 16 }}>
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
            {data.description}
          </div>
        </Card>
      )}

      {/* 備註 */}
      {data.notes && (
        <Card title="備註">
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6, color: '#666' }}>
            {data.notes}
          </div>
        </Card>
      )}
    </div>
  );

  // TAB 2: 相關文件
  const renderRelatedDocuments = () => (
    <Card
      title={
        <Space>
          <FileTextOutlined />
          <span>關聯公文</span>
          <Tag color="blue">{relatedDocs.length} 件</Tag>
        </Space>
      }
      extra={
        <Button type="primary" size="small">
          新增關聯
        </Button>
      }
    >
      {relatedDocs.length > 0 ? (
        <Table
          columns={documentColumns}
          dataSource={relatedDocs}
          rowKey="id"
          pagination={false}
          size="middle"
        />
      ) : (
        <Empty description="尚無關聯公文" />
      )}
    </Card>
  );

  // TAB 3: 時程里程碑
  const renderMilestones = () => (
    <Card
      title={
        <Space>
          <CalendarOutlined />
          <span>專案時程與里程碑</span>
        </Space>
      }
      extra={
        <Button type="primary" size="small">
          新增里程碑
        </Button>
      }
    >
      {/* 進度概覽 */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center', background: '#f6ffed' }}>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#52c41a' }}>
              {milestones.filter(m => m.status === 'completed').length}
            </div>
            <div style={{ color: '#666' }}>已完成</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center', background: '#e6f7ff' }}>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#1890ff' }}>
              {milestones.filter(m => m.status === 'in_progress').length}
            </div>
            <div style={{ color: '#666' }}>進行中</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center', background: '#fff7e6' }}>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#fa8c16' }}>
              {milestones.filter(m => m.status === 'pending').length}
            </div>
            <div style={{ color: '#666' }}>待執行</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center', background: '#fff1f0' }}>
            <div style={{ fontSize: 24, fontWeight: 'bold', color: '#ff4d4f' }}>
              {milestones.filter(m => m.status === 'overdue').length}
            </div>
            <div style={{ color: '#666' }}>已逾期</div>
          </Card>
        </Col>
      </Row>

      {/* 時間軸 */}
      <Timeline mode="left">
        {milestones.map((milestone) => (
          <Timeline.Item
            key={milestone.id}
            color={getMilestoneColor(milestone.status)}
            dot={getMilestoneIcon(milestone.status)}
            label={
              <div>
                <div style={{ fontWeight: 'bold' }}>{milestone.due_date}</div>
                {milestone.completed_date && milestone.status === 'completed' && (
                  <div style={{ fontSize: 12, color: '#52c41a' }}>
                    完成於 {milestone.completed_date}
                  </div>
                )}
              </div>
            }
          >
            <Card size="small" style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Text strong>{milestone.title}</Text>
                  {milestone.description && (
                    <div style={{ color: '#666', marginTop: 4 }}>
                      {milestone.description}
                    </div>
                  )}
                </div>
                <Tag color={getMilestoneColor(milestone.status)}>
                  {milestone.status === 'completed' ? '已完成' :
                   milestone.status === 'in_progress' ? '進行中' :
                   milestone.status === 'overdue' ? '已逾期' : '待執行'}
                </Tag>
              </div>
            </Card>
          </Timeline.Item>
        ))}
      </Timeline>
    </Card>
  );

  // TAB 4: 附件管理
  const renderAttachments = () => (
    <Card
      title={
        <Space>
          <PaperClipOutlined />
          <span>附件管理</span>
          <Tag color="blue">{attachments.length} 個檔案</Tag>
        </Space>
      }
      extra={
        <Upload>
          <Button type="primary" icon={<UploadOutlined />}>
            上傳附件
          </Button>
        </Upload>
      }
    >
      {attachments.length > 0 ? (
        <Table
          columns={attachmentColumns}
          dataSource={attachments}
          rowKey="id"
          pagination={false}
          size="middle"
        />
      ) : (
        <Empty description="尚無附件" />
      )}
    </Card>
  );

  // Tab 項目定義
  const tabItems = [
    {
      key: 'basic',
      label: (
        <span>
          <InfoCircleOutlined />
          基本資訊
        </span>
      ),
      children: renderBasicInfo(),
    },
    {
      key: 'documents',
      label: (
        <span>
          <FileTextOutlined />
          相關文件
          <Tag color="blue" style={{ marginLeft: 8 }}>{relatedDocs.length}</Tag>
        </span>
      ),
      children: renderRelatedDocuments(),
    },
    {
      key: 'milestones',
      label: (
        <span>
          <CalendarOutlined />
          時程里程碑
        </span>
      ),
      children: renderMilestones(),
    },
    {
      key: 'attachments',
      label: (
        <span>
          <PaperClipOutlined />
          附件管理
          <Tag color="blue" style={{ marginLeft: 8 }}>{attachments.length}</Tag>
        </span>
      ),
      children: renderAttachments(),
    },
  ];

  return (
    <div>
      {/* 頁面標題和操作 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={handleBack}
            >
              返回
            </Button>
            <div>
              <Title level={3} style={{ margin: 0 }}>
                {data.project_name}
              </Title>
              <div style={{ marginTop: 8 }}>
                <Tag color={CONTRACT_CASE_TYPE_COLORS[data.case_type]}>
                  {CONTRACT_CASE_TYPE_LABELS[data.case_type]}
                </Tag>
                <Tag color={CONTRACT_CASE_STATUS_COLORS[data.case_status]}>
                  {CONTRACT_CASE_STATUS_LABELS[data.case_status]}
                </Tag>
              </div>
            </div>
          </div>
          <Space>
            <Button type="primary" icon={<EditOutlined />} onClick={handleEdit}>
              編輯
            </Button>
            <Popconfirm
              title="確定要刪除此專案嗎？"
              description="此操作無法復原"
              okText="確定"
              cancelText="取消"
              onConfirm={handleDelete}
            >
              <Button danger icon={<DeleteOutlined />}>
                刪除
              </Button>
            </Popconfirm>
          </Space>
        </div>
      </Card>

      {/* 4個TAB分頁 */}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          items={tabItems}
          size="large"
        />
      </Card>
    </div>
  );
};

export default ContractCaseDetailPage;
