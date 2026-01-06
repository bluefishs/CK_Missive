import React, { useState, useEffect } from 'react';
import {
  Card, Table, Tabs, Button, Space, Typography, Row, Col,
  Statistic, Alert, Modal, Input, Select, Tag, App,
  Tooltip, Popconfirm, Divider, Progress, Badge,
  Switch, Drawer
} from 'antd';
import type { ColumnType } from 'antd/es/table';
import {
  DatabaseOutlined, TableOutlined, SearchOutlined, ReloadOutlined,
  ExportOutlined, InfoCircleOutlined, WarningOutlined, CodeOutlined,
  DownloadOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  PlayCircleOutlined, CopyOutlined, EyeOutlined, UpOutlined
} from '@ant-design/icons';
import { API_BASE_URL } from '../api/client';
import { SimpleDatabaseViewer } from '../components/admin/SimpleDatabaseViewer';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

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

export const DatabaseManagementPage: React.FC = () => {
  const { message } = App.useApp();
  const [loading, setLoading] = useState(false);
  const [databaseInfo, setDatabaseInfo] = useState<DatabaseInfo | null>(null);
  const [selectedTable, setSelectedTable] = useState<string>('');
  const [tableData, setTableData] = useState<any>({ columns: [], rows: [] });
  const [customQuery, setCustomQuery] = useState<string>('SELECT * FROM documents LIMIT 10;');
  const [queryResult, setQueryResult] = useState<any>(null);
  const [integrityResult, setIntegrityResult] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<string>('overview');
  const [useEnhancedView, setUseEnhancedView] = useState(false);
  const [enhancedDrawerVisible, setEnhancedDrawerVisible] = useState(false);

  // 獲取資料庫信息
  const fetchDatabaseInfo = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/admin/database/info`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setDatabaseInfo(data);
      message.success('資料庫信息載入成功');
    } catch (error) {
      console.error('獲取資料庫信息失敗:', error);
      message.error('獲取資料庫信息失敗');
    } finally {
      setLoading(false);
    }
  };

  // 獲取表格數據
  const fetchTableData = async (tableName: string, limit: number = 50, offset: number = 0) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/admin/database/table/${tableName}?limit=${limit}&offset=${offset}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setTableData(data);
      setSelectedTable(tableName);
      message.success(`載入 ${tableName} 數據成功`);
    } catch (error) {
      console.error('獲取表格數據失敗:', error);
      message.error('獲取表格數據失敗');
    } finally {
      setLoading(false);
    }
  };

  // 執行 SQL 查詢
  const executeQuery = async () => {
    if (!customQuery.trim()) {
      message.warning('請輸入查詢語句');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/admin/database/query`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: customQuery }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }
      
      const result = await response.json();
      setQueryResult(result);
      message.success(`查詢完成，返回 ${result.totalRows} 條結果，耗時 ${result.executionTime}ms`);
    } catch (error: any) {
      console.error('查詢執行失敗:', error);
      message.error(`查詢執行失敗: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  // 檢查數據完整性
  const checkIntegrity = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/admin/database/integrity`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const result = await response.json();
      setIntegrityResult(result);
      
      if (result.issues.length === 0) {
        message.success('數據完整性檢查通過');
      } else {
        Modal.warning({
          title: '發現數據問題',
          content: (
            <div>
              {result.issues.map((issue: any, index: number) => (
                <div key={index}>
                  <Text type="danger">{issue.table}</Text>: {issue.description}
                </div>
              ))}
            </div>
          )
        });
      }
    } catch (error) {
      console.error('完整性檢查失敗:', error);
      message.error('完整性檢查失敗');
    } finally {
      setLoading(false);
    }
  };

  // 匯出表格數據
  const exportTableData = async (tableName: string) => {
    try {
      message.success(`開始匯出 ${tableName} 數據...`);
      // 實際實現中應該調用後端 API
    } catch (error) {
      message.error('匯出失敗');
    }
  };

  useEffect(() => {
    fetchDatabaseInfo();
  }, []);

  // 渲染表格列表
  const renderTableList = () => {
    const columns = [// 添加類型定義
  
      {
        title: '表格名稱',
        dataIndex: 'name',
        key: 'name',
        render: (name: string) => (
          <Space>
            <Button type="link" onClick={() => fetchTableData(name)} style={{ padding: 0 }}>
              <TableOutlined /> {name}
            </Button>
          </Space>
        )
      },
      {
        title: '記錄數量',
        dataIndex: 'recordCount',
        key: 'recordCount',
        render: (count: number) => (
          <Badge count={count} style={{ backgroundColor: '#52c41a' }} />
        )
      },
      {
        title: '大小',
        dataIndex: 'size',
        key: 'size',
        render: (size: string) => <Tag color="blue">{size}</Tag>
      },
      {
        title: '最後修改',
        dataIndex: 'lastModified',
        key: 'lastModified',
        render: (time: string) => <Text type="secondary">{time}</Text>
      },
      {
        title: '操作',
        key: 'actions',
        render: (_: any, record: TableInfo) => (
          <Space size="small">
            <Tooltip title="查看數據">
              <Button
                type="text"
                size="small"
                icon={<SearchOutlined />}
                onClick={() => fetchTableData(record.name)}
              />
            </Tooltip>
            <Tooltip title="匯出 CSV">
              <Button
                type="text"
                size="small"
                icon={<DownloadOutlined />}
                onClick={() => exportTableData(record.name)}
              />
            </Tooltip>
          </Space>
        )
      }
    ];

    return (
      <Table
        columns={columns}
        dataSource={databaseInfo?.tables || []}
        size="small"
        pagination={false}
        rowKey="name"
      />
    );
  };

  // 渲染表格詳情
  const renderTableDetail = () => {
    if (!selectedTable) {
      return <Alert message="請點擊表格名稱查看詳細數據" type="info" showIcon />;
    }

    const table = databaseInfo?.tables.find(t => t.name === selectedTable);
    if (!table) return null;

    const columns = table.columns.map(col => {
      const baseColumn: ColumnType<any> = {
        title: (
          <Space>
            {col.name}
            {col.primaryKey && <Tag color="gold" style={{ fontSize: '10px' }}>PK</Tag>}
            <Tooltip title={`${col.type}${!col.nullable ? ' (NOT NULL)' : ''}`}>
              <InfoCircleOutlined style={{ color: '#999', fontSize: '12px' }} />
            </Tooltip>
          </Space>
        ),
        dataIndex: col.name,
        key: col.name,
        ellipsis: {
          showTitle: false,
        },
        width: col.type.includes('TEXT') ? 200 : 120,
        render: (text: any) => (
          <Tooltip placement="topLeft" title={text}>
            {text}
          </Tooltip>
        ),
      };

      // 添加排序功能
      if (col.type.includes('INTEGER') || col.type.includes('REAL')) {
        baseColumn.sorter = (a: any, b: any) => {
          const aVal = parseFloat(a[col.name]) || 0;
          const bVal = parseFloat(b[col.name]) || 0;
          return aVal - bVal;
        };
      } else {
        baseColumn.sorter = (a: any, b: any) => {
          const aVal = a[col.name] || '';
          const bVal = b[col.name] || '';
          return aVal.toString().localeCompare(bVal.toString());
        };
      }

      // 添加篩選功能
      if (col.name === 'status' || col.name === 'doc_type' || col.name === 'category') {
        const uniqueValues = [...new Set(tableData.rows.map((row: any[]) => {
          const colIndex = table.columns.findIndex(c => c.name === col.name);
          return row[colIndex];
        }))].filter(Boolean);

        baseColumn.filters = uniqueValues.map(value => ({
          text: String(value),
          value: value as React.Key,
        }));

        baseColumn.onFilter = (value: any, record: any) => record[col.name] === value;
      }

      // 添加搜尋功能
      if (col.type.includes('TEXT') || col.type.includes('VARCHAR')) {
        baseColumn.filterDropdown = ({ setSelectedKeys, selectedKeys, confirm, clearFilters }: any) => (
          <div style={{ padding: 8 }}>
            <Input
              placeholder={`搜尋 ${col.name}`}
              value={selectedKeys[0]}
              onChange={(e) => setSelectedKeys(e.target.value ? [e.target.value] : [])}
              onPressEnter={() => confirm()}
              style={{ marginBottom: 8, display: 'block' }}
            />
            <Space>
              <Button
                type="primary"
                onClick={() => confirm()}
                icon={<SearchOutlined />}
                size="small"
                style={{ width: 90 }}
              >
                搜尋
              </Button>
              <Button onClick={() => clearFilters()} size="small" style={{ width: 90 }}>
                重置
              </Button>
            </Space>
          </div>
        );
        baseColumn.filterIcon = (filtered: boolean) => (
          <SearchOutlined style={{ color: filtered ? '#1890ff' : undefined }} />
        );
        baseColumn.onFilter = (value: any, record: any) =>
          record[col.name] ? record[col.name].toString().toLowerCase().includes(value.toLowerCase()) : false;
      }

      return baseColumn;
    });

    const dataSource = tableData.rows.map((row: any[], index: number) => {
      const obj: any = { key: index };
      table.columns.forEach((col, colIndex) => {
        obj[col.name] = row[colIndex];
      });
      return obj;
    });

    return (
      <div>
        <Space style={{ marginBottom: 16, width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Title level={4} style={{ margin: 0 }}>
              <TableOutlined /> {selectedTable}
            </Title>
            <Tag color="green">{tableData.total || tableData.totalRows} 條記錄</Tag>
            <Tag color="blue">{table.columns.length} 個欄位</Tag>
          </Space>
          <Space>
            <Button
              icon={<ReloadOutlined />}
              onClick={() => fetchTableData(selectedTable)}
              loading={loading}
            >
              重新整理
            </Button>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              onClick={() => exportTableData(selectedTable)}
            >
              匯出 CSV
            </Button>
          </Space>
        </Space>

        <Card size="small" style={{ marginBottom: 16 }}>
          <Title level={5}>表格結構</Title>
          <Row gutter={[8, 8]}>
            {table.columns.map((col) => (
              <Col key={col.name}>
                <Tag color={col.primaryKey ? 'gold' : col.nullable ? 'default' : 'blue'}>
                  {col.name}: {col.type}
                  {col.primaryKey && ' (PK)'}
                  {!col.nullable && !col.primaryKey && ' (NOT NULL)'}
                </Tag>
              </Col>
            ))}
          </Row>
        </Card>

        <Table
          columns={columns}
          dataSource={dataSource}
          size="small"
          scroll={{ x: 'max-content' }}
          pagination={{
            current: tableData.page,
            pageSize: tableData.pageSize || 50,
            total: tableData.total || tableData.totalRows,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => `第 ${range[0]}-${range[1]} 條，共 ${total} 條記錄`,
            onChange: (page, pageSize) => {
              const offset = (page - 1) * pageSize;
              fetchTableData(selectedTable, pageSize, offset);
            },
            onShowSizeChange: (current, size) => {
              fetchTableData(selectedTable, size, 0);
            }
          }}
          loading={loading}
        />
      </div>
    );
  };

  // 渲染 SQL 查詢工具
  const renderQueryTool = () => (
    <Space direction="vertical" style={{ width: '100%' }}>
      <Alert
        message="SQL 查詢工具"
        description="僅支援 SELECT 查詢，禁止 DROP、DELETE、INSERT、UPDATE 等危險操作"
        type="info"
        showIcon
      />

      <div>
        <Space style={{ marginBottom: 8 }}>
          <Text strong>快速查詢模板：</Text>
          <Button
            size="small"
            onClick={() => setCustomQuery('SELECT * FROM documents ORDER BY created_at DESC LIMIT 10;')}
          >
            最新文檔
          </Button>
          <Button
            size="small"
            onClick={() => setCustomQuery('SELECT COUNT(*) as total FROM documents;')}
          >
            統計記錄
          </Button>
          <Button
            size="small"
            onClick={() => setCustomQuery('SELECT category, COUNT(*) as count FROM documents GROUP BY category ORDER BY count DESC;')}
          >
            按類型統計
          </Button>
          <Button
            size="small"
            onClick={() => setCustomQuery('SELECT status, COUNT(*) as count FROM documents GROUP BY status;')}
          >
            按狀態統計
          </Button>
          <Button
            size="small"
            onClick={() => setCustomQuery('SELECT DATE(doc_date) as date, COUNT(*) as count FROM documents GROUP BY DATE(doc_date) ORDER BY date DESC LIMIT 30;')}
          >
            日期分佈
          </Button>
        </Space>

        <TextArea
          value={customQuery}
          onChange={(e) => setCustomQuery(e.target.value)}
          placeholder="輸入您的 SELECT 查詢語句..."
          rows={6}
          style={{ fontFamily: 'monospace' }}
        />

        <Space style={{ marginTop: 8 }}>
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={executeQuery}
            loading={loading}
          >
            執行查詢
          </Button>
          <Button
            icon={<CopyOutlined />}
            onClick={() => {
              navigator.clipboard.writeText(customQuery);
              message.success('查詢語句已複製到剪貼簿');
            }}
          >
            複製查詢
          </Button>
        </Space>
      </div>

      {queryResult && (
        <Card title={`查詢結果 (${queryResult.totalRows} 條記錄，耗時 ${queryResult.executionTime}ms)`}>
          <Table
            columns={queryResult.columns.map((col: string) => ({
              title: col,
              dataIndex: col,
              key: col,
              ellipsis: true
            }))}
            dataSource={queryResult.rows.map((row: any[], index: number) => {
              const obj: any = { key: index };
              queryResult.columns.forEach((col: string, colIndex: number) => {
                obj[col] = row[colIndex];
              });
              return obj;
            })}
            size="small"
            pagination={{ pageSize: 20 }}
            scroll={{ x: 'max-content' }}
          />
        </Card>
      )}
    </Space>
  );

  return (
    <div style={{ padding: '24px', background: '#f5f5f5', minHeight: '100vh' }}>
      <div style={{ maxWidth: 1400, margin: '0 auto' }}>
        
        {/* 頁面標題 */}
        <Row justify="space-between" align="middle" style={{ marginBottom: 24 }}>
          <Col>
            <Title level={2} style={{ margin: 0, color: '#1976d2' }}>
              <DatabaseOutlined style={{ marginRight: 12 }} />
              資料庫管理
              {useEnhancedView && (
                <Tag color="green" style={{ marginLeft: 8 }}>增強模式</Tag>
              )}
            </Title>
            <Typography.Text type="secondary" style={{ fontSize: '14px' }}>
              {useEnhancedView
                ? '增強檢視：包含關聯圖、中英文對照、前端頁面對應'
                : '標準檢視：基本資料庫管理功能'
              }
            </Typography.Text>
          </Col>
          <Col>
            <Space>
              <Space>
                <Typography.Text>檢視模式:</Typography.Text>
                <Switch
                  checked={useEnhancedView}
                  onChange={setUseEnhancedView}
                  checkedChildren="增強"
                  unCheckedChildren="標準"
                />
              </Space>
              <Button
                icon={<EyeOutlined />}
                onClick={() => setEnhancedDrawerVisible(true)}
                type="primary"
                ghost
              >
                開啟增強檢視
              </Button>
              <Button
                icon={<ReloadOutlined />}
                onClick={fetchDatabaseInfo}
                loading={loading}
              >
                重新整理
              </Button>
              <Button
                icon={<WarningOutlined />}
                onClick={checkIntegrity}
                loading={loading}
              >
                完整性檢查
              </Button>
            </Space>
          </Col>
        </Row>

        {/* 資料庫統計儀表板 */}
        {databaseInfo && (
          <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
            <Col xs={12} md={6}>
              <Card>
                <Statistic
                  title="資料庫大小"
                  value={databaseInfo.size}
                  prefix={<DatabaseOutlined style={{ color: '#1976d2' }} />}
                  valueStyle={{ color: '#1976d2' }}
                />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card>
                <Statistic
                  title="資料表數量"
                  value={databaseInfo.tables.length}
                  prefix={<TableOutlined style={{ color: '#52c41a' }} />}
                  valueStyle={{ color: '#52c41a' }}
                />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card>
                <Statistic
                  title="總記錄數"
                  value={databaseInfo.totalRecords}
                  prefix={<InfoCircleOutlined style={{ color: '#faad14' }} />}
                  valueStyle={{ color: '#faad14' }}
                />
              </Card>
            </Col>
            <Col xs={12} md={6}>
              <Card>
                <Statistic
                  title="資料庫狀態"
                  value={databaseInfo.status === 'healthy' ? '正常' : '警告'}
                  prefix={
                    databaseInfo.status === 'healthy' ? 
                    <CheckCircleOutlined style={{ color: '#52c41a' }} /> :
                    <ExclamationCircleOutlined style={{ color: '#faad14' }} />
                  }
                  valueStyle={{ 
                    color: databaseInfo.status === 'healthy' ? '#52c41a' : '#faad14'
                  }}
                />
              </Card>
            </Col>
          </Row>
        )}

        {/* 主要內容區 */}
        {useEnhancedView ? (
          <SimpleDatabaseViewer />
        ) : (
          <Card>
            <div style={{ marginBottom: 16 }}>
              <Alert
                message="升級提示"
                description={
                  <Space>
                    <span>嘗試新的增強檢視模式，包含關聯圖、中英文對照、前端頁面對應等進階功能</span>
                    <Button
                      size="small"
                      type="link"
                      icon={<UpOutlined />}
                      onClick={() => setUseEnhancedView(true)}
                    >
                      立即體驗
                    </Button>
                  </Space>
                }
                type="info"
                showIcon
                closable
              />
            </div>
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              size="large"
              items={[
                {
                  key: 'overview',
                  label: <span><TableOutlined />資料表概覽</span>,
                  children: renderTableList()
                },
                {
                  key: 'data',
                  label: <span><SearchOutlined />資料檢視</span>,
                  children: renderTableDetail()
                },
                {
                  key: 'query',
                  label: <span><CodeOutlined />SQL 查詢</span>,
                  children: renderQueryTool()
                },
                {
                  key: 'integrity',
                  label: <span><WarningOutlined />完整性檢查</span>,
                  children: (
                    <Space direction="vertical" style={{ width: '100%' }}>
                      <Alert
                        message="數據完整性檢查"
                        description="檢查資料庫表格完整性、外鍵約束和數據一致性"
                        type="info"
                        showIcon
                      />

                      <Button
                        type="primary"
                        icon={<PlayCircleOutlined />}
                        onClick={checkIntegrity}
                        loading={loading}
                        size="large"
                      >
                        開始完整性檢查
                      </Button>

                      {integrityResult && (
                        <Card title="檢查結果">
                          <Space direction="vertical" style={{ width: '100%' }}>
                            <div>
                              <Text strong>檢查狀態：</Text>
                              <Tag color={integrityResult.totalIssues === 0 ? 'green' : 'orange'}>
                                {integrityResult.totalIssues === 0 ? '通過' : `發現 ${integrityResult.totalIssues} 個問題`}
                              </Tag>
                            </div>

                            <div>
                              <Text strong>檢查時間：</Text>
                              <Text type="secondary">{new Date(integrityResult.checkTime).toLocaleString()}</Text>
                            </div>

                            {integrityResult.totalIssues === 0 ? (
                              <Alert message="數據完整性檢查通過，未發現問題" type="success" showIcon />
                            ) : (
                              <Alert message="發現數據問題，請檢查以下項目" type="warning" showIcon />
                            )}
                          </Space>
                        </Card>
                      )}
                    </Space>
                  )
                }
              ]}
            />
          </Card>
        )}

        {/* 增強檢視 Drawer */}
        <Drawer
          title="增強型資料庫檢視"
          width="90%"
          onClose={() => setEnhancedDrawerVisible(false)}
          open={enhancedDrawerVisible}
          styles={{ body: { padding: 0 } }}
        >
          <SimpleDatabaseViewer />
        </Drawer>

      </div>
    </div>
  );
};
