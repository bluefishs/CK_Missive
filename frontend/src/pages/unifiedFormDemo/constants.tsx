/**
 * UnifiedFormDemo - 常數定義
 * 表格列配置、篩選配置、模擬數據
 */
import { Typography, Tag } from 'antd';
import type { FilterConfig } from '../../components/common/UnifiedTable';

const { Text } = Typography;

/** 模擬數據接口 */
export interface DemoRecord {
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

/** 初始模擬數據 */
export const INITIAL_DEMO_DATA: DemoRecord[] = [
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
    remarks: '需要在本月底前完成初稿',
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
    remarks: '已通過設計審查',
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
    remarks: '等待前期需求確認完成',
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
    remarks: '主要功能模組開發中',
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
    remarks: '正在評估技術方案與成本',
  },
];

const STATUS_COLORS: Record<string, string> = {
  '進行中': 'processing',
  '已完成': 'success',
  '待開始': 'default',
  '洽談中': 'warning',
};

const PRIORITY_COLORS: Record<string, string> = {
  '高': 'red',
  '中': 'orange',
  '低': 'green',
};

/** 表格列配置 */
export const DEMO_COLUMNS = [
  {
    title: '標題',
    dataIndex: 'title',
    key: 'title',
    render: (text: string) => <Text strong>{text}</Text>,
  },
  {
    title: '流水號',
    dataIndex: 'sequence_number',
    key: 'sequence_number',
    width: 150,
    render: (text: string) => <Text code>{text}</Text>,
  },
  {
    title: '類別',
    dataIndex: 'category',
    key: 'category',
    width: 120,
  },
  {
    title: '狀態',
    dataIndex: 'status',
    key: 'status',
    width: 100,
    render: (status: string) => (
      <Tag color={STATUS_COLORS[status]}>{status}</Tag>
    ),
  },
  {
    title: '優先級',
    dataIndex: 'priority',
    key: 'priority',
    width: 80,
    render: (priority: string) => (
      <Tag color={PRIORITY_COLORS[priority]}>{priority}</Tag>
    ),
  },
  {
    title: '金額',
    dataIndex: 'amount',
    key: 'amount',
    width: 120,
    render: (amount: number) => (amount ? `NT$ ${amount.toLocaleString()}` : '-'),
  },
  {
    title: '建立日期',
    dataIndex: 'created_date',
    key: 'created_date',
    width: 120,
  },
  {
    title: '建立者',
    dataIndex: 'created_by',
    key: 'created_by',
    width: 100,
  },
];

/** 篩選配置 */
export const DEMO_FILTER_CONFIGS: FilterConfig[] = [
  {
    key: 'category',
    label: '類別',
    type: 'select',
    options: [
      { value: '技術文件', label: '技術文件' },
      { value: '設計文件', label: '設計文件' },
      { value: '軟體開發', label: '軟體開發' },
      { value: '合作夥伴', label: '合作夥伴' },
    ],
  },
  {
    key: 'status',
    label: '狀態',
    type: 'select',
    options: [
      { value: '進行中', label: '進行中' },
      { value: '已完成', label: '已完成' },
      { value: '待開始', label: '待開始' },
      { value: '洽談中', label: '洽談中' },
    ],
  },
  {
    key: 'priority',
    label: '優先級',
    type: 'select',
    options: [
      { value: '高', label: '高' },
      { value: '中', label: '中' },
      { value: '低', label: '低' },
    ],
  },
  {
    key: 'created_by',
    label: '建立者',
    type: 'autocomplete',
    autoCompleteOptions: ['張三', '李四', '王五', '陳六', '趙七'],
  },
  {
    key: 'created_date',
    label: '建立日期',
    type: 'dateRange',
  },
];
