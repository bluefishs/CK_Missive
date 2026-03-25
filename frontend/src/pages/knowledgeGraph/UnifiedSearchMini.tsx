import React, { useState, useCallback, useRef } from 'react';
import { Input, Spin, Tag, Typography, Empty } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { unifiedGraphSearch } from '../../api/ai/knowledgeGraph';
import type { UnifiedGraphResult } from '../../types/ai';

const { Text } = Typography;

const SOURCE_TAG_COLOR: Record<string, string> = {
  kg: 'blue',
  code: 'green',
  db: 'orange',
};

const UnifiedSearchMini: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<UnifiedGraphResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>();

  const handleSearch = useCallback(async (value: string) => {
    const trimmed = value.trim();
    if (trimmed.length < 2) {
      setResults([]);
      setSearched(false);
      return;
    }
    setLoading(true);
    setSearched(true);
    try {
      const resp = await unifiedGraphSearch({ query: trimmed, limit_per_graph: 5 });
      setResults(resp?.results ?? []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    if (timerRef.current) clearTimeout(timerRef.current);
    if (val.trim().length >= 2) {
      timerRef.current = setTimeout(() => handleSearch(val), 400);
    } else {
      setResults([]);
      setSearched(false);
    }
  }, [handleSearch]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      <Input
        size="small"
        placeholder="跨圖譜搜尋 (KG+Code+DB)..."
        prefix={<SearchOutlined style={{ color: '#999' }} />}
        value={query}
        onChange={handleChange}
        onPressEnter={() => handleSearch(query)}
        allowClear
        onClear={() => { setResults([]); setSearched(false); setQuery(''); }}
      />
      {loading && <Spin size="small" style={{ alignSelf: 'center' }} />}
      {!loading && searched && results.length === 0 && (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="無結果" style={{ margin: '4px 0' }} />
      )}
      {!loading && results.length > 0 && (
        <div style={{ maxHeight: 180, overflow: 'auto' }}>
          {results.map((r, i) => (
            <div key={`${r.source}-${r.name}-${i}`} style={{ padding: '3px 0', borderBottom: '1px solid #f5f5f5' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <Tag color={SOURCE_TAG_COLOR[r.source] ?? 'default'} style={{ fontSize: 10, lineHeight: '16px', margin: 0 }}>
                  {r.source.toUpperCase()}
                </Tag>
                <Text strong style={{ fontSize: 12, flex: 1 }} ellipsis>{r.name}</Text>
              </div>
              {r.description && (
                <Text type="secondary" style={{ fontSize: 10, marginLeft: 4 }} ellipsis>
                  {r.description}
                </Text>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default UnifiedSearchMini;
