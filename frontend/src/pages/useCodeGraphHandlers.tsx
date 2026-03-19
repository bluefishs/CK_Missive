/**
 * Code Graph Management - Admin Handlers Hook
 *
 * Extracted from CodeGraphManagementPage.tsx to reduce main file size.
 */

import { useState, useCallback } from 'react';
import { App, Tag, Divider, Typography } from 'antd';
import { aiApi } from '../api/aiApi';
import type { useCodeWikiGraph } from '../hooks/useCodeWikiGraph';

interface UseCodeGraphHandlersParams {
  codeWiki: ReturnType<typeof useCodeWikiGraph>;
  loadStats: () => void;
}

export function useCodeGraphHandlers({ codeWiki, loadStats }: UseCodeGraphHandlersParams) {
  const { message, modal } = App.useApp();

  const [codeIngestLoading, setCodeIngestLoading] = useState(false);
  const [cycleLoading, setCycleLoading] = useState(false);
  const [archLoading, setArchLoading] = useState(false);
  const [jsonImportLoading, setJsonImportLoading] = useState(false);

  const [ingestIncremental, setIngestIncremental] = useState(true);
  const [ingestClean, setIngestClean] = useState(false);
  const [jsonClean, setJsonClean] = useState(true);

  const handleCodeGraphIngest = useCallback(async () => {
    setCodeIngestLoading(true);
    try {
      const result = await aiApi.triggerCodeGraphIngest({
        incremental: ingestIncremental,
        clean: ingestClean,
      });
      if (result?.success) {
        const parts = [result.message];
        if (result.elapsed_seconds > 0) parts.push(`（耗時 ${result.elapsed_seconds.toFixed(1)}s）`);
        message.success(parts.join(''));
        codeWiki.loadCodeWiki();
        loadStats();
      } else {
        message.error(result?.message || '代碼圖譜入圖失敗');
      }
    } catch {
      message.error('代碼圖譜入圖請求失敗');
    } finally {
      setCodeIngestLoading(false);
    }
  }, [message, ingestIncremental, ingestClean, codeWiki, loadStats]);

  const handleCycleDetection = useCallback(async () => {
    setCycleLoading(true);
    try {
      const result = await aiApi.detectImportCycles();
      if (result?.success) {
        if (result.cycles_found === 0) {
          message.success(`掃描 ${result.total_modules} 個模組、${result.total_import_edges} 條匯入，未發現循環依賴`);
        } else {
          const { Text } = Typography;
          modal.warning({
            title: `發現 ${result.cycles_found} 個循環依賴`,
            width: 600,
            content: (
              <div style={{ maxHeight: 400, overflow: 'auto' }}>
                {result.cycles.slice(0, 20).map((cycle: string[], i: number) => (
                  <div key={i} style={{ marginBottom: 8, fontSize: 12, fontFamily: 'monospace' }}>
                    <Tag color="red">Cycle {i + 1}</Tag>
                    {cycle.join(' → ')}
                  </div>
                ))}
                {result.cycles_found > 20 && (
                  <Text type="secondary">...還有 {result.cycles_found - 20} 個循環</Text>
                )}
              </div>
            ),
          });
        }
      } else {
        message.error('循環偵測失敗');
      }
    } catch {
      message.error('循環偵測請求失敗');
    } finally {
      setCycleLoading(false);
    }
  }, [message, modal]);

  const handleArchAnalysis = useCallback(async () => {
    setArchLoading(true);
    try {
      const result = await aiApi.analyzeArchitecture();
      if (result?.success) {
        modal.info({
          title: '架構分析報告',
          width: 700,
          content: (
            <div style={{ maxHeight: 500, overflow: 'auto', fontSize: 12 }}>
              <Divider titlePlacement="left" style={{ fontSize: 13 }}>概要</Divider>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {Object.entries(result.summary || {}).map(([k, v]) => (
                  <Tag key={k}>{k}: {String(v)}</Tag>
                ))}
              </div>
              {result.complexity_hotspots.length > 0 && (
                <>
                  <Divider titlePlacement="left" style={{ fontSize: 13 }}>高耦合模組 (出向依賴最多)</Divider>
                  {result.complexity_hotspots.map((h: { module: string; outgoing_deps: number }, i: number) => (
                    <div key={i} style={{ fontFamily: 'monospace', marginBottom: 2 }}>
                      <Tag color="red">{h.outgoing_deps}</Tag> {h.module}
                    </div>
                  ))}
                </>
              )}
              {result.hub_modules.length > 0 && (
                <>
                  <Divider titlePlacement="left" style={{ fontSize: 13 }}>樞紐模組 (被匯入最多)</Divider>
                  {result.hub_modules.map((h: { module: string; imported_by: number }, i: number) => (
                    <div key={i} style={{ fontFamily: 'monospace', marginBottom: 2 }}>
                      <Tag color="blue">{h.imported_by}</Tag> {h.module}
                    </div>
                  ))}
                </>
              )}
              {result.large_modules.length > 0 && (
                <>
                  <Divider titlePlacement="left" style={{ fontSize: 13 }}>大型模組 (行數最多)</Divider>
                  {result.large_modules.map((h: { module: string; lines: number }, i: number) => (
                    <div key={i} style={{ fontFamily: 'monospace', marginBottom: 2 }}>
                      <Tag color="orange">{h.lines} 行</Tag> {h.module}
                    </div>
                  ))}
                </>
              )}
              {result.god_classes.length > 0 && (
                <>
                  <Divider titlePlacement="left" style={{ fontSize: 13 }}>巨型類別 (方法數最多)</Divider>
                  {result.god_classes.map((h: { class: string; method_count: number }, i: number) => (
                    <div key={i} style={{ fontFamily: 'monospace', marginBottom: 2 }}>
                      <Tag color="purple">{h.method_count} 方法</Tag> {h.class}
                    </div>
                  ))}
                </>
              )}
              {result.orphan_modules.length > 0 && (
                <>
                  <Divider titlePlacement="left" style={{ fontSize: 13 }}>孤立模組 (無入向匯入) — 前 {result.orphan_modules.length} 個</Divider>
                  <div style={{ fontFamily: 'monospace', lineHeight: 1.8 }}>
                    {result.orphan_modules.map((m: string, i: number) => (
                      <Tag key={i} style={{ marginBottom: 2 }}>{m}</Tag>
                    ))}
                  </div>
                </>
              )}
            </div>
          ),
        });
      } else {
        message.error('架構分析失敗');
      }
    } catch {
      message.error('架構分析請求失敗');
    } finally {
      setArchLoading(false);
    }
  }, [message, modal]);

  const handleJsonImport = useCallback(async () => {
    setJsonImportLoading(true);
    try {
      const result = await aiApi.importJsonGraph({ clean: jsonClean });
      if (result?.success) {
        message.success(`${result.message}（耗時 ${result.elapsed_seconds.toFixed(1)}s）`);
        codeWiki.loadCodeWiki();
        loadStats();
      } else {
        message.error(result?.message || 'JSON 圖譜匯入失敗');
      }
    } catch {
      message.error('JSON 圖譜匯入請求失敗');
    } finally {
      setJsonImportLoading(false);
    }
  }, [message, jsonClean, codeWiki, loadStats]);

  return {
    codeIngestLoading,
    cycleLoading,
    archLoading,
    jsonImportLoading,
    ingestIncremental,
    setIngestIncremental,
    ingestClean,
    setIngestClean,
    jsonClean,
    setJsonClean,
    handleCodeGraphIngest,
    handleCycleDetection,
    handleArchAnalysis,
    handleJsonImport,
  };
}
