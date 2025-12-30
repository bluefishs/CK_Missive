import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Input,
  Space,
  Card,
  message,
  Modal,
  Form,
  Select,
  Typography,
  Tag,
  Popconfirm,
  Row,
  Col,
  Statistic
} from 'antd';
import {
  PlusOutlined,
  SearchOutlined,
  EditOutlined,
  DeleteOutlined,
  UserOutlined,
  PhoneOutlined,
  MailOutlined,
  ShopOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Title } = Typography;
const { Option } = Select;

interface Vendor {
  id: number;
  vendor_name: string;
  vendor_code?: string;
  contact_person?: string;
  phone?: string;
  address?: string;
  email?: string;
  business_type?: string;
  rating?: number;
  created_at: string;
  updated_at: string;
}

interface VendorFormData {
  vendor_name: string;
  vendor_code?: string;
  contact_person?: string;
  phone?: string;
  address?: string;
  email?: string;
  business_type?: string;
  rating?: number;
}

const VendorList: React.FC = () => {
  const [vendors, setVendors] = useState<Vendor[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [current, setCurrent] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [searchText, setSearchText] = useState('');
  const [businessTypeFilter, setBusinessTypeFilter] = useState<string>('');
  const [ratingFilter, setRatingFilter] = useState<number | undefined>();

  const [modalVisible, setModalVisible] = useState(false);
  const [editingVendor, setEditingVendor] = useState<Vendor | null>(null);
  const [form] = Form.useForm();

  // 載入廠商列表
  const loadVendors = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: ((current - 1) * pageSize).toString(),
        limit: pageSize.toString(),
      });

      if (searchText) params.append('search', searchText);
      if (businessTypeFilter) params.append('business_type', businessTypeFilter);
      if (ratingFilter) params.append('rating', ratingFilter.toString());

      const response = await fetch(`/api/vendors/?${params}`);
      const data = await response.json();

      if (response.ok) {
        setVendors(data.vendors || []);
        setTotal(data.total || 0);
      } else {
        message.error('載入廠商列表失敗');
      }
    } catch (error) {
      message.error('網路錯誤，請稍後再試');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVendors();
  }, [current, pageSize, searchText, businessTypeFilter, ratingFilter]);

  // 新增或編輯廠商
  const handleSubmit = async (values: VendorFormData) => {
    try {
      const url = editingVendor 
        ? `/api/vendors/${editingVendor.id}`
        : '/api/vendors/';
      
      const method = editingVendor ? 'PUT' : 'POST';
      
      const response = await fetch(url, {
        method,
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(values),
      });

      if (response.ok) {
        message.success(editingVendor ? '廠商更新成功' : '廠商建立成功');
        setModalVisible(false);
        form.resetFields();
        setEditingVendor(null);
        loadVendors();
      } else {
        const error = await response.json();
        message.error(error.detail || '操作失敗');
      }
    } catch (error) {
      message.error('網路錯誤，請稍後再試');
    }
  };

  // 刪除廠商
  const handleDelete = async (id: number) => {
    try {
      const response = await fetch(`/api/vendors/${id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        message.success('廠商刪除成功');
        loadVendors();
      } else {
        const error = await response.json();
        message.error(error.detail || '刪除失敗');
      }
    } catch (error) {
      message.error('網路錯誤，請稍後再試');
    }
  };

  // 開啟編輯模態框
  const handleEdit = (vendor: Vendor) => {
    setEditingVendor(vendor);
    form.setFieldsValue(vendor);
    setModalVisible(true);
  };

  // 評價顏色
  const getRatingColor = (rating?: number) => {
    if (!rating) return 'default';
    if (rating >= 4) return 'green';
    if (rating >= 3) return 'orange';
    return 'red';
  };

  const columns: ColumnsType<Vendor> = [
    {
      title: '廠商名稱',
      dataIndex: 'vendor_name',
      key: 'vendor_name',
      render: (text: string, record: Vendor) => (
        <Space direction="vertical" size="small">
          <strong>{text}</strong>
          {record.vendor_code && (
            <small style={{ color: '#666' }}>統編: {record.vendor_code}</small>
          )}
        </Space>
      ),
    },
    {
      title: '聯絡資訊',
      key: 'contact',
      render: (_, record: Vendor) => (
        <Space direction="vertical" size="small">
          {record.contact_person && (
            <span><UserOutlined /> {record.contact_person}</span>
          )}
          {record.phone && (
            <span><PhoneOutlined /> {record.phone}</span>
          )}
          {record.email && (
            <span><MailOutlined /> {record.email}</span>
          )}
        </Space>
      ),
    },
    {
      title: '營業項目',
      dataIndex: 'business_type',
      key: 'business_type',
      render: (text: string) => text && <Tag icon={<ShopOutlined />}>{text}</Tag>,
    },
    {
      title: '評價',
      dataIndex: 'rating',
      key: 'rating',
      render: (rating: number) => (
        rating ? (
          <Tag color={getRatingColor(rating)}>
            {rating} 星
          </Tag>
        ) : <span style={{ color: '#999' }}>未評價</span>
      ),
    },
    {
      title: '建立時間',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record: Vendor) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            編輯
          </Button>
          <Popconfirm
            title="確定要刪除此廠商嗎？"
            description="刪除後無法恢復，且需確保沒有關聯的專案。"
            onConfirm={() => handleDelete(record.id)}
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
    <div style={{ padding: '24px' }}>
      <Card>
        <div style={{ marginBottom: '16px' }}>
          <Row gutter={16}>
            <Col span={6}>
              <Statistic title="總廠商數" value={total} />
            </Col>
          </Row>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <Title level={3}>廠商管理</Title>
          
          <Space style={{ marginBottom: '16px' }}>
            <Input
              placeholder="搜尋廠商名稱、聯絡人或營業項目"
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{ width: 300 }}
              allowClear
            />
            
            <Input
              placeholder="營業項目篩選"
              value={businessTypeFilter}
              onChange={(e) => setBusinessTypeFilter(e.target.value)}
              style={{ width: 150 }}
              allowClear
            />
            
            <Select
              placeholder="評價篩選"
              value={ratingFilter}
              onChange={setRatingFilter}
              style={{ width: 120 }}
              allowClear
            >
              <Option value={5}>5星</Option>
              <Option value={4}>4星</Option>
              <Option value={3}>3星</Option>
              <Option value={2}>2星</Option>
              <Option value={1}>1星</Option>
            </Select>

            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={() => {
                setEditingVendor(null);
                form.resetFields();
                setModalVisible(true);
              }}
            >
              新增廠商
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={vendors}
          rowKey="id"
          loading={loading}
          pagination={{
            current,
            pageSize,
            total,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => 
              `第 ${range[0]}-${range[1]} 項，共 ${total} 項`,
            onChange: (page, size) => {
              setCurrent(page);
              setPageSize(size || 10);
            },
          }}
        />
      </Card>

      <Modal
        title={editingVendor ? '編輯廠商' : '新增廠商'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          setEditingVendor(null);
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
            name="vendor_name"
            label="廠商名稱"
            rules={[{ required: true, message: '請輸入廠商名稱' }]}
          >
            <Input placeholder="請輸入廠商名稱" />
          </Form.Item>

          <Form.Item
            name="vendor_code"
            label="統一編號"
          >
            <Input placeholder="請輸入統一編號" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="contact_person"
                label="聯絡人"
              >
                <Input placeholder="請輸入聯絡人" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="phone"
                label="電話"
              >
                <Input placeholder="請輸入電話" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="email"
            label="電子郵件"
            rules={[{ type: 'email', message: '請輸入有效的電子郵件地址' }]}
          >
            <Input placeholder="請輸入電子郵件" />
          </Form.Item>

          <Form.Item
            name="address"
            label="地址"
          >
            <Input.TextArea 
              placeholder="請輸入地址" 
              rows={2}
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="business_type"
                label="營業項目"
              >
                <Input placeholder="請輸入營業項目" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="rating"
                label="合作評價"
              >
                <Select placeholder="請選擇評價">
                  <Option value={5}>5星 - 優秀</Option>
                  <Option value={4}>4星 - 良好</Option>
                  <Option value={3}>3星 - 普通</Option>
                  <Option value={2}>2星 - 待改善</Option>
                  <Option value={1}>1星 - 不佳</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item style={{ textAlign: 'right', marginBottom: 0 }}>
            <Space>
              <Button 
                onClick={() => {
                  setModalVisible(false);
                  setEditingVendor(null);
                  form.resetFields();
                }}
              >
                取消
              </Button>
              <Button type="primary" htmlType="submit">
                {editingVendor ? '更新' : '建立'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default VendorList;