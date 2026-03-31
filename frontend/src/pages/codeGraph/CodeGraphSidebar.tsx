import React, { useState, useCallback } from 'react';
import {
  App,
  Card,
  Space,
  Button,
  Popconfirm,
  Collapse,
  Divider,
  Table,
  Typography,
  Row,
  Col,
  Statistic,
  Spin,
  Switch,
  Tag,
} from 'antd';
import {
  CodeOutlined,
  FileTextOutlined,
  ForkOutlined,
  DatabaseOutlined,
  UploadOutlined,
  SyncOutlined,
  NodeIndexOutlined,
  ApartmentOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { CodeWikiFiltersCard } from '../../components/ai/CodeWikiFiltersCard';
import { CODE_TYPE_LABELS } from '../../constants/codeGraphOptions';
import { aiApi } from '../../api/aiApi';
import type { useCodeWikiGraph } from '../../hooks/useCodeWikiGraph';

const { Title, Text } = Typography;

const TYPE_LABELS = CODE_TYPE_LABELS;

export interface CodeGraphStats {
  totalEntities: number;
  totalRelationships: number;
  typeDistribution: Record<string, number>;
}

export interface CodeGraphSidebarProps {
  stats: CodeGraphStats | null | undefined;
  statsLoading: boolean;
  loadStats: () => void;
  codeIngestLoading: boolean;
  cycleLoading: boolean;
  archLoading: boolean;
  jsonImportLoading: boolean;
  ingestIncremental: boolean;
  setIngestIncremental: (v: boolean) => void;
  ingestClean: boolean;
  setIngestClean: (v: boolean) => void;
  jsonClean: boolean;
  setJsonClean: (v: boolean) => void;
  handleCodeGraphIngest: () => void;
  handleJsonImport: () => void;
  handleCycleDetection: () => void;
  handleArchAnalysis: () => void;
  codeWiki: ReturnType<typeof useCodeWikiGraph>;
}

const CodeGraphSidebar: React.FC<CodeGraphSidebarProps> = ({
  stats,
  statsLoading,
  loadStats,
  codeIngestLoading,
  cycleLoading,
  archLoading,
  jsonImportLoading,
  ingestIncremental,
  setIngestIncremental,
  ingestClean,
  setIngestClean,
  jsonClean,
  setJsonClean,
  handleCodeGraphIngest,
  handleJsonImport,
  handleCycleDetection,
  handleArchAnalysis,
  codeWiki,
}) => {
  const { message, modal } = App.useApp();
  const [rebuilding, setRebuilding] = useState(false);
  const [diffAnalyzing, setDiffAnalyzing] = useState(false);

  const handleRebuild = useCallback(async () => {
    setRebuilding(true);
    try {
      await aiApi.triggerCodeGraphIngest({});
      message.success('Code Graph 重建已觸發');
      loadStats();
    } catch {
      message.error('重建失敗');
    } finally {
      setRebuilding(false);
    }
  }, [message, loadStats]);

  const handleDiffImpact = useCallback(async () => {
    setDiffAnalyzing(true);
    try {
      const result = await aiApi.analyzeDiffImpact();
      if (result?.success && result.data) {
        const d = result.data;
        const downstreamColumns = [
          {
            title: '實體名稱',
            dataIndex: 'entity',
            key: 'entity',
            ellipsis: true,
            render: (v: string) => <Text code style={{ fontSize: 11 }}>{v}</Text>,
          },
          {
            title: '類型',
            dataIndex: 'type',
            key: 'type',
            width: 100,
            render: (v: string) => <Tag color="processing">{TYPE_LABELS[v] || v}</Tag>,
          },
          {
            title: '關係',
            dataIndex: 'relation',
            key: 'relation',
            width: 90,
            render: (v: string) => <Tag color="orange">{v}</Tag>,
          },
          {
            title: '依賴於',
            dataIndex: 'depends_on',
            key: 'depends_on',
            ellipsis: true,
            render: (v: string) => <Text code style={{ fontSize: 11 }}>{v}</Text>,
          },
        ];
        modal.info({
          title: 'Diff 影響分析',
          width: 700,
          content: (
            <div style={{ maxHeight: 500, overflow: 'auto' }}>
              <Text type="secondary" style={{ fontSize: 12 }}>{d.summary}</Text>

              {/* Summary stats */}
              <Row gutter={12} style={{ marginTop: 12 }}>
                <Col span={8}>
                  <Statistic
                    title={<span style={{ fontSize: 11 }}>變更檔案數</span>}
                    value={d.changed_files?.length ?? 0}
                    prefix={<FileTextOutlined style={{ fontSize: 12 }} />}
                    styles={{ content: { fontSize: 20, color: '#1677ff' } }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title={<span style={{ fontSize: 11 }}>影響實體數</span>}
                    value={d.affected_entities ?? 0}
                    prefix={<NodeIndexOutlined style={{ fontSize: 12 }} />}
                    styles={{ content: { fontSize: 20, color: '#fa8c16' } }}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title={<span style={{ fontSize: 11 }}>下游依賴數</span>}
                    value={d.downstream_dependents ?? 0}
                    prefix={<ApartmentOutlined style={{ fontSize: 12 }} />}
                    styles={{ content: { fontSize: 20, color: '#f5222d' } }}
                  />
                </Col>
              </Row>

              {/* Changed files collapse */}
              {d.changed_files?.length > 0 && (
                <Collapse
                  size="small"
                  style={{ marginTop: 12 }}
                  items={[{
                    key: 'files',
                    label: <span style={{ fontSize: 12 }}>變更檔案 ({d.changed_files.length})</span>,
                    children: (
                      <div style={{ fontFamily: 'monospace', fontSize: 11, lineHeight: 1.8 }}>
                        {d.changed_files.map((f: string, i: number) => (
                          <Tag key={i} style={{ marginBottom: 2 }}>{f}</Tag>
                        ))}
                      </div>
                    ),
                  }]}
                />
              )}

              {/* Affected by type */}
              {Object.keys(d.affected_by_type || {}).length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <Text strong style={{ fontSize: 12 }}>受影響實體類型</Text>
                  <div style={{ marginTop: 6 }}>
                    {Object.entries(d.affected_by_type).map(([type, count]) => (
                      <Tag key={type} color="blue" style={{ marginBottom: 4 }}>
                        {TYPE_LABELS[type] || type}: {String(count)}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}

              {/* Downstream dependents table */}
              {d.downstream?.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  <Text strong style={{ fontSize: 12 }}>下游依賴者</Text>
                  <Table
                    size="small"
                    dataSource={d.downstream.map(
                      (dep: { entity: string; type: string; relation: string; depends_on: string }, i: number) => ({
                        ...dep,
                        key: i,
                      }),
                    )}
                    columns={downstreamColumns}
                    pagination={d.downstream.length > 10 ? { pageSize: 10, size: 'small' } : false}
                    style={{ marginTop: 6 }}
                    scroll={{ x: 500 }}
                  />
                </div>
              )}
            </div>
          ),
        });
      } else {
        message.warning('無影響分析結果');
      }
    } catch {
      message.error('影響分析失敗');
    } finally {
      setDiffAnalyzing(false);
    }
  }, [message, modal]);

  return (
    <div
      style={{
        width: 300,
        minWidth: 300,
        background: '#fff',
        borderRight: '1px solid #f0f0f0',
        overflow: 'auto',
        padding: 16,
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}
    >
      <div>
        <Title level={5} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
          <CodeOutlined /> 代碼圖譜
        </Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          程式碼結構分析、入圖、匯入與品質檢測
        </Text>
      </div>

      <Divider style={{ margin: '4px 0' }} />

      <Card
        size="small"
        title={<span style={{ fontSize: 13 }}><DatabaseOutlined /> 圖譜統計</span>}
        extra={
          <Button size="small" type="text" icon={<SyncOutlined spin={statsLoading} />} onClick={loadStats} />
        }
        styles={{ body: { padding: '8px 12px' } }}
      >
        {statsLoading ? (
          <Spin size="small" />
        ) : stats ? (
          <>
            <Row gutter={[8, 8]}>
              <Col span={12}>
                <Statistic
                  title={<span style={{ fontSize: 11 }}>程式碼實體</span>}
                  value={stats.totalEntities}
                  prefix={<NodeIndexOutlined style={{ fontSize: 12 }} />}
                  styles={{ content: { fontSize: 18 } }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title={<span style={{ fontSize: 11 }}>關係數量</span>}
                  value={stats.totalRelationships}
                  prefix={<ApartmentOutlined style={{ fontSize: 12 }} />}
                  styles={{ content: { fontSize: 18 } }}
                />
              </Col>
            </Row>
            {Object.keys(stats.typeDistribution).length > 0 && (
              <div style={{ marginTop: 8 }}>
                {Object.entries(stats.typeDistribution).map(([type, count]) => (
                  <div key={type} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '2px 0' }}>
                    <span>{TYPE_LABELS[type] || type}</span>
                    <Text type="secondary">{count}</Text>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : (
          <Text type="secondary" style={{ fontSize: 12 }}>無資料</Text>
        )}
      </Card>

      <Card
        size="small"
        title={<span style={{ fontSize: 13 }}><CodeOutlined /> 管理動作</span>}
        styles={{ body: { padding: '8px 12px' } }}
      >
        <Space vertical style={{ width: '100%' }} size={8}>
          <div>
            <div style={{ display: 'flex', gap: 12, marginBottom: 4 }}>
              <label style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}>
                <Switch size="small" checked={ingestIncremental} onChange={setIngestIncremental} />
                增量模式
              </label>
              <label style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4 }}>
                <Switch size="small" checked={ingestClean} onChange={setIngestClean} />
                清除重建
              </label>
            </div>
            <Popconfirm
              title={`確定要${ingestClean ? '清除並重新' : ingestIncremental ? '增量' : '全量'}掃描代碼圖譜？`}
              onConfirm={handleCodeGraphIngest}
            >
              <Button block size="small" icon={<CodeOutlined />} loading={codeIngestLoading}>
                代碼圖譜入圖
              </Button>
            </Popconfirm>
          </div>

          <Divider style={{ margin: '4px 0' }} />

          <div>
            <label style={{ fontSize: 11, display: 'flex', alignItems: 'center', gap: 4, marginBottom: 4 }}>
              <Switch size="small" checked={jsonClean} onChange={setJsonClean} />
              匯入前清除舊資料
            </label>
            <Popconfirm
              title={`匯入本地 knowledge_graph.json？${jsonClean ? '將清除現有代碼圖譜資料後重新匯入。' : ''}`}
              onConfirm={handleJsonImport}
            >
              <Button block size="small" icon={<UploadOutlined />} loading={jsonImportLoading}>
                JSON 圖譜匯入
              </Button>
            </Popconfirm>
          </div>

          <Divider style={{ margin: '4px 0' }} />

          <Button
            block
            size="small"
            icon={<ForkOutlined />}
            loading={cycleLoading}
            onClick={handleCycleDetection}
          >
            循環依賴偵測
          </Button>
          <Button
            block
            size="small"
            icon={<DatabaseOutlined />}
            loading={archLoading}
            onClick={handleArchAnalysis}
          >
            架構分析報告
          </Button>

          <Divider style={{ margin: '4px 0' }} />

          <Button
            block
            size="small"
            icon={<SyncOutlined />}
            loading={rebuilding}
            onClick={handleRebuild}
          >
            重建 Code Graph
          </Button>
          <Button
            block
            size="small"
            icon={<ThunderboltOutlined />}
            loading={diffAnalyzing}
            onClick={handleDiffImpact}
          >
            影響分析
          </Button>
        </Space>
      </Card>

      <CodeWikiFiltersCard graph={codeWiki} title="圖譜篩選" />
    </div>
  );
};

export default CodeGraphSidebar;
