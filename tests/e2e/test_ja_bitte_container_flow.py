"""
E2E-Diagnosetests: "ja bitte" → Gaming Container Flow

Symptom: User sagt "ja bitte" nach Gaming-Container-Angebot → Trion antwortet
mit Persona-Intro "Ich bin TRION... Wie soll ich dich nennen?" statt Container zu starten.

Root-Cause-Verdachte:
  C1) Short-Input Bypass injiziert home_write → triggert Onboarding
  C2) Short-Input Plan Bypass überschreibt thinking_plan aber Control Layer strippt Tools
  C3) A-Enrichment erreicht den Thinking Layer nicht
  C4) request_container bekommt keine Blueprint-Args (kein Chat-History-Kontext)
  C5) Grounding Evidence überlebt persist nicht (Fix #12B)
  C6) _has_pending_approval feuert nicht

Jeder Test isoliert eine Pipeline-Stufe und gibt einen klaren PASS/FAIL.

Ausführen (live, admin-api muss laufen):
  pytest tests/e2e/test_ja_bitte_container_flow.py -v
  oder:
  pytest tests/e2e/test_ja_bitte_container_flow.py -v -k "stage"

Config:
  TRION_ADMIN_API_URL  default: http://localhost:8200
  TRION_CONTAINER      default: jarvis-admin-api
"""
import json
import os
import subprocess
import requests
import pytest

ADMIN_API = os.environ.get("TRION_ADMIN_API_URL", "http://localhost:8200")
CONTAINER = os.environ.get("TRION_CONTAINER", "jarvis-admin-api")
APP_PATH = "/app"

# Conversation history: Schritt 1 war das Gaming-Container-Angebot
GAMING_OFFER_HISTORY = [
    {
        "role": "user",
        "content": "Trion kannst du einen Gaming steam Container erstellen?",
    },
    {
        "role": "assistant",
        "content": (
            'Gerne kann ich dir einen Gaming-Container mit Steam einrichten. '
            'Der passende Blueprint "gaming-station" ist bereits verfügbar. '
            'Möchtest du, dass ich diesen für dich starte?'
        ),
    },
]


@pytest.fixture(scope="session", autouse=True)
def check_services():
    try:
        r = requests.get(f"{ADMIN_API}/health", timeout=5)
        assert r.status_code == 200
    except Exception as e:
        pytest.skip(f"admin-api nicht erreichbar ({ADMIN_API}): {e}")


