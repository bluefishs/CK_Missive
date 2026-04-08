"""
TypeScript / React 提取器

以 regex 解析 .ts/.tsx 原始碼，提取模組、元件、Hook 及匯入關係。
不依賴 Node.js。

Version: 1.0.0
Created: 2026-03-10
Extracted from: code_graph_service.py (v3.0.0)
"""

import logging
import os
import re
from pathlib import Path, PurePosixPath
from typing import List, Optional, Set, Tuple

from app.services.ai.code_graph_types import CodeEntity, CodeRelation

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patterns for TypeScript/React extraction
# ---------------------------------------------------------------------------

_RE_IMPORT = re.compile(
    r"""(?:import\s+(?:(?:type\s+)?(?:\{[^}]*\}|[\w*]+))\s+from\s+['"]([^'"]+)['"])""",
    re.MULTILINE,
)
_RE_COMPONENT_FUNC = re.compile(
    r"""export\s+(?:default\s+)?function\s+([A-Z]\w+)""",
)
_RE_COMPONENT_CONST = re.compile(
    r"""export\s+(?:default\s+)?const\s+([A-Z]\w+)\s*[=:]\s*.*(?:React\.FC|React\.memo|forwardRef|React\.forwardRef|\(\s*(?:props|{))""",
)
_RE_HOOK_FUNC = re.compile(
    r"""export\s+(?:default\s+)?function\s+(use[A-Z]\w+)""",
)
_RE_HOOK_CONST = re.compile(
    r"""export\s+(?:default\s+)?const\s+(use[A-Z]\w+)\s*=""",
)
# Re-export patterns: `export { X } from './Y'` or `export * from './Y'`
_RE_REEXPORT_NAMED = re.compile(
    r"""export\s+\{[^}]*\}\s+from\s+['"]([^'"]+)['"]""",
    re.MULTILINE,
)
_RE_REEXPORT_STAR = re.compile(
    r"""export\s+\*\s+from\s+['"]([^'"]+)['"]""",
)
# Type/Interface definitions
_RE_INTERFACE = re.compile(
    r"""export\s+(?:default\s+)?interface\s+(\w+)""",
)
_RE_TYPE_ALIAS = re.compile(
    r"""export\s+(?:default\s+)?type\s+(\w+)\s*=""",
)
# Enum definitions
_RE_ENUM = re.compile(
    r"""export\s+(?:const\s+)?enum\s+(\w+)""",
)

TS_EXCLUDE_DIRS = {"__pycache__", ".git", "node_modules", ".claude", "dist", "build", "coverage"}


