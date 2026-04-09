/**
 * Gateway 健康狀態徽章
 *
 * 週期性檢查 NemoClaw/OpenClaw Gateway 連線狀態。
 */
import React from 'react';
import { Badge } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { checkGatewayHealth } from '../../api/digitalTwin';

export const GatewayHealthBadge: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['dt-gateway-health'],
    queryFn: checkGatewayHealth,
    staleTime: 30_000,
    refetchInterval: 60_000,
  });
  if (isLoading) return <Badge status="processing" text="檢測中..." />;
  if (!data) return <Badge status="default" text="未知" />;
  return (
    <Badge
      status={data.available ? 'success' : 'error'}
      text={data.available ? `連線正常 (${data.latencyMs}ms)` : '離線'}
    />
  );
};
