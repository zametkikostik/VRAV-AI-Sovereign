from core.agent_loop import AgentToolLoop


def test_extract_tool_call_xml():
    loop = AgentToolLoop()
    text = 'Thinking...\n<tool_call>\n{"name": "wiki_summary", "arguments": {"title": "GDPR"}}\n</tool_call>'
    tc = loop._extract_tool_call(text)
    assert tc is not None
    assert tc["name"] == "wiki_summary"
    assert tc["arguments"]["title"] == "GDPR"


def test_extract_no_tool():
    loop = AgentToolLoop()
    assert loop._extract_tool_call("Just a normal final answer about privacy.") is None


def test_tools_prompt_nonempty():
    import core.mcp.builtin_tools  # noqa
    import core.mcp.research_tools  # noqa
    loop = AgentToolLoop()
    p = loop._tools_prompt()
    assert "web_search" in p or "eurlex_get" in p
