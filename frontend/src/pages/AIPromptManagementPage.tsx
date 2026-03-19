import React from 'react';
import { PromptManagementContent } from '../components/ai/management/PromptManagementPanel';
import { ResponsiveContent } from '@ck-shared/ui-components';

export { PromptManagementContent };

/** 獨立頁面包裝（保留向後相容） */
export const AIPromptManagementPage: React.FC = () => (
  <ResponsiveContent maxWidth="full" padding="medium">
    <PromptManagementContent />
  </ResponsiveContent>
);

export default AIPromptManagementPage;
