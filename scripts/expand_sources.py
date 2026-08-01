#!/usr/bin/env python3
"""Expand embedded VRAV sources. Run from repo root: python scripts/expand_sources.py"""
import base64, pathlib, json
ROOT = pathlib.Path(__file__).resolve().parents[1]
parts = sorted((ROOT / "releases" / "src_parts").glob("part_*.json"))
payload = {}
for p in parts:
    payload.update(json.loads(p.read_text()))
for path, b64 in payload.items():
    dest = ROOT / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(base64.b64decode(b64))
    print("wrote", path)
print("done", len(payload), "files")
