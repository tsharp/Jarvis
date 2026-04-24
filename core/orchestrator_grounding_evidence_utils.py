import json
from datetime import datetime
from typing import Any, Dict, List, Optional


def build_grounding_evidence_entry(
    tool_name: str,
    raw_result: str,
    status: str,
    ref_id: str,
    *,
    timestamp_iso: Optional[str] = None,
) -> Dict[str, Any]:
    timestamp = str(timestamp_iso or (datetime.utcnow().isoformat() + "Z"))
    lines = [
        line.strip()
        for line in str(raw_result or "").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    entry: Dict[str, Any] = {
        "tool_name": str(tool_name or "").strip(),
        "status": str(status or "").strip().lower() or "unknown",
        "ref_id": str(ref_id or "").strip(),
        "timestamp": timestamp,
        "key_facts": lines[:3] if lines else [str(raw_result or "")[:200] or "Keine Ausgabe"],
    }
    try:
        parsed = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
    except Exception:
        parsed = None
        # Formatted tool results have a header line ("### TOOL-ERGEBNIS..." / "--- Fast Lane ---")
        # followed by the actual JSON on the next line — extract and retry.
        if isinstance(raw_result, str):
            for _line in raw_result.splitlines():
                _line = _line.strip()
                if _line.startswith(("{", "[")):
                    try:
                        parsed = json.loads(_line)
                    except Exception:
                        pass
                    break
    if isinstance(parsed, dict):
        payload = parsed.get("structuredContent") if isinstance(parsed.get("structuredContent"), dict) else parsed
        if str(tool_name or "").strip() == "list_skills":
            installed = payload.get("installed")
            available = payload.get("available")
            installed_items = installed if isinstance(installed, list) else []
            available_items = available if isinstance(available, list) else []
            installed_count = payload.get("installed_count")
            available_count = payload.get("available_count")
            try:
                installed_count = int(installed_count)
            except Exception:
                installed_count = len(installed_items)
            try:
                available_count = int(available_count)
            except Exception:
                available_count = len(available_items)
            installed_names: List[str] = []
            for row in installed_items:
                if not isinstance(row, dict):
                    continue
                name = str(row.get("name") or "").strip()
                if name:
                    installed_names.append(name)
                if len(installed_names) >= 8:
                    break
            summary_lines = [
                f"installed_count: {installed_count}",
                f"available_count: {available_count}",
            ]
            if installed_names:
                summary_lines.append("installed_names: " + ", ".join(installed_names))
            entry["key_facts"] = summary_lines
        elif str(tool_name or "").strip() == "list_draft_skills":
            drafts = payload.get("drafts")
            draft_items = drafts if isinstance(drafts, list) else []
            draft_names: List[str] = []
            for row in draft_items:
                if isinstance(row, dict):
                    name = str(row.get("name") or "").strip()
                else:
                    name = str(row or "").strip()
                if name:
                    draft_names.append(name)
                if len(draft_names) >= 8:
                    break
            draft_count = len(draft_items)
            summary_lines = [f"draft_count: {draft_count}"]
            if draft_names:
                summary_lines.append("draft_names: " + ", ".join(draft_names))
            entry["key_facts"] = summary_lines

        # Skills return {"result": "..."} — use result lines as key_facts so the
        # grounding evidence covers the full tool output (not just the first 3 raw lines).
        result_str = str(payload.get("result") or "").strip()
        if result_str:
            result_lines = [
                line.strip()
                for line in result_str.splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            if result_lines:
                entry["key_facts"] = result_lines[:8]

        metrics = payload.get("metrics")
        if isinstance(metrics, dict):
            entry["metrics"] = {str(k): v for k, v in metrics.items() if str(k).strip()}
        elif isinstance(metrics, list):
            safe_metrics = []
            for item in metrics:
                if not isinstance(item, dict):
                    continue
                key = str(item.get("key") or item.get("name") or "").strip()
                if not key:
                    continue
                safe_metrics.append(
                    {
                        "key": key,
                        "value": item.get("value"),
                        "unit": item.get("unit"),
                    }
                )
            if safe_metrics:
                entry["metrics"] = safe_metrics
        structured = {}
        for key in ("output", "result", "description", "type", "success"):
            if key in payload:
                structured[key] = payload.get(key)
        if str(tool_name or "").strip() == "container_list":
            rows = payload.get("containers")
            if isinstance(rows, list):
                structured["containers"] = [row for row in rows if isinstance(row, dict)]
            if "count" in payload:
                structured["count"] = payload.get("count")
            if "filter" in payload:
                structured["filter"] = payload.get("filter")
        elif str(tool_name or "").strip() == "container_inspect":
            for key in (
                "container_id",
                "short_id",
                "name",
                "blueprint_id",
                "image",
                "status",
                "running",
                "network",
                "ip_address",
            ):
                if key in payload:
                    structured[key] = payload.get(key)
        elif str(tool_name or "").strip() == "blueprint_list":
            rows = payload.get("blueprints")
            if isinstance(rows, list):
                structured["blueprints"] = [row for row in rows if isinstance(row, dict)]
            if "count" in payload:
                structured["count"] = payload.get("count")
        if str(tool_name or "").strip() == "list_skills":
            structured["installed_count"] = installed_count
            structured["available_count"] = available_count
            structured["installed_names"] = installed_names
        elif str(tool_name or "").strip() == "list_draft_skills":
            structured["draft_count"] = draft_count
            structured["draft_names"] = draft_names
        if structured:
            entry["structured"] = structured
    return entry
