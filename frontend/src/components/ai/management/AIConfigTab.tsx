/**
 * AIConfigTab - AI 配置合併視圖
 *
 * 合併同義詞管理 + Prompt 管理，透過 Segmented 切換子視圖。
 *
 * @version 1.0.0
 * @created 2026-02-27
 */
import React, { useState } from 'react';
import { Segmented } from 'antd';
import { TagsOutlined, RobotOutlined } from '@ant-design/icons';

import { SynonymManagementContent } from '../../../pages/AISynonymManagementPage';
import { PromptManagementContent } from '../../../pages/AIPromptManagementPage';

type SubView = 'synonyms' | 'prompts';

export const AIConfigTab: React.FC = () => {
  const [activeView, setActiveView] = useState<SubView>('synonyms');

  return (
    <div>
      <Segmented
        options={[
          { label: <span><TagsOutlined /> 同義詞管理</span>, value: 'synonyms' },
          { label: <span><RobotOutlined /> Prompt 管理</span>, value: 'prompts' },
        ]}
        value={activeView}
        onChange={(val) => setActiveView(val as SubView)}
        style={{ marginBottom: 16 }}
      />
      {activeView === 'synonyms' && <SynonymManagementContent />}
      {activeView === 'prompts' && <PromptManagementContent />}
    </div>
  );
};
