"""Skill Snapshot Service — Git-based versioning for agent skills before evolution.

Creates a snapshot of the current skill state before each evolution cycle,
enabling rollback if evolution degrades quality.

Version: 1.0.0
"""
import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Project root (backend/app/services/ai/ -> 4 levels up)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


class SkillSnapshotService:
    """Manages git-based skill snapshots for safe evolution."""

    @staticmethod
    async def create_snapshot(
        trigger: str = "evolution",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Create a git tag snapshot of current skill state.

        Args:
            trigger: What triggered the snapshot (evolution/manual/scheduled)
            metadata: Optional metadata to include in tag message

        Returns:
            Tag name if created, None if failed.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        tag_name = f"skill-snapshot-{trigger}-{timestamp}"

        try:
            # Check if there are changes to snapshot
            result = subprocess.run(
                [
                    "git", "status", "--porcelain",
                    ".claude/skills/", "backend/app/services/ai/",
                ],
                capture_output=True, text=True,
                cwd=str(PROJECT_ROOT), timeout=10,
            )

            # Create annotated tag with metadata
            tag_message = f"Skill snapshot: {trigger}\n"
            if metadata:
                tag_message += (
                    f"Metadata: {json.dumps(metadata, ensure_ascii=False)}\n"
                )
            tag_message += f"Timestamp: {timestamp}\n"
            tag_message += (
                f"Has uncommitted changes: "
                f"{'yes' if result.stdout.strip() else 'no'}\n"
            )

            # Create annotated tag (doesn't require clean state)
            subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", tag_message],
                capture_output=True, text=True,
                cwd=str(PROJECT_ROOT), timeout=10,
            )

            logger.info("Skill snapshot created: %s", tag_name)
            return tag_name

        except Exception as e:
            logger.warning("Failed to create skill snapshot: %s", e)
            return None

    @staticmethod
    async def list_snapshots(limit: int = 20) -> List[str]:
        """List recent skill snapshots."""
        try:
            result = subprocess.run(
                ["git", "tag", "-l", "skill-snapshot-*", "--sort=-creatordate"],
                capture_output=True, text=True,
                cwd=str(PROJECT_ROOT), timeout=10,
            )
            tags = result.stdout.strip().split("\n")
            return [t for t in tags[:limit] if t]
        except Exception:
            return []

    @staticmethod
    async def get_snapshot_info(tag_name: str) -> Optional[Dict[str, str]]:
        """Get metadata for a specific snapshot."""
        try:
            result = subprocess.run(
                ["git", "tag", "-n99", tag_name],
                capture_output=True, text=True,
                cwd=str(PROJECT_ROOT), timeout=10,
            )
            return {"tag": tag_name, "message": result.stdout.strip()}
        except Exception:
            return None

    @staticmethod
    async def diff_from_snapshot(tag_name: str) -> Optional[str]:
        """Show what changed since a snapshot."""
        try:
            result = subprocess.run(
                [
                    "git", "diff", "--stat", tag_name, "HEAD", "--",
                    ".claude/skills/", "backend/app/services/ai/",
                ],
                capture_output=True, text=True,
                cwd=str(PROJECT_ROOT), timeout=10,
            )
            return result.stdout.strip()
        except Exception:
            return None
