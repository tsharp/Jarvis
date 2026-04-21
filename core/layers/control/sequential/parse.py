"""Step parsing helpers for sequential reasoning streams."""

from __future__ import annotations

import re


def parse_sequential_steps(
    content_buffer: str,
    *,
    log_info_fn,
    log_warning_fn,
) -> list[dict[str, object]]:
    """Parse streamed sequential content into structured steps."""
    patterns = [
        r"## Step (\d+):\s*([^\n]*)\n(.*?)(?=## Step \d+:|$)",
        r"\*\*Step (\d+)\*\*[:\s]*([^\n]*)\n(.*?)(?=\*\*Step \d+|$)",
        r"(?:^|\n)Step (\d+):\s*([^\n]*)\n(.*?)(?=Step \d+:|$)",
    ]

    matches = []
    for pattern in patterns:
        matches = list(re.finditer(pattern, content_buffer, re.DOTALL | re.IGNORECASE))
        if matches:
            log_info_fn(f"[ControlLayer] Matched {len(matches)} steps")
            break

    if not matches:
        log_warning_fn(f"[ControlLayer] No steps found in content! Length: {len(content_buffer)}")
        if content_buffer.strip():
            return [{"step": 1, "title": "Analysis", "thought": content_buffer, "_synthetic": True}]
        return []

    all_steps = []
    for match in matches:
        step_num = int(match.group(1))
        step_title = match.group(2).strip()
        step_content = match.group(3).strip()
        all_steps.append(
            {
                "step": step_num,
                "title": step_title,
                "thought": step_content,
                "_synthetic": False,
            }
        )
    return all_steps
