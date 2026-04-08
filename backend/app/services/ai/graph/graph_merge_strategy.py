"""
圖譜實體合併策略（Phase 2.5 ~ Phase 4）

從 graph_query_service.py 抽出的三階段實體合併、類型統一、
地點聚合、共現邊、超級樞紐限流邏輯。

Version: 1.0.0
Created: 2026-03-13
"""

import logging

from .graph_helpers import (
    _clean_agency_name,
    _normalize_for_match,
    _names_overlap,
    _extract_district,
)

logger = logging.getLogger(__name__)


class GraphMergeStrategy:
    """圖譜實體合併策略（Phase 2.5 ~ Phase 4）"""

    @staticmethod
    def merge_same_origin_entities(
        nodes: list[dict],
        edges: list[dict],
        seen_nodes: set[str],
        seen_edges: set[str],
        ner_fullname: dict[str, str],
        biz_fullname: dict[str, str],
        entity_id_set: set[int],
        entity_by_id: dict,
        doc_entities: dict[int, list[int]],
        doc_map: dict,
        doc_ids: list[int],
    ) -> tuple[int, dict[str, str]]:
        """
        Phase 2.5: 三階段同源實體合併。

        Returns:
            (merged_count, id_remap) — 合併數量與 ID 重映射表
        """
        merged_count = 0
        merged_away: set[str] = set()
        id_remap: dict[str, str] = {}

        # NER 索引（用全名）
        ner_index: dict[str, dict[str, str]] = {"org": {}, "ner_project": {}}
        for n in nodes:
            if n["type"] in ner_index:
                fullname = ner_fullname.get(n["id"], n["label"])
                ner_index[n["type"]][_normalize_for_match(fullname)] = n["id"]

        # 階段 A: 完全匹配（正規化後相同）
        for n in nodes:
            if n["type"] not in ("agency", "typroject"):
                continue
            target_ner = "org" if n["type"] == "agency" else "ner_project"
            fullname = biz_fullname.get(n["id"], n["label"])
            n_norm = _normalize_for_match(fullname)
            for ner_label, ner_id in ner_index.get(target_ner, {}).items():
                if ner_id in merged_away:
                    continue
                if n_norm == ner_label:
                    id_remap[ner_id] = n["id"]
                    merged_away.add(ner_id)
                    merged_count += 1
                    break

        # 階段 B: 包含匹配（用全名比對，放寬到 40%）
        for n in nodes:
            if n["type"] not in ("agency", "typroject"):
                continue
            target_ner = "org" if n["type"] == "agency" else "ner_project"
            fullname = biz_fullname.get(n["id"], n["label"])
            for ner_label, ner_id in ner_index.get(target_ner, {}).items():
                if ner_id in merged_away:
                    continue
                if _names_overlap(fullname, ner_label):
                    id_remap[ner_id] = n["id"]
                    merged_away.add(ner_id)
                    merged_count += 1
                    break

        # 階段 C: 實體共現配對（同一公文出現的 org 與 agency）
        if doc_ids and doc_map:
            for doc_id, ent_list in doc_entities.items():
                doc = doc_map.get(doc_id)
                if not doc:
                    continue
                # 此公文的 sender/receiver 機關名稱
                doc_agencies = set()
                for field in ("sender", "receiver"):
                    name = getattr(doc, field, None)
                    if name:
                        doc_agencies.add(_clean_agency_name(name))

                for eid in set(ent_list):
                    if eid not in entity_id_set:
                        continue
                    ner_node_id = f"ce_{eid}"
                    if ner_node_id in merged_away:
                        continue
                    # 只處理 org 類型的 NER 實體
                    ent_obj = entity_by_id.get(eid)
                    if not ent_obj or ent_obj.entity_type not in ("organization", "org"):
                        continue
                    ner_name_norm = _normalize_for_match(ent_obj.canonical_name or "")
                    if len(ner_name_norm) < 3:
                        continue
                    for ag_name in doc_agencies:
                        ag_norm = _normalize_for_match(_clean_agency_name(ag_name))
                        # 放寬：短名 >= 長名 40% 且包含
                        shorter = ner_name_norm if len(ner_name_norm) <= len(ag_norm) else ag_norm
                        longer = ag_norm if len(ner_name_norm) <= len(ag_norm) else ner_name_norm
                        if len(shorter) >= len(longer) * 0.4 and shorter in longer:
                            ag_id = f"agency_{ag_name}"
                            if ag_id in seen_nodes and ner_node_id not in merged_away:
                                id_remap[ner_node_id] = ag_id
                                merged_away.add(ner_node_id)
                                merged_count += 1
                                break

        # 重寫邊
        if id_remap:
            for e in edges:
                if e["source"] in id_remap:
                    e["source"] = id_remap[e["source"]]
                if e["target"] in id_remap:
                    e["target"] = id_remap[e["target"]]
            edges[:] = [e for e in edges if e["source"] != e["target"]]
            nodes[:] = [n for n in nodes if n["id"] not in merged_away]
            seen_nodes -= merged_away
            deduped_edges: list[dict] = []
            deduped_keys: set[str] = set()
            for e in edges:
                key = f"{e['source']}->{e['target']}:{e.get('type', '')}"
                if key not in deduped_keys:
                    deduped_keys.add(key)
                    deduped_edges.append(e)
            edges[:] = deduped_edges
            seen_edges.clear()
            seen_edges.update(deduped_keys)

        if merged_count:
            logger.info(f"Entity merge: {merged_count} NER entities merged into DB entities (3-phase)")

        return merged_count, id_remap

    @staticmethod
    def unify_node_types(nodes: list[dict]) -> None:
        """Phase 2.5D: 統一節點類型（消除 org/ner_project 冗餘類型）"""
        type_unify_map = {"org": "agency", "ner_project": "typroject"}
        for n in nodes:
            if n["type"] in type_unify_map:
                n["type"] = type_unify_map[n["type"]]

    @staticmethod
    def aggregate_locations(
        nodes: list[dict],
        edges: list[dict],
        seen_nodes: set[str],
        seen_edges: set[str],
        id_remap: dict[str, str],
    ) -> None:
        """Phase 2.6: 地點聚合為行政區域"""
        location_nodes = [n for n in nodes if n["type"] == "location"]
        if location_nodes:
            district_mentions: dict[str, int] = {}
            aggregated_ids: set[str] = set()
            for n in location_nodes:
                district = _extract_district(n["label"])
                if district:
                    district_mentions[district] = (
                        district_mentions.get(district, 0)
                        + (n.get("mention_count") or 1)
                    )
                    aggregated_ids.add(n["id"])
                    # 加入 id_remap 供 Phase 3 共現邊使用
                    id_remap[n["id"]] = f"district_{district}"

            if aggregated_ids:
                # 移除原始地址節點
                nodes[:] = [n for n in nodes if n["id"] not in aggregated_ids]
                seen_nodes -= aggregated_ids
                # 加入行政區域節點（僅保留 mention_count >= 2 的區域）
                for district, mention_sum in district_mentions.items():
                    if mention_sum < 2:
                        continue
                    dist_id = f"district_{district}"
                    if dist_id not in seen_nodes:
                        seen_nodes.add(dist_id)
                        nodes.append({
                            "id": dist_id,
                            "type": "location",
                            "label": district,
                            "mention_count": mention_sum,
                        })
                # 重寫邊：原始地址 ID → 行政區域 ID
                for e in edges:
                    if e["source"] in aggregated_ids:
                        # 找原始節點的區域
                        orig = next((n for n in location_nodes if n["id"] == e["source"]), None)
                        if orig:
                            d = _extract_district(orig["label"])
                            if d:
                                e["source"] = f"district_{d}"
                    if e["target"] in aggregated_ids:
                        orig = next((n for n in location_nodes if n["id"] == e["target"]), None)
                        if orig:
                            d = _extract_district(orig["label"])
                            if d:
                                e["target"] = f"district_{d}"
                # 移除自環、去重
                edges[:] = [e for e in edges if e["source"] != e["target"]]
                final_edges: list[dict] = []
                final_keys: set[str] = set()
                for e in edges:
                    key = f"{e['source']}->{e['target']}:{e.get('type', '')}"
                    if key not in final_keys:
                        final_keys.add(key)
                        final_edges.append(e)
                edges[:] = final_edges
                seen_edges.clear()
                seen_edges.update(final_keys)
                logger.info(
                    f"Location aggregation: {len(aggregated_ids)} addresses → "
                    f"{len(district_mentions)} districts"
                )

        # 過濾低頻 location 節點（未被聚合的非地址格式 location，需 mention >= 2）
        low_freq_locs = {
            n["id"] for n in nodes
            if n["type"] == "location" and (n.get("mention_count") or 0) < 2
        }
        if low_freq_locs:
            nodes[:] = [n for n in nodes if n["id"] not in low_freq_locs]
            edges[:] = [e for e in edges
                        if e["source"] not in low_freq_locs and e["target"] not in low_freq_locs]
            seen_nodes -= low_freq_locs

    @staticmethod
    def add_co_mention_edges(
        nodes: list[dict],
        edges: list[dict],
        seen_nodes: set[str],
        seen_edges: set[str],
        doc_entities: dict[int, list[int]],
        entity_id_set: set[int],
        id_remap: dict[str, str],
    ) -> None:
        """Phase 3: NER 實體間共現邊"""
        co_mention_counts: dict[tuple, int] = {}
        for _doc_id, ent_list in doc_entities.items():
            unique_ents = list(set(e for e in ent_list if e in entity_id_set))
            for i in range(len(unique_ents)):
                for j in range(i + 1, len(unique_ents)):
                    pair = (min(unique_ents[i], unique_ents[j]), max(unique_ents[i], unique_ents[j]))
                    co_mention_counts[pair] = co_mention_counts.get(pair, 0) + 1

        # 共現邊：只保留 top-150 高頻對（避免邊數爆炸 → 星狀糾結）
        MAX_CO_MENTION_EDGES = 150
        qualified_pairs = [
            ((eid1, eid2), count) for (eid1, eid2), count in co_mention_counts.items()
            if count >= 2
        ]
        qualified_pairs.sort(key=lambda x: x[1], reverse=True)

        def _add_edge(e: dict) -> None:
            key = f"{e['source']}->{e['target']}:{e.get('type', '')}"
            if key not in seen_edges:
                seen_edges.add(key)
                edges.append(e)

        for (eid1, eid2), count in qualified_pairs[:MAX_CO_MENTION_EDGES]:
            src = id_remap.get(f"ce_{eid1}", f"ce_{eid1}")
            tgt = id_remap.get(f"ce_{eid2}", f"ce_{eid2}")
            # 跳過自環邊或指向不存在節點的懸空邊
            if src == tgt or src not in seen_nodes or tgt not in seen_nodes:
                continue
            _add_edge({
                "source": src,
                "target": tgt,
                "label": f"共現 {count} 篇",
                "type": "co_mention",
                "weight": min(count / 5, 1.0),
            })

        # 移除指向不存在節點的懸空邊
        final_node_ids = {n["id"] for n in nodes}
        edges[:] = [e for e in edges if e["source"] in final_node_ids and e["target"] in final_node_ids]

    @staticmethod
    def throttle_hubs(
        edges: list[dict],
    ) -> None:
        """Phase 4: 超級樞紐限流"""
        HUB_DEGREE_THRESHOLD = 50
        HUB_EDGES_PER_TYPE = 15

        node_degree: dict[str, int] = {}
        for e in edges:
            node_degree[e["source"]] = node_degree.get(e["source"], 0) + 1
            node_degree[e["target"]] = node_degree.get(e["target"], 0) + 1

        hub_nodes = {nid for nid, deg in node_degree.items() if deg > HUB_DEGREE_THRESHOLD}
        if hub_nodes:
            # 收集每個 hub 節點每種邊類型的邊，保留 weight 最高的 top-N
            hub_edge_groups: dict[str, dict[str, list[dict]]] = {}
            non_hub_edges: list[dict] = []
            for e in edges:
                src_hub = e["source"] in hub_nodes
                tgt_hub = e["target"] in hub_nodes
                if src_hub or tgt_hub:
                    hub_id = e["source"] if src_hub else e["target"]
                    hub_edge_groups.setdefault(hub_id, {}).setdefault(e["type"], []).append(e)
                else:
                    non_hub_edges.append(e)

            kept_hub_edges: list[dict] = []
            removed_count = 0
            for hub_id, type_groups in hub_edge_groups.items():
                for edge_type, type_edges in type_groups.items():
                    # 結構化邊（sends/receives）也限流，但容量加倍
                    structural_limit = HUB_EDGES_PER_TYPE * 2
                    if edge_type in ("sends", "receives"):
                        type_edges.sort(key=lambda x: x.get("weight", 0), reverse=True)
                        kept_hub_edges.extend(type_edges[:structural_limit])
                        removed_count += max(0, len(type_edges) - structural_limit)
                        continue
                    if edge_type in ("issues", "approves", "copies"):
                        kept_hub_edges.extend(type_edges)
                        continue
                    # 其餘按 weight 排序保留 top-N
                    type_edges.sort(key=lambda x: x.get("weight", 0), reverse=True)
                    kept_hub_edges.extend(type_edges[:HUB_EDGES_PER_TYPE])
                    removed_count += max(0, len(type_edges) - HUB_EDGES_PER_TYPE)

            # 合併（去重：hub edge 可能被兩個 hub 都收集到）
            seen_final: set[str] = set()
            final_merged: list[dict] = []
            for e in non_hub_edges + kept_hub_edges:
                key = f"{e['source']}->{e['target']}:{e.get('type', '')}"
                if key not in seen_final:
                    seen_final.add(key)
                    final_merged.append(e)
            edges[:] = final_merged

            if removed_count > 0:
                logger.info(
                    f"Hub throttle: removed {removed_count} edges from "
                    f"{len(hub_nodes)} hub nodes (threshold={HUB_DEGREE_THRESHOLD})"
                )
