"""OS_STATE.md auto-update manager.

Maintains docs/OS_STATE.md with current system state (macro, portfolio, health).
Called by daily_update.py every 6 hours.
"""
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)

OS_STATE_PATH = Path(__file__).parent.parent.parent / "docs" / "OS_STATE.md"


class OSStateManager:
    """Manages OS_STATE.md auto-updates."""

    def __init__(self, os_state_path: Path | None = None):
        """Initialize manager.

        Args:
            os_state_path: Path to OS_STATE.md (default: docs/OS_STATE.md)
        """
        self.path = os_state_path or OS_STATE_PATH

    def load(self) -> Dict[str, Any]:
        """Load current OS_STATE.md as dict.

        Returns:
            Dict with all sections (metadata, macro_data, etc.)
        """
        if not self.path.exists():
            logger.warning(f"OS_STATE.md not found at {self.path}")
            return {}

        try:
            with open(self.path, "r") as f:
                content = f.read()

            # Extract YAML blocks between ```yaml ... ```
            import re

            yaml_blocks = re.findall(r"```yaml\n(.*?)\n```", content, re.DOTALL)
            if not yaml_blocks:
                logger.warning("No YAML blocks found in OS_STATE.md")
                return {}

            # Merge all blocks (later keys override)
            merged = {}
            for block in yaml_blocks:
                try:
                    data = yaml.safe_load(block)
                    if data:
                        merged.update(data)
                except yaml.YAMLError as e:
                    logger.error(f"YAML parse error: {e}")
                    continue

            return merged

        except Exception as e:
            logger.error(f"Failed to load OS_STATE.md: {e}")
            return {}

    def update_metadata(self) -> None:
        """Update metadata section (timestamps, intervals)."""
        state = self.load()

        # Set current timestamp
        now = datetime.utcnow()
        state["metadata"]["updated_at"] = now.isoformat() + "Z"

        # Calculate next update (+ 6 hours)
        next_update = now + timedelta(hours=6)
        state["metadata"]["next_update"] = next_update.isoformat() + "Z"

        self._save(state)
        logger.info(f"OS_STATE metadata updated: {now.isoformat()}Z")

    def update_macro_data(
        self,
        usd_try: float | None = None,
        brent: float | None = None,
        vix: float | None = None,
        cds_bps: float | None = None,
        cds_source: str | None = None,
        bist100: float | None = None,
    ) -> None:
        """Update macro data section.

        Args:
            usd_try: USD/TRY exchange rate
            brent: Brent crude price
            vix: VIX index
            cds_bps: Turkey CDS 5Y in basis points
            cds_source: "primary", "proxy", or "cache"
            bist100: BIST 100 index value
        """
        state = self.load()

        if not state:
            logger.error("Cannot update macro data: no state loaded")
            return

        now = datetime.utcnow()
        now_str = now.isoformat() + "Z"

        if usd_try is not None:
            state.setdefault("macro_data", {})["usd_try"] = {
                "value": usd_try,
                "updated_at": now_str,
                "age_hours": 0,
            }

        if brent is not None:
            state.setdefault("macro_data", {})["brent"] = {
                "value": brent,
                "updated_at": now_str,
                "age_hours": 0,
            }

        if vix is not None:
            state.setdefault("macro_data", {})["vix"] = {
                "value": vix,
                "updated_at": now_str,
                "age_hours": 0,
            }

        if cds_bps is not None:
            state.setdefault("macro_data", {})["cds_turkey_5y_bps"] = {
                "value": cds_bps,
                "source": cds_source or "primary",
                "updated_at": now_str,
                "age_hours": 0,
            }

        if bist100 is not None:
            state.setdefault("macro_data", {})["bist100"] = {
                "value": bist100,
                "updated_at": now_str,
                "age_hours": 0,
            }

        self._save(state)
        logger.info(f"OS_STATE macro data updated: {len([u for u in [usd_try, brent, vix, cds_bps, bist100] if u])} fields")

    def update_health(self, source: str, status: str, last_success: str = None) -> None:
        """Update system health for a data source.

        Args:
            source: Source name ("local_macro", "kap_pipeline", "strategist_agent", etc.)
            status: "OK" or "FAILED"
            last_success: ISO timestamp of last success
        """
        state = self.load()

        if not state.get("system_health"):
            state["system_health"] = {}

        state["system_health"][source] = {
            "status": status,
            "last_success": last_success or datetime.utcnow().isoformat() + "Z",
        }

        self._save(state)
        logger.info(f"OS_STATE health updated: {source} = {status}")

    def check_staleness(self) -> str | None:
        """Check if OS_STATE is stale.

        Returns:
            None if fresh
            "WARNING" if 24-48h old
            "CRITICAL" if > 48h old
        """
        state = self.load()

        if not state.get("metadata", {}).get("updated_at"):
            return "CRITICAL"

        try:
            updated = datetime.fromisoformat(
                state["metadata"]["updated_at"].replace("Z", "+00:00")
            )
            now = datetime.utcnow()
            age = (now - updated).total_seconds() / 3600  # hours

            if age > 48:
                return "CRITICAL"
            elif age > 24:
                return "WARNING"
            else:
                return None

        except Exception as e:
            logger.error(f"Failed to check staleness: {e}")
            return "CRITICAL"

    def _save(self, state: Dict[str, Any]) -> None:
        """Save state to OS_STATE.md (internal).

        Args:
            state: State dict to save
        """
        try:
            # Create parent directory if needed
            self.path.parent.mkdir(parents=True, exist_ok=True)

            # Build markdown file with YAML blocks
            lines = [
                "# OS_STATE.md — System State Snapshot",
                "",
                "**This file is auto-updated every 6 hours by `scripts/daily_update.py`**",
                "",
                "---",
                "",
            ]

            # Metadata section
            if "metadata" in state:
                lines.append("## Metadata")
                lines.append("")
                lines.append("```yaml")
                lines.append(yaml.dump(state["metadata"], default_flow_style=False))
                lines.append("```")
                lines.append("")
                lines.append("---")
                lines.append("")

            # Macro data section
            if "macro_data" in state:
                lines.append("## Macro Data (Current)")
                lines.append("")
                lines.append("```yaml")
                lines.append(yaml.dump({"macro_data": state["macro_data"]}, default_flow_style=False))
                lines.append("```")
                lines.append("")
                lines.append("---")
                lines.append("")

            # Other sections (regime, portfolio, health)
            for section in ["regime", "portfolio", "system_health", "alerts", "configuration", "backlog"]:
                if section in state:
                    lines.append(f"## {section.title()}")
                    lines.append("")
                    lines.append("```yaml")
                    lines.append(yaml.dump({section: state[section]}, default_flow_style=False))
                    lines.append("```")
                    lines.append("")
                    lines.append("---")
                    lines.append("")

            # Test suite status
            if "test_suite" in state:
                lines.append("## Test Suite Status")
                lines.append("")
                lines.append("```yaml")
                lines.append(yaml.dump(state["test_suite"], default_flow_style=False))
                lines.append("```")
                lines.append("")

            # Footer
            now = datetime.utcnow().isoformat() + "Z"
            lines.append(f"**Last Auto-Update:** {now}  ")
            next_update = (datetime.utcnow() + timedelta(hours=6)).isoformat() + "Z"
            lines.append(f"**Next Auto-Update:** {next_update}  ")
            lines.append("**Manual Edit Status:** ✅ Ready for architect edits (config section)")

            content = "\n".join(lines)

            # Atomic write (write to temp, then move)
            temp_path = self.path.with_suffix(".tmp")
            with open(temp_path, "w") as f:
                f.write(content)

            temp_path.replace(self.path)
            logger.info(f"OS_STATE.md saved: {self.path}")

        except Exception as e:
            logger.error(f"Failed to save OS_STATE.md: {e}")
