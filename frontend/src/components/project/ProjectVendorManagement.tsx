import React, { useState, useCallback } from 'react';
import {
  Modal,
  Table,
  Button,
  Form,
  App,
  Space,
  Tag,
  Popconfirm,
  Card,
  Row,
  Col,
  Statistic
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  UserOutlined,
  PhoneOutlined,
  DollarOutlined,
  CalendarOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import { logger } from '../../services/logger';
import type { Vendor } from '../../types/api';
import VendorAssociationForm from './VendorAssociationForm';

interface ProjectVendorAssociation {
  project_id: number;
  vendor_id: number;
  vendor_name: string;
  vendor_code?: string;
  vendor_contact_person?: string;
  vendor_phone?: string;
  vendor_business_type?: string;
  role?: string;
  contract_amount?: number;
  start_date?: string;
  end_date?: string;
  status?: string;
  created_at: string;
  updated_at: string;
}

interface ProjectVendorFormData {
  vendor_id: number;
  role?: string;
  contract_amount?: number;
  start_date?: string;
  end_date?: string;
  status?: string;
}

interface ProjectVendorManagementProps {
  projectId: number;
  projectName: string;
  open: boolean;
  onClose: () => void;
}

const getStatusColor = (status?: string) => {
  switch (status) {
    case 'active': return 'processing';
    case 'completed': return 'success';
    case 'inactive': return 'warning';
    case 'cancelled': return 'error';
    default: return 'default';
  }
};

const getRoleColor = (role?: string) => {
  switch (role) {
    case '主承包商': return 'red';
    case '分包商': return 'orange';
    case '供應商': return 'green';
    case '顧問': return 'blue';
    case '監造': return 'purple';
    default: return 'default';
  }
};

const formatAmount = (amount?: number) => {
  if (!amount) return '-';
  return new Intl.NumberFormat('zh-TW').format(amount);
};

const ProjectVendorManagement: React.FC<ProjectVendorManagementProps> = ({
  projectId, projectName, open, onClose,
}) => {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [formVisible, setFormVisible] = useState(false);
  const [editingAssociation, setEditingAssociation] = useState<ProjectVendorAssociation | null>(null);
  const [form] = Form.useForm();

  const { data: associations = [], isLoading: loading } = useQuery({
    queryKey: ['project-vendor-associations', projectId],
    queryFn: async () => {
      const data = await apiClient.post<{ associations: ProjectVendorAssociation[]; total: number }>(
        API_ENDPOINTS.PROJECT_VENDORS.PROJECT_LIST(projectId), {}
      );
      return data.associations || [];
    },
    enabled: open && !!projectId,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const { data: vendors = [] } = useQuery({
    queryKey: ['vendor-list-for-project'],
    queryFn: async () => {
      const data = await apiClient.post<{ items: Vendor[] }>(API_ENDPOINTS.VENDORS.LIST, { page: 1, limit: 100 });
      return data.items || [];
    },
    enabled: open,
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const loadAssociations = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['project-vendor-associations', projectId] });
  }, [queryClient, projectId]);

  const handleSubmit = async (values: ProjectVendorFormData) => {
    try {
      if (editingAssociation) {
        await apiClient.post(
          API_ENDPOINTS.PROJECT_VENDORS.UPDATE(projectId, editingAssociation.vendor_id),
          {
            role: values.role,
            contract_amount: values.contract_amount,
            start_date: values.start_date ? dayjs(values.start_date).format('YYYY-MM-DD') : undefined,
            end_date: values.end_date ? dayjs(values.end_date).format('YYYY-MM-DD') : undefined,
            status: values.status,
          }
        );
      } else {
        await apiClient.post(API_ENDPOINTS.PROJECT_VENDORS.CREATE, {
          project_id: projectId, vendor_id: values.vendor_id, role: values.role,
          contract_amount: values.contract_amount,
          start_date: values.start_date ? dayjs(values.start_date).format('YYYY-MM-DD') : undefined,
          end_date: values.end_date ? dayjs(values.end_date).format('YYYY-MM-DD') : undefined,
          status: values.status || 'active',
        });
      }
      message.success(editingAssociation ? '關聯更新成功' : '關聯建立成功');
      setFormVisible(false);
      form.resetFields();
      setEditingAssociation(null);
      loadAssociations();
    } catch (error) {
      logger.error('廠商關聯操作失敗:', error);
      message.error('操作失敗，請稍後再試');
    }
  };

  const handleDelete = async (vendorId: number) => {
    try {
      await apiClient.post(API_ENDPOINTS.PROJECT_VENDORS.DELETE(projectId, vendorId), {});
      message.success('關聯刪除成功');
      loadAssociations();
    } catch (error) {
      logger.error('刪除廠商關聯失敗:', error);
      message.error('刪除失敗，請稍後再試');
    }
  };

  const handleEdit = (association: ProjectVendorAssociation) => {
    setEditingAssociation(association);
    form.setFieldsValue({
      vendor_id: association.vendor_id,
      role: association.role,
      contract_amount: association.contract_amount,
      start_date: association.start_date ? dayjs(association.start_date) : undefined,
      end_date: association.end_date ? dayjs(association.end_date) : undefined,
      status: association.status,
    });
    setFormVisible(true);
  };

  const getAvailableVendors = () => {
    const associatedVendorIds = associations.map(a => a.vendor_id);
    return vendors.filter(vendor =>
      editingAssociation
        ? (vendor.id === editingAssociation.vendor_id || !associatedVendorIds.includes(vendor.id))
        : !associatedVendorIds.includes(vendor.id)
    );
  };

  const columns: ColumnsType<ProjectVendorAssociation> = [
    {
      title: '廠商資訊', key: 'vendor_info',
      render: (_, record) => (
        <Space vertical size="small">
          <strong>{record.vendor_name}</strong>
          {record.vendor_code && <small style={{ color: '#666' }}>統編: {record.vendor_code}</small>}
          {record.vendor_business_type && <Tag>{record.vendor_business_type}</Tag>}
        </Space>
      ),
    },
    {
      title: '聯絡資訊', key: 'contact',
      render: (_, record) => (
        <Space vertical size="small">
          {record.vendor_contact_person && <span><UserOutlined /> {record.vendor_contact_person}</span>}
          {record.vendor_phone && <span><PhoneOutlined /> {record.vendor_phone}</span>}
        </Space>
      ),
    },
    {
      title: '角色', dataIndex: 'role', key: 'role',
      render: (role: string) => role ? <Tag color={getRoleColor(role)}>{role}</Tag> : <span style={{ color: '#999' }}>未設定</span>,
    },
    {
      title: '合約金額', dataIndex: 'contract_amount', key: 'contract_amount',
      render: (amount: number) => <span><DollarOutlined style={{ marginRight: 4 }} />${formatAmount(amount)}</span>,
    },
    {
      title: '合作期間', key: 'duration',
      render: (_, record) => (
        <Space vertical size="small">
          {record.start_date && <span><CalendarOutlined style={{ marginRight: 4 }} />開始: {dayjs(record.start_date).format('YYYY-MM-DD')}</span>}
          {record.end_date && <span><CalendarOutlined style={{ marginRight: 4 }} />結束: {dayjs(record.end_date).format('YYYY-MM-DD')}</span>}
        </Space>
      ),
    },
    {
      title: '狀態', dataIndex: 'status', key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {status === 'active' ? '合作中' : status === 'completed' ? '已完成' :
           status === 'inactive' ? '暫停' : status === 'cancelled' ? '已取消' : status}
        </Tag>
      ),
    },
    {
      title: '操作', key: 'action',
      render: (_, record) => (
        <Space>
          <Button type="link" icon={<EditOutlined />} onClick={() => handleEdit(record)}>編輯</Button>
          <Popconfirm title="確定要刪除此關聯嗎？" description="刪除後無法恢復。"
            onConfirm={() => handleDelete(record.vendor_id)} okText="確定" cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>刪除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Modal title={`專案廠商管理 - ${projectName}`} open={open} onCancel={onClose} footer={null} width={1200}>
        <Card style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}><Statistic title="關聯廠商數" value={associations.length} /></Col>
            <Col span={8}>
              <Statistic title="合約總金額"
                value={associations.reduce((sum, a) => sum + (a.contract_amount || 0), 0)}
                formatter={value => `$${formatAmount(Number(value))}`}
              />
            </Col>
            <Col span={8}>
              <Statistic title="進行中廠商" value={associations.filter(a => a.status === 'active').length} />
            </Col>
          </Row>
        </Card>

        <div style={{ marginBottom: 16, textAlign: 'right' }}>
          <Button type="primary" icon={<PlusOutlined />}
            onClick={() => { setEditingAssociation(null); form.resetFields(); setFormVisible(true); }}
            disabled={getAvailableVendors().length === 0}
          >
            新增廠商關聯
          </Button>
        </div>

        <Table columns={columns} dataSource={associations} rowKey="vendor_id" loading={loading} pagination={false} scroll={{ y: 400 }} />
      </Modal>

      <VendorAssociationForm
        open={formVisible}
        editing={!!editingAssociation}
        form={form}
        availableVendors={getAvailableVendors()}
        onSubmit={handleSubmit}
        onCancel={() => { setFormVisible(false); setEditingAssociation(null); form.resetFields(); }}
      />
    </>
  );
};

export default ProjectVendorManagement;
