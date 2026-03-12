/**
 * DatabaseGraphPage - 資料庫圖譜頁面
 *
 * 獨立的資料庫 ER 關聯視覺化頁面：
 * - 左側面板：統計資訊
 * - 中央：KnowledgeGraph 力導向 ER 視覺化
 * - 右側抽屜：點擊表節點時顯示欄位詳情 + 資料預覽
 *
 * 使用 /ai/graph/db-graph 端點直接反射 DB schema，
 * 無需依賴 code-wiki 入圖資料。
 *
 * @version 4.0.0
 * @created 2026-03-11
 * @updated 2026-03-11 - v4.0.0 新增表資料預覽功能
 */

import React, { useMemo, useCallback, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Card,
  Row,
  Col,
  Statistic,
  Spin,
  Typography,
  Divider,
  Button,
  Drawer,
  Table,
  Tag,
  Descriptions,
  Tabs,
  Empty,
  App,
} from 'antd';
import {
  DatabaseOutlined,
  NodeIndexOutlined,
  ApartmentOutlined,
  SyncOutlined,
  KeyOutlined,
  LinkOutlined,
  CloseOutlined,
  TableOutlined,
  ReloadOutlined,
} from '@ant-design/icons';

import { aiApi } from '../api/aiApi';
import { apiClient } from '../api/client';
import { API_ENDPOINTS } from '../api/endpoints';
import type { DbTableInfo } from '../api/ai';
import { KnowledgeGraph } from '../components/ai/KnowledgeGraph';
import type { ExternalGraphData } from '../components/ai/KnowledgeGraph';
import type { TableDataResponse } from '../types/admin-system';

const { Title, Text } = Typography;

/** 表資料預覽每頁筆數 */
const TABLE_DATA_PAGE_SIZE = 20;

