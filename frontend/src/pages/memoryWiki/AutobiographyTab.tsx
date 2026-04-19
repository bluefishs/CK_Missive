/**
 * AutobiographyTab — 每週自傳（Phase 4 輸出）
 *
 * 左側週次清單 + 右側 markdown 敘事。
 */
import React, { useEffect, useState } from 'react';
import { Alert, Card, Col, Empty, Row, Spin, Tag, Typography } from 'antd';

import MarkdownRenderer from '../../components/common/MarkdownRenderer';
import { useAutobiographyLatest, useAutobiographyList } from '../../hooks/useMemoryData';
import type { AutobiographySummary } from '../../types/memory';

const AutobiographyTab: React.FC = () => {
  const { data: list = [], isLoading: loadingList } = useAutobiographyList({ limit: 20 });
  const { data: latest } = useAutobiographyLatest();
  const [selected, setSelected] = useState<AutobiographySummary | null>(null);

  useEffect(() => {
    if (selected) return;
    const next = latest ?? list[0] ?? null;
    if (next) setSelected(next);
  }, [latest, list, selected]);

  return (
    <Row gutter={16} style={{ marginTop: 12 }}>
      <Col xs={24} md={8}>
        <Card size="small" title="週自傳清單" bodyStyle={{ padding: 12 }}>
          {loadingList ? (
            <Spin />
          ) : list.length === 0 ? (
            <Empty description="尚無週自傳（每週日 18:00 自動產生）" />
          ) : (
            <div style={{ maxHeight: 520, overflowY: 'auto' }}>
              {list.map((item) => {
                const active = selected?.filename === item.filename;
                return (
                  <div
                    key={item.filename}
                    onClick={() => setSelected(item)}
                    style={{
                      padding: '8px 10px',
                      marginBottom: 4,
                      cursor: 'pointer',
                      borderRadius: 4,
                      background: active ? '#fff7e6' : 'transparent',
                      border: active ? '1px solid #ffd591' : '1px solid transparent',
                    }}
                  >
                    <Typography.Text strong={active}>
                      {String(item.meta?.week_id ?? item.filename.replace('.md', ''))}
                    </Typography.Text>
                    {item.meta?.total_queries !== undefined && (
                      <Tag color="blue" style={{ marginLeft: 8 }}>
                        {String(item.meta.total_queries)} 筆
                      </Tag>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </Col>
      <Col xs={24} md={16}>
        <Card
          size="small"
          title={selected?.filename ?? '週自傳'}
          bodyStyle={{ padding: 16, maxHeight: 640, overflowY: 'auto' }}
        >
          {!selected ? (
            <Alert type="info" message="尚未選擇週自傳" showIcon />
          ) : (
            <MarkdownRenderer content={selected.body_preview} />
          )}
        </Card>
      </Col>
    </Row>
  );
};

export default AutobiographyTab;
