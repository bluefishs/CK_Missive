import React from 'react';
import {
  Row,
  Col,
  Spin,
  Progress,
  Statistic,
  Typography,
} from 'antd';
import {
  ApartmentOutlined,
  ExperimentOutlined,
  NodeIndexOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import type {
  EmbeddingStatsResponse,
  EntityStatsResponse,
  KGGraphStatsResponse,
} from '../../types/ai';

const { Text } = Typography;

export interface CoverageStats {
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
  const kgEmbCoverage = stats.graph?.embedding_coverage_percent ?? 0;

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
          <Text style={{ fontSize: 12 }}>文件 Embedding</Text>
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

      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <Text style={{ fontSize: 12 }}>KG 實體 Embedding</Text>
          <Text style={{ fontSize: 12 }} type="secondary">
            {stats.graph?.entities_with_embedding ?? 0}/{canonicalEntities}
          </Text>
        </div>
        <Progress
          percent={kgEmbCoverage}
          size="small"
          status={kgEmbCoverage >= 80 ? 'success' : kgEmbCoverage >= 50 ? 'normal' : 'exception'}
          format={(p) => `${(p ?? 0).toFixed(1)}%`}
        />
        {stats.graph?.embedding_backfill_needed && (
          <Text type="warning" style={{ fontSize: 10, display: 'block', marginTop: 2 }}>
            {stats.graph.entities_without_embedding ?? 0} 個實體缺少向量，建議執行 Embedding 回填
          </Text>
        )}
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

export default CoveragePanel;
