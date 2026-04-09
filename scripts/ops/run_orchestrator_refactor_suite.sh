#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

LABEL="${1:-full}"
STAMP="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
REPORT_DIR="$ROOT_DIR/artifacts/test-reports/orchestrator"
mkdir -p "$REPORT_DIR"

LOG_PATH="$REPORT_DIR/${STAMP}-${LABEL}.log"
JUNIT_PATH="$REPORT_DIR/${STAMP}-${LABEL}.junit.xml"
LATEST_LOG="$REPORT_DIR/latest-${LABEL}.log"
LATEST_JUNIT="$REPORT_DIR/latest-${LABEL}.junit.xml"

TESTS=(
  tests/drift/test_container_state_paths.py
  tests/drift/test_workspace_event_paths.py
  tests/unit/test_single_truth_skill_context_sync_stream.py
  tests/unit/test_single_truth_channel.py
  tests/unit/test_container_commander_gaming_route_contract.py
  tests/unit/test_skill_discovery_drift_parity.py
  tests/unit/test_skill_package_policy.py
  tests/unit/test_orchestrator_domain_container_policy_utils.py
  tests/unit/test_orchestrator_semantic_context_utils.py
  tests/unit/test_orchestrator_response_guard_utils.py
  tests/unit/test_orchestrator_output_glue_utils.py
  tests/unit/test_orchestrator_policy_runtime_utils.py
  tests/unit/test_orchestrator_state_runtime_utils.py
  tests/unit/test_orchestrator_context_workspace_utils.py
  tests/unit/test_orchestrator_execution_resolution_utils.py
  tests/unit/test_orchestrator_postprocess_utils.py
  tests/unit/test_orchestrator_compact_context_utils.py
  tests/unit/test_orchestrator_container_candidate_utils.py
  tests/unit/test_orchestrator_cron_intent_utils.py
  tests/unit/test_orchestrator.py
)

{
  echo "[orchestrator-refactor-suite]"
  echo "label=$LABEL"
  echo "timestamp_utc=$STAMP"
  echo "repo_root=$ROOT_DIR"
  echo "log_path=$LOG_PATH"
  echo "junit_path=$JUNIT_PATH"
  echo "tests=${#TESTS[@]}"
  echo
  python -m pytest "${TESTS[@]}" --junitxml="$JUNIT_PATH"
} | tee "$LOG_PATH"

ln -sfn "$(basename "$LOG_PATH")" "$LATEST_LOG"
ln -sfn "$(basename "$JUNIT_PATH")" "$LATEST_JUNIT"

echo
echo "Saved log: $LOG_PATH"
echo "Saved junit: $JUNIT_PATH"
echo "Latest log alias: $LATEST_LOG"
echo "Latest junit alias: $LATEST_JUNIT"
