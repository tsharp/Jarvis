"""Sequential streaming flow for ControlLayer."""

from __future__ import annotations

from typing import Any


async def check_sequential_thinking_stream(
    user_text: str,
    thinking_plan: dict[str, Any],
    *,
    mcp_hub,
    registry,
    ollama_base: str,
    asyncio_module,
    json_module,
    async_client_cls,
    resolve_role_provider_fn,
    resolve_role_endpoint_fn,
    stream_chat_fn,
    resolve_sequential_model_fn,
    build_system_prompt_fn,
    build_user_prompt_fn,
    parse_steps_fn,
    log_info_fn,
    log_error_fn,
    log_debug_fn,
    log_warning_fn,
):
    """
    Sequential Thinking v5.0 - TRUE LIVE STREAMING

    Two-Phase Approach:
    - Phase 1: Stream 'thinking' field live to UI (DeepSeek's internal reasoning)
    - Phase 2: Parse 'content' field for steps when complete
    """
    import traceback
    import uuid

    needs_sequential = thinking_plan.get("needs_sequential_thinking", False)

    if not needs_sequential:
        log_debug_fn("[ControlLayer] Sequential Thinking not needed")
        return

    task_id = f"seq-{str(uuid.uuid4())[:8]}"
    complexity = thinking_plan.get("sequential_complexity", 5)
    cim_modes = thinking_plan.get("suggested_cim_modes", [])
    reasoning_type = thinking_plan.get("reasoning_type", "direct")

    log_info_fn(f"[ControlLayer] Sequential v5.0 LIVE STREAM (complexity={complexity}, id={task_id})")

    yield {
        "type": "sequential_start",
        "task_id": task_id,
        "complexity": complexity,
        "cim_modes": cim_modes,
        "reasoning_type": reasoning_type,
    }

    try:
        causal_context = ""
        if mcp_hub:
            try:
                if hasattr(mcp_hub, "call_tool_async"):
                    cim_result = await mcp_hub.call_tool_async("analyze", {"query": user_text})
                else:
                    cim_result = await asyncio_module.to_thread(
                        mcp_hub.call_tool, "analyze", {"query": user_text}
                    )
                if cim_result and cim_result.get("success"):
                    causal_context = cim_result.get("causal_prompt", "")
            except Exception as exc:
                log_debug_fn(f"[ControlLayer] CIM skipped: {exc}")

        system_prompt = build_system_prompt_fn(
            complexity,
            causal_context=causal_context,
        )
        user_prompt = build_user_prompt_fn(user_text)

        seq_provider = resolve_role_provider_fn("thinking", default="ollama")
        log_info_fn(f"[ControlLayer] Starting TRUE STREAMING provider={seq_provider}...")
        content_buffer = ""
        thinking_buffer = ""
        last_thinking_yield = ""
        seq_model = resolve_sequential_model_fn()
        seq_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        if seq_provider == "ollama":
            route = resolve_role_endpoint_fn("thinking", default_endpoint=ollama_base)
            log_info_fn(
                f"[Routing] role=thinking provider=ollama requested_target={route['requested_target']} "
                f"effective_target={route['effective_target'] or 'none'} "
                f"fallback={bool(route['fallback_reason'])} "
                f"fallback_reason={route['fallback_reason'] or 'none'} "
                f"endpoint_source={route['endpoint_source']}"
            )
            if route["hard_error"]:
                yield {
                    "type": "sequential_error",
                    "task_id": task_id,
                    "error": f"compute_unavailable:{route['requested_target']}",
                }
                return
            endpoint = route["endpoint"] or ollama_base
            async with async_client_cls(timeout=180.0) as client:
                async with client.stream(
                    "POST",
                    f"{endpoint}/api/chat",
                    json={
                        "model": seq_model,
                        "messages": seq_messages,
                        "stream": True,
                    },
                ) as response:
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                        try:
                            chunk = json_module.loads(line)
                        except json_module.JSONDecodeError:
                            continue

                        msg = chunk.get("message", {})
                        thinking = msg.get("thinking", "")
                        content = msg.get("content", "")
                        done = chunk.get("done", False)

                        if thinking and thinking != last_thinking_yield:
                            thinking_buffer += thinking
                            last_thinking_yield = thinking
                            yield {
                                "type": "seq_thinking_stream",
                                "task_id": task_id,
                                "chunk": thinking,
                                "total_length": len(thinking_buffer),
                            }

                        if content:
                            content_buffer += content
                        if done:
                            log_info_fn(
                                f"[ControlLayer] Stream complete. Thinking: {len(thinking_buffer)} chars, "
                                f"Content: {len(content_buffer)} chars"
                            )
                            break
        else:
            log_info_fn(
                f"[Routing] role=thinking provider={seq_provider} endpoint=cloud"
            )
            async for content in stream_chat_fn(
                provider=seq_provider,
                model=seq_model,
                messages=seq_messages,
                timeout_s=180.0,
                ollama_endpoint="",
            ):
                if not content:
                    continue
                content_buffer += content
                yield {
                    "type": "seq_thinking_stream",
                    "task_id": task_id,
                    "chunk": content,
                    "total_length": len(content_buffer),
                }

        log_info_fn("[ControlLayer] Parsing steps from content...")

        if thinking_buffer:
            yield {
                "type": "seq_thinking_done",
                "task_id": task_id,
                "total_length": len(thinking_buffer),
            }

        all_steps = parse_steps_fn(
            content_buffer,
            log_info_fn=log_info_fn,
            log_warning_fn=log_warning_fn,
        )
        for step_data in all_steps:
            step_num = int(step_data["step"])
            step_title = str(step_data["title"])
            step_content = str(step_data["thought"])

            log_info_fn(f"[ControlLayer] YIELD Step {step_num}: {step_title[:40]}...")

            yield {
                "type": "sequential_step",
                "task_id": task_id,
                "step_number": step_num,
                "title": step_title,
                "thought": step_content,
                "status": "complete",
            }

            if not bool(step_data.get("_synthetic")):
                await asyncio_module.sleep(0.3)

        registry_task_id = registry.create_task(user_text, complexity)
        registry.update_status(registry_task_id, "completed")
        registry.set_result(registry_task_id, {"steps": all_steps})

        log_info_fn(f"[ControlLayer] Sequential v5.0 {task_id} done: {len(all_steps)} steps")

        yield {
            "type": "sequential_done",
            "task_id": task_id,
            "steps": all_steps,
            "thinking_length": len(thinking_buffer),
            "summary": f"{len(all_steps)} steps completed",
        }

        thinking_plan["_sequential_result"] = {"steps": all_steps}

    except Exception as exc:
        log_error_fn(f"[ControlLayer] Sequential failed: {exc}")
        log_error_fn(traceback.format_exc())
        yield {
            "type": "sequential_error",
            "task_id": task_id,
            "error": str(exc),
        }
