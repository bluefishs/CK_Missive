import React, { useState, useEffect, useMemo } from 'react';
import {
  Card, Table, Tabs, Button, Space, Typography, Row, Col,
  Statistic, Alert, Select, Tag, App,
  Tooltip, Badge, Switch, Collapse
} from 'antd';
import {
  DatabaseOutlined, TableOutlined, ReloadOutlined,
  NodeExpandOutlined, TranslationOutlined, LinkOutlined,
  BranchesOutlined, InfoCircleOutlined, EyeOutlined
} from '@ant-design/icons';
import { apiClient } from '../../api/client';
import { databaseMetadata, TableMetadataItem } from '../../config/databaseMetadata';

const { Title, Text } = Typography;
const { Panel } = Collapse;

interface DatabaseInfo {
  name: string;
  size: string;
  tables: TableInfo[];
  totalRecords: number;
  status: string;
}

interface TableInfo {
  name: string;
  recordCount: number;
  columns: ColumnInfo[];
  size: string;
  lastModified: string;
}

interface ColumnInfo {
  name: string;
  type: string;
  nullable: boolean;
  primaryKey: boolean;
}

export const EnhancedDatabaseViewer: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [databaseInfo, setDatabaseInfo] = useState<DatabaseInfo | null>(null);
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [viewMode, setViewMode] = useState<'overview' | 'relations' | 'mapping'>('overview');
  const [showChineseNames, setShowChineseNames] = useState(true);
  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  // 獲取資料庫信息
  const fetchDatabaseInfo = async () => {
    setLoading(true);
    try {
      const data = await apiClient.post<DatabaseInfo>('/admin/database/info', {});
      setDatabaseInfo(data);
      message.success('資料庫信息載入成功');
    } catch (error) {
      console.error('獲取資料庫信息失敗:', error);
      message.error('獲取資料庫信息失敗');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatabaseInfo();
  }, []);

  // 增強表格資料，加入中文資訊
  const enhancedTables = useMemo(() => {
    if (!databaseInfo?.tables) return [];

    return databaseInfo.tables.map(table => {
      const metadata = databaseMetadata.table_metadata[table.name] as TableMetadataItem | undefined;
      return {
        ...table,
        chinese_name: metadata?.chinese_name || table.name,
        description: metadata?.description || '無描述',
        category: metadata?.category || 'unknown',
        frontend_pages: metadata?.frontend_pages || [],
        relationships: metadata?.relationships || [],
        categoryInfo: databaseMetadata.categories[metadata?.category || 'unknown'] || {
          chinese_name: '未分類',
          description: '未分類的資料表',
          color: '#999999',
          icon: 'QuestionOutlined'
        }
      };
    });
  }, [databaseInfo]);

  // 按分類篩選表格
  const filteredTables = useMemo(() => {
    if (selectedCategory === 'all') return enhancedTables;
    return enhancedTables.filter(table => table.category === selectedCategory);
  }, [enhancedTables, selectedCategory]);

  // 生成關聯圖資料 (reserved for future use)
  const _relationshipData = useMemo(() => {
    const nodes: any[] = [];
    const edges: any[] = [];

    enhancedTables.forEach(table => {
      nodes.push({
        key: table.name,
        title: showChineseNames ? table.chinese_name : table.name,
        category: table.category,
        records: table.recordCount,
        color: table.categoryInfo.color
      });

      table.relationships.forEach((rel: any) => {
        edges.push({
          source: table.name,
          target: rel.table,
          type: rel.type,
          description: rel.description
        });
      });
    });

    return { nodes, edges };
  }, [enhancedTables, showChineseNames]);

  // 渲染表格概覽
  const renderTableOverview = () => {
    const columns = [
      {
        title: '表格名稱',
        dataIndex: 'name',
        key: 'name',
        render: (name: string, record: any) => (
          <Space direction="vertical" size="small">
            <Space>
              <Button
                type="link"
                onClick={() => setSelectedTable(name)}
                style={{ padding: 0, fontWeight: 'bold' }}
              >
                <TableOutlined />
                {showChineseNames ? record.chinese_name : name}
              </Button>
              <Tag color={record.categoryInfo.color} style={{ fontSize: '12px' }}>
                {record.categoryInfo.chinese_name}
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
        width: '30%'
      },
      {
        title: '記錄數量',
        dataIndex: 'recordCount',
        key: 'recordCount',
        render: (count: number) => (
          <Badge count={count} style={{ backgroundColor: '#52c41a' }} />
        ),
        width: '12%'
      },
      {
        title: '關聯數量',
        key: 'relationshipCount',
        render: (record: any) => (
          <Space>
            <Badge
              count={record.relationships.length}
              style={{ backgroundColor: '#1976d2' }}
            />
            <Tooltip title="檢視關聯">
              <Button
                type="text"
                size="small"
                icon={<BranchesOutlined />}
                onClick={() => {
                  setSelectedTable(record.name);
                  setViewMode('relations');
                }}
              />
            </Tooltip>
          </Space>
        ),
        width: '12%'
      },
      {
        title: '前端頁面',
        key: 'frontend_pages',
        render: (record: any) => (
          <Space direction="vertical" size="small">
            {record.frontend_pages.length === 0 ? (
              <Text type="secondary">無對應頁面</Text>
            ) : (
              record.frontend_pages.map((page: string, index: number) => (
                <Tag key={index} color="blue" style={{ margin: 0 }}>
                  {page}
                </Tag>
              ))
            )}
          </Space>
        ),
        width: '25%'
      },
      {
        title: '資料大小',
        dataIndex: 'size',
        key: 'size',
        render: (size: string) => <Tag color="green">{size}</Tag>,
        width: '10%'
      },
      {
        title: '操作',
        key: 'actions',
        render: (record: any) => (
          <Space>
            <Tooltip title="檢視資料">
              <Button
                type="text"
                size="small"
                icon={<EyeOutlined />}
                onClick={() => setSelectedTable(record.name)}
              />
            </Tooltip>
            <Tooltip title="檢視關聯">
              <Button
                type="text"
                size="small"
                icon={<BranchesOutlined />}
                onClick={() => {
                  setSelectedTable(record.name);
                  setViewMode('relations');
                }}
              />
            </Tooltip>
          </Space>
        ),
        width: '11%'
      }
    ];

    return (
      <div>
        <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Select
              value={selectedCategory}
              onChange={setSelectedCategory}
              style={{ width: 200 }}
              placeholder="選擇分類"
            >
              <Select.Option value="all">全部分類</Select.Option>
              {Object.entries(databaseMetadata.categories).map(([key, cat]) => (
                <Select.Option key={key} value={key}>
                  <Tag color={cat.color} style={{ marginRight: 4 }}>
                    {cat.chinese_name}
                  </Tag>
                </Select.Option>
              ))}
            </Select>

            <Space>
              <Text>中文顯示:</Text>
              <Switch
                checked={showChineseNames}
                onChange={setShowChineseNames}
                checkedChildren="中"
                unCheckedChildren="英"
              />
            </Space>
          </Space>

          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={fetchDatabaseInfo}
              loading={loading}
            >
              重新整理
            </Button>
          </Space>
        </Space>

        <Table
          columns={columns}
          dataSource={filteredTables}
          size="small"
          pagination={false}
          rowKey="name"
          expandable={{
            expandedRowRender: (record) => {
              const metadata = databaseMetadata.table_metadata[record.name] as TableMetadataItem | undefined;
              return (
                <div style={{ padding: '8px 0' }}>
                  <Collapse size="small" ghost>
                    <Panel header="欄位詳細資訊" key="columns">
                      <Row gutter={[8, 8]}>
                        {record.columns.map((col: ColumnInfo) => {
                          const colMetadata = metadata?.columns?.[col.name];
                          return (
                            <Col key={col.name} span={8}>
                              <Card size="small" style={{ height: '100%' }}>
                                <Space direction="vertical" size="small" style={{ width: '100%' }}>
                                  <Space>
                                    <Text strong>
                                      {showChineseNames && colMetadata?.chinese_name
                                        ? colMetadata.chinese_name
                                        : col.name}
                                    </Text>
                                    {col.primaryKey && <Tag color="gold" style={{ fontSize: '12px' }}>PK</Tag>}
                                    {!col.nullable && !col.primaryKey && <Tag color="red" style={{ fontSize: '12px' }}>NOT NULL</Tag>}
                                  </Space>
                                  <Text type="secondary" style={{ fontSize: '12px' }}>
                                    {col.type}
                                  </Text>
                                  {colMetadata?.description && (
                                    <Text type="secondary" style={{ fontSize: '11px' }}>
                                      {colMetadata.description}
                                    </Text>
                                  )}
                                </Space>
                              </Card>
                            </Col>
                          );
                        })}
                      </Row>
                    </Panel>
                  </Collapse>
                </div>
              );
            },
            expandIcon: ({ expanded, onExpand, record }) => (
              <Button
                type="text"
                size="small"
                icon={<InfoCircleOutlined />}
                onClick={e => onExpand(record, e)}
                style={{ color: expanded ? '#1976d2' : '#999' }}
              />
            )
          }}
        />
      </div>
    );
  };

  // 渲染關聯圖
  const renderRelationshipView = () => {
    const selectedTableData = enhancedTables.find(t => t.name === selectedTable);

    if (!selectedTableData) {
      return (
        <Alert
          message="請選擇一個資料表查看其關聯關係"
          type="info"
          showIcon
        />
      );
    }

    return (
      <div>
        <Card title={`${selectedTableData.chinese_name} (${selectedTableData.name}) - 關聯關係`}>
          <Row gutter={16}>
            <Col span={12}>
              <Title level={5}>
                <LinkOutlined /> 對外關聯 ({selectedTableData.relationships.length})
              </Title>
              {selectedTableData.relationships.length === 0 ? (
                <Alert message="此表格沒有定義對外關聯" type="info" />
              ) : (
                <Space direction="vertical" style={{ width: '100%' }}>
                  {selectedTableData.relationships.map((rel: any, index: number) => {
                    const targetTable = enhancedTables.find(t => t.name === rel.table);
                    return (
                      <Card key={index} size="small">
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Space>
                            <Tag color="blue">{rel.type.replace('_', ' ')}</Tag>
                            <Button
                              type="link"
                              onClick={() => setSelectedTable(rel.table)}
                              style={{ padding: 0 }}
                            >
                              {targetTable?.chinese_name || rel.table}
                            </Button>
                          </Space>
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            {rel.description}
                          </Text>
                          {rel.foreign_key && (
                            <Text code style={{ fontSize: '11px' }}>
                              外鍵: {rel.foreign_key}
                            </Text>
                          )}
                        </Space>
                      </Card>
                    );
                  })}
                </Space>
              )}
            </Col>

            <Col span={12}>
              <Title level={5}>
                <BranchesOutlined /> 被關聯
              </Title>
              {(() => {
                const incomingRelations = enhancedTables.filter(table =>
                  table.relationships.some(rel => rel.table === selectedTableData.name)
                ).map(table => ({
                  ...table,
                  relation: table.relationships.find(rel => rel.table === selectedTableData.name)
                }));

                return incomingRelations.length === 0 ? (
                  <Alert message="沒有其他表格關聯到此表格" type="info" />
                ) : (
                  <Space direction="vertical" style={{ width: '100%' }}>
                    {incomingRelations.map((item: any, index: number) => (
                      <Card key={index} size="small">
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Space>
                            <Tag color="green">{item.relation.type.replace('_', ' ')}</Tag>
                            <Button
                              type="link"
                              onClick={() => setSelectedTable(item.name)}
                              style={{ padding: 0 }}
                            >
                              {item.chinese_name}
                            </Button>
                          </Space>
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            {item.relation.description}
                          </Text>
                        </Space>
                      </Card>
                    ))}
                  </Space>
                );
              })()}
            </Col>
          </Row>
        </Card>
      </div>
    );
  };

  // 渲染系統對應
  const renderSystemMapping = () => {
    const categoryGroups = enhancedTables.reduce((groups: any, table) => {
      const category = table.category;
      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(table);
      return groups;
    }, {});

    return (
      <div>
        <Title level={4}>
          <NodeExpandOutlined /> 系統架構對應圖
        </Title>

        <Collapse>
          {Object.entries(categoryGroups).map(([category, tables]: [string, any]) => {
            const categoryInfo = databaseMetadata.categories[category as keyof typeof databaseMetadata.categories];
            return (
              <Panel
                key={category}
                header={
                  <Space>
                    <Tag color={categoryInfo?.color}>{categoryInfo?.chinese_name}</Tag>
                    <Badge count={tables.length} style={{ backgroundColor: categoryInfo?.color }} />
                    <Text type="secondary">{categoryInfo?.description}</Text>
                  </Space>
                }
              >
                <Row gutter={[16, 16]}>
                  {tables.map((table: any) => (
                    <Col key={table.name} span={8}>
                      <Card
                        size="small"
                        title={table.chinese_name}
                        extra={
                          <Badge count={table.recordCount} style={{ backgroundColor: '#52c41a' }} />
                        }
                        style={{ height: '100%' }}
                      >
                        <Space direction="vertical" style={{ width: '100%' }}>
                          <Text type="secondary" style={{ fontSize: '12px' }}>
                            {table.description}
                          </Text>

                          {table.frontend_pages.length > 0 && (
                            <div>
                              <Text strong style={{ fontSize: '12px' }}>前端頁面:</Text>
                              <div style={{ marginTop: 4 }}>
                                {table.frontend_pages.map((page: string, idx: number) => (
                                  <Tag key={idx} color="blue" style={{ margin: '2px', fontSize: '12px' }}>
                                    {page}
                                  </Tag>
                                ))}
                              </div>
                            </div>
                          )}

                          {table.relationships.length > 0 && (
                            <div>
                              <Text strong style={{ fontSize: '12px' }}>關聯數量:</Text>
                              <Badge
                                count={table.relationships.length}
                                style={{ backgroundColor: '#1976d2', marginLeft: 8 }}
                              />
                            </div>
                          )}
                        </Space>
                      </Card>
                    </Col>
                  ))}
                </Row>
              </Panel>
            );
          })}
        </Collapse>
      </div>
    );
  };

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      <div style={{ maxWidth: 1600, margin: '0 auto' }}>

        {/* 頁面標題 */}
        <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
          <Col>
            <Title level={2} style={{ margin: 0, color: '#1976d2' }}>
              <DatabaseOutlined style={{ marginRight: 12 }} />
              增強型資料庫管理
            </Title>
            <Text type="secondary">
              包含關聯圖、中英文對照、前端頁面對應的完整資料庫檢視工具
            </Text>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<TranslationOutlined />}
                onClick={() => setShowChineseNames(!showChineseNames)}
                type={showChineseNames ? 'primary' : 'default'}
              >
                {showChineseNames ? '中文模式' : '英文模式'}
              </Button>
            </Space>
          </Col>
        </Row>

        {/* 資料庫統計 */}
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
                  title="分類數量"
                  value={Object.keys(databaseMetadata.categories).length}
                  prefix={<BranchesOutlined style={{ color: '#722ed1' }} />}
                />
              </Card>
            </Col>
          </Row>
        )}

        {/* 主要內容 */}
        <Card>
          <Tabs
            activeKey={viewMode}
            onChange={(key: any) => setViewMode(key)}
            size="large"
            items={[
              {
                key: 'overview',
                label: (
                  <Space>
                    <TableOutlined />
                    資料表總覽
                  </Space>
                ),
                children: renderTableOverview()
              },
              {
                key: 'relations',
                label: (
                  <Space>
                    <BranchesOutlined />
                    關聯關係
                  </Space>
                ),
                children: renderRelationshipView()
              },
              {
                key: 'mapping',
                label: (
                  <Space>
                    <NodeExpandOutlined />
                    系統對應
                  </Space>
                ),
                children: renderSystemMapping()
              }
            ]}
          />
        </Card>

      </div>
    </div>
  );
};