import React from 'react';
import {
  Card,
  Checkbox,
  Select,
  Switch,
  Button,
  Typography,
  Divider,
  Tooltip,
} from 'antd';
import {
  ApartmentOutlined,
  SyncOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  BgColorsOutlined,
  GlobalOutlined,
} from '@ant-design/icons';
import type {
  KGEntityItem,
  KGShortestPathResponse,
} from '../../types/ai';
import type { ColorByMode } from '../../components/ai/knowledgeGraph/useGraphTransform';
import { SOURCE_PROJECT_COLORS, SOURCE_PROJECT_LABELS } from '../../config/graphNodeConfig';
import { KGAdminPanel } from './KGAdminPanel';
import CoveragePanel from './CoveragePanel';
import type { CoverageStats } from './CoveragePanel';
import TimelineTrendMini from './TimelineTrendMini';
import UnifiedSearchMini from './UnifiedSearchMini';
import FederationHealthMini from './FederationHealthMini';
import EntityTypeDistribution from './EntityTypeDistribution';
import TopEntitiesRanking from './TopEntitiesRanking';
import ShortestPathFinder from './ShortestPathFinder';

const COLOR_BY_OPTIONS = [
  { label: '依類型', value: 'type' as const },
  { label: '依來源專案', value: 'source_project' as const },
];

const { Title, Text } = Typography;

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
  sourceProjectDistribution?: Record<string, number>;
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
  visibleSourceProjects: Set<string>;
  onVisibleSourceProjectsChange: (projects: Set<string>) => void;
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
  sourceProjectDistribution,
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
  visibleSourceProjects,
  onVisibleSourceProjectsChange,
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

      <UnifiedSearchMini />

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
          options={COLOR_BY_OPTIONS}
        />
      </div>

      {colorBy === 'source_project' && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, margin: '0 0 4px 0' }}>
          {Object.entries(SOURCE_PROJECT_COLORS).map(([key, color]) => {
            const isActive = visibleSourceProjects.size === 0 || visibleSourceProjects.has(key);
            return (
              <Checkbox
                key={key}
                checked={isActive}
                onChange={(e) => {
                  const next = new Set(
                    visibleSourceProjects.size === 0
                      ? Object.keys(SOURCE_PROJECT_COLORS)
                      : visibleSourceProjects,
                  );
                  if (e.target.checked) {
                    next.add(key);
                  } else {
                    next.delete(key);
                  }
                  const allKeys = Object.keys(SOURCE_PROJECT_COLORS);
                  onVisibleSourceProjectsChange(
                    next.size === allKeys.length ? new Set() : next,
                  );
                }}
                style={{ fontSize: 12 }}
              >
                <span style={{
                  display: 'inline-block', width: 10, height: 10, borderRadius: '50%',
                  background: color, marginRight: 4, verticalAlign: 'middle',
                }} />
                {SOURCE_PROJECT_LABELS[key] ?? key}
              </Checkbox>
            );
          })}
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

      <Card
        size="small"
        title={
          <span style={{ fontSize: 13 }}>
            <GlobalOutlined /> 跨專案同步
          </span>
        }
        styles={{ body: { padding: '8px 12px' } }}
      >
        <FederationHealthMini />
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

      {sourceProjectDistribution && Object.keys(sourceProjectDistribution).length > 1 && (
        <div style={{ marginBottom: 12 }}>
          <Text strong style={{ fontSize: 12, display: 'block', marginBottom: 6 }}>
            來源專案分布
          </Text>
          {Object.entries(sourceProjectDistribution).map(([project, count]) => (
            <div
              key={project}
              style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}
            >
              <span style={{
                width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                background: SOURCE_PROJECT_COLORS[project] ?? '#999',
              }} />
              <Text style={{ fontSize: 11, flex: 1 }}>
                {SOURCE_PROJECT_LABELS[project] ?? project}
              </Text>
              <Text type="secondary" style={{ fontSize: 11 }}>{count}</Text>
            </div>
          ))}
        </div>
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
