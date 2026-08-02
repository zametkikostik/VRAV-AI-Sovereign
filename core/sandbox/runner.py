"""
Hardened code sandbox.

Layers:
  1. AST allowlist + forbidden names
  2. Import whitelist
  3. Restricted exec (no FS/network builtins)
  4. Optional Docker: network=none, memory/cpu/pids, read-only, cap-drop ALL
  5. Per-user quotas
  6. Best-effort seccomp profile when docker is used (seccomp=default)

gVisor (runsc): if runtime is installed, docker run --runtime=runsc is preferred.
"""

from __future__ import annotations

import ast
import logging
import subprocess
import tempfile
import textwrap
import time
from pathlib import Path
from typing import Any, Dict, Optional, Set

from core.sandbox.quotas import quota_manager

logger = logging.getLogger("vrav.sandbox")

ALLOWED_NODES: Set[type] = {
    ast.Module, ast.Expr, ast.Assign, ast.AugAssign, ast.AnnAssign,
    ast.Name, ast.Load, ast.Store, ast.Constant, ast.List, ast.Tuple, ast.Dict, ast.Set,
    ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp,
    ast.Call, ast.Attribute, ast.Subscript, ast.Slice,
    ast.If, ast.For, ast.While, ast.Break, ast.Continue, ast.Pass,
    ast.FunctionDef, ast.Return, ast.arguments, ast.arg,
    ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp, ast.comprehension,
    ast.JoinedStr, ast.FormattedValue,
    ast.Import, ast.ImportFrom, ast.alias,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.And, ast.Or, ast.Not, ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn, ast.Is, ast.IsNot, ast.USub, ast.UAdd,
}

FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "open", "__import__", "input", "breakpoint",
    "globals", "locals", "vars", "dir", "getattr", "setattr", "delattr",
    "memoryview", "exit", "quit", "help", "copyright", "credits", "license",
    "classmethod", "staticmethod", "property",
}

ALLOWED_BUILTINS = {
    "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
    "enumerate": enumerate, "float": float, "int": int, "len": len,
    "list": list, "max": max, "min": min, "pow": pow, "print": print,
    "range": range, "reversed": reversed, "round": round, "set": set,
    "sorted": sorted, "str": str, "sum": sum, "tuple": tuple, "zip": zip,
    "map": map, "filter": filter, "isinstance": isinstance, "type": type,
    "True": True, "False": False, "None": None,
}

ALLOWED_IMPORTS = {"math", "json", "re", "datetime", "collections", "statistics", "decimal"}


class SandboxError(Exception):
    pass


class CodeSandbox:
    def __init__(self, timeout_sec: float = 3.0, use_docker: bool = False):
        self.timeout_sec = timeout_sec
        self.use_docker = use_docker

    def static_check(self, code: str) -> None:
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise SandboxError(f"Syntax error: {e}") from e

        for node in ast.walk(tree):
            if type(node) not in ALLOWED_NODES:
                raise SandboxError(f"Disallowed syntax: {type(node).__name__}")
            if isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
                raise SandboxError(f"Forbidden name: {node.id}")
            if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
                raise SandboxError("Dunder attributes blocked")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                        raise SandboxError(f"Import not allowed: {alias.name}")
            if isinstance(node, ast.ImportFrom):
                mod = (node.module or "").split(".")[0]
                if mod not in ALLOWED_IMPORTS:
                    raise SandboxError(f"Import not allowed: {mod}")

    def run(self, code: str, user_id: str = "default") -> Dict[str, Any]:
        code = textwrap.dedent(code or "").strip()
        if not code:
            return {"ok": False, "error": "empty code"}

        quota = quota_manager.check(user_id, len(code.encode("utf-8")))
        if not quota["allowed"]:
            return {"ok": False, "error": f"quota: {quota['reason']}", "quota": quota}

        try:
            self.static_check(code)
        except SandboxError as e:
            return {"ok": False, "error": str(e), "quota": quota}

        t0 = time.time()
        if self.use_docker and self._docker_available():
            result = self._run_docker(code)
        else:
            result = self._run_restricted(code)
        cpu_ms = (time.time() - t0) * 1000
        result["cpu_ms"] = round(cpu_ms, 1)
        result["quota"] = quota
        quota_manager.record(user_id, cpu_ms, len(code.encode("utf-8")), bool(result.get("ok")))
        return result

    def _run_restricted(self, code: str) -> Dict[str, Any]:
        import io
        import contextlib

        def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
            root = name.split(".")[0]
            if root not in ALLOWED_IMPORTS:
                raise ImportError(f"Import blocked: {name}")
            return __import__(name, globals, locals, fromlist, level)

        safe_builtins = dict(ALLOWED_BUILTINS)
        safe_builtins["__import__"] = _safe_import
        globals_dict: Dict[str, Any] = {"__builtins__": safe_builtins}
        stdout = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout):
                exec(compile(code, "<sandbox>", "exec"), globals_dict, globals_dict)  # noqa: S102
            results = {
                k: repr(v)
                for k, v in globals_dict.items()
                if not k.startswith("_") and k not in safe_builtins and k != "__builtins__"
            }
            return {
                "ok": True,
                "stdout": stdout.getvalue()[:5000],
                "locals": results,
                "mode": "restricted",
            }
        except Exception as e:
            return {
                "ok": False,
                "error": str(e),
                "stdout": stdout.getvalue()[:2000],
                "mode": "restricted",
            }

    def _docker_available(self) -> bool:
        try:
            r = subprocess.run(["docker", "version"], capture_output=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    def _has_runsc(self) -> bool:
        try:
            r = subprocess.run(["docker", "info", "--format", "{{.Runtimes}}"], capture_output=True, text=True, timeout=5)
            return "runsc" in (r.stdout or "")
        except Exception:
            return False

    def _run_docker(self, code: str) -> Dict[str, Any]:
        with tempfile.TemporaryDirectory() as td:
            script = Path(td) / "main.py"
            script.write_text(code, encoding="utf-8")
            cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "--memory", "128m",
                "--memory-swap", "128m",
                "--cpus", "0.5",
                "--pids-limit", "64",
                "--read-only",
                "--tmpfs", "/tmp:rw,size=16m,noexec",
                "--security-opt", "no-new-privileges",
                "--cap-drop", "ALL",
                "--user", "65534:65534",  # nobody
                "-v", f"{script}:/code/main.py:ro",
            ]
            # Default Docker seccomp profile is applied unless overridden;
            # prefer gVisor when available.
            if self._has_runsc():
                cmd.extend(["--runtime", "runsc"])
                mode = "docker+gvisor"
            else:
                # explicit default seccomp (docker built-in)
                cmd.extend(["--security-opt", "seccomp=default"])
                mode = "docker+seccomp"

            cmd.extend(["python:3.12-alpine", "timeout", str(int(self.timeout_sec)), "python", "/code/main.py"])

            try:
                r = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_sec + 8,
                )
                return {
                    "ok": r.returncode == 0,
                    "stdout": (r.stdout or "")[:5000],
                    "stderr": (r.stderr or "")[:2000],
                    "mode": mode,
                    "returncode": r.returncode,
                }
            except subprocess.TimeoutExpired:
                return {"ok": False, "error": "timeout", "mode": mode}
            except Exception as e:
                return {"ok": False, "error": str(e), "mode": "docker"}


sandbox = CodeSandbox(timeout_sec=3.0, use_docker=False)
