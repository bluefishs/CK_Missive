"""
AST Endpoint Extractor Mixin

FastAPI router endpoint detection: 路由裝飾器解析、Depends() 依賴偵測、
Pydantic schema 型別註解偵測。

Extracted from: code_graph_ast_analyzer.py (PythonASTExtractor)
Version: 1.0.0
"""

import ast
import logging
from pathlib import PurePosixPath
from typing import List, Optional

from app.services.ai.graph.code_graph_types import CodeEntity, CodeRelation

logger = logging.getLogger(__name__)


class EndpointExtractorMixin:
    """Mixin providing FastAPI endpoint extraction from Python AST."""

    @staticmethod
    def _name_of(node: ast.expr) -> str:
        """Resolve an AST node to a dotted name string."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{EndpointExtractorMixin._name_of(node.value)}.{node.attr}"
        return "?"

    def _extract_endpoints(
        self,
        tree: ast.Module,
        module_name: str,
        file_rel: str,
        entities: List[CodeEntity],
        relations: List[CodeRelation],
    ) -> None:
        """Detect FastAPI router-decorated functions as api_endpoint entities."""
        router_methods = {"post", "get", "put", "delete", "patch"}

        for node in ast.iter_child_nodes(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                # Match: @router.post("/path") or @router.get("/path")
                if not isinstance(dec, ast.Call):
                    continue
                func_attr = dec.func if hasattr(dec, "func") else None
                if not isinstance(func_attr, ast.Attribute):
                    continue
                if func_attr.attr not in router_methods:
                    continue

                route_path = ""
                if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                    route_path = dec.args[0].value

                ep_name = f"{module_name}::{node.name}"
                entities.append(CodeEntity(
                    canonical_name=ep_name,
                    entity_type="api_endpoint",
                    description={
                        "file_path": file_rel,
                        "line_start": node.lineno,
                        "line_end": node.end_lineno or node.lineno,
                        "route": route_path,
                        "method": func_attr.attr.upper(),
                        "is_async": isinstance(node, ast.AsyncFunctionDef),
                    },
                ))

                # serves_route relation (endpoint -> module)
                if route_path:
                    relations.append(CodeRelation(
                        source_name=ep_name,
                        source_type="api_endpoint",
                        target_name=module_name,
                        target_type="py_module",
                        relation_type="serves_route",
                    ))

                # Detect service dependencies via Depends() in function args
                self._extract_endpoint_dependencies(
                    node, ep_name, relations,
                )

                # Detect schema validation via type annotations on params
                self._extract_endpoint_schemas(
                    node, ep_name, module_name, entities, relations,
                )
                break  # Only process first matching decorator per function

    def _extract_endpoint_dependencies(
        self,
        func_node: ast.FunctionDef,
        ep_name: str,
        relations: List[CodeRelation],
    ) -> None:
        """Detect Depends(ServiceClass) or Depends(get_service_with_db(ServiceClass))."""
        for arg in func_node.args.args:
            if arg.arg == "self":
                continue
            # Check default value for Depends(...)
            # defaults are in func_node.args.defaults (positional) and func_node.args.kw_defaults (keyword)
        # Also check via annotation: service: ServiceClass = Depends(...)
        all_defaults = list(func_node.args.defaults) + list(func_node.args.kw_defaults)
        for default in all_defaults:
            if default is None:
                continue
            if not isinstance(default, ast.Call):
                continue
            # Depends(SomeService) or Depends(get_service_with_db(SomeService))
            dep_func = default.func if hasattr(default, "func") else None
            if isinstance(dep_func, ast.Name) and dep_func.id == "Depends":
                for dep_arg in default.args:
                    svc_name = self._resolve_depends_target(dep_arg)
                    if svc_name and svc_name.endswith("Service"):
                        relations.append(CodeRelation(
                            source_name=ep_name,
                            source_type="api_endpoint",
                            target_name=svc_name,
                            target_type="service",
                            relation_type="uses_service",
                        ))

    def _resolve_depends_target(self, node: ast.expr) -> Optional[str]:
        """Resolve the target name from a Depends() argument."""
        if isinstance(node, ast.Name):
            return node.id
        # get_service_with_db(SomeService) pattern
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "get_service_with_db":
                if node.args and isinstance(node.args[0], ast.Name):
                    return node.args[0].id
        return None

    def _extract_endpoint_schemas(
        self,
        func_node: ast.FunctionDef,
        ep_name: str,
        module_name: str,
        entities: List[CodeEntity],
        relations: List[CodeRelation],
    ) -> None:
        """Detect Pydantic schema usage via type annotations on endpoint params."""
        schema_suffixes = ("Request", "Response", "Create", "Update", "Schema", "Params")
        for arg in func_node.args.args:
            if arg.arg in ("self", "db", "request", "response"):
                continue
            ann = arg.annotation
            if ann is None:
                continue
            ann_name = self._name_of(ann)
            if ann_name and ann_name != "?" and any(ann_name.endswith(s) for s in schema_suffixes):
                schema_key = f"{module_name}::{ann_name}"
                entities.append(CodeEntity(
                    canonical_name=schema_key,
                    entity_type="schema",
                    description={"name": ann_name, "source_module": module_name},
                ))
                relations.append(CodeRelation(
                    source_name=ep_name,
                    source_type="api_endpoint",
                    target_name=schema_key,
                    target_type="schema",
                    relation_type="validates_with",
                ))
