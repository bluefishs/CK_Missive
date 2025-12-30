import React, { useState, useEffect } from 'react';
import {
  Table, Button, Space, Modal, Form, Input, Select, Card,
  Popconfirm, Tag, Row, Col, Switch, InputNumber, App
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, SettingOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { secureApiService } from '../../services/secureApiService';

const { Option } = Select;
const { TextArea } = Input;

interface SiteConfig {
  id: number;
  key: string;
  value: string;
  description?: string;
  category: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface ConfigFormData {
  key: string;
  value: string;
  config_type: string;
  description?: string;
  category: string;
}

const SiteConfigManagement: React.FC = () => {
  const { message } = App.useApp();
  const [configs, setConfigs] = useState<SiteConfig[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingConfig, setEditingConfig] = useState<SiteConfig | null>(null);
  const [form] = Form.useForm();
  const [searchText, setSearchText] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [categories, setCategories] = useState<string[]>([]);

  // 配置類型選項
  const configTypes = [
    { value: 'string', label: '字串' },
    { value: 'number', label: '數字' },
    { value: 'boolean', label: '布林值' },
    { value: 'json', label: 'JSON' }
  ];

  // 配置分類選項
  const categoryOptions = [
    { value: 'general', label: '一般設定' },
    { value: 'ui', label: '介面設定' },
    { value: 'features', label: '功能設定' },
    { value: 'system', label: '系統設定' }
  ];

  // 載入配置數據
  const loadConfigData = async () => {
    setLoading(true);
    try {
      const filters: any = {};
      if (selectedCategory) filters.category = selectedCategory;
      if (searchText) filters.search = searchText;

      const data = await secureApiService.getConfigurations(filters);
      setConfigs(data.configs || []);
    } catch (error) {
      console.warn('Configuration API not available, using fallback data');
      // 提供一些模擬配置數據作為 fallback
      setConfigs([
        {
          id: 1,
          key: 'site.title',
          value: 'CK Missive 公文系統',
          description: '網站標題設定',
          category: 'general',
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        {
          id: 2,
          key: 'site.description',
          value: '政府公文管理系統',
          description: '網站描述設定',
          category: 'general',
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        },
        {
          id: 3,
          key: 'navigation.max_depth',
          value: '3',
          description: '導覽選單最大層級',
          category: 'navigation',
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // 載入分類列表
  const loadCategories = async () => {
    try {
      // 使用正確的 API 基礎 URL
      const apiUrl = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001'}/api/site-management/config/categories`;
      const response = await fetch(apiUrl);
      if (response.ok) {
        const data = await response.json();
        setCategories(data.categories);
      } else {
        console.warn('Categories endpoint not available, using fallback data');
        // 提供預設分類
        setCategories([
          { id: 'general', name: '一般設定', description: '系統一般配置項目' },
          { id: 'navigation', name: '導覽設定', description: '網站導覽相關設定' },
          { id: 'ui', name: '界面設定', description: '使用者界面配置' },
          { id: 'security', name: '安全設定', description: '系統安全相關配置' },
          { id: 'api', name: 'API設定', description: 'API相關配置' }
        ]);
      }
    } catch (error) {
      console.error('Error loading categories:', error);
      // 提供預設分類作為 fallback
      setCategories([
        { id: 'general', name: '一般設定', description: '系統一般配置項目' },
        { id: 'navigation', name: '導覽設定', description: '網站導覽相關設定' },
        { id: 'ui', name: '界面設定', description: '使用者界面配置' },
        { id: 'security', name: '安全設定', description: '系統安全相關配置' },
        { id: 'api', name: 'API設定', description: 'API相關配置' }
      ]);
    }
  };

  useEffect(() => {
    loadConfigData();
    loadCategories();
  }, [searchText, selectedCategory]);

  // 顯示新增/編輯對話框
  const showModal = (config?: SiteConfig) => {
    setEditingConfig(config || null);
    if (config) {
      form.setFieldsValue(config);
    } else {
      form.resetFields();
      form.setFieldsValue({
        config_type: 'string',
        category: 'general'
      });
    }
    setModalVisible(true);
  };

  // 提交表單
  const handleSubmit = async (values: ConfigFormData) => {
    try {
      if (editingConfig) {
        // 更新配置
        await secureApiService.updateConfiguration({
          key: editingConfig.key,
          ...values
        });
        message.success('更新成功');
      } else {
        // 新增配置
        await secureApiService.createConfiguration(values);
        message.success('新增成功');
      }
      
      setModalVisible(false);
      form.resetFields();
      loadConfigData();
      loadCategories();
    } catch (error) {
      message.error('操作失敗');
      console.error('Error submitting form:', error);
    }
  };

  // 刪除配置
  const handleDelete = async (configKey: string) => {
    try {
      await secureApiService.deleteConfiguration(configKey);
      message.success('刪除成功');
      loadConfigData();
    } catch (error) {
      message.error('刪除失敗');
      console.error('Error deleting config:', error);
    }
  };

  // 格式化配置值顯示
  const formatConfigValue = (value: string, type: string) => {
    if (!value) return <span style={{ color: '#ccc' }}>空值</span>;
    
    switch (type) {
      case 'boolean':
        return (
          <Tag color={value === 'true' ? 'green' : 'red'}>
            {value === 'true' ? '是' : '否'}
          </Tag>
        );
      case 'json':
        try {
          return <pre style={{ margin: 0, fontSize: '12px' }}>{JSON.stringify(JSON.parse(value), null, 2)}</pre>;
        } catch {
          return <code>{value}</code>;
        }
      case 'number':
        return <Tag color="blue">{value}</Tag>;
      default:
        return value.length > 50 ? (
          <span title={value}>{value.substring(0, 50)}...</span>
        ) : value;
    }
  };

  // 渲染配置值輸入組件
  const renderConfigValueInput = (type: string) => {
    switch (type) {
      case 'boolean':
        return (
          <Select placeholder="選擇布林值">
            <Option value="true">是 (true)</Option>
            <Option value="false">否 (false)</Option>
          </Select>
        );
      case 'number':
        return <InputNumber style={{ width: '100%' }} placeholder="請輸入數字" />;
      case 'json':
        return <TextArea rows={4} placeholder="請輸入 JSON 格式數據" />;
      default:
        return <Input placeholder="請輸入配置值" />;
    }
  };

  // 表格列定義
  const columns: ColumnsType<SiteConfig> = [
    {
      title: '配置鍵值',
      dataIndex: 'key',
      key: 'key',
      width: 200,
      render: (text) => <code>{text}</code>,
    },
    {
      title: '配置值',
      dataIndex: 'value',
      key: 'value',
      render: (value, record) => formatConfigValue(value, record.config_type),
    },
    {
      title: '類型',
      dataIndex: 'config_type',
      key: 'config_type',
      width: 100,
      render: (type) => {
        const colors = {
          string: 'default',
          number: 'blue',
          boolean: 'green',
          json: 'purple'
        };
        return <Tag color={colors[type as keyof typeof colors] || 'default'}>{type}</Tag>;
      },
    },
    {
      title: '分類',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category) => <Tag>{category}</Tag>,
    },
    {
      title: '說明',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '系統配置',
      dataIndex: 'is_system',
      key: 'is_system',
      width: 100,
      render: (isSystem) => (
        <Tag color={isSystem ? 'red' : 'default'}>
          {isSystem ? '系統' : '一般'}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_, record) => (
        <Space>
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => showModal(record)}
          />
          {!record.is_system && (
            <Popconfirm
              title="確定要刪除這個配置嗎？"
              onConfirm={() => handleDelete(record.key)}
              okText="確定"
              cancelText="取消"
            >
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
              />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => showModal()}
          >
            新增配置
          </Button>
        </Col>
        <Col span={6}>
          <Select
            placeholder="選擇分類"
            style={{ width: '100%' }}
            value={selectedCategory}
            onChange={setSelectedCategory}
            allowClear
          >
            {categoryOptions.map(option => (
              <Option key={option.value} value={option.value}>
                {option.label}
              </Option>
            ))}
          </Select>
        </Col>
        <Col span={12}>
          <Input.Search
            placeholder="搜尋配置鍵值或說明"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            style={{ width: '100%' }}
          />
        </Col>
      </Row>

      <Card>
        <Table
          columns={columns}
          dataSource={configs}
          loading={loading}
          rowKey="id"
          pagination={{
            pageSize: 20,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 項配置`,
          }}
          size="small"
        />
      </Card>

      <Modal
        title={editingConfig ? '編輯配置' : '新增配置'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="key"
                label="配置鍵值"
                rules={[
                  { required: true, message: '請輸入配置鍵值' },
                  { pattern: /^[a-zA-Z_][a-zA-Z0-9_]*$/, message: '只能包含字母、數字和下劃線，且不能以數字開頭' }
                ]}
              >
                <Input 
                  placeholder="請輸入配置鍵值" 
                  disabled={!!editingConfig}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="config_type"
                label="配置類型"
                rules={[{ required: true, message: '請選擇配置類型' }]}
              >
                <Select placeholder="請選擇配置類型">
                  {configTypes.map(type => (
                    <Option key={type.value} value={type.value}>
                      {type.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="value"
            label="配置值"
            rules={[{ required: true, message: '請輸入配置值' }]}
          >
            <Form.Item noStyle shouldUpdate={(prevValues, currentValues) => 
              prevValues.config_type !== currentValues.config_type
            }>
              {({ getFieldValue }) => renderConfigValueInput(getFieldValue('config_type'))}
            </Form.Item>
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="category"
                label="分類"
                rules={[{ required: true, message: '請選擇分類' }]}
              >
                <Select placeholder="請選擇分類">
                  {categoryOptions.map(option => (
                    <Option key={option.value} value={option.value}>
                      {option.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="description"
            label="說明"
          >
            <TextArea rows={3} placeholder="請輸入配置說明" />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button type="primary" htmlType="submit">
                {editingConfig ? '更新' : '新增'}
              </Button>
              <Button onClick={() => setModalVisible(false)}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default SiteConfigManagement;