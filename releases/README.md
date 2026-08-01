# Full source release

Complete VRAV AI tree is split across base64 parts (GitHub commit size limits).

```bash
cd releases
bash decode_source.sh
# extracts ../vrav_ai with all modules
```

Or:

```bash
cat full-source.part_*.b64 | base64 -d > full-source.tar.gz
tar xzf full-source.tar.gz
```
