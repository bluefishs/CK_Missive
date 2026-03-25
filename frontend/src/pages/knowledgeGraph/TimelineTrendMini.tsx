import React from 'react';
import { Spin, Tooltip, Typography } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { getTimelineAggregate } from '../../api/ai/knowledgeGraph';

const { Text } = Typography;

const TimelineTrendMini: React.FC<{
  onClickPeriod?: (rocYear: number) => void;
  activeYear?: number;
}> = ({ onClickPeriod, activeYear }) => {
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

export default TimelineTrendMini;
