/**
 * BattleTab - Tab4 投標戰情
 *
 * Sections:
 *   1. 歷史相似標案
 *   2. 本案潛在對手 — 競爭強度
 *   3. 機關生態完整分析
 */
import React from 'react';
import {
  Card, Typography, Space, List, Tag, Button, Empty,
} from 'antd';
import { useNavigate } from 'react-router-dom';

const { Text } = Typography;

export interface BattleTabProps {
  battleRoom?: {
    similar_tenders?: Array<{ title: string; date: string; unit_name: string; winner_names?: string[] }>;
    competitors?: Array<{
      name: string; count?: number; appear_count?: number;
      win_count?: number; win_rate?: number; total_amount?: number;
    }>;
  };
  orgEcosystem?: {
    org_name?: string;
    total?: number;
    top_vendors?: Array<{ name: string; appear_count: number; win_count: number; win_rate: number }>;
    recent_tenders?: Array<{
      title: string; date: string; type: string; unit_name: string;
      unit_id: string; job_number: string; winner_names?: string[];
    }>;
  };
  unitName?: string;
}

const BattleTab: React.FC<BattleTabProps> = ({ battleRoom: battle, orgEcosystem, unitName }) => {
  const navigate = useNavigate();

  return (
    <div>
      {/* 1. 歷史相似標案 */}
      <Card title="① 歷史相似標案" size="small" style={{ marginBottom: 16 }}>
        {battle?.similar_tenders?.length ? (
          <List size="small" dataSource={battle.similar_tenders.slice(0, 10)}
            renderItem={(t) => (
              <List.Item>
                <List.Item.Meta
                  title={t.title}
                  description={<Space><Text type="secondary">{t.date}</Text>{t.winner_names?.map((w, i) => <Tag key={i} color="green">{w}</Tag>)}</Space>}
                />
              </List.Item>
            )}
          />
        ) : <Empty description="查無相似標案" />}
      </Card>

      {/* 2. 潛在對手 — 競爭強度 */}
      <Card title="② 本案潛在對手 — 競爭強度" size="small" style={{ marginBottom: 16 }}>
        {battle?.competitors?.length ? (
          <table style={{ width: '100%', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #f0f0f0', textAlign: 'left' }}>
                <th style={{ padding: '8px 4px' }}>廠商</th>
                <th style={{ padding: '8px 4px', textAlign: 'center' }}>出現</th>
                <th style={{ padding: '8px 4px', textAlign: 'center' }}>得標</th>
                <th style={{ padding: '8px 4px', textAlign: 'center' }}>得標率</th>
                <th style={{ padding: '8px 4px', textAlign: 'right' }}>得標金額</th>
              </tr>
            </thead>
            <tbody>
              {battle.competitors.slice(0, 10).map((c, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #f5f5f5', cursor: 'pointer' }}
                  onClick={() => window.open(`/tender/company-profile?q=${encodeURIComponent(c.name)}`, '_blank')}>
                  <td style={{ padding: '6px 4px' }}>
                    <a>{c.name}</a>
                  </td>
                  <td style={{ padding: '6px 4px', textAlign: 'center' }}>{c.appear_count ?? c.count ?? 0}</td>
                  <td style={{ padding: '6px 4px', textAlign: 'center' }}>
                    <Tag color={(c.win_count ?? 0) > 0 ? 'green' : 'default'}>{c.win_count ?? 0}</Tag>
                  </td>
                  <td style={{ padding: '6px 4px', textAlign: 'center' }}>
                    <Tag color={c.win_rate && c.win_rate >= 50 ? 'blue' : 'default'}>{c.win_rate ?? 0}%</Tag>
                  </td>
                  <td style={{ padding: '6px 4px', textAlign: 'right', color: '#1890ff' }}>
                    {c.total_amount ? `${(c.total_amount / 10000).toFixed(0)}萬` : '–'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <Empty description="查無潛在對手資料" />}
      </Card>

      {/* 3. 機關生態完整分析 */}
      <Card title={`③ 機關生態 — ${orgEcosystem?.org_name ?? unitName ?? ''} (${orgEcosystem?.total ?? 0} 筆)`} size="small"
        extra={<Button type="link" size="small" onClick={() => window.open(`/tender/org-ecosystem?org=${encodeURIComponent(unitName ?? '')}`, '_blank')}>獨立頁面 →</Button>}
      >
        {orgEcosystem?.top_vendors?.length ? (
          <>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>Top 廠商 — 競爭強度</Text>
            <table style={{ width: '100%', fontSize: 13, marginBottom: 16 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #f0f0f0', textAlign: 'left' }}>
                  <th style={{ padding: '6px 4px' }}>廠商</th>
                  <th style={{ padding: '6px 4px', textAlign: 'center' }}>出現</th>
                  <th style={{ padding: '6px 4px', textAlign: 'center' }}>得標</th>
                  <th style={{ padding: '6px 4px', textAlign: 'center' }}>得標率</th>
                </tr>
              </thead>
              <tbody>
                {orgEcosystem.top_vendors.slice(0, 10).map((v, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #f5f5f5', cursor: 'pointer' }}
                    onClick={() => window.open(`/tender/company-profile?q=${encodeURIComponent(v.name)}`, '_blank')}>
                    <td style={{ padding: '5px 4px' }}><a>{v.name}</a></td>
                    <td style={{ padding: '5px 4px', textAlign: 'center' }}>{v.appear_count}</td>
                    <td style={{ padding: '5px 4px', textAlign: 'center' }}><Tag color={(v.win_count ?? 0) > 0 ? 'green' : 'default'}>{v.win_count}</Tag></td>
                    <td style={{ padding: '5px 4px', textAlign: 'center' }}><Tag color={v.win_rate >= 50 ? 'blue' : 'default'}>{v.win_rate}%</Tag></td>
                  </tr>
                ))}
              </tbody>
            </table>

            {orgEcosystem.recent_tenders?.length ? (
              <>
                <Text strong style={{ display: 'block', marginBottom: 8 }}>近期標案</Text>
                <List size="small" dataSource={orgEcosystem.recent_tenders.slice(0, 8)}
                  renderItem={(r) => (
                    <List.Item actions={[<Button key="go" type="link" size="small" onClick={() => navigate(`/tender/${encodeURIComponent(r.unit_id)}/${encodeURIComponent(r.job_number)}`)}>查看</Button>]}>
                      <List.Item.Meta title={r.title} description={<Space><Tag>{r.type?.slice(0, 10)}</Tag><Text type="secondary">{r.date}</Text>{r.winner_names?.map((w, i) => <Tag key={i} color="green">{w}</Tag>)}</Space>} />
                    </List.Item>
                  )}
                />
              </>
            ) : null}
          </>
        ) : <Empty description="查無機關生態資料" />}
      </Card>
    </div>
  );
};

export default BattleTab;
