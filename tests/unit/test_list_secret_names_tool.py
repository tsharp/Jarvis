"""Tests for ListSecretNamesTool and its registration."""
import json
from unittest.mock import patch, MagicMock
import pytest

from core.tools.fast_lane.definitions import ListSecretNamesTool
from core.task_loop.action_resolution.tool_utility_policy.tool_catalog import (
    DISCOVERY_TOOLS,
    is_discovery_only,
)
from core.layers.control.tools.availability import is_tool_available


# ---------------------------------------------------------------------------
# ListSecretNamesTool unit tests
# ---------------------------------------------------------------------------

class TestListSecretNamesTool:
    def _mock_response(self, body: bytes):
        resp = MagicMock()
        resp.read.return_value = body
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    def test_returns_sorted_list_from_list_payload(self):
        payload = json.dumps(["OPENAI_KEY", "ANTHROPIC_KEY", "DISCORD_TOKEN"]).encode()
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = ListSecretNamesTool().execute()
        assert result == ["ANTHROPIC_KEY", "DISCORD_TOKEN", "OPENAI_KEY"]

    def test_returns_sorted_list_from_dict_names_key(self):
        payload = json.dumps({"names": ["OPENAI_KEY", "GITHUB_TOKEN"]}).encode()
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = ListSecretNamesTool().execute()
        assert result == ["GITHUB_TOKEN", "OPENAI_KEY"]

    def test_returns_sorted_list_from_dict_secrets_key(self):
        payload = json.dumps({"secrets": ["B_KEY", "A_KEY"]}).encode()
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = ListSecretNamesTool().execute()
        assert result == ["A_KEY", "B_KEY"]

    def test_returns_empty_list_for_empty_payload(self):
        payload = json.dumps([]).encode()
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = ListSecretNamesTool().execute()
        assert result == []

    def test_deduplicates_names(self):
        payload = json.dumps(["KEY", "KEY", "OTHER"]).encode()
        with patch("urllib.request.urlopen", return_value=self._mock_response(payload)):
            result = ListSecretNamesTool().execute()
        assert result == ["KEY", "OTHER"]

    def test_raises_on_network_error(self):
        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            with pytest.raises(RuntimeError, match="list_secret_names"):
                ListSecretNamesTool().execute()

    def test_url_derivation_strips_resolve_suffix(self):
        captured = {}
        payload = json.dumps([]).encode()

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            return self._mock_response(payload)

        with patch.dict("os.environ", {"SECRETS_API_URL": "http://jarvis-admin-api:8200/api/secrets/resolve"}):
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                ListSecretNamesTool().execute()

        assert captured["url"] == "http://jarvis-admin-api:8200/api/secrets"

    def test_url_derivation_uses_default_when_env_not_set(self):
        captured = {}
        payload = json.dumps([]).encode()

        def fake_urlopen(req, timeout):
            captured["url"] = req.full_url
            return self._mock_response(payload)

        with patch.dict("os.environ", {}, clear=False):
            import os
            os.environ.pop("SECRETS_API_URL", None)
            with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                ListSecretNamesTool().execute()

        assert captured["url"] == "http://jarvis-admin-api:8200/api/secrets"


# ---------------------------------------------------------------------------
# Discovery-Tool registration
# ---------------------------------------------------------------------------

class TestListSecretNamesRegistration:
    def test_is_in_discovery_tools(self):
        assert "list_secret_names" in DISCOVERY_TOOLS

    def test_is_discovery_only_for_single_tool(self):
        assert is_discovery_only(["list_secret_names"]) is True

    def test_is_discovery_only_combined_with_other_discovery(self):
        assert is_discovery_only(["list_secret_names", "list_skills"]) is True

    def test_not_discovery_only_when_mixed_with_action_tool(self):
        assert is_discovery_only(["list_secret_names", "create_skill"]) is False

    def test_is_available_as_native_tool(self):
        result = is_tool_available(
            "list_secret_names",
            mcp_hub=None,
            get_hub_fn=lambda: None,
            log_info_fn=lambda _: None,
            log_warning_fn=lambda _: None,
            get_available_skills_fn=lambda: [],
        )
        assert result is True
