/**
 * 「來源標案」連結（L3 回指，2026-07-31）
 *
 * 背景（全鏈路架構檢視 §2-D）：標案與案件雙向都看不到對方 ——
 * 案件不知道自己從哪個標案來，人工建立的對應關係下次進來就消失。
 *
 * 案件端只存 `source_tender_id`，故需查一次標案最小資訊才能組出正確路由
 * （ADR-0032 多源分流：ezbid 與 pcc 的 URL namespace 不同）。
 */
import React from 'react';
import { Button, Tooltip } from 'antd';
import { LinkOutlined } from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { tenderApi } from '../../api/tenderApi';
import { ROUTES } from '../../router/types';

interface Props {
  sourceTenderId?: number | null;
  size?: 'small' | 'middle' | 'large';
}

export const SourceTenderLink: React.FC<Props> = ({ sourceTenderId, size = 'middle' }) => {
  const navigate = useNavigate();
  const { data } = useQuery({
    queryKey: ['tender-by-id', sourceTenderId],
    queryFn: () => tenderApi.getById(sourceTenderId as number),
    enabled: !!sourceTenderId,
    staleTime: 5 * 60 * 1000,
  });

  if (!sourceTenderId || !data) return null;

  const to =
    data.source === 'ezbid' && data.ezbid_id
      ? ROUTES.TENDER_DETAIL_EZBID.replace(':ezbidId', encodeURIComponent(data.ezbid_id))
      : data.unit_id && data.job_number
        ? ROUTES.TENDER_DETAIL_PCC
            .replace(':unitId', encodeURIComponent(data.unit_id))
            .replace(':jobNumber', encodeURIComponent(data.job_number))
        : null;

  if (!to) return null;

  return (
    <Tooltip title={`來源標案：${data.title}`}>
      <Button size={size} icon={<LinkOutlined />} onClick={() => navigate(to)}>
        來源標案
      </Button>
    </Tooltip>
  );
};

export default SourceTenderLink;
