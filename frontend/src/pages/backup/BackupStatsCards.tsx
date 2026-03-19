import React from 'react';
import { Card, Row, Col, Statistic } from 'antd';
import {
  DatabaseOutlined, FolderOutlined,
  CheckCircleOutlined, CloseCircleOutlined
} from '@ant-design/icons';

interface BackupStatistics {
  database_backup_count: number;
  attachment_backup_count: number;
  total_size_mb: number;
}

interface EnvironmentStatus {
  docker_available: boolean;
  docker_path: string;
  last_success_time: string | null;
  consecutive_failures: number;
  backup_dir_exists: boolean;
  uploads_dir_exists: boolean;
}

interface BackupStatsCardsProps {
  statistics: BackupStatistics | null;
  envStatus: EnvironmentStatus | null;
}

export const BackupStatsCards: React.FC<BackupStatsCardsProps> = ({
  statistics,
  envStatus,
}) => {
  return (
    <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
      <Col xs={12} md={6}>
        <Card>
          <Statistic
            title="資料庫備份"
            value={statistics?.database_backup_count || 0}
            prefix={<DatabaseOutlined style={{ color: '#1976d2' }} />}
            suffix="個"
          />
        </Card>
      </Col>
      <Col xs={12} md={6}>
        <Card>
          <Statistic
            title="附件備份"
            value={statistics?.attachment_backup_count || 0}
            prefix={<FolderOutlined style={{ color: '#52c41a' }} />}
            suffix="個"
          />
        </Card>
      </Col>
      <Col xs={12} md={6}>
        <Card>
          <Statistic
            title="總備份大小"
            value={statistics?.total_size_mb || 0}
            precision={2}
            suffix="MB"
          />
        </Card>
      </Col>
      <Col xs={12} md={6}>
        <Card>
          <Statistic
            title="Docker 狀態"
            value={envStatus?.docker_available ? '可用' : '不可用'}
            styles={{ content: {
              color: envStatus?.docker_available ? '#3f8600' : '#cf1322'
            } }}
            prefix={envStatus?.docker_available ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
          />
        </Card>
      </Col>
    </Row>
  );
};
