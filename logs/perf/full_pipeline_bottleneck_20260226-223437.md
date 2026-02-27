# Full Pipeline Bottleneck Report

## Core
- Perf report: `/DATA/AppData/MCP/Jarvis/Jarvis/logs/perf/full_pipeline_perf_20260226-223437.json`
- Legacy dataset rows: **150** (`2025-07-01T22:34:37.896643Z` .. `2025-09-14T10:34:37.896643Z`)
- CPU embedding prepare/restore: **True / True**

## Performance
- overall p95_e2e_ms: **15114.817**
- stream p95_ttft_ms: **2302.34**
- stream p50_tokens_per_sec: **49.874**

## Pipeline Signals
- requests_total: 4
- thinking/control/output events: 2/2/4
- tool_execution_events: 6
- embedding routes cpu/gpu: 38/0
- routing_fallbacks: 6
- ollama unload events: 0

## Error Hotspots
- tool_not_found: 0
- memory_fts: 0
- decide_tools attr errors: 0

## Bottlenecks
- [medium] high_e2e_latency: User-perceived latency spikes under mixed sync/stream workload.
- [medium] high_ttft: Slow first token on stream path; startup and retrieval/tool orchestration likely dominates.