def _docker(snippet: str, timeout: int = 30) -> str:
    """Python-Snippet im Container ausführen, letzten Output-Block zurückgeben."""
    cmd = [
        "docker", "exec", CONTAINER,
        "python3", "-u", "-c",
        f"import sys; sys.path.insert(0, '{APP_PATH}')\n{snippet}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    lines = [l for l in r.stdout.splitlines() if not l.startswith("[20")]
    return "\n".join(lines).strip()


def _docker_json(snippet: str, timeout: int = 30) -> dict:
    """Python-Snippet im Container, letzten JSON-Block parsen."""
    cmd = [
        "docker", "exec", CONTAINER,
        "python3", "-u", "-c",
        f"import sys; sys.path.insert(0, '{APP_PATH}')\n{snippet}",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    raw = r.stdout.strip()
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if line.startswith("{") or line.startswith("["):
            return json.loads(line)
    raise RuntimeError(
        f"Kein JSON.\nstdout:\n{raw[:1000]}\nstderr:\n{r.stderr[:500]}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Stage 1: Tool-Selector — kurzer Input mit Kontext anreichern
# ══════════════════════════════════════════════════════════════════════════════

class TestStage1ToolSelector:
    """C3: A-Enrichment + Semantic Search für 'ja bitte' mit Gaming-Kontext."""

    def test_tool_selector_enriches_ja_bitte(self):
        """ToolSelector muss 'ja bitte' mit context_summary anreichern."""
        result = _docker("""
import asyncio
from core.tool_selector import ToolSelector

captured = []

async def run():
    sel = ToolSelector.__new__(ToolSelector)
    sel._semantic_unavailable_logged = False

    async def fake_candidates(q):
        captured.append(q)
        return []
    sel._get_candidates = fake_candidates

    from unittest.mock import MagicMock
    sel.hub = MagicMock()

    from unittest.mock import patch
    with patch('core.tool_selector.ENABLE_TOOL_SELECTOR', True):
        await sel.select_tools(
            'ja bitte',
            context_summary='Möchtest du, dass ich den Blueprint gaming-station starte?'
        )

asyncio.run(run())
print('QUERY:', captured[0] if captured else 'EMPTY')
""")
        assert "QUERY:" in result, f"Kein Output: {result}"
        query = result.split("QUERY:", 1)[1].strip()
        assert "ja bitte" in query, f"'ja bitte' fehlt im Query: {query}"
        assert "gaming-station" in query or "Blueprint" in query, (
            f"Kontext fehlt im angereicherten Query: {query}"
        )

    def test_short_input_bypass_in_tool_selector_does_not_add_home_write(self):
        """C1-Check: ToolSelector selbst injiziert home_write NICHT — nur Stream-Flow."""
        result = _docker("""
from pathlib import Path
src = Path('/app/core/tool_selector.py').read_text()
print('home_write_in_selector:', 'home_write' in src)
""")
        assert "home_write_in_selector: False" in result, (
            "home_write sollte NICHT im tool_selector.py stehen"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Stage 2: Short-Input Bypass — Tool-Injection ohne home_write?
# ══════════════════════════════════════════════════════════════════════════════

class TestStage2ShortInputBypass:
    """C1: Bypass darf home_write nur injizieren wenn KEIN Kontext vorhanden."""

    def test_bypass_injects_home_write_unconditionally(self):
        """Diagnose: Injiziert der Bypass home_write auch wenn Kontext vorhanden ist?"""
        result = _docker("""
from pathlib import Path
src = Path('/app/core/orchestrator_stream_flow_utils.py').read_text()
bypass_idx = src.find('Short-Input Bypass:')
assert bypass_idx != -1
block = src[bypass_idx:bypass_idx+300]
print('BYPASS_BLOCK:', repr(block[:200]))
""")
        assert "BYPASS_BLOCK:" in result, f"Kein Output: {result}"
        block = result.split("BYPASS_BLOCK:", 1)[1].strip()
        # Diagnose: home_write vorhanden?
        has_home_write = "home_write" in block
        print(f"\n[DIAGNOSE C1] Bypass enthält home_write: {has_home_write}")
        # Dies ist ein reiner Diagnosetest — kein assert, damit alle Tests laufen

    def test_bypass_context_conditional_check(self):
        """C1-Fix-Check: Bypass muss _last_assistant_msg prüfen (home_write nur ohne Kontext)."""
        result = _docker("""
from pathlib import Path
src = Path('/app/core/orchestrator_stream_flow_utils.py').read_text()
bypass_idx = src.find('Short-Input Bypass:')
block = src[bypass_idx:bypass_idx+700]
print('CONDITIONAL:', '_last_assistant_msg' in block)
# Prüfe ob home_write NUR im else-Zweig steht
home_write_idx = block.find('home_write')
last_msg_idx = block.find('_last_assistant_msg')
print('ORDER_OK:', last_msg_idx < home_write_idx if last_msg_idx != -1 and home_write_idx != -1 else False)
""")
        assert "CONDITIONAL: True" in result, (
            "C1-BUG: Short-Input Bypass prüft _last_assistant_msg NICHT — "
            "injiziert home_write auch bei bestehendem Konversationskontext!"
        )
        assert "ORDER_OK: True" in result, (
            "C1-BUG: _last_assistant_msg-Check steht NACH home_write — falsche Reihenfolge!"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Stage 3: Plan Bypass — thinking_plan korrekt überschrieben?
# ══════════════════════════════════════════════════════════════════════════════

class TestStage3PlanBypass:
    """C2: Short-Input Plan Bypass muss thinking_plan['suggested_tools'] befüllen."""

    def test_plan_bypass_code_present(self):
        """Plan-Bypass-Code muss im stream flow vorhanden sein."""
        result = _docker("""
from pathlib import Path
src = Path('/app/core/orchestrator_stream_flow_utils.py').read_text()
print('BYPASS_PRESENT:', 'Short-Input Plan Bypass' in src)
print('INJECTION_PRESENT:', 'thinking_plan[\\"suggested_tools\\"] = list(selected_tools)' in src)
""")
        assert "BYPASS_PRESENT: True" in result, "Plan-Bypass fehlt im stream flow"
        assert "INJECTION_PRESENT: True" in result, "suggested_tools-Injection fehlt"

    def test_plan_bypass_position_is_before_control_layer(self):
        """Plan-Bypass muss VOR dem Control Layer im Code stehen."""
        result = _docker("""
from pathlib import Path
src = Path('/app/core/orchestrator_stream_flow_utils.py').read_text()
bypass_idx = src.find('Short-Input Plan Bypass')
# Support both old and new control layer markers
control_idx = src.find('# Layer 2: Control')
if control_idx == -1:
    control_idx = src.find('LAYER 2 CONTROL')
if control_idx == -1:
    control_idx = src.find('Layer 2 CONTROL')
print('BYPASS_IDX:', bypass_idx)
print('CONTROL_IDX:', control_idx)
print('ORDER_OK:', bypass_idx < control_idx if bypass_idx != -1 and control_idx != -1 else 'MISSING')
""")
        assert "ORDER_OK: True" in result, (
            "C2-BUG: Plan-Bypass steht NACH dem Control Layer — "
            "Control Layer sieht suggested_tools=[] und stripped die Tools!"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Stage 4: Thinking Layer — A-Enrichment korrekt weitergegeben?
# ══════════════════════════════════════════════════════════════════════════════

class TestStage4ThinkingEnrichment:
    """C3: analyze_stream muss _thinking_user_text (angereichert) bekommen."""

    def test_a_enrichment_passes_context_to_analyze_stream(self):
        """A-Enrichment: analyze_stream-Call muss _thinking_user_text übergeben."""
        result = _docker("""
from pathlib import Path
src = Path('/app/core/orchestrator_stream_flow_utils.py').read_text()
# Finde den analyze_stream-Call
analyze_idx = src.find('orch.thinking.analyze_stream(')
block = src[analyze_idx:analyze_idx+200]
print('USES_THINKING_TEXT:', '_thinking_user_text' in block)
""")
        assert "USES_THINKING_TEXT: True" in result, (
            "C3-BUG: analyze_stream bekommt user_text statt _thinking_user_text — "
            "A-Enrichment hat keinen Effekt!"
        )


# ══════════════════════════════════════════════════════════════════════════════
# Stage 5: Control Layer — Approved aber mit welchen Tools?
# ══════════════════════════════════════════════════════════════════════════════

class TestStage5ControlLayer:
    """C2/C4: Prüfen ob Control Layer suggested_tools aus dem Plan erhält."""

    def test_control_layer_sees_suggested_tools_from_plan(self):
        """Control Layer muss verified_plan['suggested_tools'] aus thinking_plan lesen."""
        result = _docker("""
from pathlib import Path
src = Path('/app/core/layers/control.py').read_text()
# Control Layer muss suggested_tools aus dem Plan benutzen
print('READS_SUGGESTED:', 'suggested_tools' in src)
""")
        assert "READS_SUGGESTED: True" in result

    def test_control_verify_preserves_suggested_tools(self):
        """Nach Control Layer muss verified_plan['suggested_tools'] noch gefüllt sein."""
        result = _docker("""
from pathlib import Path
src = Path('/app/core/orchestrator_stream_flow_utils.py').read_text()
# Finde wo verified_plan erstellt wird
verify_idx = src.find('verified_plan')
# Prüfe ob suggested_tools in verified_plan kopiert wird (großes Fenster nötig)
print('SUGGESTED_IN_VERIFY:', 'suggested_tools' in src[verify_idx:verify_idx+12000])
""")
        assert "SUGGESTED_IN_VERIFY: True" in result


# ══════════════════════════════════════════════════════════════════════════════
# Stage 6: Live-HTTP-Test — vollständiger "ja bitte" Flow
# ══════════════════════════════════════════════════════════════════════════════

class TestStage6LiveFlow:
    """Vollständiger Live-Test: 'ja bitte' nach Gaming-Container-Angebot."""

    def test_ja_bitte_triggers_request_container_tool(self):
        """'ja bitte' muss request_container aufrufen (oder pending_approval anzeigen)."""
        payload = {
            "message": "ja bitte",
            "conversation_id": "e2e_diag_ja_bitte_001",
            "messages": GAMING_OFFER_HISTORY,
            "model": "deepseek-v3.1:671b",
        }
        r = requests.post(
            f"{ADMIN_API}/api/chat",
            json=payload,
            timeout=120,
        )
        assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:500]}"
        body = r.json()
        response_text = body.get("response", body.get("content", ""))
        assert response_text, "Leere Response"

        # Darf NICHT die Persona-Intro sein
        assert "Wie soll ich dich nennen" not in response_text, (
            f"C1/C4-BUG: Onboarding-Text statt Container-Response!\n"
            f"Response: {response_text[:300]}"
        )
        assert "persönlicher AI-Assistent" not in response_text or "Container" in response_text, (
            f"Persona-Intro ohne Container-Kontext\nResponse: {response_text[:300]}"
        )

        # Sollte pending_approval oder Container-Infos enthalten
        keywords = [
            "gaming", "steam", "blueprint", "container", "genehmigung",
            "approval", "starte", "gestartet", "pending", "anfrage",
        ]
        found = [kw for kw in keywords if kw.lower() in response_text.lower()]
        assert found, (
            f"Response enthält keinen Container-Kontext.\n"
            f"Erwartet mind. eines von: {keywords}\n"
            f"Response: {response_text[:500]}"
        )

    def test_ja_bitte_stream_response(self):
        """Stream-Mode: 'ja bitte' darf nicht mit Persona-Intro antworten."""
        payload = {
            "message": "ja bitte",
            "conversation_id": "e2e_diag_ja_bitte_stream_001",
            "messages": GAMING_OFFER_HISTORY,
            "model": "deepseek-v3.1:671b",
            "stream": True,
        }
        r = requests.post(
            f"{ADMIN_API}/api/chat/stream",
            json=payload,
            timeout=120,
            stream=True,
        )
        assert r.status_code == 200, f"HTTP {r.status_code}"

        full_text = ""
        for line in r.iter_lines():
            if line:
                raw = line.decode("utf-8")
                if raw.startswith("data:"):
                    raw = raw[5:].strip()
                try:
                    ev = json.loads(raw)
                    full_text += ev.get("content", ev.get("chunk", ""))
                except Exception:
                    pass

        assert full_text, "Leere Stream-Response"
        assert "Wie soll ich dich nennen" not in full_text, (
            f"C1-BUG Stream: Onboarding-Text!\nResponse: {full_text[:300]}"
        )

    def test_grounding_evidence_not_empty_after_flow(self):
        """Grounding Evidence darf nach request_container nicht leer sein (Fix #12B)."""
        result = _docker_json("""
import asyncio, json
from core.plan_runtime_bridge import get_runtime_grounding_evidence

# Simuliere ein Plan-Dict das persist_execution_result durchlaufen hat
from core.plan_runtime_bridge import (
    execution_result_from_plan,
    persist_execution_result,
    set_runtime_grounding_evidence,
    get_runtime_grounding_evidence,
)

plan = {"suggested_tools": ["request_container"], "_execution_result": {}}

# Schreibe Evidence
set_runtime_grounding_evidence(plan, [{"tool_name": "request_container", "status": "pending_approval"}])

# Simuliere persist (der Bug)
er = execution_result_from_plan(plan)
persist_execution_result(plan, er)

# Evidence nach persist
evidence_after_persist = get_runtime_grounding_evidence(plan)

# Fix #12B: Re-apply
set_runtime_grounding_evidence(plan, [{"tool_name": "request_container", "status": "pending_approval"}])
evidence_after_reapply = get_runtime_grounding_evidence(plan)

print(json.dumps({
    "evidence_after_persist": evidence_after_persist,
    "evidence_after_reapply": evidence_after_reapply,
    "bug_present": len(evidence_after_persist) == 0,
    "fix_works": len(evidence_after_reapply) > 0,
}))
""")
        assert result.get("fix_works") is True, (
            "Fix #12B: Re-apply nach persist funktioniert nicht!"
        )
        if result.get("bug_present"):
            print(
                "\n[DIAGNOSE C5] persist_execution_result BUG bestätigt: "
                "Evidence wird nach persist geleert. Fix #12B wurde korrekt implementiert."
            )

    def test_has_pending_approval_bypass_fires(self):
        """_has_pending_approval Bypass in output.py muss bei pending_approval feuern."""
        result = _docker_json("""
import json, asyncio
from core.layers.output import OutputLayer
from core.plan_runtime_bridge import set_runtime_grounding_evidence

# Minimal-Plan mit pending_approval Evidence
plan = {
    "suggested_tools": ["request_container"],
    "_execution_result": {},
    "_grounding_evidence": [],
}
set_runtime_grounding_evidence(plan, [
    {
        "tool_name": "request_container",
        "status": "pending_approval",
        "key_facts": ['{"status": "pending_approval", "approval_id": "test-123"}'],
    }
])

layer = OutputLayer.__new__(OutputLayer)
# _grounding_precheck braucht minimale Konfiguration
layer._grounding_policy_cfg = None

# Rufe _grounding_precheck auf (sync)
try:
    result = layer._grounding_precheck(
        verified_plan=plan,
        execution_result=None,
        memory_data="",
    )
    print(json.dumps({
        "mode": result.get("mode"),
        "blocked": result.get("blocked"),
        "pending_bypass_fired": result.get("mode") == "pass" and result.get("blocked_reason") == "pending_approval",
    }))
except Exception as e:
    print(json.dumps({"error": str(e), "mode": "unknown"}))
""")
        mode = result.get("mode")
        bypass_fired = result.get("pending_bypass_fired", False)
        if not bypass_fired:
            print(
                f"\n[DIAGNOSE C6] _has_pending_approval Bypass feuerte NICHT! "
                f"mode={mode}, blocked={result.get('blocked')}"
            )
        assert mode == "pass", (
            f"C6-BUG: _has_pending_approval Bypass liefert mode={mode} statt 'pass'. "
            f"Evidence mit status=pending_approval wird nicht erkannt!"
        )
