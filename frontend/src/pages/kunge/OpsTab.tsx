/**
 * 坤哥 — 運維儀表板 Tab
 *
 * v5.8.1 整合：承接原 /admin/ai-assistant + /agent/dashboard + /digital-twin
 * - admin 使用者：見管理模式（12 子頁籤：效能/分析/管線/服務狀態/雙模式...）
 * - 一般使用者：見使用者模式（7 子頁籤：對話/自省/追蹤/派工/儀表板/進化/拓撲）
 *
 * @version 1.0.0 — 2026-04-22
 */

import React from 'react';
import { Alert } from 'antd';
import OpsDashboard from '../../components/kunge/OpsDashboard';
import { useAuthGuard } from '../../hooks/utility/useAuthGuard';

export const OpsTab: React.FC = () => {
  const { isAdmin } = useAuthGuard();

  return (
    <>
      {isAdmin ? (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 12, fontSize: 12 }}
          message="運維儀表板 — 管理模式"
          description="效能監控、資料管線、服務狀態、雙模式比較；一般使用者看到的是精簡的 7 頁籤版本。"
        />
      ) : null}
      <OpsDashboard mode={isAdmin ? 'admin' : 'user'} />
    </>
  );
};

export default OpsTab;
