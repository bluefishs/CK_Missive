/**
 * 里程碑 + 甘特圖合併頁籤
 *
 * 上方：里程碑 CRUD 表格（MilestonesTab）
 * 下方：Mermaid 甘特圖（GanttTab）
 *
 * @version 1.0.0
 */
import { Suspense, lazy } from 'react';
import { Spin, Divider } from 'antd';

const MilestonesTab = lazy(() => import('./MilestonesTab'));
const GanttTab = lazy(() => import('./GanttTab'));

interface MilestonesGanttTabProps {
  pmCaseId: number;
}

export default function MilestonesGanttTab({ pmCaseId }: MilestonesGanttTabProps) {
  return (
    <div>
      <Suspense fallback={<Spin />}>
        <MilestonesTab pmCaseId={pmCaseId} />
      </Suspense>
      <Divider style={{ margin: '16px 0' }} />
      <Suspense fallback={<Spin />}>
        <GanttTab pmCaseId={pmCaseId} />
      </Suspense>
    </div>
  );
}
