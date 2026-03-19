import React from 'react';
import { SynonymManagementContent, DEFAULT_CATEGORIES, CATEGORY_COLORS } from '../components/ai/management/SynonymManagementPanel';
import { ResponsiveContent } from '@ck-shared/ui-components';

// eslint-disable-next-line react-refresh/only-export-components
export { SynonymManagementContent, DEFAULT_CATEGORIES, CATEGORY_COLORS };

/** 獨立頁面包裝（保留向後相容） */
export const AISynonymManagementPage: React.FC = () => (
  <ResponsiveContent maxWidth="full" padding="medium">
    <SynonymManagementContent />
  </ResponsiveContent>
);

export default AISynonymManagementPage;
