/**
 * CodeWikiFiltersCard - 圖譜篩選面板
 *
 * 共用於 KnowledgeGraphPage、CodeGraphManagementPage、DatabaseGraphPage。
 * 透過 props 傳入不同的選項常數以適配不同圖譜。
 */
import React from 'react';
import { Card, Space, Button, Select, Input, Typography } from 'antd';
import { CodeOutlined, SyncOutlined } from '@ant-design/icons';

import { CODE_WIKI_TYPE_OPTIONS, CODE_RELATION_OPTIONS } from '../../constants/codeGraphOptions';
import type { UseCodeWikiGraphReturn } from '../../hooks/useCodeWikiGraph';

const { Text } = Typography;

interface OptionItem {
  label: string;
  value: string;
}

export interface CodeWikiFiltersCardProps {
  graph: UseCodeWikiGraphReturn;
  /** Card 標題，預設 "代碼圖譜篩選" */
  title?: string;
  /** Card 標題圖示，預設 CodeOutlined */
  icon?: React.ReactNode;
  /** 實體類型選項，預設 CODE_WIKI_TYPE_OPTIONS */
  typeOptions?: readonly OptionItem[];
  /** 關聯類型選項，預設 CODE_RELATION_OPTIONS */
  relationOptions?: readonly OptionItem[];
  /** 載入按鈕文字，預設 "載入代碼圖譜" */
  loadButtonText?: string;
  /** 是否顯示模組前綴輸入框，預設 true */
  showModulePrefix?: boolean;
}

export const CodeWikiFiltersCard: React.FC<CodeWikiFiltersCardProps> = ({
  graph,
  title = '代碼圖譜篩選',
  icon = <CodeOutlined />,
  typeOptions = CODE_WIKI_TYPE_OPTIONS,
  relationOptions = CODE_RELATION_OPTIONS,
  loadButtonText = '載入代碼圖譜',
  showModulePrefix = true,
}) => {
  const displayData = graph.filteredData ?? graph.codeWikiData;

  return (
    <Card
      size="small"
      title={
        <span style={{ fontSize: 13 }}>
          {icon} {title}
        </span>
      }
      styles={{ body: { padding: '8px 12px' } }}
    >
      <Space vertical style={{ width: '100%' }} size={8}>
        <div>
          <Text style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>實體類型</Text>
          <Select
            mode="multiple"
            size="small"
            style={{ width: '100%' }}
            value={graph.entityTypes}
            onChange={graph.setEntityTypes}
            options={typeOptions.map((o) => ({ label: o.label, value: o.value }))}
            placeholder="選擇要顯示的實體類型"
          />
        </div>
        {showModulePrefix && (
          <div>
            <Text style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>模組前綴</Text>
            <Input
              size="small"
              placeholder="如 app.services.ai"
              value={graph.modulePrefix}
              onChange={(e) => graph.setModulePrefix(e.target.value)}
              allowClear
            />
          </div>
        )}
        <div>
          <Text style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>關聯類型篩選</Text>
          <Select
            mode="multiple"
            size="small"
            style={{ width: '100%' }}
            value={graph.relTypes}
            onChange={graph.setRelTypes}
            options={relationOptions.map((o) => ({ label: o.label, value: o.value }))}
            placeholder="全部（不篩選）"
            allowClear
          />
        </div>
        <Button
          block
          size="small"
          type="primary"
          icon={<SyncOutlined spin={graph.loading} />}
          loading={graph.loading}
          onClick={graph.loadCodeWiki}
          disabled={graph.entityTypes.length === 0}
        >
          {loadButtonText}
        </Button>
        {graph.codeWikiData && displayData && (
          <Text type="secondary" style={{ fontSize: 11 }}>
            {displayData.nodes.length} 個節點 · {displayData.edges.length} 條關聯
            {graph.relTypes.length > 0 && ' (已篩選)'}
          </Text>
        )}
      </Space>
    </Card>
  );
};
