/**
 * AI 同義詞管理頁面
 *
 * 管理員可透過此頁面新增/編輯/刪除同義詞群組，
 * 無需修改後端 YAML 檔案。
 *
 * @version 1.0.0
 * @created 2026-02-08
 */

import React, { useState, useCallback, useEffect, useMemo } from 'react';
import { ResponsiveContent } from '../components/common';
import {
  Card,
  Table,
  Button,
  Tag,
  Space,
  Modal,
  Form,
  Input,
  Select,
  Switch,
  message,
  Popconfirm,
  Typography,
  Row,
  Col,
  Tooltip,
  Badge,
  Divider,
} from 'antd';
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  TagsOutlined,
  SearchOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { aiApi } from '../api/aiApi';
import type {
  AISynonymItem,
  AISynonymCreateRequest,
  AISynonymUpdateRequest,
} from '../api/aiApi';

const { Title, Text } = Typography;
const { TextArea } = Input;

// 預設分類選項
const DEFAULT_CATEGORIES = [
  { value: 'agency_synonyms', label: '機關名稱' },
  { value: 'doc_type_synonyms', label: '公文類型' },
  { value: 'status_synonyms', label: '狀態別稱' },
  { value: 'business_synonyms', label: '業務用語' },
];

// 分類顏色映射
const CATEGORY_COLORS: Record<string, string> = {
  agency_synonyms: 'blue',
  doc_type_synonyms: 'green',
  status_synonyms: 'orange',
  business_synonyms: 'purple',
};

