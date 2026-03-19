/**
 * AI 同義詞管理面板
 *
 * 管理員可透過此面板新增/編輯/刪除同義詞群組，
 * 無需修改後端 YAML 檔案。
 *
 * @version 1.1.0 - Modal 拆分至 SynonymFormModal
 */

import React, { useState, useMemo } from 'react';
import {
  App,
  Card,
  Table,
  Button,
  Tag,
  Space,
  Switch,
  Popconfirm,
  Typography,
  Row,
  Col,
  Tooltip,
  Badge,
  Divider,
  Input,
  Select,
} from 'antd';
import {
  CheckCircleOutlined,
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  ReloadOutlined,
  TagsOutlined,
  SearchOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { Form } from 'antd';
import {
  useAISynonyms,
  useCreateSynonym,
  useUpdateSynonym,
  useDeleteSynonym,
  useReloadSynonyms,
} from '../../../hooks';
import type {
  AISynonymItem,
  AISynonymCreateRequest,
  AISynonymUpdateRequest,
} from '../../../types/ai';
import SynonymFormModal from './SynonymFormModal';

const { Title, Text } = Typography;

// eslint-disable-next-line react-refresh/only-export-components
export const DEFAULT_CATEGORIES = [
  { value: 'agency_synonyms', label: '機關名稱' },
  { value: 'doc_type_synonyms', label: '公文類型' },
  { value: 'status_synonyms', label: '狀態別稱' },
  { value: 'business_synonyms', label: '業務用語' },
];

// eslint-disable-next-line react-refresh/only-export-components
export const CATEGORY_COLORS: Record<string, string> = {
  agency_synonyms: 'blue',
  doc_type_synonyms: 'green',
  status_synonyms: 'orange',
  business_synonyms: 'purple',
};

export const SynonymManagementContent: React.FC = () => {
  const { message } = App.useApp();
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<AISynonymItem | null>(null);
  const [form] = Form.useForm();
  const [searchText, setSearchText] = useState('');
  const [lastSyncTime, setLastSyncTime] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<'idle' | 'syncing' | 'success' | 'error'>('idle');

  const synonymsQuery = useAISynonyms({ category: selectedCategory || undefined });
  const createMutation = useCreateSynonym();
  const updateMutation = useUpdateSynonym();
  const deleteMutation = useDeleteSynonym();
  const reloadMutation = useReloadSynonyms();

  // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
  const synonyms = useMemo(() => synonymsQuery.data?.items ?? [], [synonymsQuery.data?.items]);
  // eslint-disable-next-line @typescript-eslint/no-unnecessary-condition
  const categories = useMemo(() => synonymsQuery.data?.categories ?? [], [synonymsQuery.data?.categories]);

  const afterCrudSync = async () => {
    setSyncStatus('syncing');
    try {
      const result = await reloadMutation.mutateAsync();
      if (result.success) {
        setSyncStatus('success');
        setLastSyncTime(new Date().toLocaleTimeString('zh-TW', { hour12: false }));
        message.info(`同義詞已同步（${result.total_groups} 組 / ${result.total_words} 詞）`, 2);
      } else {
        setSyncStatus('error');
        message.warning('同義詞已儲存，但同步失敗，請手動點擊重新載入', 4);
      }
    } catch {
      setSyncStatus('error');
      message.warning('同義詞已儲存，但自動同步失敗，請手動點擊重新載入', 4);
    }
  };

  const filteredSynonyms = useMemo(() => {
    if (!searchText) return synonyms;
    const lower = searchText.toLowerCase();
    return synonyms.filter(s => s.words.toLowerCase().includes(lower) || s.category.toLowerCase().includes(lower));
  }, [synonyms, searchText]);

  const stats = useMemo(() => {
    const activeCount = synonyms.filter(s => s.is_active).length;
    const totalWords = synonyms.reduce((acc, s) => acc + s.words.split(',').filter(w => w.trim()).length, 0);
    return { total: synonyms.length, active: activeCount, totalWords };
  }, [synonyms]);

  const getCategoryLabel = (category: string): string => {
    const found = DEFAULT_CATEGORIES.find(c => c.value === category);
    return found ? found.label : category;
  };

  const handleAdd = () => {
    setEditingItem(null);
    form.resetFields();
    form.setFieldsValue({ is_active: true });
    setModalOpen(true);
  };

  const handleEdit = (item: AISynonymItem) => {
    setEditingItem(item);
    form.setFieldsValue({ category: item.category, words: item.words, is_active: item.is_active });
    setModalOpen(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (editingItem) {
        const request: AISynonymUpdateRequest = { id: editingItem.id, category: values.category, words: values.words, is_active: values.is_active };
        await updateMutation.mutateAsync(request);
        message.success('更新成功');
      } else {
        const request: AISynonymCreateRequest = { category: values.category, words: values.words, is_active: values.is_active ?? true };
        await createMutation.mutateAsync(request);
        message.success('新增成功');
      }
      setModalOpen(false);
      form.resetFields();
      void afterCrudSync();
    } catch (error) {
      if (error && typeof error === 'object' && 'errorFields' in error) return;
      message.error('操作失敗');
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteMutation.mutateAsync(id);
      message.success('刪除成功');
      void afterCrudSync();
    } catch { message.error('刪除失敗'); }
  };

  const handleToggleActive = async (item: AISynonymItem) => {
    try {
      await updateMutation.mutateAsync({ id: item.id, is_active: !item.is_active });
      message.success(item.is_active ? '已停用' : '已啟用');
      void afterCrudSync();
    } catch { message.error('操作失敗'); }
  };

  const handleReload = async () => {
    setSyncStatus('syncing');
    try {
      const result = await reloadMutation.mutateAsync();
      if (result.success) {
        message.success(result.message);
        setSyncStatus('success');
        setLastSyncTime(new Date().toLocaleTimeString('zh-TW', { hour12: false }));
      } else { message.error(result.message); setSyncStatus('error'); }
    } catch { message.error('重新載入失敗'); setSyncStatus('error'); }
  };

  const columns: ColumnsType<AISynonymItem> = [
    {
      title: '分類', dataIndex: 'category', key: 'category', width: 140,
      render: (category: string) => <Tag color={CATEGORY_COLORS[category] || 'default'}>{getCategoryLabel(category)}</Tag>,
      filters: categories.map(c => ({ text: getCategoryLabel(c), value: c })),
      onFilter: (value, record) => record.category === value,
    },
    {
      title: '同義詞', dataIndex: 'words', key: 'words',
      render: (words: string) => (
        <Space size={[4, 4]} wrap>
          {words.split(',').map(w => w.trim()).filter(Boolean).map((word, idx) => <Tag key={idx}>{word}</Tag>)}
        </Space>
      ),
    },
    {
      title: '狀態', dataIndex: 'is_active', key: 'is_active', width: 80, align: 'center',
      render: (isActive: boolean, record: AISynonymItem) => <Switch checked={isActive} size="small" onChange={() => handleToggleActive(record)} />,
      filters: [{ text: '啟用', value: true }, { text: '停用', value: false }],
      onFilter: (value, record) => record.is_active === value,
    },
    {
      title: '詞數', key: 'word_count', width: 70, align: 'center',
      render: (_: unknown, record: AISynonymItem) => <Badge count={record.words.split(',').filter(w => w.trim()).length} showZero style={{ backgroundColor: '#52c41a' }} />,
    },
    {
      title: '操作', key: 'actions', width: 120, align: 'center',
      render: (_: unknown, record: AISynonymItem) => (
        <Space size="small">
          <Tooltip title="編輯"><Button type="text" size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)} /></Tooltip>
          <Popconfirm title="確認刪除" description="確定要刪除此同義詞群組嗎？" onConfirm={() => handleDelete(record.id)} okText="確認" cancelText="取消">
            <Tooltip title="刪除"><Button type="text" size="small" danger icon={<DeleteOutlined />} /></Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const allCategoryOptions = useMemo(() => {
    const defaultValues = DEFAULT_CATEGORIES.map(c => c.value);
    const extra = categories.filter(c => !defaultValues.includes(c));
    return [...DEFAULT_CATEGORIES, ...extra.map(c => ({ value: c, label: c }))];
  }, [categories]);

  return (
    <>
      <Card>
        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Space>
              <TagsOutlined style={{ fontSize: 24, color: '#1890ff' }} />
              <Title level={4} style={{ margin: 0 }}>AI 同義詞管理</Title>
            </Space>
            <div style={{ marginTop: 4 }}>
              <Text type="secondary">管理 AI 自然語言搜尋使用的同義詞字典，異動後自動同步至 AI 服務</Text>
            </div>
          </Col>
          <Col>
            <Space size={8}>
              <Text type="secondary">共 {stats.total} 組 / {stats.active} 啟用 / {stats.totalWords} 詞</Text>
              {syncStatus === 'syncing' && <Text type="secondary" style={{ fontSize: 12 }}><SyncOutlined spin /> 同步中...</Text>}
              {syncStatus === 'success' && lastSyncTime && <Text type="success" style={{ fontSize: 12 }}><CheckCircleOutlined /> 已同步 {lastSyncTime}</Text>}
              {syncStatus === 'error' && <Text type="danger" style={{ fontSize: 12 }}>同步失敗</Text>}
            </Space>
          </Col>
        </Row>

        <Divider style={{ margin: '12px 0' }} />

        <Row justify="space-between" align="middle" style={{ marginBottom: 16 }}>
          <Col>
            <Space>
              <Select placeholder="依分類篩選" allowClear style={{ width: 180 }} value={selectedCategory} onChange={val => setSelectedCategory(val || null)} options={allCategoryOptions} />
              <Input placeholder="搜尋同義詞..." prefix={<SearchOutlined />} allowClear style={{ width: 200 }} value={searchText} onChange={e => setSearchText(e.target.value)} />
            </Space>
          </Col>
          <Col>
            <Space>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>新增群組</Button>
              <Tooltip title="手動同步同義詞到 AI 服務記憶體（系統已自動同步）">
                <Button icon={<ReloadOutlined />} loading={reloadMutation.isPending} onClick={handleReload}>手動同步</Button>
              </Tooltip>
            </Space>
          </Col>
        </Row>

        <Table
          columns={columns} dataSource={filteredSynonyms} rowKey="id" loading={synonymsQuery.isLoading}
          scroll={{ x: 700 }} pagination={{ showSizeChanger: true, showTotal: (total) => `共 ${total} 筆`, defaultPageSize: 20, pageSizeOptions: ['10', '20', '50', '100'] }}
          size="middle"
        />
      </Card>

      <SynonymFormModal
        open={modalOpen}
        editing={!!editingItem}
        form={form}
        categoryOptions={allCategoryOptions}
        onSave={handleSave}
        onCancel={() => { setModalOpen(false); form.resetFields(); }}
      />
    </>
  );
};
