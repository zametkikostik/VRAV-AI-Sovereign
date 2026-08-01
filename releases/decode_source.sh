#!/bin/bash
set -e
cat full-source.part_*.b64 | base64 -d > full-source.tar.gz
tar xzf full-source.tar.gz
echo "OK: extracted"
ls -la vrav_ai | head
