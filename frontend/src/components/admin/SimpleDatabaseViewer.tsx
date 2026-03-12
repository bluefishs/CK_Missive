/**
 * 簡易資料庫檢視器
 * @description 提供資料庫表格概覽、關聯圖和 API 對應表功能
 */
import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Card, Table, Tabs, Button, Space, Typography, Row, Col,
  Statistic, Alert, Tag, App, Tooltip, Badge, Switch, Modal, Descriptions, Divider
} from 'antd';
import {
  DatabaseOutlined, TableOutlined, ReloadOutlined,
  BranchesOutlined, InfoCircleOutlined, EyeOutlined,
  ApiOutlined, LinkOutlined,
  FieldTimeOutlined, FileTextOutlined
} from '@ant-design/icons';
import { apiClient } from '../../api/client';
import { API_ENDPOINTS } from '../../api/endpoints';
import {
  databaseMetadata,
  getCategoryDisplayName,
  getCategoryColor,
  type TableMetadataItem
} from '../../config/databaseMetadata';
import { logger } from '../../utils/logger';
import type { DatabaseInfo, TableInfo } from '../../types/api';

const { Title, Text } = Typography;

/** 增強的表格資訊介面（含中文名稱、分類等） */
interface EnhancedTableInfo extends TableInfo {
  chinese_name: string;
  description: string;
  category: string;
  frontend_pages: string[];
  api_endpoints: string[];
  main_fields: string[];
  color: string;
}

// 使用共享的表格元數據
const tableMetadata = databaseMetadata.table_metadata;

/** Fallback data when API is unreachable */
const FALLBACK_DATABASE_INFO: DatabaseInfo = {
  name: "ck_documents",
  size: "8597 kB",
  status: "healthy",
  totalRecords: 15,
  tables: [
    {
      name: "users",
      recordCount: 2,
      columns: [
        { name: "id", type: "integer", nullable: false, primaryKey: true },
        { name: "email", type: "character varying", nullable: false, primaryKey: false },
        { name: "username", type: "character varying", nullable: false, primaryKey: false }
      ],
      size: "80 kB",
      lastModified: "2024-01-01"
    },
    {
      name: "documents",
      recordCount: 0,
      columns: [
        { name: "id", type: "integer", nullable: false, primaryKey: true },
        { name: "doc_number", type: "character varying", nullable: false, primaryKey: false },
        { name: "subject", type: "character varying", nullable: false, primaryKey: false }
      ],
      size: "72 kB",
      lastModified: "2024-01-01"
    },
    {
      name: "contract_projects",
      recordCount: 0,
      columns: [
        { name: "id", type: "integer", nullable: false, primaryKey: true },
        { name: "project_name", type: "character varying", nullable: false, primaryKey: false }
      ],
      size: "32 kB",
      lastModified: "2024-01-01"
    }
  ]
};

