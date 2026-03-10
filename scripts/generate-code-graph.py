#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitNexus — 本地代碼圖譜產生器

零雲端依賴，純本地執行。掃描 Python AST + TypeScript regex，
產出 knowledge_graph.json 供雲端 Agent 直接檢索。

用法:
  python scripts/generate-code-graph.py                    # 產生圖譜
  python scripts/generate-code-graph.py --incremental      # 增量模式（比對 mtime）
  python scripts/generate-code-graph.py --check            # 乾跑（僅顯示統計）
  python scripts/generate-code-graph.py --output my.json   # 自訂輸出路徑
  python scripts/generate-code-graph.py --analyze          # 含架構分析

輸出:
  knowledge_graph.json — 完整圖譜（nodes + edges + metadata）

@version 1.0.0
@date 2026-03-10
"""

import argparse
import json
import logging
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Resolve project root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent

# Add backend to path for reusing extractors
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("gitnexus")

# Cache file for mtime tracking
MTIME_CACHE = PROJECT_ROOT / ".claude" / "code_graph_mtime.json"


def load_mtime_cache() -> Dict[str, float]:
    """Load cached file mtimes from previous run."""
    if MTIME_CACHE.exists():
        try:
            return json.loads(MTIME_CACHE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_mtime_cache(mtime_map: Dict[str, float]) -> None:
    """Save file mtimes for incremental builds."""
    MTIME_CACHE.parent.mkdir(parents=True, exist_ok=True)
    MTIME_CACHE.write_text(
        json.dumps(mtime_map, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def extract_all(
    incremental: bool = False,
    include_schema: bool = False,
) -> Tuple[List[Dict], List[Dict], Dict[str, Any]]:
    """Run all extractors and return (nodes, edges, stats).

    Returns plain dicts (not DB models) for JSON serialization.
    """
    from app.services.ai.code_graph_service import (
        PythonASTExtractor,
        TypeScriptExtractor,
        CodeEntity,
        CodeRelation,
    )

    stats: Dict[str, int] = {
        "py_modules": 0, "py_classes": 0, "py_functions": 0,
        "ts_modules": 0, "ts_components": 0, "ts_hooks": 0,
        "relations": 0, "errors": 0, "skipped": 0,
    }

    all_entities: List[CodeEntity] = []
    all_relations: List[CodeRelation] = []

    # Load mtime cache for incremental mode
    mtime_cache = load_mtime_cache() if incremental else {}
    new_mtime_cache: Dict[str, float] = {}

    # --- Python AST ---
    backend_app = PROJECT_ROOT / "backend" / "app"
    if backend_app.is_dir():
        extractor = PythonASTExtractor(project_prefix="app")
        files = extractor.discover_files(backend_app)
        logger.info("Python: %d files discovered", len(files))

        for fpath, mod_name in files:
            try:
                file_mtime = fpath.stat().st_mtime
            except OSError:
                file_mtime = 0.0

            new_mtime_cache[mod_name] = file_mtime

            if incremental and file_mtime > 0:
                cached = mtime_cache.get(mod_name, 0.0)
                if file_mtime <= cached:
                    stats["skipped"] += 1
                    continue

            try:
                ents, rels = extractor.extract_file(fpath, mod_name)
                all_entities.extend(ents)
                all_relations.extend(rels)
            except Exception as e:
                logger.warning("Python extract error %s: %s", fpath.name, e)
                stats["errors"] += 1

    # --- TypeScript/React ---
    frontend_src = PROJECT_ROOT / "frontend" / "src"
    if frontend_src.is_dir():
        ts_ext = TypeScriptExtractor(project_prefix="src")
        ts_files = ts_ext.discover_files(frontend_src)
        logger.info("TypeScript: %d files discovered", len(ts_files))

        for fpath, mod_path in ts_files:
            try:
                file_mtime = fpath.stat().st_mtime
            except OSError:
                file_mtime = 0.0

            new_mtime_cache[mod_path] = file_mtime

            if incremental and file_mtime > 0:
                cached = mtime_cache.get(mod_path, 0.0)
                if file_mtime <= cached:
                    stats["skipped"] += 1
                    continue

            try:
                ents, rels = ts_ext.extract_file(fpath, mod_path)
                all_entities.extend(ents)
                all_relations.extend(rels)
            except Exception as e:
                logger.warning("TS extract error %s: %s", fpath.name, e)
                stats["errors"] += 1

    # Save mtime cache
    save_mtime_cache(new_mtime_cache)

    # Deduplicate entities
    seen_entities: Set[str] = set()
    unique_entities: List[CodeEntity] = []
    for ent in all_entities:
        key = f"{ent.entity_type}:{ent.canonical_name}"
        if key not in seen_entities:
            seen_entities.add(key)
            unique_entities.append(ent)

    # Count by type
    type_map = {
        "py_module": "py_modules", "py_class": "py_classes",
        "py_function": "py_functions", "ts_module": "ts_modules",
        "ts_component": "ts_components", "ts_hook": "ts_hooks",
    }
    for ent in unique_entities:
        key = type_map.get(ent.entity_type)
        if key:
            stats[key] += 1

    # Deduplicate relations
    seen_rels: Set[str] = set()
    unique_relations: List[CodeRelation] = []
    for rel in all_relations:
        key = f"{rel.source_type}:{rel.source_name}|{rel.target_type}:{rel.target_name}|{rel.relation_type}"
        if key not in seen_rels:
            seen_rels.add(key)
            unique_relations.append(rel)
    stats["relations"] = len(unique_relations)

    # Convert to plain dicts
    nodes = []
    for ent in unique_entities:
        node = {
            "id": f"{ent.entity_type}:{ent.canonical_name}",
            "label": ent.canonical_name.split("::")[-1] if "::" in ent.canonical_name else ent.canonical_name.split(".")[-1],
            "type": ent.entity_type,
            "canonical_name": ent.canonical_name,
        }
        if ent.description:
            node["description"] = ent.description
        nodes.append(node)

    edges = []
    for rel in unique_relations:
        edges.append({
            "source": f"{rel.source_type}:{rel.source_name}",
            "target": f"{rel.target_type}:{rel.target_name}",
            "type": rel.relation_type,
            "label": rel.relation_type.replace("_", " "),
        })

    return nodes, edges, stats


def run_architecture_analysis(
    nodes: List[Dict], edges: List[Dict]
) -> Dict[str, Any]:
    """Pure in-memory architecture analysis (no DB needed)."""
    # Build adjacency
    outgoing: Dict[str, int] = defaultdict(int)
    incoming: Dict[str, int] = defaultdict(int)
    method_count: Dict[str, int] = defaultdict(int)

    for edge in edges:
        if edge["type"] == "imports":
            outgoing[edge["source"]] += 1
            incoming[edge["target"]] += 1
        elif edge["type"] == "has_method":
            method_count[edge["source"]] += 1

    # Node lookups
    node_map = {n["id"]: n for n in nodes}
    module_types = {"py_module", "ts_module"}

    # 1. Complexity hotspots
    complexity = sorted(
        [
            {"module": node_map[nid]["canonical_name"], "outgoing_deps": cnt}
            for nid, cnt in outgoing.items()
            if nid in node_map and node_map[nid]["type"] in module_types
        ],
        key=lambda x: x["outgoing_deps"],
        reverse=True,
    )[:15]

    # 2. Hub modules
    hubs = sorted(
        [
            {"module": node_map[nid]["canonical_name"], "imported_by": cnt}
            for nid, cnt in incoming.items()
            if nid in node_map and node_map[nid]["type"] in module_types
        ],
        key=lambda x: x["imported_by"],
        reverse=True,
    )[:15]

    # 3. Large modules
    large = sorted(
        [
            {
                "module": n["canonical_name"],
                "lines": n.get("description", {}).get("lines", 0),
                "type": n["type"],
            }
            for n in nodes
            if n["type"] in module_types
            and n.get("description", {}).get("lines", 0) > 0
        ],
        key=lambda x: x["lines"],
        reverse=True,
    )[:15]

    # 4. God classes
    gods = sorted(
        [
            {"class": node_map[nid]["canonical_name"], "method_count": cnt}
            for nid, cnt in method_count.items()
            if nid in node_map and node_map[nid]["type"] == "py_class"
        ],
        key=lambda x: x["method_count"],
        reverse=True,
    )[:15]

    # 5. Cycle detection (DFS)
    adj: Dict[str, List[str]] = defaultdict(list)
    for edge in edges:
        if edge["type"] == "imports":
            adj[edge["source"]].append(edge["target"])

    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {}
    path: List[str] = []
    cycles: List[List[str]] = []

    # Freeze adj keys to avoid defaultdict mutation during iteration
    adj_keys = list(adj.keys())

    def dfs(u: str) -> None:
        color[u] = GRAY
        path.append(u)
        for v in adj.get(u, []):
            v_color = color.get(v, WHITE)
            if v_color == GRAY:
                idx = path.index(v)
                cycle = [node_map.get(nid, {}).get("canonical_name", nid) for nid in path[idx:]]
                cycles.append(cycle)
            elif v_color == WHITE:
                dfs(v)
        path.pop()
        color[u] = BLACK

    for nid in adj_keys:
        if color.get(nid, WHITE) == WHITE:
            dfs(nid)

    return {
        "complexity_hotspots": complexity,
        "hub_modules": hubs,
        "large_modules": large,
        "god_classes": gods,
        "cycles": cycles[:30],
        "cycles_found": len(cycles),
    }


def generate_graph(
    output: str = "knowledge_graph.json",
    incremental: bool = False,
    analyze: bool = False,
    check_only: bool = False,
) -> None:
    """Main entry point: generate knowledge_graph.json."""
    start = time.monotonic()

    logger.info("GitNexus — 本地代碼圖譜產生器")
    logger.info("Project root: %s", PROJECT_ROOT)

    nodes, edges, stats = extract_all(incremental=incremental)
    elapsed = round(time.monotonic() - start, 2)

    if check_only:
        print("\n=== GitNexus 乾跑結果 ===")
        print(f"  Python 模組:    {stats['py_modules']}")
        print(f"  Python 類別:    {stats['py_classes']}")
        print(f"  Python 函數:    {stats['py_functions']}")
        print(f"  TS 模組:        {stats['ts_modules']}")
        print(f"  React 元件:     {stats['ts_components']}")
        print(f"  React Hook:     {stats['ts_hooks']}")
        print(f"  關聯:           {stats['relations']}")
        print(f"  跳過（未變更）: {stats['skipped']}")
        print(f"  錯誤:           {stats['errors']}")
        print(f"  節點總數:       {len(nodes)}")
        print(f"  邊總數:         {len(edges)}")
        print(f"  耗時:           {elapsed}s")
        return

    # Build output JSON
    graph_data: Dict[str, Any] = {
        "_meta": {
            "generator": "GitNexus v1.0.0",
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "project": "CK_Missive",
            "incremental": incremental,
            "stats": stats,
            "elapsed_seconds": elapsed,
        },
        "nodes": nodes,
        "edges": edges,
    }

    # Architecture analysis
    if analyze:
        logger.info("Running architecture analysis...")
        analysis = run_architecture_analysis(nodes, edges)
        graph_data["architecture"] = analysis
        logger.info(
            "Analysis: %d hotspots, %d hubs, %d large, %d god classes, %d cycles",
            len(analysis["complexity_hotspots"]),
            len(analysis["hub_modules"]),
            len(analysis["large_modules"]),
            len(analysis["god_classes"]),
            analysis["cycles_found"],
        )

    # Edge type distribution
    edge_types = Counter(e["type"] for e in edges)
    graph_data["_meta"]["edge_distribution"] = dict(edge_types)

    # Write output
    output_path = PROJECT_ROOT / output
    output_path.write_text(
        json.dumps(graph_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    file_size = output_path.stat().st_size
    size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024 * 1024 else f"{file_size / 1024 / 1024:.1f} MB"

    print(f"\n=== GitNexus 圖譜產生完成 ===")
    print(f"  輸出:    {output_path}")
    print(f"  大小:    {size_str}")
    print(f"  節點:    {len(nodes)}")
    print(f"  邊:      {len(edges)}")
    print(f"  耗時:    {elapsed}s")
    if stats["skipped"] > 0:
        print(f"  跳過:    {stats['skipped']} 個未變更檔案")
    if stats["errors"] > 0:
        print(f"  錯誤:    {stats['errors']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="GitNexus — 本地代碼圖譜產生器（零雲端依賴）",
    )
    parser.add_argument(
        "--output", "-o",
        default="knowledge_graph.json",
        help="輸出檔案路徑 (預設: knowledge_graph.json)",
    )
    parser.add_argument(
        "--incremental", "-i",
        action="store_true",
        help="增量模式：僅處理已變更的檔案",
    )
    parser.add_argument(
        "--analyze", "-a",
        action="store_true",
        help="包含架構分析（熱點/樞紐/大型模組/循環偵測）",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="乾跑模式：僅顯示統計，不產生檔案",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="詳細日誌輸出",
    )

    args = parser.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    generate_graph(
        output=args.output,
        incremental=args.incremental,
        analyze=args.analyze,
        check_only=args.check,
    )


if __name__ == "__main__":
    main()
