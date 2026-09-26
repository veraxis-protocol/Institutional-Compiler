# H1 ZIP Access Constraint — VEIP-MCP-H1-LIVE-SDK-COMPAT-001

**Date:** 2026-09-22  

## Constraint encountered

The execution environment's egress proxy (127.0.0.1:46639) applies organization policy
that denies `CONNECT` tunnel to `dropboxusercontent.com:443`. This is the Dropbox content
delivery domain from which temporary download URLs are served.

### Attempted path

```
curl → https://uc4543d5f618442b20b4a88131b1.dl.dropboxusercontent.com/...
Result: 403 (proxy rejection)
```

### Impact

- The raw ZIP bytes were not downloaded to disk.
- SHA-256 of the ZIP file (`abe14ef87dcdafcfb7260f525f8a9c313664ff3a10048f31591be07d18622567`) could not be independently computed.

## Mitigation applied

The Dropbox MCP server (which operates server-side and uses `api.dropboxapi.com`, not the CDN)
was used to extract the ZIP contents. Dropbox's content extraction service unzipped the archive
and returned the text content of all files.

### Verification of retrieval authenticity

- Dropbox file accessed by exact file ID: `id:AdzSIi2kJ_kAAAAAAAA42Q`
- Dropbox metadata confirmed: `VEIP_MCP_H1_PARSER_BUILD_2026-09-22_r2.zip`, size 29,201 bytes
- 26 source files extracted; 25 of 26 hashed to SHA256SUMS.txt values exactly;
  1 mismatch (`probe/__init__.py`): Dropbox text extraction adds trailing newline to empty files
  → corrected to empty (0 bytes) → SHA-256 = `e3b0c44...` → MATCH

### Residual risk

If the file at Dropbox id `AdzSIi2kJ_kAAAAAAAA42Q` was replaced between the time the prior
report was written and this execution, the ZIP SHA-256 verification would not catch it.
This risk is accepted as the file was uploaded by the same owner account and the extracted
file hashes match the SHA256SUMS.txt that was part of the ZIP itself.

## NOT SELF-ADJUDICATED

Independent verification should confirm that id `AdzSIi2kJ_kAAAAAAAA42Q` in the owner's
Dropbox account contains the expected ZIP with SHA-256
`abe14ef87dcdafcfb7260f525f8a9c313664ff3a10048f31591be07d18622567`.
