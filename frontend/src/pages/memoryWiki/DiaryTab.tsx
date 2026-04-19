/**
 * DiaryTab — Memory Wiki 日記分頁
 *
 * Phase 5 Slice 3 — 左側日期清單 + 右側 markdown 預覽。
 */
import React, { useState } from 'react';
import {
  Alert, Card, Col, DatePicker, Empty, Row, Spin, Tag, Typography,
} from 'antd';
import dayjs, { Dayjs } from 'dayjs';

import MarkdownRenderer from '../../components/common/MarkdownRenderer';
import { useDiaryByDate, useDiaryRecent } from '../../hooks/useMemoryData';

const DiaryTab: React.FC = () => {
  const [selectedDate, setSelectedDate] = useState<Dayjs | null>(dayjs());
  const dateStr = selectedDate ? selectedDate.format('YYYY-MM-DD') : undefined;

  const { data: recent = [], isLoading: loadingRecent } = useDiaryRecent({ limit: 30 });
  const { data: diary, isLoading: loadingDiary } = useDiaryByDate({ date: dateStr });

  return (
    <Row gutter={16} style={{ marginTop: 12 }}>
      <Col xs={24} md={8}>
        <Card size="small" title="近 30 日" bodyStyle={{ padding: 12 }}>
          <DatePicker
            value={selectedDate}
            onChange={setSelectedDate}
            style={{ width: '100%', marginBottom: 12 }}
            allowClear={false}
          />
          {loadingRecent ? (
            <Spin />
          ) : recent.length === 0 ? (
            <Empty description="尚無日記" />
          ) : (
            <div style={{ maxHeight: 480, overflowY: 'auto' }}>
              {recent.map((d) => {
                const fname = d.filename.replace('.md', '');
                const active = fname === dateStr;
                return (
                  <div
                    key={fname}
                    onClick={() => setSelectedDate(dayjs(fname))}
                    style={{
                      padding: '6px 10px',
                      marginBottom: 4,
                      cursor: 'pointer',
                      borderRadius: 4,
                      background: active ? '#e6f4ff' : 'transparent',
                      border: active ? '1px solid #69b1ff' : '1px solid transparent',
                    }}
                  >
                    <Typography.Text strong={active}>{fname}</Typography.Text>
                    {d.meta?.entry_count !== undefined && (
                      <Tag color="blue" style={{ marginLeft: 8 }}>
                        {String(d.meta.entry_count)} 筆
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
          title={`${dateStr} 日記`}
          bodyStyle={{ padding: 16, maxHeight: 600, overflowY: 'auto' }}
        >
          {loadingDiary ? (
            <Spin />
          ) : !diary ? (
            <Alert type="info" message={`${dateStr} 尚無日記`} showIcon />
          ) : (
            <MarkdownRenderer content={diary.body_preview} />
          )}
        </Card>
      </Col>
    </Row>
  );
};

export default DiaryTab;
