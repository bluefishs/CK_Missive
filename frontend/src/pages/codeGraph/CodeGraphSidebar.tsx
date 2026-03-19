import React from 'react';
import {
  Card,
  Space,
  Button,
  Popconfirm,
  Divider,
  Typography,
  Row,
  Col,
  Statistic,
  Spin,
  Switch,
} from 'antd';
import {
  CodeOutlined,
  ForkOutlined,
  DatabaseOutlined,
  UploadOutlined,
  SyncOutlined,
  NodeIndexOutlined,
  ApartmentOutlined,
} from '@ant-design/icons';
import { CodeWikiFiltersCard } from '../../components/ai/CodeWikiFiltersCard';
import { CODE_TYPE_LABELS } from '../../constants/codeGraphOptions';
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
        </Space>
      </Card>

      <CodeWikiFiltersCard graph={codeWiki} title="圖譜篩選" />
    </div>
  );
};

export default CodeGraphSidebar;
