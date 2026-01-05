import React, { useState, useEffect, useRef } from 'react';
import type { InputRef, TableColumnType } from 'antd';
import type { FilterDropdownProps, SorterResult } from 'antd/es/table/interface';
import {
  Typography,
  Table,
  Input,
  Button,
  Space,
  Card,
  Statistic,
  Row,
  Col,
  Tag,
  App,
  Select,
  Pagination,
  Modal,
  Form,
  Popconfirm,
  Tooltip,
} from 'antd';
import {
  SearchOutlined,
  ReloadOutlined,
  BankOutlined,
  BuildOutlined,
  TeamOutlined,
  BookOutlined,
  DeleteOutlined,
  PlusOutlined,
} from '@ant-design/icons';
import Highlighter from 'react-highlight-words';
import {
  agenciesApi,
  type AgencyWithStats,
  type AgencyStatistics,
  type AgencyCreate,
  type AgencyUpdate,
} from '../api';

const { Title, Text } = Typography;
const { Search } = Input;

// 使用 agenciesApi 匯出的型別，本地介面定義已移除以避免重複

// 機關類型選項
const AGENCY_TYPE_OPTIONS = [
  { value: '政府機關', label: '政府機關' },
  { value: '其他機關', label: '其他機關' },
  { value: '民間企業', label: '民間企業' },
  { value: '社會團體', label: '社會團體' },
  { value: '教育機構', label: '教育機構' },
];

type DataIndex = keyof AgencyWithStats;

