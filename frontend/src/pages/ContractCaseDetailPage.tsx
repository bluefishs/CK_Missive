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
  InfoCircleOutlined,
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

// 專案資料類型 (對應後端 ProjectResponse)
interface ProjectData {
  id: number;
  project_name: string;
  project_code?: string;
  year: number;
  category?: string;
  status?: string;
  client_agency?: string;
  contract_amount?: number;
  start_date?: string;
  end_date?: string;
  description?: string;
  created_at: string;
  updated_at: string;
}

// 承辦同仁類型 (使用 API 回傳的 ProjectStaff)
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

// 協力廠商關聯類型 (使用 API 回傳的 ProjectVendor)
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

export const ContractCaseDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<ProjectData | null>(null);
  const [activeTab, setActiveTab] = useState('info');
  const [staffList, setStaffList] = useState<Staff[]>([]);
  const [vendorList, setVendorList] = useState<VendorAssociation[]>([]);

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
        id: v.vendor_id, // 使用 vendor_id 作為唯一識別
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
      const users = (response as any).users || response || [];
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

  // 獲取狀態標籤顏色
  const getStatusTagColor = (status?: string) => {
    if (!status) return 'default';
    switch (status) {
      case 'in_progress': return 'processing';
      case 'completed': return 'success';
      case 'pending': return 'warning';
      case 'cancelled': return 'error';
      default: return 'default';
    }
  };

  // 獲取狀態標籤文字
  const getStatusTagText = (status?: string) => {
    if (!status) return '未知';
    switch (status) {
      case 'in_progress': return '進行中';
      case 'completed': return '已完成';
      case 'pending': return '待處理';
      case 'cancelled': return '已取消';
      default: return status;
    }
  };

  // 獲取類別標籤顏色
  const getCategoryTagColor = (category?: string) => {
    if (!category) return 'default';
    switch (category) {
      case '測繪': return 'blue';
      case '軟體開發': return 'green';
      case '顧問服務': return 'purple';
      case '資料處理': return 'orange';
      default: return 'default';
    }
  };

  // 格式化金額
  const formatAmount = (amount?: number) => {
    if (!amount) return '-';
    return new Intl.NumberFormat('zh-TW').format(amount);
  };

  // 角色顏色
  const getRoleColor = (role: string) => {
    switch (role) {
      case '主辦': return 'red';
      case '協辦': return 'blue';
      case '支援': return 'green';
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
        is_primary: values.role === '主辦',
        start_date: dayjs().format('YYYY-MM-DD'),
        status: 'active',
      });

      staffForm.resetFields();
      setStaffModalVisible(false);
      message.success('新增承辦同仁成功');

      // 重新載入資料
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

      // 重新載入資料
      loadData();
    } catch (error: any) {
      console.error('新增協力廠商失敗:', error);
      message.error(error.response?.data?.detail || '新增協力廠商失敗');
    }
  };

  // 處理案件資訊編輯
  const handleSaveCaseInfo = async (values: any) => {
    if (!data || !id) return;
    const projectId = parseInt(id, 10);

    try {
      await projectsApi.updateProject(projectId, {
        project_name: values.project_name,
        client_agency: values.client_agency,
        description: values.description,
      });

      setData({
        ...data,
        project_name: values.project_name,
        client_agency: values.client_agency,
        description: values.description,
      });
      setIsEditingCaseInfo(false);
      message.success('案件資訊已更新');
    } catch (error: any) {
      console.error('更新案件資訊失敗:', error);
      message.error(error.response?.data?.detail || '更新案件資訊失敗');
    }
  };

  // 開始編輯案件資訊
  const startEditCaseInfo = () => {
    if (data) {
      caseInfoForm.setFieldsValue({
        project_name: data.project_name,
        client_agency: data.client_agency,
        description: data.description,
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
        is_primary: newRole === '主辦',
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
          <Avatar icon={<UserOutlined />} style={{ backgroundColor: getRoleColor(record.role) === 'red' ? '#f5222d' : '#1890ff' }} />
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 120,
      render: (role, record) =>
        editingStaffId === record.id ? (
          <Select
            size="small"
            defaultValue={role}
            style={{ width: 100 }}
            onChange={(value) => handleStaffRoleChange(record.id, value)}
            onBlur={() => setEditingStaffId(null)}
            autoFocus
          >
            <Option value="主辦">主辦</Option>
            <Option value="協辦">協辦</Option>
            <Option value="支援">支援</Option>
          </Select>
        ) : (
          <Tag
            color={getRoleColor(role)}
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
        editingVendorId === record.id ? (
          <Select
            size="small"
            defaultValue={role}
            style={{ width: 120 }}
            onChange={(value) => handleVendorRoleChange(record.id, value)}
            onBlur={() => setEditingVendorId(null)}
            autoFocus
          >
            <Option value="主承包商">主承包商</Option>
            <Option value="分包商">分包商</Option>
            <Option value="供應商">供應商</Option>
            <Option value="顧問">顧問</Option>
          </Select>
        ) : (
          <Tag
            color={getRoleColor(role)}
            style={{ cursor: 'pointer' }}
            onClick={() => setEditingVendorId(record.id)}
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
          onConfirm={() => handleDeleteVendor(record.id)}
        >
          <Tooltip title="移除">
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Tooltip>
        </Popconfirm>
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
      {/* 進度顯示 */}
      {data.status === 'in_progress' && (
        <Card title="執行進度" style={{ marginBottom: 16 }}>
          <Row gutter={[16, 16]}>
            <Col span={18}>
              <Progress percent={progress} status={progress === 100 ? "success" : "active"} />
            </Col>
            <Col span={6} style={{ textAlign: 'right' }}>
              <div>完成度: {progress}%</div>
              <div style={{ color: '#666', fontSize: '12px' }}>根據契約期程計算</div>
            </Col>
          </Row>
        </Card>
      )}

      {/* 基本資訊 - 支援直接編輯 */}
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
              <Col span={24}>
                <Form.Item name="project_name" label="專案名稱" rules={[{ required: true }]}>
                  <Input />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item name="client_agency" label="委託單位">
                  <Input />
                </Form.Item>
              </Col>
              <Col span={12}>
                <Form.Item label="案件狀態">
                  <Tag color={getStatusTagColor(data.status)}>
                    {getStatusTagText(data.status)}
                  </Tag>
                </Form.Item>
              </Col>
              <Col span={24}>
                <Form.Item name="description" label="案件說明">
                  <Input.TextArea rows={4} />
                </Form.Item>
              </Col>
            </Row>
          </Form>
        ) : (
          <Descriptions column={2} bordered>
            <Descriptions.Item label="專案名稱" span={2}>{data.project_name}</Descriptions.Item>
            <Descriptions.Item label="年度別">{data.year}年</Descriptions.Item>
            <Descriptions.Item label="案件類別">
              <Tag color={getCategoryTagColor(data.category)}>
                {data.category || '未分類'}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="委託單位">{data.client_agency || '-'}</Descriptions.Item>
            <Descriptions.Item label="案件狀態">
              <Tag color={getStatusTagColor(data.status)}>
                {getStatusTagText(data.status)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="契約金額">
              {data.contract_amount ? `NT$ ${formatAmount(data.contract_amount)}` : '未填寫'}
            </Descriptions.Item>
            <Descriptions.Item label="契約期程">
              {data.start_date || '未設定'} ~ {data.end_date || '未設定'}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      {/* 案件說明 - 非編輯模式時顯示 */}
      {!isEditingCaseInfo && data.description && (
        <Card title="案件說明" style={{ marginBottom: 16 }}>
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
      {/* 統計概覽 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small" style={{ textAlign: 'center', background: '#fff1f0' }}>
            <Statistic
              title="主辦"
              value={staffList.filter(s => s.role === '主辦').length}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" style={{ textAlign: 'center', background: '#e6f7ff' }}>
            <Statistic
              title="協辦"
              value={staffList.filter(s => s.role === '協辦').length}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small" style={{ textAlign: 'center', background: '#f6ffed' }}>
            <Statistic
              title="支援"
              value={staffList.filter(s => s.role === '支援').length}
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
      {/* 簡化的統計概覽 */}
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

  // Tab 項目定義
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

      {/* 3個TAB分頁 */}
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
          <Form.Item name="role" label="角色" rules={[{ required: true, message: '請選擇角色' }]}>
            <Select placeholder="請選擇角色">
              <Option value="主辦">主辦</Option>
              <Option value="協辦">協辦</Option>
              <Option value="支援">支援</Option>
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
