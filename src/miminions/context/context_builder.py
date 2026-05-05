from __future__ import annotations

from collections import Counter
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from miminions.memory.md_store import read_memory
from miminions.memory.sqlite import SQLiteMemory, get_global_memory_db_path
from miminions.workspace_fs.reader import list_skills, read_prompt_files


def _safe_get(obj: Any, name: str, default: Any = None) -> Any:
    """Safely get an attribute or dict value."""
    if obj is None:
        return default

    if isinstance(obj, dict):
        return obj.get(name, default)

    return getattr(obj, name, default)


def _normalize_mapping(obj: Any) -> dict[str, Any]:
    """Convert a simple object into a dict where possible."""
    if obj is None:
        return {}

    if isinstance(obj, dict):
        return obj

    if is_dataclass(obj):
        try:
            return asdict(obj)
        except Exception:
            return {}

    if hasattr(obj, "__dict__"):
        return {
            key: value
            for key, value in vars(obj).items()
            if not key.startswith("_")
        }

    return {}


def _count_nodes_by_type(nodes: Any) -> dict[str, int]:
    """Count nodes by type from a variety of possible shapes."""
    if nodes is None:
        return {}

    items: list[Any]
    if isinstance(nodes, dict):
        items = list(nodes.values())
    elif isinstance(nodes, list):
        items = nodes
    else:
        return {}

    counts: Counter[str] = Counter()
    for node in items:
        node_type = _safe_get(node, "type", None) or _safe_get(node, "node_type", None)
        if node_type is None:
            node_type = "unknown"
        counts[str(node_type)] += 1

    return dict(sorted(counts.items(), key=lambda item: item[0]))


def _rules_to_list(rules: Any) -> list[Any]:
    """Normalize rules to a list."""
    if rules is None:
        return []

    if isinstance(rules, dict):
        return list(rules.values())

    if isinstance(rules, list):
        return rules

    return []


def _rule_priority(rule: Any) -> tuple[int, str]:
    """Sort rules by descending priority, then by name/id."""
    priority = _safe_get(rule, "priority", 0)
    try:
        priority_int = int(priority)
    except (TypeError, ValueError):
        priority_int = 0

    label = (
        _safe_get(rule, "name", None)
        or _safe_get(rule, "id", None)
        or _safe_get(rule, "rule_id", None)
        or "unnamed-rule"
    )
    return (-priority_int, str(label))


def _format_rule_line(rule: Any) -> str:
    """Format a single rule summary line."""
    label = (
        _safe_get(rule, "name", None)
        or _safe_get(rule, "id", None)
        or _safe_get(rule, "rule_id", None)
        or "unnamed-rule"
    )
    priority = _safe_get(rule, "priority", 0)
    rule_type = _safe_get(rule, "type", None) or _safe_get(rule, "rule_type", None)

    parts = [f"- {label}", f"(priority={priority})"]
    if rule_type is not None:
        parts.append(f"[type={rule_type}]")

    return " ".join(parts)


def _state_keys(state: Any) -> list[str]:
    """Return sorted top-level state keys only."""
    if state is None:
        return []

    if isinstance(state, dict):
        return sorted(str(key) for key in state.keys())

    normalized = _normalize_mapping(state)
    return sorted(str(key) for key in normalized.keys())


def _fetch_global_insights(top_k: int = 5, db_path: str | None = None) -> list[str]:
    """Return top-k plain-text global insights from SQLite, or [] on any failure."""
    path = db_path or get_global_memory_db_path(create_dir=False)
    try:
        mem = SQLiteMemory(db_path=path)
        try:
            rows = mem.date_time_search(top_k=top_k)
            return [r["text"] for r in rows if r.get("text")]
        finally:
            mem.close()
    except Exception:
        return []


class ContextBuilder:
    """Build a composed agent context from markdown files and workspace summary."""

    def __init__(self, global_top_k: int = 5, global_db_path: str | None = None):
        """Configure optional global memory injection.

        Args:
            global_top_k: Number of global SQLite insights to inject. Set to 0 to disable.
            global_db_path: Override path to global_memory.db. Defaults to ~/.miminions/global_memory.db.
        """
        self.global_top_k = global_top_k
        self.global_db_path = global_db_path

    def build(
        self,
        workspace_obj: Any,
        root_path: str | Path,
        skills_index_only: bool = True,
    ) -> str:
        root = Path(root_path)
        prompt_files = read_prompt_files(root)
        memory_text = read_memory(root)
        skills = list_skills(root)

        workspace_id = _safe_get(workspace_obj, "id", None)
        workspace_name = _safe_get(workspace_obj, "name", None)
        workspace_root_path = _safe_get(workspace_obj, "root_path", None) or str(root)

        nodes = _safe_get(workspace_obj, "nodes", None)
        rules = _safe_get(workspace_obj, "rules", None)
        state = _safe_get(workspace_obj, "state", None)

        node_counts = _count_nodes_by_type(nodes)
        rule_list = sorted(_rules_to_list(rules), key=_rule_priority)
        top_rules = rule_list[:10]
        state_key_list = _state_keys(state)

        data_dir = root / "data"
        now_utc = datetime.now(timezone.utc).isoformat()

        lines: list[str] = []

        lines.append("# MiMinions Agent Context")
        lines.append("")
        lines.append("## Identity")
        lines.append(f"- workspace_name: {workspace_name}")
        lines.append(f"- workspace_id: {workspace_id}")
        lines.append(f"- root_path: {workspace_root_path}")
        lines.append(f"- current_time_utc: {now_utc}")
        lines.append(f"- data_dir: {data_dir}")
        lines.append("")

        lines.append("## Tool Boundary")
        lines.append("Only read and write workspace data inside the data_dir shown above.")
        lines.append("Do not assume access outside the workspace boundary.")
        lines.append("")

        lines.append("## Prompt Files")
        if prompt_files:
            for name in sorted(prompt_files.keys()):
                lines.append(f"### {name}")
                lines.append(prompt_files[name].rstrip())
                lines.append("")
        else:
            lines.append("No prompt files found.")
            lines.append("")

        if self.global_top_k > 0:
            global_insights = _fetch_global_insights(
                top_k=self.global_top_k, db_path=self.global_db_path
            )
            if global_insights:
                lines.append("## Global Knowledge")
                for insight in global_insights:
                    lines.append(f"- {insight}")
                lines.append("")

        lines.append("## Memory")
        lines.append(memory_text.rstrip())
        lines.append("")

        lines.append("## Workspace Graph Summary")
        lines.append("### Node Counts By Type")
        if node_counts:
            for node_type, count in node_counts.items():
                lines.append(f"- {node_type}: {count}")
        else:
            lines.append("- No nodes found.")
        lines.append("")

        lines.append("### Top Rules By Priority")
        if top_rules:
            for rule in top_rules:
                lines.append(_format_rule_line(rule))
        else:
            lines.append("- No rules found.")
        lines.append("")

        lines.append("### State Keys")
        if state_key_list:
            for key in state_key_list:
                lines.append(f"- {key}")
        else:
            lines.append("- No state keys found.")
        lines.append("")

        lines.append("## Skills Index")
        if skills:
            for skill in skills:
                skill_name = skill.get("name", "unknown")
                skill_path = skill.get("path", "")
                lines.append(f"- {skill_name}: {skill_path}")
        else:
            lines.append("- No skills found.")
        lines.append("")

        if skills_index_only:
            lines.append("Instruction: read a skill file before using it.")
        else:
            lines.append("Instruction: skills may be expanded separately before use.")

        lines.append("")

        return "\n".join(lines)