const DatabaseGraphPage: React.FC = () => {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const [selectedTable, setSelectedTable] = useState<DbTableInfo | null>(null);

  // Table data preview state
  const [tableData, setTableData] = useState<TableDataResponse | null>(null);
  const [tableDataLoading, setTableDataLoading] = useState(false);
  const [tableDataPage, setTableDataPage] = useState(1);

  // DB graph + schema via React Query
  const { data: dbGraphResult, isLoading: loading } = useQuery({
    queryKey: ['db-graph-data'],
    queryFn: async () => {
      const [graphResult, schemaResult] = await Promise.all([
        aiApi.getDbSchemaGraph(),
        aiApi.getDbSchema(),
      ]);

      const graphData: ExternalGraphData = graphResult?.success
        ? { nodes: graphResult.nodes, edges: graphResult.edges }
        : { nodes: [], edges: [] };

      const schemaMap = new Map<string, DbTableInfo>();
      if (schemaResult?.success && schemaResult.tables) {
        for (const table of schemaResult.tables) {
          schemaMap.set(table.name, table);
        }
      }

      return { graphData, schemaMap };
    },
    staleTime: 5 * 60 * 1000, // 5 min
    retry: 1,
  });

  const graphData = dbGraphResult?.graphData ?? null;
  const schemaMap = useMemo(
    () => dbGraphResult?.schemaMap ?? new Map<string, DbTableInfo>(),
    [dbGraphResult?.schemaMap],
  );

  // Stats derived from graph data
  const stats = useMemo(() => {
    if (!graphData) return null;
    return {
      totalTables: graphData.nodes.length,
      totalRelationships: graphData.edges.length,
    };
  }, [graphData]);

  // Stable empty array for KnowledgeGraph documentIds
  const emptyDocumentIds = useMemo<number[]>(() => [], []);

  // Refresh handler
  const loadDbGraph = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['db-graph-data'] });
  }, [queryClient]);

  // Fetch table data preview
  const fetchTableData = useCallback(async (tableName: string, page: number) => {
    setTableDataLoading(true);
    try {
      const offset = (page - 1) * TABLE_DATA_PAGE_SIZE;
      const result = await apiClient.post<TableDataResponse>(
        API_ENDPOINTS.ADMIN_DATABASE.TABLE(tableName),
        {},
        { params: { limit: TABLE_DATA_PAGE_SIZE, offset } },
      );
      setTableData(result);
    } catch {
      setTableData(null);
      message.error('載入表資料失敗（需管理員權限）');
    } finally {
      setTableDataLoading(false);
    }
  }, [message]);

  // Node click handler — open table detail drawer
  const handleNodeClick = useCallback((node: { id: string; label: string; type: string }) => {
    const tableName = node.label;
    const tableInfo = schemaMap.get(tableName);
    setSelectedTable(tableInfo ?? null);
    setTableData(null);
    setTableDataPage(1);
  }, [schemaMap]);

  // Column table columns definition
  const columnDefs = useMemo(() => [
    {
      title: '欄位',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: { primary_key: boolean }) => (
        <span>
          {record.primary_key && <KeyOutlined style={{ color: '#faad14', marginRight: 4 }} />}
          <Text strong={record.primary_key}>{name}</Text>
        </span>
      ),
    },
    {
      title: '型別',
      dataIndex: 'type',
      key: 'type',
      render: (type: string) => <Tag color="blue" style={{ fontSize: 11 }}>{type}</Tag>,
    },
    {
      title: 'NULL',
      dataIndex: 'nullable',
      key: 'nullable',
      width: 60,
      render: (nullable: boolean) => nullable ? <Tag>YES</Tag> : <Tag color="red">NO</Tag>,
    },
  ], []);

  return (
    <div style={{ display: 'flex', gap: 0, height: 'calc(100vh - 120px)', overflow: 'hidden' }}>
      {/* Left Panel */}
      <div
        style={{
          width: 280,
          minWidth: 280,
          background: '#fff',
          borderRight: '1px solid #f0f0f0',
          overflow: 'auto',
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        {/* Title */}
        <div style={{ marginBottom: 4 }}>
          <Title level={5} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <DatabaseOutlined />
            <span>資料庫圖譜</span>
          </Title>
          <Text type="secondary" style={{ fontSize: 12 }}>
            視覺化資料表 ER 關聯與欄位結構
          </Text>
        </div>

        <Divider style={{ margin: '4px 0' }} />

        {/* Stats */}
        <Card
          size="small"
          title={
            <span style={{ fontSize: 13 }}>
              <DatabaseOutlined /> 圖譜統計
            </span>
          }
          extra={
            <Button
              size="small"
              type="text"
              icon={<SyncOutlined spin={loading} />}
              onClick={loadDbGraph}
            />
          }
          styles={{ body: { padding: '8px 12px' } }}
        >
          {loading ? (
            <Spin size="small" />
          ) : stats ? (
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <Statistic
                  title={<span style={{ fontSize: 11 }}>資料表</span>}
                  value={stats.totalTables}
                  prefix={<NodeIndexOutlined style={{ fontSize: 12 }} />}
                  valueStyle={{ fontSize: 18 }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={<span style={{ fontSize: 11 }}>FK 關係</span>}
                  value={stats.totalRelationships}
                  prefix={<ApartmentOutlined style={{ fontSize: 12 }} />}
                  valueStyle={{ fontSize: 18 }}
                />
              </Col>
            </Row>
          ) : (
            <Text type="secondary" style={{ fontSize: 12 }}>無資料</Text>
          )}
        </Card>
      </div>

      {/* Center: Graph */}
      <div style={{ flex: 1, minWidth: 0, overflow: 'hidden', background: '#fafafa' }}>
        {loading || !graphData ? (
          <div style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
            <Spin size="large" />
            <div style={{ marginTop: 12, color: '#888' }}>載入資料庫圖譜...</div>
          </div>
        ) : (
          <KnowledgeGraph
            documentIds={emptyDocumentIds}
            height={typeof window !== 'undefined' ? window.innerHeight - 120 : 700}
            externalGraphData={graphData}
            onExternalRefresh={loadDbGraph}
            onNodeClickExternal={handleNodeClick}
          />
        )}
      </div>

      {/* Right Drawer: Table Detail */}
      <Drawer
        title={
          <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <DatabaseOutlined />
            {selectedTable?.name ?? '表格詳情'}
          </span>
        }
        open={!!selectedTable}
        onClose={() => { setSelectedTable(null); setTableData(null); }}
        width={560}
        closeIcon={<CloseOutlined />}
        styles={{ body: { padding: '12px 16px' } }}
      >
        {selectedTable && (
          <Tabs
            defaultActiveKey="schema"
            size="small"
            items={[
              {
                key: 'schema',
                label: <><KeyOutlined /> 結構定義</>,
                children: (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                    {/* Basic Info */}
                    <Descriptions size="small" column={2} bordered>
                      <Descriptions.Item label="欄位數">
                        {selectedTable.columns.length}
                      </Descriptions.Item>
                      <Descriptions.Item label="主鍵">
                        {selectedTable.primary_key_columns.join(', ') || '-'}
                      </Descriptions.Item>
                      <Descriptions.Item label="外鍵數">
                        {selectedTable.foreign_keys.length}
                      </Descriptions.Item>
                      <Descriptions.Item label="索引數">
                        {selectedTable.indexes.length}
                      </Descriptions.Item>
                    </Descriptions>

                    {/* Columns */}
                    <div>
                      <Title level={5} style={{ margin: '0 0 8px', fontSize: 14 }}>
                        欄位定義
                      </Title>
                      <Table
                        dataSource={selectedTable.columns}
                        columns={columnDefs}
                        rowKey="name"
                        size="small"
                        pagination={false}
                        scroll={{ y: 300 }}
                      />
                    </div>

                    {/* Foreign Keys */}
                    {selectedTable.foreign_keys.length > 0 && (
                      <div>
                        <Title level={5} style={{ margin: '0 0 8px', fontSize: 14 }}>
                          <LinkOutlined /> 外鍵關聯
                        </Title>
                        {selectedTable.foreign_keys.map((fk, i) => (
                          <Card key={i} size="small" style={{ marginBottom: 8 }} styles={{ body: { padding: '8px 12px' } }}>
                            <Text code>{fk.constrained_columns.join(', ')}</Text>
                            <Text type="secondary"> → </Text>
                            <Text strong>{fk.referred_table}</Text>
                            <Text type="secondary"> (</Text>
                            <Text code>{fk.referred_columns.join(', ')}</Text>
                            <Text type="secondary">)</Text>
                          </Card>
                        ))}
                      </div>
                    )}

                    {/* Indexes */}
                    {selectedTable.indexes.length > 0 && (
                      <div>
                        <Title level={5} style={{ margin: '0 0 8px', fontSize: 14 }}>
                          索引
                        </Title>
                        {selectedTable.indexes.map((idx, i) => (
                          <div key={i} style={{ marginBottom: 4 }}>
                            <Text code style={{ fontSize: 11 }}>{idx.name}</Text>
                            <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>
                              ({idx.columns.join(', ')})
                            </Text>
                            {idx.unique && <Tag color="orange" style={{ marginLeft: 4, fontSize: 10 }}>UNIQUE</Tag>}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ),
              },
              {
                key: 'data',
                label: <><TableOutlined /> 資料預覽</>,
                children: (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {tableData ? `共 ${tableData.total} 筆記錄` : '點擊載入查看表資料'}
                      </Text>
                      <Button
                        size="small"
                        icon={<ReloadOutlined spin={tableDataLoading} />}
                        onClick={() => fetchTableData(selectedTable.name, tableDataPage)}
                        loading={tableDataLoading}
                      >
                        {tableData ? '重新載入' : '載入資料'}
                      </Button>
                    </div>
                    {tableDataLoading ? (
                      <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
                    ) : tableData && tableData.columns.length > 0 ? (
                      <Table
                        dataSource={tableData.rows.map((row, idx) => {
                          const record: Record<string, unknown> = { _key: `${tableDataPage}-${idx}` };
                          tableData.columns.forEach((col, ci) => { record[col] = row[ci]; });
                          return record;
                        })}
                        columns={tableData.columns.map((col) => ({
                          title: col,
                          dataIndex: col,
                          key: col,
                          width: 140,
                          ellipsis: true,
                          render: (v: unknown) => {
                            if (v === null || v === undefined) return <Text type="secondary" italic>NULL</Text>;
                            const str = String(v);
                            return str.length > 60 ? `${str.slice(0, 60)}...` : str;
                          },
                        }))}
                        rowKey="_key"
                        size="small"
                        scroll={{ x: Math.max(tableData.columns.length * 140, 500), y: 400 }}
                        pagination={{
                          current: tableDataPage,
                          pageSize: TABLE_DATA_PAGE_SIZE,
                          total: tableData.total,
                          size: 'small',
                          showTotal: (total) => `共 ${total} 筆`,
                          onChange: (page) => {
                            setTableDataPage(page);
                            fetchTableData(selectedTable.name, page);
                          },
                        }}
                      />
                    ) : tableData ? (
                      <Empty description="此表無資料" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    ) : (
                      <Empty description="點擊「載入資料」查看表內容" image={Empty.PRESENTED_IMAGE_SIMPLE} />
                    )}
                  </div>
                ),
              },
            ]}
          />
        )}
      </Drawer>
    </div>
  );
};

export default DatabaseGraphPage;