class TypeScriptExtractor:
    """Extract entities and relationships from TypeScript/React source via regex.

    Identifies:
    - ts_module: each .ts/.tsx file
    - ts_component: React components (PascalCase exported functions/consts)
    - ts_hook: Custom hooks (useXxx exported functions/consts)
    - ts_interface: exported interface definitions
    - ts_type: exported type alias definitions
    - ts_enum: exported enum definitions
    - imports: intra-project import relations (including re-exports)
    - defines_component / defines_hook / defines_type / defines_enum: module → entity relations
    """

    def __init__(self, project_prefix: str = "src"):
        self.project_prefix = project_prefix

    def discover_files(self, root: Path) -> List[Tuple[Path, str]]:
        """Walk directory, return (file_path, module_path) pairs for .ts/.tsx files."""
        results: List[Tuple[Path, str]] = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in TS_EXCLUDE_DIRS]

            for fname in sorted(filenames):
                if not (fname.endswith(".ts") or fname.endswith(".tsx")):
                    continue
                # Skip test/spec files and declaration files
                if ".test." in fname or ".spec." in fname or fname.endswith(".d.ts"):
                    continue

                fpath = Path(dirpath) / fname
                # Build module path relative to root
                rel = fpath.relative_to(root)
                mod_path = str(PurePosixPath(rel.with_suffix(""))).replace("/", "/")
                # Normalize: remove trailing /index
                if mod_path.endswith("/index"):
                    mod_path = mod_path[:-6] or "index"
                results.append((fpath, mod_path))
        return results

    def extract_file(
        self, file_path: Path, module_path: str
    ) -> Tuple[List[CodeEntity], List[CodeRelation]]:
        """Parse a single .ts/.tsx file → entities + relations."""
        try:
            source = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            logger.warning("Failed to read %s: %s", file_path, e)
            return [], []

        file_rel = str(file_path).replace("\\", "/")
        line_count = len(source.splitlines())

        entities: List[CodeEntity] = []
        relations: List[CodeRelation] = []

        try:
            file_mtime = file_path.stat().st_mtime
        except OSError:
            file_mtime = 0.0

        # Module entity
        entities.append(CodeEntity(
            canonical_name=module_path,
            entity_type="ts_module",
            description={
                "file_path": file_rel,
                "lines": line_count,
                "is_tsx": file_path.suffix == ".tsx",
                "mtime": file_mtime,
            },
        ))

        # Extract components
        for pattern in (_RE_COMPONENT_FUNC, _RE_COMPONENT_CONST):
            for match in pattern.finditer(source):
                name = match.group(1)
                # Skip hooks (handled separately)
                if name.startswith("use") and len(name) > 3 and name[3].isupper():
                    continue
                comp_name = f"{module_path}::{name}"
                entities.append(CodeEntity(
                    canonical_name=comp_name,
                    entity_type="ts_component",
                    description={
                        "file_path": file_rel,
                        "component_name": name,
                    },
                ))
                relations.append(CodeRelation(
                    source_name=module_path, source_type="ts_module",
                    target_name=comp_name, target_type="ts_component",
                    relation_type="defines_component",
                ))

        # Extract hooks
        seen_hooks: Set[str] = set()
        for pattern in (_RE_HOOK_FUNC, _RE_HOOK_CONST):
            for match in pattern.finditer(source):
                name = match.group(1)
                if name in seen_hooks:
                    continue
                seen_hooks.add(name)
                hook_name = f"{module_path}::{name}"
                entities.append(CodeEntity(
                    canonical_name=hook_name,
                    entity_type="ts_hook",
                    description={
                        "file_path": file_rel,
                        "hook_name": name,
                    },
                ))
                relations.append(CodeRelation(
                    source_name=module_path, source_type="ts_module",
                    target_name=hook_name, target_type="ts_hook",
                    relation_type="defines_hook",
                ))

        # Extract interfaces
        for match in _RE_INTERFACE.finditer(source):
            name = match.group(1)
            iface_name = f"{module_path}::{name}"
            entities.append(CodeEntity(
                canonical_name=iface_name,
                entity_type="ts_interface",
                description={
                    "file_path": file_rel,
                    "interface_name": name,
                },
            ))
            relations.append(CodeRelation(
                source_name=module_path, source_type="ts_module",
                target_name=iface_name, target_type="ts_interface",
                relation_type="defines_type",
            ))

        # Extract type aliases
        for match in _RE_TYPE_ALIAS.finditer(source):
            name = match.group(1)
            type_name = f"{module_path}::{name}"
            entities.append(CodeEntity(
                canonical_name=type_name,
                entity_type="ts_type",
                description={
                    "file_path": file_rel,
                    "type_name": name,
                },
            ))
            relations.append(CodeRelation(
                source_name=module_path, source_type="ts_module",
                target_name=type_name, target_type="ts_type",
                relation_type="defines_type",
            ))

        # Extract enums
        for match in _RE_ENUM.finditer(source):
            name = match.group(1)
            enum_name = f"{module_path}::{name}"
            entities.append(CodeEntity(
                canonical_name=enum_name,
                entity_type="ts_enum",
                description={
                    "file_path": file_rel,
                    "enum_name": name,
                },
            ))
            relations.append(CodeRelation(
                source_name=module_path, source_type="ts_module",
                target_name=enum_name, target_type="ts_enum",
                relation_type="defines_enum",
            ))

        # Extract imports (intra-project relative imports only)
        for match in _RE_IMPORT.finditer(source):
            import_path = match.group(1)
            # Only track relative imports (starts with . or ..)
            if not import_path.startswith("."):
                continue
            # Resolve relative path
            resolved = self._resolve_import(module_path, import_path)
            if resolved and resolved != module_path:
                relations.append(CodeRelation(
                    source_name=module_path, source_type="ts_module",
                    target_name=resolved, target_type="ts_module",
                    relation_type="imports",
                ))

        # Extract re-exports: `export { X } from './Y'` and `export * from './Y'`
        for pattern in (_RE_REEXPORT_NAMED, _RE_REEXPORT_STAR):
            for match in pattern.finditer(source):
                reexport_path = match.group(1)
                if not reexport_path.startswith("."):
                    continue
                resolved = self._resolve_import(module_path, reexport_path)
                if resolved and resolved != module_path:
                    relations.append(CodeRelation(
                        source_name=module_path, source_type="ts_module",
                        target_name=resolved, target_type="ts_module",
                        relation_type="imports",
                    ))

        return entities, relations

    @staticmethod
    def _resolve_import(current_module: str, import_path: str) -> Optional[str]:
        """Resolve a relative import path to a module path."""
        current_parts = current_module.split("/")
        # Current module's directory
        if len(current_parts) > 1:
            base_parts = current_parts[:-1]
        else:
            base_parts = []

        import_parts = import_path.split("/")
        for part in import_parts:
            if part == ".":
                continue
            elif part == "..":
                if base_parts:
                    base_parts.pop()
            else:
                base_parts.append(part)

        return "/".join(base_parts) if base_parts else None
