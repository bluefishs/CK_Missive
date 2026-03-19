/**
 * PM 案件甘特圖頁籤
 *
 * 使用 Mermaid Gantt 語法渲染里程碑時程
 */
import React, { Suspense } from 'react';
import { Card, Empty, Spin } from 'antd';
import { usePMCaseGantt } from '../../hooks/business/usePMCases';

const MermaidBlock = React.lazy(() => import('../../components/common/MermaidBlock'));

interface GanttTabProps {
  pmCaseId: number;
}

export default function GanttTab({ pmCaseId }: GanttTabProps) {
  const { data: ganttCode, isLoading } = usePMCaseGantt(pmCaseId);

  if (isLoading) return <Spin description="載入甘特圖..." style={{ display: 'block', margin: '40px auto' }} />;

  if (!ganttCode) {
    return (
      <Card>
        <Empty description="尚無里程碑資料（請先新增含日期的里程碑）" />
      </Card>
    );
  }

  return (
    <Card title="里程碑甘特圖" styles={{ body: { padding: 16 } }}>
      <Suspense fallback={<Spin description="渲染圖表..."><div style={{ padding: 40 }} /></Spin>}>
        <MermaidBlock code={ganttCode} />
      </Suspense>
    </Card>
  );
}
