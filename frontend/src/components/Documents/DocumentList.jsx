import React, { useState, useEffect, useCallback } from 'react';
import { Table, Card, Tabs, Tag, Button, Space, message, Popconfirm, Tooltip } from 'antd';
import { EditOutlined, DeleteOutlined, EyeOutlined, ReloadOutlined } from '@ant-design/icons';
import { documentAPI } from '../services/documentAPI';
import moment from 'moment';

const { TabPane } = Tabs;

const DocumentList = ({ refreshTrigger, onEdit, onView }) => {
  const [loading, setLoading] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 50,
    total: 0,
  });
  const [activeTab, setActiveTab] = useState('all');
  const [filters, setFilters] = useState({});

  // 載入文件列表
  const loadDocuments = useCallback(async (page = 1, pageSize = 50, category = null) => {
    setLoading(true);
    try {
      const params = {
        page,
        per_page: pageSize,
        ...filters,
      };
      
      if (category && category !== 'all') {
        params.category = category;
      }

      const result = await documentAPI.getDocuments(params);
      
      setDocuments(result.documents);
      setPagination({
        current: page,
        pageSize: pageSize,
        total: result.total,
      });
    } catch (error) {
      console.error('載入文件列表失敗:', error);
      message.error('載入文件列表失敗');
    } finally {
      setLoading(false);
    }
  }, [filters]);

  // 初始載入
  useEffect(() => {
    loadDocuments(1, 50, activeTab);
  }, [loadDocuments, activeTab, refreshTrigger]);

  // 刪除文件
  const handleDelete = async (id) => {
    try {
      await documentAPI.deleteDocument(id);
      message.success('刪除成功');
      loadDocuments(pagination.current, pagination.pageSize, activeTab);
    } catch (error) {
      console.error('刪除失敗:', error);
      message.error('刪除失敗');
    }
  };

  // 分頁變更
  const handleTableChange = (paginationInfo) => {
    loadDocuments(paginationInfo.current, paginationInfo.pageSize, activeTab);
  };

  // 標籤變更
  const handleTabChange = (key) => {
    setActiveTab(key);
    setPagination({ ...pagination, current: 1 });
  };

  // 刷新
  const handleRefresh = () => {
    loadDocuments(pagination.current, pagination.pageSize, activeTab);
  };

  // 表格欄位定義
  const columns = [
    {
      title: '流水號',
      dataIndex: 'auto_serial',
      key: 'auto_serial',
      width: 100,
      sorter: true,
    },
    {
      title: '公文文號',
      dataIndex: 'doc_number',
      key: 'doc_number',
      width: 180,
      ellipsis: true,
    },
    {
      title: '分類',
      dataIndex: 'category',
      key: 'category',
      width: 80,
      render: (category) => (
        <Tag color={category === 'receive' ? 'blue' : 'green'}>
          {category === 'receive' ? '收文' : '發文'}
        </Tag>
      ),
    },
    {
      title: '主旨',
      dataIndex: 'subject',
      key: 'subject',
      ellipsis: true,
      render: (text) => (
        <Tooltip title={text}>
          <span>{text}</span>
        </Tooltip>
      ),
    },
    {
      title: '發文機關',
      dataIndex: 'sender',
      key: 'sender',
      width: 150,
      ellipsis: true,
    },
    {
      title: '收文機關',
      dataIndex: 'receiver',
      key: 'receiver',
      width: 150,
      ellipsis: true,
    },
    {
      title: '公文日期',
      dataIndex: 'doc_date',
      key: 'doc_date',
      width: 120,
      render: (date) => date ? moment(date).format('YYYY-MM-DD') : '-',
    },
    {
      title: '承攬案件',
      dataIndex: 'contract_case',
      key: 'contract_case',
      width: 150,
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      fixed: 'right',
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="檢視">
            <Button
              type="text"
              icon={<EyeOutlined />}
              onClick={() => onView && onView(record)}
              size="small"
            />
          </Tooltip>
          <Tooltip title="編輯">
            <Button
              type="text"
              icon={<EditOutlined />}
              onClick={() => onEdit && onEdit(record)}
              size="small"
            />
          </Tooltip>
          <Popconfirm
            title="確定要刪除這筆資料嗎？"
            onConfirm={() => handleDelete(record.id)}
            okText="確定"
            cancelText="取消"
          >
            <Tooltip title="刪除">
              <Button
                type="text"
                icon={<DeleteOutlined />}
                danger
                size="small"
              />
            </Tooltip>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <Card 
      title="公文列表"
      extra={
        <Button
          icon={<ReloadOutlined />}
          onClick={handleRefresh}
          loading={loading}
        >
          刷新
        </Button>
      }
    >
      <Tabs activeKey={activeTab} onChange={handleTabChange}>
        <TabPane tab="全部" key="all" />
        <TabPane tab="收文" key="receive" />
        <TabPane tab="發文" key="send" />
      </Tabs>

      <Table
        columns={columns}
        dataSource={documents}
        rowKey="id"
        loading={loading}
        pagination={{
          ...pagination,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total, range) => 
            `第 ${range[0]}-${range[1]} 筆，共 ${total} 筆`,
          pageSizeOptions: ['20', '50', '100', '200'],
        }}
        onChange={handleTableChange}
        scroll={{ x: 1200 }}
        size="middle"
      />
    </Card>
  );
};

export default DocumentList;
