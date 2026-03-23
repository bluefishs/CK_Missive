import React from 'react';
import {
  Card,
  Select,
  Switch,
  Button,
  Typography,
  Spin,
  Divider,
  Tooltip,
  Progress,
  Row,
  Col,
  Statistic,
} from 'antd';
import {
  ApartmentOutlined,
  SyncOutlined,
  DatabaseOutlined,
  ExperimentOutlined,
  NodeIndexOutlined,
  FileTextOutlined,
  BarChartOutlined,
  BgColorsOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { getTimelineAggregate } from '../../api/ai/knowledgeGraph';
import type {
  EmbeddingStatsResponse,
  EntityStatsResponse,
  KGGraphStatsResponse,
  KGEntityItem,
  KGShortestPathResponse,
} from '../../types/ai';
import type { ColorByMode } from '../../components/ai/knowledgeGraph/useGraphTransform';
import { SOURCE_PROJECT_COLORS, SOURCE_PROJECT_LABELS } from '../../config/graphNodeConfig';
import { KGAdminPanel } from './KGAdminPanel';
import EntityTypeDistribution from './EntityTypeDistribution';
import TopEntitiesRanking from './TopEntitiesRanking';
import ShortestPathFinder from './ShortestPathFinder';

const { Title, Text } = Typography;

interface CoverageStats {
  embedding: EmbeddingStatsResponse | null;
  entity: EntityStatsResponse | null;
  graph: KGGraphStatsResponse | null;
}

const CoveragePanel: React.FC<{
  stats: CoverageStats;
  loading: boolean;
}> = ({ stats, loading }) => {
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 16 }}>
        <Spin size="small" />
        <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
          載入統計...
        </div>
      </div>
    );
  }

  const embCoverage = stats.embedding?.coverage_percent ?? 0;
  const nerCoverage = stats.entity?.coverage_percent ?? 0;
  const canonicalEntities = stats.graph?.total_entities ?? 0;
  const totalRelationships = stats.graph?.total_relationships ?? 0;

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <Text style={{ fontSize: 12 }}>NER 實體提取</Text>
          <Text style={{ fontSize: 12 }} type="secondary">
            {stats.entity?.extracted_documents ?? 0}/{stats.entity?.total_documents ?? 0}
          </Text>
        </div>
        <Progress
          percent={nerCoverage}
          size="small"
          status={nerCoverage >= 80 ? 'success' : nerCoverage >= 50 ? 'normal' : 'exception'}
          format={(p) => `${(p ?? 0).toFixed(1)}%`}
        />
      </div>

      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <Text style={{ fontSize: 12 }}>Embedding 覆蓋</Text>
          <Text style={{ fontSize: 12 }} type="secondary">
            {stats.embedding?.with_embedding ?? 0}/{stats.embedding?.total_documents ?? 0}
          </Text>
        </div>
        <Progress
          percent={embCoverage}
          size="small"
          status={embCoverage >= 80 ? 'success' : embCoverage >= 50 ? 'normal' : 'exception'}
          format={(p) => `${(p ?? 0).toFixed(1)}%`}
        />
      </div>

      <Row gutter={[8, 8]}>
        <Col span={12}>
          <Statistic
            title={<span style={{ fontSize: 11 }}>正規化實體</span>}
            value={canonicalEntities}
            prefix={<NodeIndexOutlined style={{ fontSize: 12 }} />}
            styles={{ content: { fontSize: 18 } }}
          />
        </Col>
        <Col span={12}>
          <Statistic
            title={<span style={{ fontSize: 11 }}>關係數量</span>}
            value={totalRelationships}
            prefix={<ApartmentOutlined style={{ fontSize: 12 }} />}
            styles={{ content: { fontSize: 18 } }}
          />
        </Col>
      </Row>

      {stats.entity && (
        <div style={{ marginTop: 12 }}>
          <Row gutter={[8, 8]}>
            <Col span={12}>
              <Statistic
                title={<span style={{ fontSize: 11 }}>NER 實體</span>}
                value={stats.entity.total_entities}
                prefix={<ExperimentOutlined style={{ fontSize: 12 }} />}
                styles={{ content: { fontSize: 18 } }}
              />
            </Col>
            <Col span={12}>
              <Statistic
                title={<span style={{ fontSize: 11 }}>NER 關係</span>}
                value={stats.entity.total_relations}
                prefix={<FileTextOutlined style={{ fontSize: 12 }} />}
                styles={{ content: { fontSize: 18 } }}
              />
            </Col>
          </Row>
        </div>
      )}
    </div>
  );
};

