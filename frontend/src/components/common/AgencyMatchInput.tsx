/**
 * AI 智慧機關匹配輸入元件
 *
 * 結合 Ant Design Select + AI 機關匹配 API：
 * - 使用者可直接從下拉選單選擇既有機關
 * - 手動輸入未在清單中的機關名稱時，自動觸發 AI 匹配建議
 * - 支援 debounce、載入狀態、匹配結果顯示
 *
 * @version 1.0.0
 * @created 2026-02-26
 */

import React, { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import { Select, Space, Tag, Tooltip, Typography } from 'antd';
import { ThunderboltOutlined, CheckCircleOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import { aiApi } from '../../api/aiApi';
import type { AgencyMatchResult, AgencyCandidate } from '../../types/ai';

const { Text } = Typography;

export interface AgencyMatchInputProps {
  /** 下拉選項 (同 buildAgencyOptions 回傳值) */
  options: Array<{ value: string; label: string }>;
  /** 選項載入中 */
  loading?: boolean;
  /** 當前值 */
  value?: string;
  /** 值變更回呼 */
  onChange?: (value: string) => void;
  /** placeholder 文字 */
  placeholder?: string;
  /** 是否允許清除 */
  allowClear?: boolean;
  /** 機關候選列表 (供 AI 匹配使用，含 id/name/short_name) */
  candidates?: AgencyCandidate[];
  /** 是否啟用 AI 匹配 (預設 true) */
  aiEnabled?: boolean;
  /** AI 匹配 debounce 延遲 (ms, 預設 600) */
  debounceMs?: number;
}

/**
 * 智慧機關選擇輸入
 *
 * 基本行為與 Select showSearch 完全相同，額外增加：
 * - 搜尋文字在既有選項中找不到高度匹配時，自動呼叫 AI 匹配
 * - 匹配結果顯示在下拉選單頂部，帶 AI 標籤
 */
export const AgencyMatchInput: React.FC<AgencyMatchInputProps> = ({
  options,
  loading = false,
  value,
  onChange,
  placeholder = '請選擇或輸入機關名稱',
  allowClear = true,
  candidates,
  aiEnabled = true,
  debounceMs = 600,
}) => {
  const [searchText, setSearchText] = useState('');
  const [aiSuggestion, setAiSuggestion] = useState<AgencyMatchResult | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiSource, setAiSource] = useState<string>('');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // 元件 unmount 時清理 debounce 計時器
  useEffect(() => {
    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, []);

  // 建構 AI 候選列表 (從 options 提取 id/name，若有 candidates prop 優先使用)
  const aiCandidates = useMemo<AgencyCandidate[]>(() => {
    if (candidates && candidates.length > 0) return candidates;
    // fallback: 從 options 提取（無 id，AI 匹配使用 name 即可）
    return options.map((opt, idx) => ({
      id: idx + 1,
      name: opt.value,
    }));
  }, [candidates, options]);

  const triggerAiMatch = useCallback(
    async (text: string) => {
      if (!aiEnabled || text.length < 2 || aiCandidates.length === 0) {
        setAiSuggestion(null);
        return;
      }

      // 檢查是否在既有選項中有完全匹配
      const exactMatch = options.some(
        (opt) => opt.value === text || opt.label.includes(text)
      );
      if (exactMatch) {
        setAiSuggestion(null);
        return;
      }

      setAiLoading(true);
      try {
        const response = await aiApi.matchAgency({
          agency_name: text,
          candidates: aiCandidates.slice(0, 20), // API 限制最多 20 個候選
        });

        if (response.best_match && response.best_match.score >= 0.5) {
          setAiSuggestion(response.best_match);
          setAiSource(response.source);
        } else {
          setAiSuggestion(null);
        }
      } catch {
        setAiSuggestion(null);
      } finally {
        setAiLoading(false);
      }
    },
    [aiEnabled, aiCandidates, options],
  );

  const handleSearch = useCallback(
    (text: string) => {
      setSearchText(text);

      // 清除之前的 debounce
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }

      // 搜尋文字過短時清除建議
      if (text.length < 2) {
        setAiSuggestion(null);
        return;
      }

      // Debounced AI 匹配
      debounceRef.current = setTimeout(() => {
        triggerAiMatch(text);
      }, debounceMs);
    },
    [triggerAiMatch, debounceMs],
  );

  const handleChange = useCallback(
    (val: string) => {
      setAiSuggestion(null);
      setSearchText('');
      onChange?.(val);
    },
    [onChange],
  );

  // 合併選項：AI 建議 + 原始選項
  const mergedOptions = useMemo(() => {
    const result = [...options];

    if (aiSuggestion && searchText.length >= 2) {
      // 在頂部插入 AI 建議
      const alreadyExists = result.some(
        (opt) => opt.value === aiSuggestion.name
      );
      if (!alreadyExists) {
        result.unshift({
          value: aiSuggestion.name,
          label: `${aiSuggestion.name} (AI 建議)`,
        });
      }
    }

    return result;
  }, [options, aiSuggestion, searchText]);

  return (
    <div>
      <Select
        showSearch
        value={value}
        onChange={handleChange}
        onSearch={handleSearch}
        placeholder={placeholder}
        loading={loading || aiLoading}
        allowClear={allowClear}
        filterOption={(input, option) =>
          (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
        }
        options={mergedOptions}
        optionRender={(option) => {
          const isAiSuggested =
            aiSuggestion && option.value === aiSuggestion.name;
          if (isAiSuggested) {
            return (
              <Space>
                <ThunderboltOutlined style={{ color: '#722ed1' }} />
                <span>{aiSuggestion.name}</span>
                <Tag color="purple" style={{ fontSize: 10 }}>
                  AI {Math.round(aiSuggestion.score * 100)}%
                </Tag>
              </Space>
            );
          }
          return <span>{option.label}</span>;
        }}
        style={{ width: '100%' }}
        notFoundContent={
          aiLoading ? (
            <Text type="secondary" style={{ fontSize: 12 }}>
              <ThunderboltOutlined spin /> AI 匹配中...
            </Text>
          ) : undefined
        }
      />
      {/* AI 匹配結果提示 */}
      {aiSuggestion && !aiLoading && searchText.length >= 2 && (
        <div style={{ marginTop: 4 }}>
          <Space size={4}>
            <Tooltip title={`匹配來源: ${aiSource}`}>
              {aiSuggestion.score >= 0.8 ? (
                <CheckCircleOutlined style={{ color: '#52c41a', fontSize: 12 }} />
              ) : (
                <QuestionCircleOutlined style={{ color: '#faad14', fontSize: 12 }} />
              )}
            </Tooltip>
            <Text type="secondary" style={{ fontSize: 11 }}>
              AI 建議: <Text strong style={{ fontSize: 11 }}>{aiSuggestion.name}</Text>
              {' '}({Math.round(aiSuggestion.score * 100)}% 匹配)
            </Text>
          </Space>
        </div>
      )}
    </div>
  );
};

export default AgencyMatchInput;
