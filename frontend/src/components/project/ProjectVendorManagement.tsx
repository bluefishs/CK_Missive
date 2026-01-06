import React, { useState, useEffect } from 'react';
import {
  Modal,
  Table,
  Button,
  Select,
  Form,
  Input,
  DatePicker,
  InputNumber,
  message,
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
import { API_BASE_URL } from '../../api/client';

const { Option } = Select;

interface Vendor {
  id: number;
  vendor_name: string;
  vendor_code?: string;
  contact_person?: string;
  phone?: string;
  business_type?: string;
}

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
  visible: boolean;
  onClose: () => void;
}

const ProjectVendorManagement: React.FC<ProjectVendorManagementProps> = ({
  projectId,
  projectName,
  visible,
  onClose,
}) => {
  const [associations, setAssociations] = useState<ProjectVendorAssociation[]>([]);
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(false);
  const [formVisible, setFormVisible] = useState(false);
  const [editingAssociation, setEditingAssociation] = useState<ProjectVendorAssociation | null>(null);
  const [form] = Form.useForm();

  // 載入專案廠商關聯
  const loadAssociations = async () => {
    if (!projectId) return;

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/project-vendors/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId })
      });
      const data = await response.json();

      if (response.ok) {
        setAssociations(data.associations || []);
      } else {
        message.error('載入廠商關聯失敗');
      }
    } catch (error) {
      message.error('網路錯誤，請稍後再試');
    } finally {
      setLoading(false);
    }
  };

  // 載入可選廠商
  const loadVendors = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/vendors/list`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ limit: 1000 })
      });
      const data = await response.json();

      if (response.ok) {
        setVendors(data.items || data.vendors || []);
      }
    } catch (error) {
      console.error('載入廠商列表失敗:', error);
    }
  };

  useEffect(() => {
    if (visible) {
      loadAssociations();
      loadVendors();
    }
  }, [visible, projectId]);

  // 新增或編輯關聯
  const handleSubmit = async (values: ProjectVendorFormData) => {
    try {
      const formData = {
        project_id: projectId,
        vendor_id: values.vendor_id,
        role: values.role,
        contract_amount: values.contract_amount,
        start_date: values.start_date ? dayjs(values.start_date).format('YYYY-MM-DD') : undefined,
        end_date: values.end_date ? dayjs(values.end_date).format('YYYY-MM-DD') : undefined,
        status: values.status || 'active',
      };

      let response;
      if (editingAssociation) {
        // 更新關聯 (使用 POST 方法)
        response = await fetch(`${API_BASE_URL}/api/project-vendors/update`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            project_id: projectId,
            vendor_id: editingAssociation.vendor_id,
            role: values.role,
            contract_amount: values.contract_amount,
            start_date: formData.start_date,
            end_date: formData.end_date,
            status: values.status,
          }),
        });
      } else {
        // 新增關聯 (使用 POST 方法)
        response = await fetch(`${API_BASE_URL}/api/project-vendors/create`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData),
        });
      }

      if (response.ok) {
        message.success(editingAssociation ? '關聯更新成功' : '關聯建立成功');
        setFormVisible(false);
        form.resetFields();
        setEditingAssociation(null);
        loadAssociations();
      } else {
        const error = await response.json();
        message.error(error.detail || '操作失敗');
      }
    } catch (error) {
      message.error('網路錯誤，請稍後再試');
    }
  };

  // 刪除關聯 (使用 POST 方法)
  const handleDelete = async (vendorId: number) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/project-vendors/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_id: projectId,
          vendor_id: vendorId
        })
      });

      if (response.ok) {
        message.success('關聯刪除成功');
        loadAssociations();
      } else {
        const error = await response.json();
        message.error(error.detail || '刪除失敗');
      }
    } catch (error) {
      message.error('網路錯誤，請稍後再試');
    }
  };

  // 開啟編輯
  const handleEdit = (association: ProjectVendorAssociation) => {
    setEditingAssociation(association);
    const formValues = {
      vendor_id: association.vendor_id,
      role: association.role,
      contract_amount: association.contract_amount,
      start_date: association.start_date ? dayjs(association.start_date) : undefined,
      end_date: association.end_date ? dayjs(association.end_date) : undefined,
      status: association.status,
    };
    form.setFieldsValue(formValues);
    setFormVisible(true);
  };

  // 狀態顏色
  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'active': return 'processing';
      case 'completed': return 'success';
      case 'inactive': return 'warning';
      case 'cancelled': return 'error';
      default: return 'default';
    }
  };

  // 角色顏色
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

  // 格式化金額
  const formatAmount = (amount?: number) => {
    if (!amount) return '-';
    return new Intl.NumberFormat('zh-TW').format(amount);
  };

  // 獲取未關聯的廠商
  const getAvailableVendors = () => {
    const associatedVendorIds = associations.map(a => a.vendor_id);
    return vendors.filter(vendor => 
      editingAssociation ? 
        (vendor.id === editingAssociation.vendor_id || !associatedVendorIds.includes(vendor.id)) :
        !associatedVendorIds.includes(vendor.id)
    );
  };

  const columns: ColumnsType<ProjectVendorAssociation> = [
    {
      title: '廠商資訊',
      key: 'vendor_info',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          <strong>{record.vendor_name}</strong>
          {record.vendor_code && (
            <small style={{ color: '#666' }}>統編: {record.vendor_code}</small>
          )}
          {record.vendor_business_type && (
            <Tag>{record.vendor_business_type}</Tag>
          )}
        </Space>
      ),
    },
    {
      title: '聯絡資訊',
      key: 'contact',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {record.vendor_contact_person && (
            <span><UserOutlined /> {record.vendor_contact_person}</span>
          )}
          {record.vendor_phone && (
            <span><PhoneOutlined /> {record.vendor_phone}</span>
          )}
        </Space>
      ),
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => (
        role ? <Tag color={getRoleColor(role)}>{role}</Tag> : <span style={{ color: '#999' }}>未設定</span>
      ),
    },
    {
      title: '合約金額',
      dataIndex: 'contract_amount',
      key: 'contract_amount',
      render: (amount: number) => (
        <span>
          <DollarOutlined style={{ marginRight: 4 }} />
          ${formatAmount(amount)}
        </span>
      ),
    },
    {
      title: '合作期間',
      key: 'duration',
      render: (_, record) => (
        <Space direction="vertical" size="small">
          {record.start_date && (
            <span>
              <CalendarOutlined style={{ marginRight: 4 }} />
              開始: {dayjs(record.start_date).format('YYYY-MM-DD')}
            </span>
          )}
          {record.end_date && (
            <span>
              <CalendarOutlined style={{ marginRight: 4 }} />
              結束: {dayjs(record.end_date).format('YYYY-MM-DD')}
            </span>
          )}
        </Space>
      ),
    },
    {
      title: '狀態',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {status === 'active' ? '合作中' : 
           status === 'completed' ? '已完成' :
           status === 'inactive' ? '暫停' :
           status === 'cancelled' ? '已取消' : status}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            編輯
          </Button>
          <Popconfirm
            title="確定要刪除此關聯嗎？"
            description="刪除後無法恢復。"
            onConfirm={() => handleDelete(record.vendor_id)}
            okText="確定"
            cancelText="取消"
          >
            <Button
              type="link"
              danger
              icon={<DeleteOutlined />}
            >
              刪除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      <Modal
        title={`專案廠商管理 - ${projectName}`}
        open={visible}
        onCancel={onClose}
        footer={null}
        width={1200}
      >
        <Card style={{ marginBottom: 16 }}>
          <Row gutter={16}>
            <Col span={8}>
              <Statistic title="關聯廠商數" value={associations.length} />
            </Col>
            <Col span={8}>
              <Statistic 
                title="合約總金額" 
                value={associations.reduce((sum, a) => sum + (a.contract_amount || 0), 0)}
                formatter={value => `$${formatAmount(Number(value))}`}
              />
            </Col>
            <Col span={8}>
              <Statistic 
                title="進行中廠商" 
                value={associations.filter(a => a.status === 'active').length}
              />
            </Col>
          </Row>
        </Card>

        <div style={{ marginBottom: 16, textAlign: 'right' }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditingAssociation(null);
              form.resetFields();
              setFormVisible(true);
            }}
            disabled={getAvailableVendors().length === 0}
          >
            新增廠商關聯
          </Button>
        </div>

        <Table
          columns={columns}
          dataSource={associations}
          rowKey="vendor_id"
          loading={loading}
          pagination={false}
          scroll={{ y: 400 }}
        />
      </Modal>

      <Modal
        title={editingAssociation ? '編輯廠商關聯' : '新增廠商關聯'}
        open={formVisible}
        onCancel={() => {
          setFormVisible(false);
          setEditingAssociation(null);
          form.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            name="vendor_id"
            label="選擇廠商"
            rules={[{ required: true, message: '請選擇廠商' }]}
          >
            <Select
              placeholder="請選擇廠商"
              disabled={!!editingAssociation}
              showSearch
              optionFilterProp="children"
            >
              {getAvailableVendors().map(vendor => (
                <Option key={vendor.id} value={vendor.id}>
                  <Space>
                    <strong>{vendor.vendor_name}</strong>
                    {vendor.vendor_code && (
                      <small style={{ color: '#666' }}>({vendor.vendor_code})</small>
                    )}
                    {vendor.business_type && (
                      <Tag size="small">{vendor.business_type}</Tag>
                    )}
                  </Space>
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            name="role"
            label="廠商角色"
          >
            <Select placeholder="請選擇角色">
              <Option value="主承包商">主承包商</Option>
              <Option value="分包商">分包商</Option>
              <Option value="供應商">供應商</Option>
              <Option value="顧問">顧問</Option>
              <Option value="監造">監造</Option>
              <Option value="其他">其他</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="contract_amount"
            label="合約金額"
          >
            <InputNumber
              placeholder="請輸入合約金額"
              min={0}
              style={{ width: '100%' }}
              formatter={value => `$ ${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}
              parser={value => value?.replace(/\$\s?|(,*)/g, '') as any}
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="start_date"
                label="合作開始日期"
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="end_date"
                label="合作結束日期"
              >
                <DatePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="status"
            label="合作狀態"
          >
            <Select placeholder="請選擇狀態" defaultValue="active">
              <Option value="active">合作中</Option>
              <Option value="completed">已完成</Option>
              <Option value="inactive">暫停</Option>
              <Option value="cancelled">已取消</Option>
            </Select>
          </Form.Item>

          <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
            <Space>
              <Button 
                onClick={() => {
                  setFormVisible(false);
                  setEditingAssociation(null);
                  form.resetFields();
                }}
              >
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                {editingAssociation ? '更新' : '建立'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </>
  );
};

export default ProjectVendorManagement;