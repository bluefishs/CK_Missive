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
  Upload,
  Empty,
  Tooltip,
  Popconfirm,
  Avatar,
  Statistic,
  Form,
  Input,
  Select,
  Modal,
  DatePicker,
  InputNumber,
} from 'antd';
import {
  ArrowLeftOutlined,
  EditOutlined,
  DeleteOutlined,
  FileTextOutlined,
  PaperClipOutlined,
  InfoCircleOutlined,
  UploadOutlined,
  DownloadOutlined,
  EyeOutlined,
  TeamOutlined,
  ShopOutlined,
  PlusOutlined,
  UserOutlined,
  PhoneOutlined,
  MailOutlined,
} from '@ant-design/icons';
import { useParams, useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { ROUTES } from '../router/types';
import {
  projectsApi,
  projectStaffApi,
  projectVendorsApi,
  usersApi,
  vendorsApi,
  type ProjectStaff,
  type ProjectVendor,
} from '../api/projects';

const { Title, Text } = Typography;
const { Option } = Select;

// 案件類別選項
const CATEGORY_OPTIONS = [
  { value: '01', label: '01委辦案件', color: 'blue' },
  { value: '02', label: '02協力計畫', color: 'green' },
  { value: '03', label: '03小額採購', color: 'orange' },
  { value: '04', label: '04其他類別', color: 'default' },
];

// 執行狀態選項
const STATUS_OPTIONS = [
  { value: 'pending', label: '待執行', color: 'warning' },
  { value: 'in_progress', label: '執行中', color: 'processing' },
  { value: 'completed', label: '已結案', color: 'success' },
  { value: 'suspended', label: '暫停', color: 'error' },
];

// 承辦同仁角色選項
const STAFF_ROLE_OPTIONS = [
  { value: '計畫主持人', label: '計畫主持人', color: 'red' },
  { value: '協同主執行', label: '協同主執行', color: 'orange' },
  { value: '專案PM', label: '專案PM', color: 'blue' },
  { value: '職業安全主管', label: '職業安全主管', color: 'green' },
];

// 專案資料類型 (對應後端 ProjectResponse - 完整欄位)
interface ProjectData {
  id: number;
  project_name: string;           // 案件名稱
  year: number;                   // 年度
  client_agency?: string;         // 委託單位
  category?: string;              // 案件類別 (01-04)
  contract_doc_number?: string;   // 契約文號
  project_code?: string;          // 專案編號 (年度+類別+流水號)
  contract_amount?: number;       // 契約金額
  winning_amount?: number;        // 得標金額
  start_date?: string;            // 開始日期
  end_date?: string;              // 結束日期
  status?: string;                // 執行狀態
  progress?: number;              // 完成進度 (0-100)
  notes?: string;                 // 備註
  project_path?: string;          // 專案路徑
  description?: string;           // 專案描述
  created_at: string;
  updated_at: string;
}

// 承辦同仁類型
interface Staff {
  id: number;
  user_id: number;
  name: string;
  role: string;
  department?: string | undefined;
  phone?: string | undefined;
  email?: string | undefined;
  join_date?: string | undefined;
  status: string;
}

// 協力廠商關聯類型
interface VendorAssociation {
  id: number;
  vendor_id: number;
  vendor_name: string;
  vendor_code?: string | undefined;
  contact_person?: string | undefined;
  phone?: string | undefined;
  role: string;
  contract_amount?: number | undefined;
  start_date?: string | undefined;
  end_date?: string | undefined;
  status: string;
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

// 附件類型
interface Attachment {
  id: number;
  filename: string;
  file_size: number;
  file_type: string;
  uploaded_at: string;
  uploaded_by: string;
}

export const ContractCaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ProjectData | null>(null);
  const [activeTab, setActiveTab] = useState('info');
  const [staffList, setStaffList] = useState<Staff[]>([]);
  const [vendorList, setVendorList] = useState<VendorAssociation[]>([]);
  const [relatedDocs, setRelatedDocs] = useState<RelatedDocument[]>([]);
  const [attachments, setAttachments] = useState<Attachment[]>([]);

  // 編輯模式狀態
  const [isEditingCaseInfo, setIsEditingCaseInfo] = useState(false);
  const [editingStaffId, setEditingStaffId] = useState<number | null>(null);
  const [editingVendorId, setEditingVendorId] = useState<number | null>(null);

  // Modal 狀態
  const [staffModalVisible, setStaffModalVisible] = useState(false);
  const [vendorModalVisible, setVendorModalVisible] = useState(false);
  const [staffForm] = Form.useForm();
  const [vendorForm] = Form.useForm();
  const [caseInfoForm] = Form.useForm();

  // 使用者和廠商選項 (用於新增時選擇)
  const [userOptions, setUserOptions] = useState<{ id: number; name: string; email: string }[]>([]);
  const [vendorOptions, setVendorOptions] = useState<{ id: number; name: string; code: string }[]>([]);

  useEffect(() => {
    if (id) {
      loadData();
    }
  }, [id]);

  const loadData = async () => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    setLoading(true);
    try {
      // 同時載入專案資料、承辦同仁、協力廠商
      const [projectResponse, staffResponse, vendorsResponse] = await Promise.all([
        projectsApi.getProject(projectId),
        projectStaffApi.getProjectStaff(projectId).catch(() => ({ staff: [], total: 0, project_id: projectId, project_name: '' })),
        projectVendorsApi.getProjectVendors(projectId).catch(() => ({ associations: [], total: 0, project_id: projectId, project_name: '' })),
      ]);

      // 設定專案資料
      setData(projectResponse);

      // 轉換承辦同仁資料格式
      const transformedStaff: Staff[] = staffResponse.staff.map((s: ProjectStaff) => ({
        id: s.id,
        user_id: s.user_id,
        name: s.user_name,
        role: s.role || 'member',
        department: s.department,
        phone: s.phone,
        email: s.user_email,
        join_date: s.start_date,
        status: s.status || 'active',
      }));
      setStaffList(transformedStaff);

      // 轉換協力廠商資料格式
      const transformedVendors: VendorAssociation[] = vendorsResponse.associations.map((v: ProjectVendor) => ({
        id: v.vendor_id,
        vendor_id: v.vendor_id,
        vendor_name: v.vendor_name,
        vendor_code: v.vendor_code,
        contact_person: v.vendor_contact_person,
        phone: v.vendor_phone,
        role: v.role || '供應商',
        contract_amount: v.contract_amount,
        start_date: v.start_date,
        end_date: v.end_date,
        status: v.status || 'active',
      }));
      setVendorList(transformedVendors);

      // TODO: 載入關聯文件和附件 (目前使用空陣列，之後接 API)
      setRelatedDocs([]);
      setAttachments([]);

      console.log('載入專案資料成功:', { projectResponse, staffResponse, vendorsResponse });
    } catch (error) {
      console.error('載入數據失敗:', error);
      message.error('載入數據失敗');
    } finally {
      setLoading(false);
    }
  };

  // 載入使用者選項 (用於新增同仁)
  const loadUserOptions = async () => {
    try {
      const response = await usersApi.getUsers({ limit: 100 });
      // API 回傳 items 欄位
      const users = (response as any).items || (response as any).users || response || [];
      setUserOptions(Array.isArray(users) ? users.map((u: any) => ({
        id: u.id,
        name: u.full_name || u.username,
        email: u.email,
      })) : []);
    } catch (error) {
      console.error('載入使用者列表失敗:', error);
    }
  };

  // 載入廠商選項 (用於新增廠商)
  const loadVendorOptions = async () => {
    try {
      const response = await vendorsApi.getVendors({ limit: 100 });
      const vendors = (response as any).vendors || response || [];
      setVendorOptions(Array.isArray(vendors) ? vendors.map((v: any) => ({
        id: v.id,
        name: v.vendor_name,
        code: v.vendor_code,
      })) : []);
    } catch (error) {
      console.error('載入廠商列表失敗:', error);
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
    if (!data || !data.start_date || !data.end_date) return 0;
    const startDate = new Date(data.start_date);
    const endDate = new Date(data.end_date);
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

  // 獲取狀態標籤顏色
  const getStatusTagColor = (status?: string) => {
    const statusOption = STATUS_OPTIONS.find(s => s.value === status);
    return statusOption?.color || 'default';
  };

  // 獲取狀態標籤文字
  const getStatusTagText = (status?: string) => {
    const statusOption = STATUS_OPTIONS.find(s => s.value === status);
    return statusOption?.label || status || '未設定';
  };

  // 獲取類別標籤顏色
  const getCategoryTagColor = (category?: string) => {
    const categoryOption = CATEGORY_OPTIONS.find(c => c.value === category);
    return categoryOption?.color || 'default';
  };

  // 獲取類別標籤文字
  const getCategoryTagText = (category?: string) => {
    const categoryOption = CATEGORY_OPTIONS.find(c => c.value === category);
    return categoryOption?.label || category || '未分類';
  };

  // 格式化金額
  const formatAmount = (amount?: number) => {
    if (!amount) return '-';
    return new Intl.NumberFormat('zh-TW').format(amount);
  };

  // 角色顏色 (承辦同仁)
  const getStaffRoleColor = (role: string) => {
    const option = STAFF_ROLE_OPTIONS.find(opt => opt.value === role);
    return option?.color || 'default';
  };

  // 角色顏色 (廠商)
  const getVendorRoleColor = (role: string) => {
    switch (role) {
      case '主承包商': return 'red';
      case '分包商': return 'orange';
      case '供應商': return 'cyan';
      case '顧問': return 'purple';
      default: return 'default';
    }
  };

  // 狀態顏色
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'processing';
      case 'completed': return 'success';
      case 'inactive': return 'warning';
      default: return 'default';
    }
  };

  // 處理新增同仁表單提交
  const handleAddStaff = async (values: any) => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    try {
      await projectStaffApi.addStaff({
        project_id: projectId,
        user_id: values.user_id,
        role: values.role,
        is_primary: values.role === '計畫主持人',
        start_date: dayjs().format('YYYY-MM-DD'),
        status: 'active',
      });

      staffForm.resetFields();
      setStaffModalVisible(false);
      message.success('新增承辦同仁成功');
      loadData();
    } catch (error: any) {
      console.error('新增承辦同仁失敗:', error);
      message.error(error.response?.data?.detail || '新增承辦同仁失敗');
    }
  };

  // 處理新增廠商表單提交
  const handleAddVendor = async (values: any) => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    try {
      const vendorData: {
        project_id: number;
        vendor_id: number;
        role?: string;
        contract_amount?: number;
        start_date?: string;
        end_date?: string;
        status?: string;
      } = {
        project_id: projectId,
        vendor_id: values.vendor_id,
        role: values.role,
        status: 'active',
      };

      if (values.contract_amount) {
        vendorData.contract_amount = values.contract_amount;
      }
      if (values.start_date) {
        vendorData.start_date = dayjs(values.start_date).format('YYYY-MM-DD');
      }
      if (values.end_date) {
        vendorData.end_date = dayjs(values.end_date).format('YYYY-MM-DD');
      }

      await projectVendorsApi.addVendor(vendorData);

      vendorForm.resetFields();
      setVendorModalVisible(false);
      message.success('新增協力廠商成功');
      loadData();
    } catch (error: any) {
      console.error('新增協力廠商失敗:', error);
      message.error(error.response?.data?.detail || '新增協力廠商失敗');
    }
  };

  // 處理案件資訊編輯 - 支援所有欄位
  const handleSaveCaseInfo = async (values: any) => {
    if (!data || !id) return;
    const projectId = parseInt(id, 10);

    try {
      // 格式化日期欄位，建立更新物件
      const updateData: Record<string, any> = {
        project_name: values.project_name,
        year: values.year,
        client_agency: values.client_agency || null,
        category: values.category || null,
        contract_doc_number: values.contract_doc_number || null,
        project_code: values.project_code || null,
        contract_amount: values.contract_amount || null,
        winning_amount: values.winning_amount || null,
        start_date: values.start_date ? dayjs(values.start_date).format('YYYY-MM-DD') : null,
        end_date: values.end_date ? dayjs(values.end_date).format('YYYY-MM-DD') : null,
        status: values.status || null,
        progress: values.progress ?? null,
        notes: values.notes || null,
        project_path: values.project_path || null,
      };

      await projectsApi.updateProject(projectId, updateData);

      // 更新本地資料
      setData({
        ...data,
        project_name: updateData['project_name'],
        year: updateData['year'],
        client_agency: updateData['client_agency'],
        category: updateData['category'],
        contract_doc_number: updateData['contract_doc_number'],
        project_code: updateData['project_code'],
        contract_amount: updateData['contract_amount'],
        winning_amount: updateData['winning_amount'],
        start_date: updateData['start_date'],
        end_date: updateData['end_date'],
        status: updateData['status'],
        progress: updateData['progress'],
        notes: updateData['notes'],
        project_path: updateData['project_path'],
      });
      setIsEditingCaseInfo(false);
      message.success('案件資訊已更新');
    } catch (error: any) {
      console.error('更新案件資訊失敗:', error);
      message.error(error.response?.data?.detail || '更新案件資訊失敗');
    }
  };

  // 開始編輯案件資訊 - 載入所有欄位到表單
  const startEditCaseInfo = () => {
    if (data) {
      caseInfoForm.setFieldsValue({
        project_name: data.project_name,
        year: data.year,
        client_agency: data.client_agency,
        category: data.category,
        contract_doc_number: data.contract_doc_number,
        project_code: data.project_code,
        contract_amount: data.contract_amount,
        winning_amount: data.winning_amount,
        start_date: data.start_date ? dayjs(data.start_date) : undefined,
        end_date: data.end_date ? dayjs(data.end_date) : undefined,
        status: data.status,
        progress: data.progress,
        notes: data.notes,
        project_path: data.project_path,
      });
      setIsEditingCaseInfo(true);
    }
  };

  // 處理同仁角色更新
  const handleStaffRoleChange = async (staffId: number, newRole: string) => {
    if (!id) return;
    const projectId = parseInt(id, 10);
    const staff = staffList.find(s => s.id === staffId);
    if (!staff) return;

    try {
      await projectStaffApi.updateStaff(projectId, staff.user_id, {
        role: newRole,
        is_primary: newRole === '計畫主持人',
      });

      setStaffList(staffList.map(s =>
        s.id === staffId ? { ...s, role: newRole } : s
      ));
      setEditingStaffId(null);
      message.success('角色已更新');
    } catch (error: any) {
      console.error('更新角色失敗:', error);
      message.error(error.response?.data?.detail || '更新角色失敗');
      setEditingStaffId(null);
    }
  };

  // 處理廠商角色更新
  const handleVendorRoleChange = async (vendorId: number, newRole: string) => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    try {
      await projectVendorsApi.updateVendor(projectId, vendorId, {
        role: newRole,
      });

      setVendorList(vendorList.map(v =>
        v.vendor_id === vendorId ? { ...v, role: newRole } : v
      ));
      setEditingVendorId(null);
      message.success('角色已更新');
    } catch (error: any) {
      console.error('更新角色失敗:', error);
      message.error(error.response?.data?.detail || '更新角色失敗');
      setEditingVendorId(null);
    }
  };

  // 刪除同仁
  const handleDeleteStaff = async (staffId: number) => {
    if (!id) return;
    const projectId = parseInt(id, 10);
    const staff = staffList.find(s => s.id === staffId);
    if (!staff) return;

    try {
      await projectStaffApi.deleteStaff(projectId, staff.user_id);
      setStaffList(staffList.filter(s => s.id !== staffId));
      message.success('已移除同仁');
    } catch (error: any) {
      console.error('移除同仁失敗:', error);
      message.error(error.response?.data?.detail || '移除同仁失敗');
    }
  };

  // 刪除廠商
  const handleDeleteVendor = async (vendorId: number) => {
    if (!id) return;
    const projectId = parseInt(id, 10);

    try {
      await projectVendorsApi.deleteVendor(projectId, vendorId);
      setVendorList(vendorList.filter(v => v.vendor_id !== vendorId));
      message.success('已移除廠商');
    } catch (error: any) {
      console.error('移除廠商失敗:', error);
      message.error(error.response?.data?.detail || '移除廠商失敗');
    }
  };

  // 承辦同仁表格欄位
  const staffColumns: ColumnsType<Staff> = [
    {
      title: '姓名',
      dataIndex: 'name',
      key: 'name',
      render: (name, record) => (
        <Space>
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: getStaffRoleColor(record.role) === 'red' ? '#f5222d' : '#1890ff' }} />
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: '角色/職責',
      dataIndex: 'role',
      key: 'role',
      width: 140,
      render: (role, record) =>
        editingStaffId === record.id ? (
          <Select
            size="small"
            defaultValue={role}
            style={{ width: 130 }}
            onChange={(value) => handleStaffRoleChange(record.id, value)}
            autoFocus
            open={true}
            onDropdownVisibleChange={(open) => {
              if (!open) setEditingStaffId(null);
            }}
          >
            {STAFF_ROLE_OPTIONS.map(opt => (
              <Option key={opt.value} value={opt.value}>{opt.label}</Option>
            ))}
          </Select>
        ) : (
          <Tag
            color={getStaffRoleColor(role)}
            style={{ cursor: 'pointer' }}
            onClick={() => setEditingStaffId(record.id)}
          >
            {role} <EditOutlined style={{ fontSize: 10, marginLeft: 4 }} />
          </Tag>
        ),
    },
    {
      title: '部門',
      dataIndex: 'department',
      key: 'department',
    },
    {
      title: '聯絡方式',
      key: 'contact',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {record.phone && <span><PhoneOutlined /> {record.phone}</span>}
          {record.email && <span><MailOutlined /> {record.email}</span>}
        </Space>
      ),
    },
    {
      title: '加入日期',
      dataIndex: 'join_date',
      key: 'join_date',
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={status === 'active' ? 'success' : 'default'}>
          {status === 'active' ? '在職' : '離職'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Popconfirm
          title="確定要移除此同仁？"
          okText="確定"
          cancelText="取消"
          onConfirm={() => handleDeleteStaff(record.id)}
        >
          <Tooltip title="移除">
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Tooltip>
        </Popconfirm>
      ),
    },
  ];

  // 協力廠商表格欄位
  const vendorColumns: ColumnsType<VendorAssociation> = [
    {
      title: '廠商資訊',
      key: 'vendor_info',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <Text strong>{record.vendor_name}</Text>
          {record.vendor_code && <Text type="secondary">統編: {record.vendor_code}</Text>}
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 140,
      render: (role, record) =>
        editingVendorId === record.vendor_id ? (
          <Select
            size="small"
            defaultValue={role}
            style={{ width: 120 }}
            onChange={(value) => handleVendorRoleChange(record.vendor_id, value)}
            autoFocus
            open={true}
            onDropdownVisibleChange={(open) => {
              if (!open) setEditingVendorId(null);
            }}
          >
            <Option value="主承包商">主承包商</Option>
            <Option value="分包商">分包商</Option>
            <Option value="供應商">供應商</Option>
            <Option value="顧問">顧問</Option>
          </Select>
        ) : (
          <Tag
            color={getVendorRoleColor(role)}
            style={{ cursor: 'pointer' }}
            onClick={() => setEditingVendorId(record.vendor_id)}
          >
            {role} <EditOutlined style={{ fontSize: 10, marginLeft: 4 }} />
          </Tag>
        ),
    },
    {
      title: '聯絡人',
      key: 'contact',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {record.contact_person && <span><UserOutlined /> {record.contact_person}</span>}
          {record.phone && <span><PhoneOutlined /> {record.phone}</span>}
        </Space>
      ),
    },
    {
      title: '合約金額',
      dataIndex: 'contract_amount',
      key: 'contract_amount',
      render: (amount) => <Text>NT$ {formatAmount(amount)}</Text>,
    },
    {
      title: '合作期間',
      key: 'period',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <span>{record.start_date} ~</span>
          <span>{record.end_date}</span>
        </Space>
      ),
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      render: (status) => (
        <Tag color={getStatusColor(status)}>
          {status === 'active' ? '合作中' : status === 'completed' ? '已完成' : '暫停'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 100,
      render: (_, record) => (
        <Popconfirm
          title="確定要移除此廠商？"
          okText="確定"
          cancelText="取消"
          onConfirm={() => handleDeleteVendor(record.vendor_id)}
        >
          <Tooltip title="移除">
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Tooltip>
        </Popconfirm>
      ),
    },
  ];

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
      render: () => (
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
          <Button type="primary" onClick={handleBack}>返回列表</Button>
        </div>
      </Card>
    );
  }

  const progress = calculateProgress();

  // TAB 1: 案件資訊
  const renderCaseInfo = () => (
    <div>
      {/* 進度顯示 - 顯示完成進度 */}
      <Card title="執行進度" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={18}>
            <Progress
              percent={data.progress ?? progress}
              status={data.status === 'completed' ? 'success' : data.status === 'suspended' ? 'exception' : 'active'}
            />
          </Col>
          <Col span={6} style={{ textAlign: 'right' }}>
            <div>完成度: {data.progress ?? progress}%</div>
            <div style={{ color: '#666', fontSize: '12px' }}>
              {data.progress !== undefined ? '手動設定' : '根據契約期程計算'}
            </div>
          </Col>
        </Row>
      </Card>

      {/* 基本資訊 - 支援直接編輯 (完整欄位) */}
      <Card
        title="基本資訊"
        style={{ marginBottom: 16 }}
        extra={
          isEditingCaseInfo ? (
            <Space>
              <Button size="small" onClick={() => setIsEditingCaseInfo(false)}>取消</Button>
              <Button size="small" type="primary" onClick={() => caseInfoForm.submit()}>儲存</Button>
            </Space>
          ) : (
            <Button size="small" icon={<EditOutlined />} onClick={startEditCaseInfo}>編輯</Button>
          )
        }
      >
        {isEditingCaseInfo ? (
          <Form form={caseInfoForm} layout="vertical" onFinish={handleSaveCaseInfo}>
            <Row gutter={16}>
              {/* 第一行: 案件名稱 */}
              <Col span={24}>
                <Form.Item name="project_name" label="案件名稱" rules={[{ required: true, message: '請輸入案件名稱' }]}>
                  <Input placeholder="請輸入案件名稱" />
                </Form.Item>
              </Col>
              {/* 第二行: 年度、委託單位、案件類別 */}
              <Col span={6}>
                <Form.Item name="year" label="年度" rules={[{ required: true, message: '請選擇年度' }]}>
                  <InputNumber style={{ width: '100%' }} min={2020} max={2030} placeholder="西元年" />
                </Form.Item>
              </Col>
              <Col span={9}>
                <Form.Item name="client_agency" label="委託單位">
                  <Input placeholder="請輸入委託單位" />
                </Form.Item>
              </Col>
              <Col span={9}>
                <Form.Item name="category" label="案件類別">
                  <Select placeholder="請選擇案件類別">
                    {CATEGORY_OPTIONS.map(opt => (
                      <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              {/* 第三行: 契約文號、專案編號 */}
              <Col span={12}>
                <Form.Item name="contract_doc_number" label="契約文號">
                  <Input placeholder="請輸入契約文號" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="project_code" label="專案編號" tooltip="格式: 年度+類別+流水號 (如202501001)">
                  <Input placeholder="如: 202501001" />
                </Form.Item>
              </Col>
              {/* 第四行: 契約金額、得標金額 */}
              <Col span={12}>
                <Form.Item name="contract_amount" label="契約金額">
                  <InputNumber
                    style={{ width: '100%' }}
                    placeholder="請輸入契約金額"
                    formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    parser={value => value?.replace(/\$\s?|(,*)/g, '') as any}
                    addonBefore="NT$"
                  />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="winning_amount" label="得標金額">
                  <InputNumber
                    style={{ width: '100%' }}
                    placeholder="請輸入得標金額"
                    formatter={value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
                    parser={value => value?.replace(/\$\s?|(,*)/g, '') as any}
                    addonBefore="NT$"
                  />
                </Form.Item>
              </Col>
              {/* 第五行: 開始日期、結束日期 */}
              <Col span={12}>
                <Form.Item name="start_date" label="開始日期">
                  <DatePicker style={{ width: '100%' }} placeholder="選擇開始日期" />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="end_date" label="結束日期">
                  <DatePicker style={{ width: '100%' }} placeholder="選擇結束日期" />
                </Form.Item>
              </Col>
              {/* 第六行: 執行狀態、完成進度 */}
              <Col span={12}>
                <Form.Item name="status" label="執行狀態">
                  <Select placeholder="請選擇執行狀態">
                    {STATUS_OPTIONS.map(opt => (
                      <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                    ))}
                  </Select>
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="progress" label="完成進度 (%)">
                  <InputNumber style={{ width: '100%' }} min={0} max={100} placeholder="0-100" />
                </Form.Item>
              </Col>
              {/* 第七行: 專案路徑 */}
              <Col span={24}>
                <Form.Item name="project_path" label="專案路徑">
                  <Input placeholder="請輸入專案資料夾路徑 (可選)" />
                </Form.Item>
              </Col>
              {/* 第八行: 備註 */}
              <Col span={24}>
                <Form.Item name="notes" label="備註">
                  <Input.TextArea rows={3} placeholder="請輸入備註說明" />
                </Form.Item>
              </Col>
            </Row>
          </Form>
        ) : (
          <Descriptions column={2} bordered size="small">
            {/* 案件名稱 */}
            <Descriptions.Item label="案件名稱" span={2}>
              <Text strong>{data.project_name}</Text>
            </Descriptions.Item>
            {/* 年度、委託單位 */}
            <Descriptions.Item label="年度">{data.year}年</Descriptions.Item>
            <Descriptions.Item label="委託單位">{data.client_agency || '-'}</Descriptions.Item>
            {/* 案件類別、契約文號 */}
            <Descriptions.Item label="案件類別">
              <Tag color={getCategoryTagColor(data.category)}>
                {getCategoryTagText(data.category)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="契約文號">{data.contract_doc_number || '-'}</Descriptions.Item>
            {/* 專案編號、執行狀態 */}
            <Descriptions.Item label="專案編號">
              {data.project_code ? <Text code>{data.project_code}</Text> : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="執行狀態">
              <Tag color={getStatusTagColor(data.status)}>
                {getStatusTagText(data.status)}
              </Tag>
            </Descriptions.Item>
            {/* 契約金額、得標金額 */}
            <Descriptions.Item label="契約金額">
              {data.contract_amount ? `NT$ ${formatAmount(data.contract_amount)}` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="得標金額">
              {data.winning_amount ? `NT$ ${formatAmount(data.winning_amount)}` : '-'}
            </Descriptions.Item>
            {/* 開始日期、結束日期 */}
            <Descriptions.Item label="開始日期">{data.start_date || '-'}</Descriptions.Item>
            <Descriptions.Item label="結束日期">{data.end_date || '-'}</Descriptions.Item>
            {/* 完成進度、專案路徑 */}
            <Descriptions.Item label="完成進度">
              {data.progress !== undefined ? `${data.progress}%` : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="專案路徑">
              {data.project_path ? <Text type="secondary">{data.project_path}</Text> : '-'}
            </Descriptions.Item>
            {/* 備註 */}
            <Descriptions.Item label="備註" span={2}>
              {data.notes || '-'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      {/* 專案說明 - 非編輯模式時顯示 */}
      {!isEditingCaseInfo && data.description && (
        <Card title="專案說明" style={{ marginBottom: 16 }}>
          <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{data.description}</div>
        </Card>
      )}
    </div>
  );

  // TAB 2: 承辦同仁
  const renderStaff = () => (
    <Card
      title={
        <Space>
          <TeamOutlined />
          <span>承辦同仁</span>
          <Tag color="blue">{staffList.length} 人</Tag>
        </Space>
      }
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setStaffModalVisible(true)}>
          新增同仁
        </Button>
      }
    >
      {/* 統計概覽 - 4種角色/職責 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center', background: '#fff1f0' }}>
            <Statistic
              title="計畫主持人"
              value={staffList.filter(s => s.role === '計畫主持人').length}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center', background: '#fff7e6' }}>
            <Statistic
              title="協同主執行"
              value={staffList.filter(s => s.role === '協同主執行').length}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center', background: '#e6f7ff' }}>
            <Statistic
              title="專案PM"
              value={staffList.filter(s => s.role === '專案PM').length}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small" style={{ textAlign: 'center', background: '#f6ffed' }}>
            <Statistic
              title="職業安全主管"
              value={staffList.filter(s => s.role === '職業安全主管').length}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {staffList.length > 0 ? (
        <Table
          columns={staffColumns}
          dataSource={staffList}
          rowKey="id"
          pagination={false}
          size="middle"
        />
      ) : (
        <Empty description="尚無承辦同仁" />
      )}
    </Card>
  );

  // TAB 3: 協力廠商
  const renderVendors = () => (
    <Card
      title={
        <Space>
          <ShopOutlined />
          <span>協力廠商</span>
          <Tag color="blue">{vendorList.length} 家</Tag>
        </Space>
      }
      extra={
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setVendorModalVisible(true)}>
          新增廠商
        </Button>
      }
    >
      {/* 統計概覽 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card size="small" style={{ textAlign: 'center' }}>
            <Statistic
              title="合約總金額"
              value={vendorList.reduce((sum, v) => sum + (v.contract_amount || 0), 0)}
              formatter={value => `NT$ ${formatAmount(Number(value))}`}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card size="small" style={{ textAlign: 'center' }}>
            <Statistic
              title="合作中廠商"
              value={vendorList.filter(v => v.status === 'active').length}
              suffix={`/ ${vendorList.length}`}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
      </Row>

      {vendorList.length > 0 ? (
        <Table
          columns={vendorColumns}
          dataSource={vendorList}
          rowKey="id"
          pagination={false}
          size="middle"
        />
      ) : (
        <Empty description="尚無協力廠商" />
      )}
    </Card>
  );

  // TAB 4: 相關文件與附件
  const renderDocumentsAndAttachments = () => (
    <div>
      {/* 關聯公文 */}
      <Card
        title={
          <Space>
            <FileTextOutlined />
            <span>關聯公文</span>
            <Tag color="blue">{relatedDocs.length} 件</Tag>
          </Space>
        }
        extra={
          <Button type="primary" size="small" icon={<PlusOutlined />}>
            新增關聯
          </Button>
        }
        style={{ marginBottom: 16 }}
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

      {/* 附件管理 */}
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
    </div>
  );

  // Tab 項目定義 - 4 個 TAB
  const tabItems = [
    {
      key: 'info',
      label: (
        <span>
          <InfoCircleOutlined />
          案件資訊
        </span>
      ),
      children: renderCaseInfo(),
    },
    {
      key: 'staff',
      label: (
        <span>
          <TeamOutlined />
          承辦同仁
          <Tag color="blue" style={{ marginLeft: 8 }}>{staffList.length}</Tag>
        </span>
      ),
      children: renderStaff(),
    },
    {
      key: 'vendors',
      label: (
        <span>
          <ShopOutlined />
          協力廠商
          <Tag color="blue" style={{ marginLeft: 8 }}>{vendorList.length}</Tag>
        </span>
      ),
      children: renderVendors(),
    },
    {
      key: 'documents',
      label: (
        <span>
          <FileTextOutlined />
          相關文件
          <Tag color="blue" style={{ marginLeft: 8 }}>{relatedDocs.length + attachments.length}</Tag>
        </span>
      ),
      children: renderDocumentsAndAttachments(),
    },
  ];

  return (
    <div>
      {/* 頁面標題和操作 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Button type="text" icon={<ArrowLeftOutlined />} onClick={handleBack}>
              返回
            </Button>
            <div>
              <Title level={3} style={{ margin: 0 }}>{data.project_name}</Title>
              <div style={{ marginTop: 8 }}>
                <Tag color={getCategoryTagColor(data.category)}>
                  {data.category || '未分類'}
                </Tag>
                <Tag color={getStatusTagColor(data.status)}>
                  {getStatusTagText(data.status)}
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
              <Button danger icon={<DeleteOutlined />}>刪除</Button>
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

      {/* 新增同仁 Modal */}
      <Modal
        title="新增承辦同仁"
        open={staffModalVisible}
        onCancel={() => setStaffModalVisible(false)}
        footer={null}
        width={500}
        destroyOnHidden
        afterOpenChange={(open) => {
          if (open) loadUserOptions();
        }}
      >
        <Form form={staffForm} layout="vertical" onFinish={handleAddStaff}>
          <Form.Item name="user_id" label="選擇同仁" rules={[{ required: true, message: '請選擇同仁' }]}>
            <Select
              placeholder="請選擇同仁"
              showSearch
              optionFilterProp="label"
              options={userOptions.map(u => ({
                value: u.id,
                label: `${u.name} (${u.email})`,
              }))}
            />
          </Form.Item>
          <Form.Item name="role" label="角色/職責" rules={[{ required: true, message: '請選擇角色/職責' }]}>
            <Select placeholder="請選擇角色/職責">
              {STAFF_ROLE_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
            <Space>
              <Button onClick={() => setStaffModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">新增</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>

      {/* 新增廠商 Modal */}
      <Modal
        title="新增協力廠商"
        open={vendorModalVisible}
        onCancel={() => setVendorModalVisible(false)}
        footer={null}
        width={600}
        destroyOnHidden
        afterOpenChange={(open) => {
          if (open) loadVendorOptions();
        }}
      >
        <Form form={vendorForm} layout="vertical" onFinish={handleAddVendor}>
          <Form.Item name="vendor_id" label="選擇廠商" rules={[{ required: true, message: '請選擇廠商' }]}>
            <Select
              placeholder="請選擇廠商"
              showSearch
              optionFilterProp="label"
              options={vendorOptions.map(v => ({
                value: v.id,
                label: `${v.name}${v.code ? ` (${v.code})` : ''}`,
              }))}
            />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true, message: '請選擇角色' }]}>
            <Select placeholder="請選擇角色">
              <Option value="主承包商">主承包商</Option>
              <Option value="分包商">分包商</Option>
              <Option value="供應商">供應商</Option>
              <Option value="顧問">顧問</Option>
            </Select>
          </Form.Item>
          <Form.Item name="contract_amount" label="合約金額">
            <InputNumber
              style={{ width: '100%' }}
              placeholder="請輸入合約金額"
              formatter={value => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={value => value?.replace(/\$\s?|(,*)/g, '') as any}
            />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="start_date" label="合作開始日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="end_date" label="合作結束日期">
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
            <Space>
              <Button onClick={() => setVendorModalVisible(false)}>取消</Button>
              <Button type="primary" htmlType="submit">新增</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default ContractCaseDetailPage;
