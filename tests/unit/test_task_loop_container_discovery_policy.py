from core.task_loop.capabilities.container.discovery_policy import (
    has_mixed_container_flow,
    preferred_container_discovery_tools,
    should_use_read_first,
    split_container_tools,
)


def test_split_container_tools_separates_query_and_action_tools():
    query_tools, action_tools = split_container_tools(
        ["blueprint_list", "request_container", "container_list"]
    )

    assert query_tools == ["blueprint_list", "container_list"]
    assert action_tools == ["request_container"]


def test_has_mixed_container_flow_requires_both_tool_classes():
    assert has_mixed_container_flow(["blueprint_list", "request_container"]) is True
    assert has_mixed_container_flow(["request_container"]) is False


def test_preferred_container_discovery_tools_prefers_existing_query_tools():
    out = preferred_container_discovery_tools(
        capability_context={"request_family": "generic_container"},
        suggested_tools=["container_list", "request_container"],
    )

    assert out == ["container_list"]


def test_preferred_container_discovery_tools_injects_blueprint_list_for_python_action_only():
    out = preferred_container_discovery_tools(
        capability_context={"request_family": "python_container"},
        suggested_tools=["request_container"],
    )

    assert out == ["blueprint_list"]


def test_should_use_read_first_for_python_action_only_container_request():
    assert should_use_read_first(
        capability_context={"request_family": "python_container"},
        suggested_tools=["request_container"],
    ) is True
