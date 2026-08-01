from core.sandbox.runner import CodeSandbox


def test_allows_math():
    sb = CodeSandbox()
    r = sb.run("import math\nprint(math.sqrt(16))\nx = 2 + 2")
    assert r["ok"] is True


def test_blocks_open():
    sb = CodeSandbox()
    r = sb.run("open('/etc/passwd').read()")
    assert r["ok"] is False


def test_blocks_import_os():
    sb = CodeSandbox()
    r = sb.run("import os\nos.system('ls')")
    assert r["ok"] is False


def test_blocks_eval_name():
    sb = CodeSandbox()
    r = sb.run("eval('1+1')")
    assert r["ok"] is False