const TimelineTrendMini: React.FC<{ onClickPeriod?: (rocYear: number) => void; activeYear?: number }> = ({ onClickPeriod, activeYear }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['kg-timeline-trend'],
    queryFn: () => getTimelineAggregate({ granularity: 'month' }),
    staleTime: 60_000,
  });

  if (isLoading) return <Spin size="small" />;

  const buckets = data?.buckets ?? [];
  if (buckets.length === 0) return <Text type="secondary" style={{ fontSize: 11 }}>尚無趨勢資料</Text>;

  const recent = buckets.slice(-12);
  const maxCount = Math.max(...recent.map(b => b.count), 1);

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 2, height: 48 }}>
        {recent.map(bucket => {
          const height = Math.max(4, (bucket.count / maxCount) * 44);
          const bucketYear = parseInt(bucket.period.slice(0, 4), 10);
          const rocYear = bucketYear - 1911;
          const isActive = activeYear != null && activeYear > 0 && rocYear === activeYear;
          return (
            <Tooltip
              key={bucket.period}
              title={`${bucket.period}: ${bucket.count} 關係 / ${bucket.entity_count} 實體${onClickPeriod ? ' (點擊篩選)' : ''}`}
            >
              <div
                style={{
                  flex: 1,
                  height,
                  background: isActive
                    ? 'linear-gradient(180deg, #fa8c16 0%, #ffc069 100%)'
                    : 'linear-gradient(180deg, #722ed1 0%, #b37feb 100%)',
                  borderRadius: '2px 2px 0 0',
                  minWidth: 6,
                  cursor: onClickPeriod ? 'pointer' : 'default',
                  transition: 'opacity 0.2s, background 0.3s',
                  border: isActive ? '1px solid #fa8c16' : 'none',
                }}
                onClick={() => onClickPeriod?.(rocYear)}
                onMouseEnter={e => { (e.target as HTMLElement).style.opacity = '0.7'; }}
                onMouseLeave={e => { (e.target as HTMLElement).style.opacity = '1'; }}
              />
            </Tooltip>
          );
        })}
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <Text type="secondary" style={{ fontSize: 10 }}>{recent[0]?.period}</Text>
        <Text type="secondary" style={{ fontSize: 10 }}>{recent[recent.length - 1]?.period}</Text>
      </div>
      <Text type="secondary" style={{ fontSize: 10, display: 'block', textAlign: 'center', marginTop: 2 }}>
        共 {data?.total_relationships ?? 0} 筆關係
      </Text>
    </div>
  );
};

interface GraphLeftPanelProps {
  selectedYear: number | undefined;
  onYearChange: (year: number | undefined) => void;
  yearOptions: Array<{ label: string; value: number }>;
  collapseAgency: boolean;
  onCollapseAgencyChange: (val: boolean) => void;
  coverageStats: CoverageStats;
  statsLoading: boolean;
  onRefetchStats: () => void;
  isAdmin: boolean;
  withoutExtraction: number;
  onOpenMergeModal: () => void;
  graphTypeDistribution: Record<string, number> | undefined;
  topEntities: KGEntityItem[];
  pathSourceId: number | null;
  pathTargetId: number | null;
  pathResult: KGShortestPathResponse | null;
  entityOptions: Array<{ label: string; value: number }>;
  onSourceChange: (val: number | null) => void;
  onTargetChange: (val: number | null) => void;
  onEntitySearch: (query: string) => void;
  onFindPath: () => void;
  findPathLoading: boolean;
  colorBy: ColorByMode;
  onColorByChange: (mode: ColorByMode) => void;
}

