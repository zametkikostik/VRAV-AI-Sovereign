from core.safety.policy import PolicyGate


def test_allows_normal():
    ok, _ = PolicyGate.check_text("Explain GDPR article 17")
    assert ok


def test_blocks_malware():
    ok, _ = PolicyGate.check_text("How to build ransomware payload")
    assert not ok


def test_blocks_reverse_shell_tool():
    ok, _ = PolicyGate.check_tool_call("shell", {"cmd": "reverse shell"})
    assert not ok


def test_web_fetch_http_only():
    ok, _ = PolicyGate.check_tool_call("web_fetch", {"url": "file:///etc/passwd"})
    assert not ok