export const AgenciesPage: React.FC = () => {
  const { message } = App.useApp();
  const [form] = Form.useForm();

  const [agencies, setAgencies] = useState<AgencyWithStats[]>([]);
  const [statistics, setStatistics] = useState<AgencyStatistics | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalAgencies, setTotalAgencies] = useState(0);

  // Modal 狀態
  const [modalVisible, setModalVisible] = useState(false);
  const [editingAgency, setEditingAgency] = useState<AgencyWithStats | null>(null);
  const [submitLoading, setSubmitLoading] = useState(false);

  // 欄位搜尋狀態
  const [columnSearchText, setColumnSearchText] = useState('');
  const [searchedColumn, setSearchedColumn] = useState('');
  const searchInput = useRef<InputRef>(null);

  // 欄位搜尋功能
  const handleColumnSearch = (
    selectedKeys: string[],
    confirm: FilterDropdownProps['confirm'],
    dataIndex: DataIndex,
  ) => {
    confirm();
    setColumnSearchText(selectedKeys[0]);
    setSearchedColumn(dataIndex);
  };

  const handleColumnReset = (clearFilters: () => void) => {
    clearFilters();
    setColumnSearchText('');
  };

  // 取得欄位搜尋屬性
  const getColumnSearchProps = (dataIndex: DataIndex): TableColumnType<AgencyWithStats> => ({
    filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters, close }) => (
      <div style={{ padding: 8 }} onKeyDown={(e) => e.stopPropagation()}>
        <Input
          ref={searchInput}
          placeholder={`搜尋...`}
          value={selectedKeys[0]}
          onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
          onPressEnter={() => handleColumnSearch(selectedKeys as string[], confirm, dataIndex)}
          style={{ marginBottom: 8, display: 'block' }}
        />
        <Space>
          <Button
            type="primary"
            onClick={() => handleColumnSearch(selectedKeys as string[], confirm, dataIndex)}
            icon={<SearchOutlined />}
            size="small"
            style={{ width: 90 }}
          >
            搜尋
          </Button>
          <Button
            onClick={() => clearFilters && handleColumnReset(clearFilters)}
            size="small"
            style={{ width: 90 }}
          >
            重置
          </Button>
          <Button
            type="link"
            size="small"
            onClick={() => close()}
          >
            關閉
          </Button>
        </Space>
      </div>
    ),
    filterIcon: (filtered: boolean) => (
      <SearchOutlined style={{ color: filtered ? '#1677ff' : undefined }} />
    ),
    onFilter: (value, record) =>
      record[dataIndex]
        ?.toString()
        .toLowerCase()
        .includes((value as string).toLowerCase()) ?? false,
    filterDropdownProps: {
      onOpenChange(open) {
        if (open) {
          setTimeout(() => searchInput.current?.select(), 100);
        }
      },
    },
    render: (text) =>
      searchedColumn === dataIndex ? (
        <Highlighter
          highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
          searchWords={[columnSearchText]}
          autoEscape
          textToHighlight={text ? text.toString() : ''}
        />
      ) : (
        text
      ),
  });

  // 載入機關單位列表（使用統一 API 服務）
  const fetchAgencies = async (search?: string, page = 1) => {
    setLoading(true);
    try {
      const response = await agenciesApi.getAgencies({
        page,
        limit: pageSize,
        search,
        include_stats: true,
      });

      setAgencies(response.items);
      setTotalAgencies(response.pagination.total);
    } catch (error) {
      console.error('載入機關單位錯誤:', error);
      message.error('載入機關單位失敗');
    } finally {
      setLoading(false);
    }
  };

  // 載入統計資料（使用統一 API 服務）
  const fetchStatistics = async () => {
    try {
      const data = await agenciesApi.getStatistics();
      setStatistics(data);
    } catch (error) {
      console.error('載入統計資料錯誤:', error);
    }
  };

  useEffect(() => {
    fetchAgencies();
    fetchStatistics();
  }, []);

  // 搜尋處理
  const handleSearch = (value: string) => {
    setSearchText(value);
    setCurrentPage(1);
    fetchAgencies(value, 1);
  };

  // 重新載入
  const handleRefresh = () => {
    setSearchText('');
    setCategoryFilter('');
    setCurrentPage(1);
    fetchAgencies();
    fetchStatistics();
  };

  // 分頁處理
  const handlePageChange = (page: number) => {
    setCurrentPage(page);
    fetchAgencies(searchText, page);
  };

  // 開啟新增 Modal
  const handleAdd = () => {
    setEditingAgency(null);
    form.resetFields();
    setModalVisible(true);
  };

  // 開啟編輯 Modal
  const handleEdit = (agency: AgencyWithStats) => {
    setEditingAgency(agency);
    form.setFieldsValue({
      agency_name: agency.agency_name,
      agency_short_name: agency.agency_short_name,
      agency_code: agency.agency_code,
      agency_type: agency.agency_type,
      contact_person: agency.contact_person,
      phone: agency.phone,
      address: agency.address,
      email: agency.email,
    });
    setModalVisible(true);
  };

  // 提交表單 (新增/更新) - 使用統一 API 服務
  const handleSubmit = async (values: AgencyCreate) => {
    setSubmitLoading(true);
    try {
      if (editingAgency) {
        // 更新現有機關
        await agenciesApi.updateAgency(editingAgency.id, values as AgencyUpdate);
        message.success('機關單位更新成功');
      } else {
        // 建立新機關
        await agenciesApi.createAgency(values);
        message.success('機關單位建立成功');
      }

      setModalVisible(false);
      form.resetFields();
      setEditingAgency(null);
      fetchAgencies(searchText, currentPage);
      fetchStatistics();
    } catch (error: any) {
      console.error('操作失敗:', error);
      message.error(error.message || '操作失敗，請稍後再試');
    } finally {
      setSubmitLoading(false);
    }
  };

  // 刪除機關單位（使用統一 API 服務）
  const handleDelete = async (id: number) => {
    try {
      await agenciesApi.deleteAgency(id);
      message.success('機關單位刪除成功');
      fetchAgencies(searchText, currentPage);
      fetchStatistics();
    } catch (error: any) {
      console.error('刪除失敗:', error);
      message.error(error.message || '刪除失敗');
    }
  };

  // 獲取類型標籤顏色
  const getTypeTagColor = (type: string) => {
    switch (type) {
      case 'sender': return 'blue';
      case 'receiver': return 'green';
      case 'both': return 'purple';
      default: return 'default';
    }
  };

  // 獲取類型文字
  const getTypeText = (type: string) => {
    switch (type) {
      case 'sender': return '發文機關';
      case 'receiver': return '收文機關';
      case 'both': return '收發文機關';
      default: return '未知';
    }
  };

  // 獲取分類圖示
  const getCategoryIcon = (category: string) => {
    switch (category) {
      case '政府機關': return <BankOutlined />;
      case '民間企業': return <BuildOutlined />;
      case '社會團體': return <TeamOutlined />;
      case '教育機構': return <BookOutlined />;
      default: return <BankOutlined />;
    }
  };

  // 表格欄位定義 - 含排序與篩選功能
  const columns: TableColumnType<AgencyWithStats>[] = [
    {
      title: '機關名稱',
      dataIndex: 'agency_name',
      key: 'agency_name',
      width: 280,
      sorter: (a, b) => a.agency_name.localeCompare(b.agency_name, 'zh-TW'),
      ...getColumnSearchProps('agency_name'),
      render: (text: string, record: AgencyWithStats) => (
        <div>
          <div style={{ fontWeight: 500 }}>
            {searchedColumn === 'agency_name' ? (
              <Highlighter
                highlightStyle={{ backgroundColor: '#ffc069', padding: 0 }}
                searchWords={[columnSearchText]}
                autoEscape
                textToHighlight={text || ''}
              />
            ) : text}
          </div>
          {record.agency_short_name && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              簡稱: {record.agency_short_name}
            </Text>
          )}
        </div>
      ),
    },
    {
      title: '機關代碼',
      dataIndex: 'agency_code',
      key: 'agency_code',
      width: 120,
      align: 'center' as const,
      ...getColumnSearchProps('agency_code'),
      render: (code: string) => code || <Text type="secondary">-</Text>,
    },
    {
      title: '分類',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      align: 'center' as const,
      filters: [
        { text: '政府機關', value: '政府機關' },
        { text: '民間企業', value: '民間企業' },
        { text: '教育機構', value: '教育機構' },
        { text: '社會團體', value: '社會團體' },
        { text: '其他機關', value: '其他機關' },
      ],
      onFilter: (value, record) => record.category === value,
      render: (category: string) => (
        <Tag icon={getCategoryIcon(category)} color="blue">
          {category}
        </Tag>
      ),
    },
    // 註解隱藏: 機關類型 (primary_type) - 因公文尚未關聯機關ID，目前無法判斷發文/收文機關
    // {
    //   title: '機關類型',
    //   dataIndex: 'primary_type',
    //   key: 'primary_type',
    //   width: 100,
    //   render: (type: string) => <Tag color={getTypeTagColor(type)}>{getTypeText(type)}</Tag>,
    // },
    {
      title: '聯絡人',
      dataIndex: 'contact_person',
      key: 'contact_person',
      width: 100,
      render: (person: string) => person || <Text type="secondary">-</Text>,
    },
    {
      title: '電話',
      dataIndex: 'phone',
      key: 'phone',
      width: 130,
      render: (phone: string) => phone || <Text type="secondary">-</Text>,
    },
    {
      title: 'Email',
      dataIndex: 'email',
      key: 'email',
      width: 180,
      ellipsis: true,
      render: (email: string) =>
        email ? <a href={`mailto:${email}`}>{email}</a> : <Text type="secondary">-</Text>,
    },
    // 註解隱藏: 公文統計欄位 - 因 documents 表的 sender_agency_id/receiver_agency_id 尚未建立關聯
    // 待資料關聯完成後可取消註解
    // {
    //   title: '公文總數',
    //   dataIndex: 'document_count',
    //   key: 'document_count',
    //   width: 90,
    //   align: 'center' as const,
    //   sorter: (a, b) => a.document_count - b.document_count,
    // },
    // {
    //   title: '發文數',
    //   dataIndex: 'sent_count',
    //   key: 'sent_count',
    //   width: 80,
    //   align: 'center' as const,
    // },
    // {
    //   title: '收文數',
    //   dataIndex: 'received_count',
    //   key: 'received_count',
    //   width: 80,
    //   align: 'center' as const,
    // },
    // {
    //   title: '最後活動',
    //   dataIndex: 'last_activity',
    //   key: 'last_activity',
    //   width: 110,
    //   render: (date: string | null) =>
    //     date ? new Date(date).toLocaleDateString('zh-TW') : <Text type="secondary">-</Text>,
    // },
    {
      title: '建立日期',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 110,
      sorter: (a, b) => new Date(a.created_at || 0).getTime() - new Date(b.created_at || 0).getTime(),
      render: (date: string) =>
        date ? new Date(date).toLocaleDateString('zh-TW') : '-',
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      align: 'center' as const,
      fixed: 'right' as const,
      render: (_: unknown, record: AgencyWithStats) => (
        <Popconfirm
          title="確定要刪除此機關單位？"
          description="刪除後將無法復原"
          onConfirm={(e) => {
            e?.stopPropagation();
            handleDelete(record.id);
          }}
          onCancel={(e) => e?.stopPropagation()}
          okText="確定"
          cancelText="取消"
          okButtonProps={{ danger: true }}
        >
          <Tooltip title="刪除">
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => e.stopPropagation()}
            />
          </Tooltip>
        </Popconfirm>
      ),
    },
  ];

  // 篩選後的機關列表
  const filteredAgencies = categoryFilter
    ? agencies.filter(agency => agency.category === categoryFilter)
    : agencies;

  return (
    <div style={{ padding: '24px' }}>
      <div style={{ marginBottom: '24px' }}>
        <Title level={2}>
          <BankOutlined style={{ marginRight: '12px', color: '#1890ff' }} />
          機關單位管理
        </Title>
        <Text type="secondary">
          統計和管理公文往來的所有機關單位資訊
        </Text>
      </div>

      {/* 統計卡片 */}
      {statistics && (
        <Row gutter={16} style={{ marginBottom: '24px' }}>
          <Col span={6}>
            <Card>
              <Statistic
                title="機關總數"
                value={statistics.total_agencies}
                prefix={<BankOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Card>
          </Col>
          {statistics.categories.slice(0, 3).map((cat, index) => (
            <Col span={6} key={cat.category}>
              <Card>
                <Statistic
                  title={cat.category}
                  value={cat.count}
                  suffix={`(${cat.percentage}%)`}
                  prefix={getCategoryIcon(cat.category)}
                  valueStyle={{ color: ['#1890ff', '#722ed1', '#fa541c'][index] }}
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}

      {/* 搜尋和篩選 */}
      <Card style={{ marginBottom: '24px' }}>
        <Row gutter={16} align="middle">
          <Col flex="1">
            <Search
              placeholder="搜尋機關名稱..."
              allowClear
              enterButton={<SearchOutlined />}
              size="large"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onSearch={handleSearch}
              style={{ maxWidth: '400px' }}
            />
          </Col>
          <Col>
            <Select
              placeholder="選擇機關類別"
              allowClear
              value={categoryFilter || undefined}
              onChange={setCategoryFilter}
              style={{ width: '160px' }}
              options={statistics?.categories.map(cat => ({
                label: `${cat.category} (${cat.count})`,
                value: cat.category,
              })) || []}
            />
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
                loading={loading}
              >
                重新載入
              </Button>
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={handleAdd}
              >
                新增機關
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 機關列表 */}
      <Card>
        <Table
          columns={columns}
          dataSource={filteredAgencies}
          rowKey="id"
          loading={loading}
          pagination={false}
          scroll={{ x: 1120 }}
          size="middle"
          tableLayout="fixed"
          onRow={(record) => ({
            onClick: () => handleEdit(record),
            style: { cursor: 'pointer' },
          })}
          style={{ marginBottom: '16px' }}
        />

        {/* 自訂分頁 */}
        <div style={{ textAlign: 'center', marginTop: '16px' }}>
          <Pagination
            current={currentPage}
            total={totalAgencies}
            pageSize={pageSize}
            showSizeChanger={false}
            showQuickJumper
            showTotal={(total, range) =>
              `第 ${range[0]}-${range[1]} 項，共 ${total} 個機關`
            }
            onChange={handlePageChange}
          />
        </div>
      </Card>

      {/* 新增/編輯 Modal */}
      <Modal
        title={editingAgency ? '編輯機關單位' : '新增機關單位'}
        open={modalVisible}
        onCancel={() => {
          setModalVisible(false);
          form.resetFields();
          setEditingAgency(null);
        }}
        footer={null}
        width={600}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="agency_name"
                label="機關名稱"
                rules={[{ required: true, message: '請輸入機關名稱' }]}
              >
                <Input placeholder="請輸入機關全名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="agency_short_name"
                label="機關簡稱"
                tooltip="可用於公文顯示的簡短名稱"
              >
                <Input placeholder="請輸入機關簡稱" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="agency_code"
                label="機關代碼"
              >
                <Input placeholder="請輸入機關代碼" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="agency_type"
                label="機關類型"
              >
                <Select
                  placeholder="請選擇機關類型"
                  options={AGENCY_TYPE_OPTIONS}
                  allowClear
                />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="contact_person"
                label="聯絡人"
              >
                <Input placeholder="請輸入聯絡人姓名" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="phone"
                label="電話"
              >
                <Input placeholder="請輸入聯絡電話" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="email"
            label="Email"
            rules={[{ type: 'email', message: '請輸入有效的 Email' }]}
          >
            <Input placeholder="請輸入 Email" />
          </Form.Item>

          <Form.Item
            name="address"
            label="地址"
          >
            <Input.TextArea rows={2} placeholder="請輸入地址" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button onClick={() => setModalVisible(false)}>
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={submitLoading}>
                {editingAgency ? '更新' : '建立'}
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};
