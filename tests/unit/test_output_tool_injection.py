import unittest
from unittest.mock import patch

from core.layers.output import OutputLayer


_TOOLS = [
    {"name": "list_skills", "mcp": "skill-server", "description": "List skills"},
    {"name": "memory_graph_search", "mcp": "sql-memory", "description": "Search memory"},
]


class TestOutputToolInjection(unittest.TestCase):
    @patch("core.layers.output.get_enabled_tools", return_value=_TOOLS)
    @patch("core.layers.output.get_output_tool_prompt_limit", return_value=10)
    @patch("core.layers.output.get_output_tool_injection_mode", return_value="selected")
    def test_selected_mode_injects_only_selected_tools(self, *_mocks):
        layer = OutputLayer()
        plan = {"_selected_tools_for_prompt": ["list_skills"]}
        prompt = layer.build_system_prompt(plan, memory_data="")
        self.assertIn("list_skills", prompt)
        self.assertNotIn("memory_graph_search", prompt)

    @patch("core.layers.output.get_enabled_tools", return_value=_TOOLS)
    @patch("core.layers.output.get_output_tool_prompt_limit", return_value=10)
    @patch("core.layers.output.get_output_tool_injection_mode", return_value="none")
    def test_none_mode_disables_tool_injection(self, *_mocks):
        layer = OutputLayer()
        prompt = layer.build_system_prompt({}, memory_data="")
        self.assertNotIn("VERFÜGBARE TOOLS", prompt)
        self.assertNotIn("list_skills", prompt)

    @patch("core.layers.output.get_enabled_tools", return_value=_TOOLS)
    @patch("core.layers.output.get_output_tool_prompt_limit", return_value=10)
    @patch("core.layers.output.get_output_tool_injection_mode", return_value="selected")
    def test_interactive_mode_adds_output_budget_hint(self, *_mocks):
        layer = OutputLayer()
        prompt = layer.build_system_prompt({"_response_mode": "interactive"}, memory_data="")
        self.assertIn("ANTWORT-BUDGET", prompt)

    @patch("core.layers.output.get_enabled_tools", return_value=_TOOLS)
    @patch("core.layers.output.get_output_tool_prompt_limit", return_value=10)
    @patch("core.layers.output.get_output_tool_injection_mode", return_value="selected")
    def test_deep_mode_includes_output_budget_hint(self, *_mocks):
        layer = OutputLayer()
        prompt = layer.build_system_prompt({"_response_mode": "deep"}, memory_data="")
        self.assertIn("ANTWORT-BUDGET", prompt)
        self.assertIn("Deep-Modus", prompt)

    @patch("core.layers.output.get_enabled_tools", return_value=_TOOLS)
    @patch("core.layers.output.get_output_tool_prompt_limit", return_value=10)
    @patch("core.layers.output.get_output_tool_injection_mode", return_value="selected")
    def test_dialog_guidance_for_feedback_turn(self, *_mocks):
        layer = OutputLayer()
        prompt = layer.build_system_prompt(
            {
                "_response_mode": "interactive",
                "dialogue_act": "feedback",
                "response_tone": "mirror_user",
                "response_length_hint": "short",
                "tone_confidence": 0.88,
            },
            memory_data="",
        )
        self.assertIn("DIALOG-FÜHRUNG", prompt)
        self.assertIn("1-3 Sätze", prompt)
        self.assertIn("Spiegle Ton", prompt)

    @patch("core.layers.output.get_enabled_tools", return_value=_TOOLS)
    @patch("core.layers.output.get_output_tool_prompt_limit", return_value=10)
    @patch("core.layers.output.get_output_tool_injection_mode", return_value="selected")
    def test_smalltalk_prompt_adds_no_fabricated_experience_guard(self, *_mocks):
        layer = OutputLayer()
        prompt = layer.build_system_prompt(
            {
                "_response_mode": "interactive",
                "dialogue_act": "smalltalk",
                "response_tone": "warm",
                "response_length_hint": "short",
            },
            memory_data="",
        )
        self.assertIn("keine erfundenen persönlichen Erlebnisse", prompt)
        self.assertIn("ohne menschlichen Alltag", prompt)

    @patch("core.layers.output.get_enabled_tools", return_value=_TOOLS)
    @patch("core.layers.output.get_output_tool_prompt_limit", return_value=10)
    @patch("core.layers.output.get_output_tool_injection_mode", return_value="selected")
    def test_skill_catalog_context_prompt_adds_skill_semantics_rules(self, *_mocks):
        layer = OutputLayer()
        prompt = layer.build_system_prompt(
            {
                "_response_mode": "interactive",
                "resolution_strategy": "skill_catalog_context",
                "_skill_catalog_policy": {
                    "mode": "inventory_read_only",
                    "required_tools": ["list_skills"],
                    "force_sections": ["Runtime-Skills", "Einordnung"],
                },
                "_skill_catalog_context": {"installed_count": 2, "draft_count": 1},
            },
            memory_data="",
        )
        self.assertIn("SKILL-SEMANTIK", prompt)
        self.assertIn("SKILL-KATALOG-ANTWORTMODUS", prompt)
        self.assertIn("`list_skills` beschreibt nur installierte Runtime-Skills", prompt)
        self.assertIn("Verbindlicher Skill-Catalog-Contract fuer diesen Turn", prompt)
        self.assertIn("Built-in Tools", prompt)
        self.assertIn("Pflichtreihenfolge: `Runtime-Skills`, dann `Einordnung`, danach optional `Nächster Schritt`.", prompt)
        self.assertIn("Der erste Satz im Abschnitt `Runtime-Skills` muss den Runtime-Befund", prompt)
        self.assertIn("Im Abschnitt `Runtime-Skills` keine Built-in Tools", prompt)
        self.assertIn("aktuell 2 installierte Runtime-Skills", prompt)
        self.assertIn("inventory_read_only", prompt)
        self.assertIn("keine ungefragten Skill-Erstellungs-", prompt)
        self.assertIn("Die Antwort MUSS mit dem Literal `Runtime-Skills:` beginnen.", prompt)
        self.assertIn("VERPFLICHTENDES ANTWORTGERUEST", prompt)
        self.assertIn("Runtime-Skills: <verifizierter Runtime-Befund", prompt)
        self.assertIn("Einordnung: <klare Trennung", prompt)

    @patch("core.layers.output.get_enabled_tools", return_value=_TOOLS)
    @patch("core.layers.output.get_output_tool_prompt_limit", return_value=10)
    @patch("core.layers.output.get_output_tool_injection_mode", return_value="selected")
    def test_skill_catalog_context_prompt_zero_inventory_demands_explicit_runtime_finding(self, *_mocks):
        layer = OutputLayer()
        prompt = layer.build_system_prompt(
            {
                "_response_mode": "interactive",
                "resolution_strategy": "skill_catalog_context",
                "strategy_hints": ["draft_skills"],
                "_skill_catalog_context": {"installed_count": 0, "draft_count": 1},
            },
            memory_data="",
        )
        self.assertIn("Im Runtime-Skill-System sind aktuell keine installierten Skills vorhanden.", prompt)
        self.assertIn("Keine unmarkierte Freitext-Liste", prompt)
        self.assertIn("Wenn die Frage nach Draft-Skills fragt, antworte trotzdem zuerst", prompt)
        self.assertIn("warum `list_skills` sie nicht anzeigt", prompt)

    @patch("core.layers.output.get_enabled_tools", return_value=_TOOLS)
    @patch("core.layers.output.get_output_tool_prompt_limit", return_value=10)
    @patch("core.layers.output.get_output_tool_injection_mode", return_value="selected")
    def test_skill_catalog_context_prompt_requires_split_for_inventory_plus_followup(self, *_mocks):
        layer = OutputLayer()
        prompt = layer.build_system_prompt(
            {
                "_response_mode": "interactive",
                "resolution_strategy": "skill_catalog_context",
                "strategy_hints": ["runtime_skills", "fact_then_followup"],
                "_skill_catalog_policy": {
                    "required_tools": ["list_skills"],
                    "force_sections": ["Runtime-Skills", "Einordnung", "Wunsch-Skills"],
                    "followup_split_required": True,
                },
                "_skill_catalog_context": {"installed_count": 0, "draft_count": 1},
            },
            memory_data="",
        )
        self.assertIn("Faktinventar und Wunsch-/Brainstorming-Teil kombiniert", prompt)
        self.assertIn("Wunsch-Skills", prompt)
        self.assertIn("Pflichtreihenfolge: `Runtime-Skills`, dann `Einordnung`, danach optional `Wunsch-Skills`.", prompt)
        self.assertIn("Der Anschlussblock muss `Wunsch-Skills` heißen", prompt)
        self.assertIn("Wunsch-Skills: <optional; Wunsch-Skills oder Vorschläge klar getrennt von Inventarfakten>.", prompt)
        self.assertNotIn("Nächster Schritt: <optional; Wunsch-Skills oder Vorschläge klar getrennt von Inventarfakten>.", prompt)

    @patch("core.layers.output.get_enabled_tools", return_value=_TOOLS)
    @patch("core.layers.output.get_output_tool_prompt_limit", return_value=10)
    @patch("core.layers.output.get_output_tool_injection_mode", return_value="selected")
    def test_container_inventory_prompt_adds_runtime_inventory_contract(self, *_mocks):
        layer = OutputLayer()
        prompt = layer.build_system_prompt(
            {
                "_response_mode": "interactive",
                "_container_query_policy": {
                    "query_class": "container_inventory",
                    "required_tools": ["container_list"],
                    "truth_mode": "runtime_inventory",
                },
            },
            memory_data="",
        )
        self.assertIn("CONTAINER-ANTWORTMODUS", prompt)
        self.assertIn("`container_list`", prompt)
        self.assertIn("truth_mode fuer diesen Turn: `runtime_inventory`.", prompt)
        self.assertIn("Pflichtreihenfolge: `Laufende Container`, dann `Gestoppte Container`, dann `Einordnung`.", prompt)
        self.assertIn("Die Antwort MUSS mit dem Literal `Laufende Container:` beginnen.", prompt)
        self.assertIn("Keine Blueprints, keine Startempfehlungen", prompt)
        self.assertIn("Keine ungefragten Betriebsdiagnosen", prompt)
        self.assertIn("Laufende Container: <verifizierter Runtime-Befund", prompt)
        self.assertIn("Gestoppte Container: <verifizierter Runtime-Befund", prompt)

    @patch("core.layers.output.get_enabled_tools", return_value=_TOOLS)
    @patch("core.layers.output.get_output_tool_prompt_limit", return_value=10)
    @patch("core.layers.output.get_output_tool_injection_mode", return_value="selected")
    def test_container_blueprint_prompt_adds_catalog_contract(self, *_mocks):
        layer = OutputLayer()
        prompt = layer.build_system_prompt(
            {
                "_response_mode": "interactive",
                "_container_query_policy": {
                    "query_class": "container_blueprint_catalog",
                    "required_tools": ["blueprint_list"],
                    "truth_mode": "blueprint_catalog",
                },
            },
            memory_data="",
        )
        self.assertIn("Pflichtreihenfolge: `Verfuegbare Blueprints`, dann `Einordnung`.", prompt)
        self.assertIn("Keine Behauptung ueber aktuell laufende oder installierte Container", prompt)
        self.assertIn("Keine zusaetzlichen Runtime-Inventar-, Running-/Stopped- oder Empty-State-Aussagen", prompt)
        self.assertIn("Die Antwort MUSS mit dem Literal `Verfuegbare Blueprints:` beginnen.", prompt)
        self.assertIn("Verfuegbare Blueprints: <verifizierter Katalog-Befund", prompt)
        self.assertIn("truth_mode fuer diesen Turn: `blueprint_catalog`.", prompt)

    @patch("core.layers.output.get_enabled_tools", return_value=_TOOLS)
    @patch("core.layers.output.get_output_tool_prompt_limit", return_value=10)
    @patch("core.layers.output.get_output_tool_injection_mode", return_value="selected")
    def test_container_binding_prompt_adds_binding_contract(self, *_mocks):
        layer = OutputLayer()
        prompt = layer.build_system_prompt(
            {
                "_response_mode": "interactive",
                "_container_query_policy": {
                    "query_class": "container_state_binding",
                    "required_tools": ["container_inspect", "container_list"],
                    "truth_mode": "session_binding",
                },
            },
            memory_data="",
        )
        self.assertIn("Pflichtreihenfolge: `Aktiver Container`, dann `Binding/Status`, dann `Einordnung`.", prompt)
        self.assertIn("`container_inspect`, `container_list` und Session-State", prompt)
        self.assertIn("Statische Profiltexte duerfen erklaeren, aber keinen Bindungsbeweis ersetzen.", prompt)
        self.assertIn("Keine Zeitspannen, Fehlerdiagnosen, Ursachenvermutungen", prompt)
        self.assertIn("Die Antwort MUSS mit dem Literal `Aktiver Container:` beginnen.", prompt)
        self.assertIn("Aktiver Container: <verifizierter Binding-Befund", prompt)
        self.assertIn("Binding/Status: <Session-Binding oder Runtime-Status", prompt)


if __name__ == "__main__":
    unittest.main()
