# Hashing fixtures

Byte-exact fixtures for `tests/unit/test_hashing.py`. **Do not reformat these files.**
`.gitattributes`, `.editorconfig`, and `.pre-commit-config.yaml` all exclude this
directory from newline and whitespace normalisation, because several of the tests exist
specifically to prove that no such normalisation happens.

| File | Bytes | SHA-256 | Why it exists |
|---|---|---|---|
| `empty.bin` | 0 | `e3b0c442...7852b855` | Empty-input vector |
| `abc.txt` | 3 | `ba7816bf...f20015ad` | NIST FIPS 180-4 `"abc"` vector |
| `all-bytes.bin` | 256 | `40aff2e9...bf944880` | Every byte value `0x00`-`0xFF`, including NUL |
| `crlf.txt` | 13 | `98ab4d3a...c2b6fc80` | CRLF line endings |
| `lf.txt` | 11 | `e49c81e2...7d0d78ee` | Same logical text with LF endings |

`crlf.txt` and `lf.txt` carry the same characters and must hash **differently**. If they
ever hash the same, something in the toolchain is normalising newlines and the byte-exact
guarantee is broken.
