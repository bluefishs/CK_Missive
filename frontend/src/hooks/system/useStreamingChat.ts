/**
 * useStreamingChat - Re-export from @ck-shared/ui-components
 *
 * The generic streaming chat hook lives in shared-modules.
 * This file re-exports it for backwards compatibility.
 *
 * @version 2.0.0
 * @created 2026-03-14
 * @updated 2026-03-15 - v2.0.0 migrated to @ck-shared/ui-components
 */

export {
  useStreamingChat,
  type BaseChatMessage,
  type BaseAgentStepInfo,
  type BaseSourceItem,
  type StreamingChatCallbacks,
  type StreamingChatAPIs,
  type UseStreamingChatOptions,
  type UseStreamingChatReturn,
} from '@ck-shared/ui-components/hooks';