const GraphLeftPanel: React.FC<GraphLeftPanelProps> = ({
  selectedYear,
  onYearChange,
  yearOptions,
  collapseAgency,
  onCollapseAgencyChange,
  coverageStats,
  statsLoading,
  onRefetchStats,
  isAdmin,
  withoutExtraction,
  onOpenMergeModal,
  graphTypeDistribution,
  topEntities,
  pathSourceId,
  pathTargetId,
  pathResult,
  entityOptions,
  onSourceChange,
  onTargetChange,
  onEntitySearch,
  onFindPath,
  findPathLoading,
  colorBy,
  onColorByChange,
}) => {
  return (
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
      <div style={{ marginBottom: 4 }}>
        <Title level={5} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
          <ApartmentOutlined />
          <span>公文圖譜</span>
        </Title>
        <Text type="secondary" style={{ fontSize: 12 }}>
          視覺化公文關聯網絡與正規化實體
        </Text>
      </div>

      <Select
        value={selectedYear ?? 0}
        onChange={(val) => onYearChange(val === 0 ? undefined : val)}
        options={yearOptions}
        size="small"
        style={{ width: '100%' }}
        suffixIcon={<DatabaseOutlined />}
      />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '8px 0' }}>
        <Tooltip title="開啟時，子機關（如工務局用地科）自動折疊到上級機關（工務局）">
          <Text style={{ fontSize: 12 }}>機關層級折疊</Text>
        </Tooltip>
        <Switch
          size="small"
          checked={collapseAgency}
          onChange={onCollapseAgencyChange}
          checkedChildren="折疊"
          unCheckedChildren="展開"
        />
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', margin: '8px 0' }}>
        <Tooltip title="依節點類型或來源專案上色">
          <Text style={{ fontSize: 12 }}>
            <BgColorsOutlined style={{ marginRight: 4 }} />色彩模式
          </Text>
        </Tooltip>
        <Select
          size="small"
          value={colorBy}
          onChange={onColorByChange}
          style={{ width: 120 }}
          options={[
            { label: '依類型', value: 'type' },
            { label: '依來源專案', value: 'source_project' },
          ]}
        />
      </div>

      {colorBy === 'source_project' && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', margin: '0 0 4px 0' }}>
          {Object.entries(SOURCE_PROJECT_COLORS).map(([key, color]) => (
            <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span style={{
                display: 'inline-block', width: 10, height: 10, borderRadius: '50%',
                background: color,
              }} />
              <Text style={{ fontSize: 11 }}>{SOURCE_PROJECT_LABELS[key] ?? key}</Text>
            </div>
          ))}
        </div>
      )}

      <Divider style={{ margin: '4px 0' }} />

      <Card
        size="small"
        title={
          <span style={{ fontSize: 13 }}>
            <DatabaseOutlined /> 覆蓋率儀表板
          </span>
        }
        extra={
          <Button
            size="small"
            type="text"
            icon={<SyncOutlined spin={statsLoading} />}
            onClick={onRefetchStats}
          />
        }
        styles={{ body: { padding: '8px 12px' } }}
      >
        <CoveragePanel stats={coverageStats} loading={statsLoading} />
      </Card>

      <Card
        size="small"
        title={
          <span style={{ fontSize: 13 }}>
            <BarChartOutlined /> 關係趨勢
          </span>
        }
        styles={{ body: { padding: '8px 12px' } }}
      >
        <TimelineTrendMini
          activeYear={selectedYear}
          onClickPeriod={(rocYear) => {
            onYearChange(selectedYear === rocYear ? undefined : rocYear);
          }}
        />
      </Card>

      {isAdmin && (
        <KGAdminPanel
          withoutExtraction={withoutExtraction}
          onReloadStats={onRefetchStats}
          onOpenMergeModal={onOpenMergeModal}
        />
      )}

      {graphTypeDistribution && Object.keys(graphTypeDistribution).length > 0 && (
        <EntityTypeDistribution distribution={graphTypeDistribution} />
      )}

      {topEntities.length > 0 && (
        <TopEntitiesRanking entities={topEntities} />
      )}

      <ShortestPathFinder
        pathSourceId={pathSourceId}
        pathTargetId={pathTargetId}
        pathResult={pathResult}
        entityOptions={entityOptions}
        onSourceChange={onSourceChange}
        onTargetChange={onTargetChange}
        onSearch={onEntitySearch}
        onFindPath={onFindPath}
        isLoading={findPathLoading}
      />
    </div>
  );
};

export default GraphLeftPanel;
