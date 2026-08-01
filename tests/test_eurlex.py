"""EUR-Lex client unit tests."""

from core.tools.eurlex import EURLexClient


def test_html_to_text():
    client = EURLexClient()
    html = "<html><head><title>GDPR</title></head><body><p>Article 1</p><script>x</script></body></html>"
    text = client._html_to_text(html)
    assert "Article 1" in text
    assert client._extract_title(html) == "GDPR"


def test_invalid_celex_format():
    import asyncio
    client = EURLexClient()
    result = asyncio.get_event_loop().run_until_complete(client.get_by_celex("not a celex!!!"))
    assert "error" in result