export const AISynonymManagementPage: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [synonyms, setSynonyms] = useState<AISynonymItem[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<AISynonymItem | null>(null);
  const [form] = Form.useForm();
  const [reloading, setReloading] = useState(false);
  const [searchText, setSearchText] = useState('');

  // 載入同義詞列表
  const loadSynonyms = useCallback(async () => {
    setLoading(true);
    try {
      const response = await aiApi.listSynonyms({
        category: selectedCategory || undefined,
      });
      setSynonyms(response.items);
      setCategories(response.categories);
    } catch {
      message.error('載入同義詞列表失敗');
    } finally {
      setLoading(false);
    }
  }, [selectedCategory]);

  useEffect(() => {
    loadSynonyms();
  }, [loadSynonyms]);

  // 篩選後的資料
  const filteredSynonyms = useMemo(() => {
    if (!searchText) return synonyms;
    const lower = searchText.toLowerCase();
    return synonyms.filter(
      (s) =>
        s.words.toLowerCase().includes(lower) ||
        s.category.toLowerCase().includes(lower)
    );
  }, [synonyms, searchText]);

  // 統計資料
  const stats = useMemo(() => {
    const activeCount = synonyms.filter((s) => s.is_active).length;
    const totalWords = synonyms.reduce((acc, s) => {
      return acc + s.words.split(',').filter((w) => w.trim()).length;
    }, 0);
    return { total: synonyms.length, active: activeCount, totalWords };
  }, [synonyms]);

  // 開啟新增 Modal
  const handleAdd = () => {
    setEditingItem(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true });
    setModalOpen(true);
  };

  // 開啟編輯 Modal
  const handleEdit = (item: AISynonymItem) => {
    setEditingItem(item);
    form.setFieldsValue({
      category: item.category,
      words: item.words,
      is_active: item.is_active,
    });
    setModalOpen(true);
  };

  // 儲存（新增或更新）
  const handleSave = async () => {
    try {
      const values = await form.validateFields();

      if (editingItem) {
        // 更新
        const request: AISynonymUpdateRequest = {
          id: editingItem.id,
          category: values.category,
          words: values.words,
          is_active: values.is_active,
        };
        await aiApi.updateSynonym(request);
        message.success('更新成功');
      } else {
        // 新增
        const request: AISynonymCreateRequest = {
          category: values.category,
          words: values.words,
          is_active: values.is_active ?? true,
        };
        await aiApi.createSynonym(request);
        message.success('新增成功');
      }

      setModalOpen(false);
      form.resetFields();
      loadSynonyms();
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) {
        // Form validation error
        return;
      }
      message.error('操作失敗');
    }
  };

  // 刪除
  const handleDelete = async (id: number) => {
    try {
      await aiApi.deleteSynonym(id);
      message.success('刪除成功');
      loadSynonyms();
    } catch {
      message.error('刪除失敗');
    }
  };

  // 切換啟用狀態
  const handleToggleActive = async (item: AISynonymItem) => {
    try {
      await aiApi.updateSynonym({
        id: item.id,
        is_active: !item.is_active,
      });
      message.success(item.is_active ? '已停用' : '已啟用');
      loadSynonyms();
    } catch {
      message.error('操作失敗');
    }
  };

  // 重新載入
  const handleReload = async () => {
    setReloading(true);
    try {
      const result = await aiApi.reloadSynonyms();
      if (result.success) {
        message.success(result.message);
      } else {
        message.error(result.message);
      }
    } catch {
      message.error('重新載入失敗');
    } finally {
      setReloading(false);
    }
  };

  // 取得分類顯示名稱
  const getCategoryLabel = (category: string): string => {
    const found = DEFAULT_CATEGORIES.find((c) => c.value === category);
    return found ? found.label : category;
  };

  // 表格欄位定義
  const columns: ColumnsType<AISynonymItem> = [
    {
      title: '分類',
      dataIndex: 'category',
      key: 'category',
      width: 140,
      render: (category: string) => (
        <Tag color={CATEGORY_COLORS[category] || 'default'}>
          {getCategoryLabel(category)}
        </Tag>
      ),
      filters: categories.map((c) => ({
        text: getCategoryLabel(c),
        value: c,
      })),
      onFilter: (value, record) => record.category === value,
    },
    {
      title: '同義詞',
      dataIndex: 'words',
      key: 'words',
      render: (words: string) => {
        const wordList = words.split(',').map((w) => w.trim()).filter(Boolean);
        return (
          <Space size={[4, 4]} wrap>
            {wordList.map((word, idx) => (
              <Tag key={idx}>{word}</Tag>
            ))}
          </Space>
        );
      },
    },
    {
      title: '狀態',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      align: 'center',
      render: (isActive: boolean, record: AISynonymItem) => (
        <Switch
          checked={isActive}
          size="small"
          onChange={() => handleToggleActive(record)}
        />
      ),
      filters: [
        { text: '啟用', value: true },
        { text: '停用', value: false },
      ],
      onFilter: (value, record) => record.is_active === value,
    },
    {
      title: '詞數',
      key: 'word_count',
      width: 70,
      align: 'center',
      render: (_: unknown, record: AISynonymItem) => {
        const count = record.words.split(',').filter((w) => w.trim()).length;
        return <Badge count={count} showZero style={{ backgroundColor: '#52c41a' }} />;
      },
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      align: 'center',
      render: (_: unknown, record: AISynonymItem) => (
        <Space size="small">
          <Tooltip title="編輯">
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            />
          </Tooltip>
          <Popconfirm
            title="確認刪除"
            description="確定要刪除此同義詞群組嗎？"
            onConfirm={() => handleDelete(record.id)}
            okText="確認"
            cancelText="取消"
          >
            <Tooltip title="刪除">
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  // 合併所有分類選項（預設 + 資料庫中已有的）
  const allCategoryOptions = useMemo(() => {
    const defaultValues = DEFAULT_CATEGORIES.map((c) => c.value);
    const extraCategories = categories.filter(
      (c) => !defaultValues.includes(c)
    );
    return [
      ...DEFAULT_CATEGORIES,
      ...extraCategories.map((c) => ({ value: c, label: c })),
    ];
  }, [categories]);

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Space>
              <TagsOutlined style={{ fontSize: 24, color: '#1890ff' }} />
              <Title level={4} style={{ margin: 0 }}>
                AI 同義詞管理
              </Title>
            </Space>
            <div style={{ marginTop: 4 }}>
              <Text type="secondary">
                管理 AI 自然語言搜尋使用的同義詞字典，新增或修改後需點擊「重新載入」生效
              </Text>
            </div>
          </Col>
          <Col>
            <Space>
              <Text type="secondary">
                共 {stats.total} 組 / {stats.active} 啟用 / {stats.totalWords} 詞
              </Text>
            </Space>
          </Col>
        </Row>

        <Divider style={{ margin: '12px 0' }} />

        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Space>
              <Select
                placeholder="依分類篩選"
                allowClear
                style={{ width: 180 }}
                value={selectedCategory}
                onChange={(val) => setSelectedCategory(val || null)}
                options={allCategoryOptions}
              />
              <Input
                placeholder="搜尋同義詞..."
                prefix={<SearchOutlined />}
                allowClear
                style={{ width: 200 }}
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
              />
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleAdd}
              >
                新增群組
              </Button>
              <Tooltip title="將資料庫中的同義詞重新載入到 AI 服務記憶體">
                <Button
                  icon={<ReloadOutlined />}
                  loading={reloading}
                  onClick={handleReload}
                >
                  重新載入
                </Button>
              </Tooltip>
            </Space>
          </Col>
        </Row>

        <Table
          columns={columns}
          dataSource={filteredSynonyms}
          rowKey="id"
          loading={loading}
          pagination={{
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 筆`,
            defaultPageSize: 20,
            pageSizeOptions: ['10', '20', '50', '100'],
          }}
          size="middle"
        />
      </Card>

      {/* 新增/編輯 Modal */}
      <Modal
        title={editingItem ? '編輯同義詞群組' : '新增同義詞群組'}
        open={modalOpen}
        onOk={handleSave}
        onCancel={() => {
          setModalOpen(false);
          form.resetFields();
        }}
        okText="儲存"
        cancelText="取消"
        destroyOnClose
        forceRender
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ is_active: true }}
        >
          <Form.Item
            name="category"
            label="分類"
            rules={[{ required: true, message: '請選擇或輸入分類' }]}
          >
            <Select
              showSearch
              placeholder="選擇或輸入分類"
              options={allCategoryOptions}
              allowClear
              // 允許自行輸入新的分類
              // 注意：Ant Design Select 的 mode 不用 tags，改用 filterOption + 不找到時的提示
            />
          </Form.Item>

          <Form.Item
            name="words"
            label="同義詞列表"
            rules={[{ required: true, message: '請輸入同義詞' }]}
            extra="以逗號分隔多個同義詞，例如：桃園市政府, 桃市府, 市政府"
          >
            <TextArea
              rows={3}
              placeholder="桃園市政府, 桃市府, 市政府, 市府"
            />
          </Form.Item>

          <Form.Item
            name="is_active"
            label="啟用狀態"
            valuePropName="checked"
          >
            <Switch checkedChildren="啟用" unCheckedChildren="停用" />
          </Form.Item>
        </Form>
      </Modal>
    </ResponsiveContent>
  );
};

export default AISynonymManagementPage;
