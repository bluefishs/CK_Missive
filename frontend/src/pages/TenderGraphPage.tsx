/**
 * 標案知識圖譜頁面
 *
 * 視覺化 機關→標案→廠商 關係網絡
 * 使用 react-force-graph-2d 力導引圖
 *
 * @version 1.0.0
 */
import React, { useState, useCallback, useRef, useMemo } from 'react';
import { Card, Input, Row, Col, Typography, Space, Tag, Statistic, App, Spin } from 'antd';
import { ApartmentOutlined, SearchOutlined } from '@ant-design/icons';
import ForceGraph2D from 'react-force-graph-2d';
import { ResponsiveContent } from '@ck-shared/ui-components';
import { useQuery } from '@tanstack/react-query';
import { tenderApi } from '../api/tenderApi';

const { Title, Text } = Typography;

// 節點顏色
const NODE_COLORS: Record<string, string> = {
  agency: '#1890ff',   // 藍 = 機關
  tender: '#faad14',   // 金 = 標案
  company: '#52c41a',  // 綠 = 廠商
};

const NODE_SIZES: Record<string, number> = {
  agency: 8,
  tender: 5,
  company: 6,
};

interface GraphNode {
  id: string;
  name: string;
  type: string;
  category?: string;
  date?: string;
  x?: number;
  y?: number;
}

interface GraphLink {
  source: string;
  target: string;
  relation: string;
}

const TenderGraphPage: React.FC = () => {
  const { message } = App.useApp();
  const [query, setQuery] = useState('測量');
  const [searchInput, setSearchInput] = useState('測量');
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(undefined);
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['tender', 'graph', query],
    queryFn: () => tenderApi.getGraph(query, 30),
    enabled: !!query,
    staleTime: 10 * 60 * 1000,
  });

  const graphData = useMemo(() => {
    if (!data) return { nodes: [], links: [] };
    return {
      nodes: data.nodes as GraphNode[],
      links: data.edges as GraphLink[],
    };
  }, [data]);

  const handleSearch = useCallback((v: string) => {
    const q = v.trim();
    if (!q) { message.warning('請輸入關鍵字'); return; }
    setQuery(q);
  }, [message]);

  const paintNode = useCallback((node: GraphNode, ctx: CanvasRenderingContext2D) => {
    const size = NODE_SIZES[node.type] || 5;
    const color = NODE_COLORS[node.type] || '#999';
    const isHover = hoverNode?.id === node.id;

    // 圓形節點
    ctx.beginPath();
    ctx.arc(node.x || 0, node.y || 0, isHover ? size * 1.5 : size, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    if (isHover) {
      ctx.strokeStyle = '#fff';
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // 標籤
    const label = node.name.length > 12 ? node.name.slice(0, 12) + '...' : node.name;
    ctx.font = `${isHover ? 'bold ' : ''}${isHover ? 4 : 3}px sans-serif`;
    ctx.fillStyle = isHover ? '#000' : '#666';
    ctx.textAlign = 'center';
    ctx.fillText(label, node.x || 0, (node.y || 0) + size + 4);
  }, [hoverNode]);

  return (
    <ResponsiveContent maxWidth="full" padding="medium">
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle" gutter={[16, 16]}>
          <Col>
            <Title level={3} style={{ margin: 0 }}>
              <ApartmentOutlined style={{ marginRight: 8 }} />標案知識圖譜
            </Title>
          </Col>
          <Col>
            <Input.Search
              placeholder="輸入關鍵字建構圖譜"
              value={searchInput}
              onChange={e => setSearchInput(e.target.value)}
              onSearch={handleSearch}
              enterButton={<SearchOutlined />}
              style={{ width: 300 }}
            />
          </Col>
        </Row>

        {data?.stats && (
          <Row gutter={[16, 8]} style={{ marginTop: 12 }}>
            <Col><Statistic title="機關" value={data.stats.agencies} valueStyle={{ color: NODE_COLORS.agency, fontSize: 18 }} /></Col>
            <Col><Statistic title="標案" value={data.stats.tenders} valueStyle={{ color: NODE_COLORS.tender, fontSize: 18 }} /></Col>
            <Col><Statistic title="廠商" value={data.stats.companies} valueStyle={{ color: NODE_COLORS.company, fontSize: 18 }} /></Col>
            <Col><Statistic title="關係" value={data.stats.edges} valueStyle={{ fontSize: 18 }} /></Col>
            <Col>
              <Space>
                <Tag color="blue">● 機關</Tag>
                <Tag color="gold">● 標案</Tag>
                <Tag color="green">● 廠商</Tag>
              </Space>
            </Col>
          </Row>
        )}
      </Card>

      <Card bodyStyle={{ padding: 0, position: 'relative' }}>
        {isLoading ? (
          <div style={{ height: 500, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Spin size="large" tip="建構圖譜中..." />
          </div>
        ) : graphData.nodes.length === 0 ? (
          <div style={{ height: 500, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Text type="secondary">輸入關鍵字開始探索標案關係網絡</Text>
          </div>
        ) : (
          <ForceGraph2D
            ref={fgRef}
            graphData={graphData}
            width={typeof window !== 'undefined' ? Math.min(window.innerWidth - 80, 1400) : 1200}
            height={500}
            nodeCanvasObject={paintNode as unknown as undefined}
            nodePointerAreaPaint={(node: GraphNode, color: string, ctx: CanvasRenderingContext2D) => {
              const size = NODE_SIZES[node.type] || 5;
              ctx.beginPath();
              ctx.arc(node.x || 0, node.y || 0, size + 2, 0, 2 * Math.PI);
              ctx.fillStyle = color;
              ctx.fill();
            }}
            linkColor={() => '#ddd'}
            linkWidth={1}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={0.8}
            linkLabel={(link: GraphLink) => link.relation}
            onNodeHover={(node: GraphNode | null) => setHoverNode(node)}
            onNodeClick={(node: GraphNode) => {
              if (node.type === 'tender') {
                message.info(`${node.name}`);
              }
            }}
            cooldownTicks={100}
            enableNodeDrag
          />
        )}

        {hoverNode && (
          <div style={{
            position: 'absolute', top: 12, right: 12,
            background: 'white', padding: 12, borderRadius: 8,
            boxShadow: '0 2px 8px rgba(0,0,0,0.15)', maxWidth: 280,
          }}>
            <Tag color={NODE_COLORS[hoverNode.type]}>{
              hoverNode.type === 'agency' ? '招標機關' :
              hoverNode.type === 'tender' ? '標案' : '廠商'
            }</Tag>
            <div style={{ marginTop: 4 }}><Text strong>{hoverNode.name}</Text></div>
            {hoverNode.date && <div><Text type="secondary">{hoverNode.date}</Text></div>}
            {hoverNode.category && <div><Tag>{hoverNode.category}</Tag></div>}
          </div>
        )}
      </Card>
    </ResponsiveContent>
  );
};

export default TenderGraphPage;
