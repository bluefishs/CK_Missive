import React, { useState, useEffect } from 'react';
import {
  Table,
  Button,
  Input,
  Space,
  Card,
  App,
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
  DeleteOutlined,
  UserOutlined,
  PhoneOutlined,
  MailOutlined,
  ShopOutlined
} from '@ant-design/icons';
import type { TableColumnType } from 'antd';
import { vendorsApi } from '../../api/vendors';
import type { Vendor as ApiVendor, VendorCreate, VendorUpdate } from '../../types/api';

const { Title } = Typography;
const { Option } = Select;

// 營業項目選項 (與 ContractCaseDetailPage 協力廠商業務類別一致)
const BUSINESS_TYPE_OPTIONS = [
  { value: '測量業務', label: '測量業務', color: 'blue' },
  { value: '系統業務', label: '系統業務', color: 'green' },
  { value: '查估業務', label: '查估業務', color: 'orange' },
  { value: '其他類別', label: '其他類別', color: 'default' },
];

// 取得營業項目標籤顏色
const getBusinessTypeColor = (type?: string) => {
  const option = BUSINESS_TYPE_OPTIONS.find(opt => opt.value === type);
  return option?.color || 'default';
};

// 使用統一型別定義
type Vendor = ApiVendor;

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
  const { message } = App.useApp();
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

  // 載入廠商列表 (使用統一 API Client)
  const loadVendors = async () => {
    setLoading(true);
    try {
      // 構建查詢參數，只包含有值的欄位
      const params: Parameters<typeof vendorsApi.getVendors>[0] = {
        page: current,
        limit: pageSize,
      };
      if (searchText) params.search = searchText;
      if (businessTypeFilter) params.business_type = businessTypeFilter;

      const response = await vendorsApi.getVendors(params);

      setVendors(response.items);
      setTotal(response.pagination.total);
    } catch (error) {
      console.error('載入廠商列表失敗:', error);
      message.error('載入廠商列表失敗');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadVendors();
  }, [current, pageSize, searchText, businessTypeFilter, ratingFilter]);

  // 新增或編輯廠商 (使用統一 API Client)
  const handleSubmit = async (values: VendorFormData) => {
    try {
      if (editingVendor) {
        await vendorsApi.updateVendor(editingVendor.id, values as VendorUpdate);
        message.success('廠商更新成功');
      } else {
        await vendorsApi.createVendor(values as VendorCreate);
        message.success('廠商建立成功');
      }
      setModalVisible(false);
      form.resetFields();
      setEditingVendor(null);
      loadVendors();
    } catch (error: any) {
      console.error('廠商操作失敗:', error);
      message.error(error?.message || '操作失敗');
    }
  };

  // 刪除廠商 (使用統一 API Client)
  const handleDelete = async (id: number) => {
    try {
      await vendorsApi.deleteVendor(id);
      message.success('廠商刪除成功');
      loadVendors();
    } catch (error: any) {
      console.error('刪除廠商失敗:', error);
      message.error(error?.message || '刪除失敗');
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

  const columns: TableColumnType<Vendor>[] = [
    {
      title: '廠商名稱',
      dataIndex: 'vendor_name',
      key: 'vendor_name',
      sorter: (a, b) => a.vendor_name.localeCompare(b.vendor_name, 'zh-TW'),
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
      sorter: (a, b) => (a.contact_person || '').localeCompare(b.contact_person || '', 'zh-TW'),
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
      width: 130,
      sorter: (a, b) => (a.business_type || '').localeCompare(b.business_type || '', 'zh-TW'),
      filters: BUSINESS_TYPE_OPTIONS.map(opt => ({ text: opt.label, value: opt.value })),
      onFilter: (value, record) => record.business_type === value,
      render: (text: string) => text ? (
        <Tag icon={<ShopOutlined />} color={getBusinessTypeColor(text)}>{text}</Tag>
      ) : <span style={{ color: '#999' }}>未設定</span>,
    },
    {
      title: '評價',
      dataIndex: 'rating',
      key: 'rating',
      sorter: (a, b) => (a.rating || 0) - (b.rating || 0),
      filters: [
        { text: '5星', value: 5 },
        { text: '4星', value: 4 },
        { text: '3星', value: 3 },
        { text: '2星', value: 2 },
        { text: '1星', value: 1 },
        { text: '未評價', value: 0 },
      ],
      onFilter: (value, record) => (record.rating || 0) === value,
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
      sorter: (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
      render: (date: string) => new Date(date).toLocaleDateString(),
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_, record: Vendor) => (
        <Popconfirm
          title="確定要刪除此廠商嗎？"
          description="刪除後無法恢復，且需確保沒有關聯的專案。"
          onConfirm={(e) => {
            e?.stopPropagation();
            handleDelete(record.id);
          }}
          onCancel={(e) => e?.stopPropagation()}
          okText="確定"
          cancelText="取消"
        >
          <Button
            type="link"
            danger
            icon={<DeleteOutlined />}
            onClick={(e) => e.stopPropagation()}
          >
            刪除
          </Button>
        </Popconfirm>
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
            
            <Select
              placeholder="營業項目篩選"
              value={businessTypeFilter || undefined}
              onChange={(value) => setBusinessTypeFilter(value || '')}
              style={{ width: 150 }}
              allowClear
            >
              {BUSINESS_TYPE_OPTIONS.map(opt => (
                <Option key={opt.value} value={opt.value}>{opt.label}</Option>
              ))}
            </Select>
            
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
          onRow={(record) => ({
            onClick: () => handleEdit(record),
            style: { cursor: 'pointer' },
          })}
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
                rules={[{ required: true, message: '請選擇營業項目' }]}
              >
                <Select placeholder="請選擇營業項目">
                  {BUSINESS_TYPE_OPTIONS.map(opt => (
                    <Option key={opt.value} value={opt.value}>{opt.label}</Option>
                  ))}
                </Select>
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