export const SimpleDatabaseViewer: React.FC = () => {
  const { message } = App.useApp();
  const [showChineseNames, setShowChineseNames] = useState(true);
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [showDetails, setShowDetails] = useState(false);
  const [activeTab, setActiveTab] = useState('overview');

  const {
    data: databaseInfo = null,
    isLoading: loading,
    refetch: refetchDatabaseInfo,
  } = useQuery({
    queryKey: ['database-info-enhanced'],
    queryFn: async () => {
      logger.debug('Fetching database info via apiClient');
      try {
        const data = await apiClient.post<DatabaseInfo>(API_ENDPOINTS.ADMIN_DATABASE.INFO, {});
        logger.debug('Database info loaded:', data);
        return data;
      } catch (error) {
        logger.error('獲取資料庫信息失敗:', error);
        logger.debug('Using fallback data for development mode');
        message.warning('使用離線資料模式（API連接失敗）');
        return FALLBACK_DATABASE_INFO;
      }
    },
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const fetchDatabaseInfo = () => {
    refetchDatabaseInfo();
  };

  const enhancedTables = databaseInfo?.tables.map(table => {
    const metadata = tableMetadata[table.name] as TableMetadataItem | undefined;
    const category = metadata?.category || 'unknown';
    return {
      ...table,
      chinese_name: metadata?.chinese_name || table.name,
      description: metadata?.description || '無描述',
      category,
      frontend_pages: metadata?.frontend_pages || [],
      api_endpoints: metadata?.api_endpoints || [],
      main_fields: metadata?.main_fields || [],
      color: getCategoryColor(category)
    };
  }) || [];

  const columns = [
    {
      title: '表格名稱',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: EnhancedTableInfo) => (
        <Space direction="vertical" size="small">
          <Space>
            <TableOutlined style={{ color: record.color }} />
            <Text strong>
              {showChineseNames ? record.chinese_name : name}
            </Text>
            <Tag color={record.color} style={{ fontSize: '12px' }}>
              {record.category}
            </Tag>
          </Space>
          {showChineseNames && name !== record.chinese_name && (
            <Text type="secondary" style={{ fontSize: '12px' }}>{name}</Text>
          )}
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.description}
          </Text>
        </Space>
      ),
      width: '35%'
    },
    {
      title: '記錄數量',
      dataIndex: 'recordCount',
      key: 'recordCount',
      render: (count: number) => (
        <Badge count={count} style={{ backgroundColor: '#52c41a' }} />
      ),
      sorter: (a: EnhancedTableInfo, b: EnhancedTableInfo) => a.recordCount - b.recordCount,
      width: '15%'
    },
    {
      title: '前端頁面 & API',
      key: 'integration',
      render: (_: unknown, record: EnhancedTableInfo) => (
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <div>
            <Text strong style={{ fontSize: '12px', color: '#1976d2' }}>
              <LinkOutlined /> 前端頁面:
            </Text>
            <div style={{ marginTop: 4 }}>
              {record.frontend_pages.length === 0 ? (
                <Text type="secondary" style={{ fontSize: '12px' }}>無對應頁面</Text>
              ) : (
                record.frontend_pages.slice(0, 2).map((page: string, index: number) => (
                  <Tag key={index} color="blue" style={{ margin: '1px 2px', fontSize: '11px' }}>
                    {page}
                  </Tag>
                ))
              )}
              {record.frontend_pages.length > 2 && (
                <Tag style={{ fontSize: '11px' }}>+{record.frontend_pages.length - 2}</Tag>
              )}
            </div>
          </div>
          <div>
            <Text strong style={{ fontSize: '12px', color: '#52c41a' }}>
              <ApiOutlined /> API 端點:
            </Text>
            <div style={{ marginTop: 4 }}>
              {record.api_endpoints.length === 0 ? (
                <Text type="secondary" style={{ fontSize: '12px' }}>無API端點</Text>
              ) : (
                record.api_endpoints.slice(0, 2).map((api: string, index: number) => (
                  <Tag key={index} color="green" style={{ margin: '1px 2px', fontSize: '11px' }}>
                    {api.split(' ')[0]} {api.split(' ')[1]?.split('/').slice(-1)[0] || '/'}
                  </Tag>
                ))
              )}
              {record.api_endpoints.length > 2 && (
                <Tag style={{ fontSize: '11px' }}>+{record.api_endpoints.length - 2}</Tag>
              )}
            </div>
          </div>
        </Space>
      ),
      width: '35%'
    },
    {
      title: '資料大小',
      dataIndex: 'size',
      key: 'size',
      render: (size: string) => <Tag color="green">{size}</Tag>,
      width: '12%'
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: EnhancedTableInfo) => (
        <Tooltip title="檢視詳細資訊">
          <Button
            type="text"
            size="small"
            icon={<EyeOutlined />}
            onClick={() => {
              setSelectedTable(record.name);
              setShowDetails(true);
            }}
            aria-label="檢視詳細資訊"
          />
        </Tooltip>
      ),
      width: '8%'
    }
  ];

  return (
    <div style={{ padding: '24px' }}>
      {/* 標題區 */}
      <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
        <Col>
          <Title level={3} style={{ margin: 0, color: '#1976d2' }}>
            <DatabaseOutlined style={{ marginRight: 12 }} />
            增強型資料庫檢視
          </Title>
          <Text type="secondary">
            包含中英文對照、前端頁面對應的資料庫管理工具
          </Text>
        </Col>
        <Col>
          <Space>
            <Space>
              <Text>中文顯示:</Text>
              <Switch
                checked={showChineseNames}
                onChange={setShowChineseNames}
                checkedChildren="中"
                unCheckedChildren="英"
              />
            </Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchDatabaseInfo}
              loading={loading}
            >
              重新整理
            </Button>
          </Space>
        </Col>
      </Row>

      {/* 統計資訊 */}
      {databaseInfo && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={12} md={6}>
            <Card>
              <Statistic
                title="資料庫大小"
                value={databaseInfo.size}
                prefix={<DatabaseOutlined style={{ color: '#1976d2' }} />}
              />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card>
              <Statistic
                title="資料表數量"
                value={enhancedTables.length}
                prefix={<TableOutlined style={{ color: '#52c41a' }} />}
              />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card>
              <Statistic
                title="總記錄數"
                value={databaseInfo.totalRecords}
                prefix={<InfoCircleOutlined style={{ color: '#faad14' }} />}
              />
            </Card>
          </Col>
          <Col xs={12} md={6}>
            <Card>
              <Statistic
                title="有前端對應"
                value={enhancedTables.filter(t => t.frontend_pages.length > 0).length}
                prefix={<BranchesOutlined style={{ color: '#722ed1' }} />}
              />
            </Card>
          </Col>
        </Row>
      )}

      {/* 主內容區域 */}
      <Card>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="large"
          items={[
            {
              key: 'overview',
              label: <span><TableOutlined />表格概覽</span>,
              children: (
                <div>
                  <Alert
                    message="增強型資料庫檢視"
                    description="提供表格中英文對照、前端頁面對應關係、API端點資訊以及分類色彩標示功能"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />

                  <Table
                    columns={columns}
                    dataSource={enhancedTables}
                    size="small"
                    pagination={{ pageSize: 20 }}
                    rowKey="name"
                    loading={loading}
                    scroll={{ x: 900 }}
                    expandable={{
                      expandedRowRender: (record) => (
                        <div style={{ padding: '16px', background: '#fafafa' }}>
                          <Row gutter={[16, 16]}>
                            <Col span={8}>
                              <Card size="small" title="主要欄位" styles={{ header: { background: '#e6f7ff' } }}>
                                <Space wrap>
                                  {record.main_fields.map((field: string, index: number) => (
                                    <Tag key={index} color="cyan" style={{ margin: '2px' }}>
                                      <FieldTimeOutlined style={{ marginRight: 4 }} />
                                      {field}
                                    </Tag>
                                  ))}
                                </Space>
                              </Card>
                            </Col>
                            <Col span={8}>
                              <Card size="small" title="API 端點詳情" styles={{ header: { background: '#f6ffed' } }}>
                                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                                  {record.api_endpoints.map((api: string, index: number) => (
                                    <Tag key={index} color="green" style={{ width: '100%', textAlign: 'left' }}>
                                      <ApiOutlined style={{ marginRight: 4 }} />
                                      {api}
                                    </Tag>
                                  ))}
                                </Space>
                              </Card>
                            </Col>
                            <Col span={8}>
                              <Card size="small" title="關聯頁面" styles={{ header: { background: '#fff7e6' } }}>
                                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                                  {record.frontend_pages.map((page: string, index: number) => (
                                    <Tag key={index} color="blue" style={{ width: '100%', textAlign: 'left' }}>
                                      <FileTextOutlined style={{ marginRight: 4 }} />
                                      {page}
                                    </Tag>
                                  ))}
                                </Space>
                              </Card>
                            </Col>
                          </Row>
                        </div>
                      ),
                      rowExpandable: (record) => record.main_fields.length > 0 || record.api_endpoints.length > 0
                    }}
                  />
                </div>
              )
            },
            {
              key: 'relations',
              label: <span><BranchesOutlined />關聯圖</span>,
              children: (
                <div>
                  <Alert
                    message="資料表關聯分析"
                    description="顯示各資料表之間的關聯關係以及與前端、API的對應情況"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  {renderRelationView()}
                </div>
              )
            },
            {
              key: 'api-mapping',
              label: <span><ApiOutlined />API 對應表</span>,
              children: (
                <div>
                  <Alert
                    message="API 端點對應關係"
                    description="完整的前端功能與後端API端點對應關係表"
                    type="info"
                    showIcon
                    style={{ marginBottom: 16 }}
                  />
                  {renderApiMappingView()}
                </div>
              )
            }
          ]}
        />
      </Card>

      {/* 表格詳情Modal */}
      <Modal
        title={`${selectedTable} 詳細資訊`}
        open={showDetails}
        onCancel={() => setShowDetails(false)}
        footer={null}
        width={800}
      >
        {selectedTable && renderTableDetailModal(selectedTable)}
      </Modal>
    </div>
  );

  // 渲染關聯圖檢視
  function renderRelationView() {
    const categorizedTables = enhancedTables.reduce<Record<string, EnhancedTableInfo[]>>((acc, table) => {
      const category = table.category;
      if (!acc[category]) {
        acc[category] = [];
      }
      acc[category]!.push(table);  // Non-null assertion: 前一行已確保存在
      return acc;
    }, {});

    return (
      <Row gutter={[16, 16]}>
        {Object.entries(categorizedTables).map(([category, tables]) => (
          <Col span={8} key={category}>
            <Card
              title={getCategoryDisplayName(category)}
              styles={{ header: { background: getCategoryColor(category), color: 'white' } }}
              size="small"
            >
              <Space direction="vertical" style={{ width: '100%' }}>
                {tables.map((table, index: number) => (
                  <Card key={index} size="small" style={{ background: '#fafafa' }}>
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      <Text strong>{showChineseNames ? table.chinese_name : table.name}</Text>
                      <Text type="secondary" style={{ fontSize: '12px' }}>{table.description}</Text>
                      <div>
                        <Badge count={table.recordCount} style={{ backgroundColor: '#52c41a' }} />
                        <Text type="secondary" style={{ marginLeft: 8, fontSize: '12px' }}>
                          {table.api_endpoints.length} API, {table.frontend_pages.length} 頁面
                        </Text>
                      </div>
                    </Space>
                  </Card>
                ))}
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    );
  }

  // 渲染API對應檢視
  function renderApiMappingView() {
    interface ApiMappingItem {
      table_name: string;
      chinese_name: string;
      api_endpoint: string;
      frontend_pages: string[];
      category: string;
    }
    const apiMappings: ApiMappingItem[] = [];

    enhancedTables.forEach(table => {
      table.api_endpoints.forEach((api: string) => {
        apiMappings.push({
          table_name: table.name,
          chinese_name: table.chinese_name,
          api_endpoint: api,
          frontend_pages: table.frontend_pages,
          category: table.category
        });
      });
    });

    const apiColumns = [
      {
        title: '資料表',
        dataIndex: 'chinese_name',
        key: 'chinese_name',
        render: (text: string, record: ApiMappingItem) => (
          <Space direction="vertical" size="small">
            <Text strong>{showChineseNames ? text : record.table_name}</Text>
            <Tag color={getCategoryColor(record.category)} style={{ fontSize: '12px' }}>{record.category}</Tag>
          </Space>
        )
      },
      {
        title: 'API 端點',
        dataIndex: 'api_endpoint',
        key: 'api_endpoint',
        render: (api: string) => {
          const [method, path] = api.split(' ');
          return (
            <Space>
              <Tag color={method === 'GET' ? 'blue' : method === 'POST' ? 'green' : method === 'PUT' ? 'orange' : 'red'}>
                {method}
              </Tag>
              <Text code>{path}</Text>
            </Space>
          );
        }
      },
      {
        title: '對應前端頁面',
        dataIndex: 'frontend_pages',
        key: 'frontend_pages',
        render: (pages: string[]) => (
          <Space wrap>
            {pages.map((page, index) => (
              <Tag key={index} color="blue" style={{ fontSize: '12px' }}>{page}</Tag>
            ))}
          </Space>
        )
      }
    ];

    return (
      <Table
        columns={apiColumns}
        dataSource={apiMappings}
        size="small"
        pagination={{ pageSize: 30 }}
        rowKey={(record, index) => `${record.table_name}-${index}`}
      />
    );
  }

  // 渲染表格詳情Modal內容
  function renderTableDetailModal(tableName: string) {
    const table = enhancedTables.find(t => t.name === tableName);
    if (!table) return null;

    return (
      <div>
        <Descriptions title="基本資訊" bordered size="small" column={2}>
          <Descriptions.Item label="中文名稱">{table.chinese_name}</Descriptions.Item>
          <Descriptions.Item label="英文名稱">{table.name}</Descriptions.Item>
          <Descriptions.Item label="資料表類型">
            <Tag color={table.color}>{table.category}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="記錄數量">
            <Badge count={table.recordCount} style={{ backgroundColor: '#52c41a' }} />
          </Descriptions.Item>
          <Descriptions.Item label="資料大小">{table.size}</Descriptions.Item>
          <Descriptions.Item label="最後修改">{table.lastModified}</Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>{table.description}</Descriptions.Item>
        </Descriptions>

        <Divider orientation="left">主要欄位</Divider>
        <Space wrap>
          {table.main_fields.map((field: string, index: number) => (
            <Tag key={index} color="cyan">
              <FieldTimeOutlined style={{ marginRight: 4 }} />
              {field}
            </Tag>
          ))}
        </Space>

        <Divider orientation="left">API 端點</Divider>
        <Space direction="vertical" style={{ width: '100%' }}>
          {table.api_endpoints.map((api: string, index: number) => {
            const [method, path] = api.split(' ');
            return (
              <Card key={index} size="small">
                <Space>
                  <Tag color={method === 'GET' ? 'blue' : method === 'POST' ? 'green' : method === 'PUT' ? 'orange' : 'red'}>
                    {method}
                  </Tag>
                  <Text code>{path}</Text>
                </Space>
              </Card>
            );
          })}
        </Space>

        <Divider orientation="left">關聯前端頁面</Divider>
        <Space wrap>
          {table.frontend_pages.map((page: string, index: number) => (
            <Tag key={index} color="blue">
              <FileTextOutlined style={{ marginRight: 4 }} />
              {page}
            </Tag>
          ))}
        </Space>
      </div>
    );
  }
};