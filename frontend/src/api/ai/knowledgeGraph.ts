/**
 * 知識圖譜 Phase 2 API
 *
 * 正規化實體搜尋、鄰居、詳情、時間軸、入圖、合併等。
 *
 * @version 1.0.0
 * @created 2026-02-24
 */

import { apiClient } from '../client';
import { AI_ENDPOINTS } from '../endpoints';
import { logger } from '../../services/logger';
import type {
  KGEntitySearchRequest,
  KGEntitySearchResponse,
  KGNeighborsRequest,
  KGNeighborsResponse,
  KGEntityDetailRequest,
  KGEntityDetailResponse,
  KGTimelineRequest,
  KGTimelineResponse,
  KGTopEntitiesRequest,
  KGTopEntitiesResponse,
  KGGraphStatsResponse,
  KGIngestRequest,
  KGIngestResponse,
  KGMergeEntitiesRequest,
  KGMergeEntitiesResponse,
} from './types';

/** 搜尋正規化實體 */
export async function searchGraphEntities(
  request: KGEntitySearchRequest,
): Promise<KGEntitySearchResponse> {
  return await apiClient.post<KGEntitySearchResponse>(
    AI_ENDPOINTS.GRAPH_ENTITY_SEARCH,
    request,
  );
}

/** 取得實體 K 跳鄰居 */
export async function getEntityNeighbors(
  request: KGNeighborsRequest,
): Promise<KGNeighborsResponse> {
  return await apiClient.post<KGNeighborsResponse>(
    AI_ENDPOINTS.GRAPH_ENTITY_NEIGHBORS,
    request,
  );
}

/** 取得實體詳情（別名、公文、關係） */
export async function getEntityDetail(
  request: KGEntityDetailRequest,
): Promise<KGEntityDetailResponse> {
  return await apiClient.post<KGEntityDetailResponse>(
    AI_ENDPOINTS.GRAPH_ENTITY_DETAIL,
    request,
  );
}

/** 取得實體關係時間軸 */
export async function getEntityTimeline(
  request: KGTimelineRequest,
): Promise<KGTimelineResponse> {
  return await apiClient.post<KGTimelineResponse>(
    AI_ENDPOINTS.GRAPH_ENTITY_TIMELINE,
    request,
  );
}

/** 高頻實體排名 */
export async function getTopEntities(
  request: KGTopEntitiesRequest,
): Promise<KGTopEntitiesResponse> {
  return await apiClient.post<KGTopEntitiesResponse>(
    AI_ENDPOINTS.GRAPH_ENTITY_TOP,
    request,
  );
}

/** 圖譜統計 */
export async function getGraphStats(): Promise<KGGraphStatsResponse> {
  return await apiClient.post<KGGraphStatsResponse>(
    AI_ENDPOINTS.GRAPH_STATS,
    {},
  );
}

/** 觸發入圖管線 */
export async function triggerGraphIngest(
  request: KGIngestRequest,
): Promise<KGIngestResponse> {
  return await apiClient.post<KGIngestResponse>(
    AI_ENDPOINTS.GRAPH_INGEST,
    request,
  );
}

/** 手動合併實體（管理員） */
export async function mergeGraphEntities(
  request: KGMergeEntitiesRequest,
): Promise<KGMergeEntitiesResponse> {
  try {
    return await apiClient.post<KGMergeEntitiesResponse>(
      AI_ENDPOINTS.GRAPH_MERGE_ENTITIES,
      request,
    );
  } catch (error) {
    logger.error('合併實體失敗', error);
    throw error;
  }
}
