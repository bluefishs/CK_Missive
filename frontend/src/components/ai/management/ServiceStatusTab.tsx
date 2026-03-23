/**
 * ServiceStatusTab - 服務狀態整合視圖
 *
 * 單一頁面：全部服務健康度 + Rate Limit + 配置 + Ollama 管理。
 * 管理員可一次看到所有基礎設施狀態，不需切換。
 *
 * @version 3.0.0
 * @created 2026-02-27
 * @updated 2026-03-23 — 新增系統覆盤儀表板 (ReviewDashboardPanel)
 */
import React from 'react';
import { Divider, Typography } from 'antd';
import { CloudServerOutlined, DeploymentUnitOutlined } from '@ant-design/icons';

import { ServiceMonitorTab } from './ServiceMonitorTab';
import { OllamaManagementTab } from './OllamaManagementTab';
import { ReviewDashboardPanel } from './ReviewDashboardPanel';

const { Text } = Typography;

export const ServiceStatusTab: React.FC = () => {
  return (
    <div>
      <OllamaManagementTab />

      <Divider style={{ margin: '24px 0' }}>
        <Text type="secondary" style={{ fontSize: 13 }}>
          <DeploymentUnitOutlined /> 系統覆盤儀表板
        </Text>
      </Divider>

      <ReviewDashboardPanel />

      <Divider style={{ margin: '24px 0' }}>
        <Text type="secondary" style={{ fontSize: 13 }}>
          <CloudServerOutlined /> 系統監控與配置
        </Text>
      </Divider>

      <ServiceMonitorTab />
    </div>
  );
};
