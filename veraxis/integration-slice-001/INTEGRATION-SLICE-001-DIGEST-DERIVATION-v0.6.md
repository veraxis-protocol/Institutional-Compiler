# INTEGRATION SLICE 001 — DIGEST DERIVATION v0.6

```
supersedes      INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.5.md
                sha256 602e6ce8d90981b08115132360f28d7ca694f4c137d8b2460e6fcac250e45d90
                15905 B — preserved unchanged as a historical artifact
companions      SEMANTIC-DESIGN-v0.4                03ca22e9…  unchanged by this document
                CRITERION-EVIDENCE-PROJECTION-v0.3  7adcc39f5656fa3fdc837bf3049a7a4a1be38947aed41b2fc0ccc23cc4781298
status          FROZEN BEFORE IMPLEMENTATION
result_bearing  false
```

**Sole change from v0.5:** the controlling projection identity moves from v0.2 to
v0.3, so the two reference fixtures that bind
`criterion_evidence_projection_sha256` are recomputed. **No algorithm changes. No
new digest class.** Classes 1–10 keep their rules exactly.

## 1. Canonical serialization (unchanged)

```
UTF-8 · keys sorted lexicographically · ensure_ascii=false · no indentation
item separator ","  ·  key separator ":"  ·  no trailing newline in hashed bytes
SHA-256 · lowercase hex · UNPREFIXED · null participates
self-digest excluded by KEY REMOVAL, never by null substitution
array order preserved as constructed — arrays are NEVER re-sorted
```

Micro-vector: `{"b": 2, "a": "é"}` → `{"a":"é","b":2}` →
`06c264c46ad5ada9493abd3aa2383fb205ae99d7d0bad40b03a43bfec8a1b8de`

## 2. Classes 1–8 — unchanged

```
1 currentness_epoch_digest      EPOCH-A 185 B 407a7c8f… · EPOCH-B 414 B 6858b71d… · EPOCH-C = EPOCH-A
2 authority_basis_record_digest BASIS-AUTH-1 431 B 7ad84cfb… · BASIS-ADM-1 371 B bf29f3d7…
3 authority_decision_digest
4 envelope_digest
5 consumer_validation_digest    checks[] frozen order 1..16
6 reliance_record_digest
7 integration_package_digest
8 synthetic_profile_digest      PROFILE-PRODUCER-1 398 B 1c7ac979… · PROFILE-CONSUMER-1 416 B 889ab97b…
```

Full definitions and complete vector inputs remain as published in v0.4 §2, §3 and
§9, unaltered.

## 3. CLASS 9 — `criterion_observation_digest` (algorithm unchanged)

```
domain    one CriterionObservation per projection v0.3 §5 → v0.2 §1–§2 → v0.1 §2–§3
excluded  observation_digest
rule      observation_digest = sha256(canonical(CriterionObservation minus observation_digest))
```

All fields participate: execution identity, semantic identity, projection
identity, implementation identity, universal observations, criterion-specific
observations, `node_accounting`. Binding `node_accounting` does not make it
evidence; it remains `non_load_bearing: true`.

### Reference vector CLASS-9-FIXTURE-2

```
fixture_class  DIGEST_FIXTURE_ONLY
result_bearing FALSE
```

Serialization fixture only. **No criterion was executed to produce it.** It
carries `criterion_id: T-EPOCH-A` for legibility and must never be read as
evidence that `T-EPOCH-A` or any other criterion ran.

Exact object entering the digest:

```json
{
  "record_class": "CDC_INTEGRATION_SLICE_001_CRITERION_OBSERVATION",
  "schema_version": "INTEGRATION-SLICE-001-CRITERION-OBSERVATION-v0.1",
  "fixture_class": "DIGEST_FIXTURE_ONLY",
  "result_bearing": false,
  "execution_id": "CDC-INTEGRATION-SLICE-001-DIGEST-FIXTURE",
  "trace_id": "CDC-INTEGRATION-SLICE-001-DIGEST-FIXTURE-TRACE",
  "semantic_design_sha256": "03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173",
  "criterion_evidence_projection_sha256": "7adcc39f5656fa3fdc837bf3049a7a4a1be38947aed41b2fc0ccc23cc4781298",
  "implementation_commit": "fa96f5c3590f54118cd926a84370be6022a80b35",
  "implementation_tree": "65a704cd9c70aef983b62ecc8176793e20004772",
  "criterion_id": "T-EPOCH-A",
  "node_id": "test_epoch_a_future_successor_excluded",
  "semantic_reference": "SEMANTIC-DESIGN-v0.4 §2 / DIGEST-DERIVATION-v0.4 §2",
  "scenario_id": "EPOCH-A",
  "inputs": [
    {
      "role": "reduced_epoch_object",
      "ref": "EPOCH-A",
      "digest": "407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46"
    }
  ],
  "expected_condition": "as_of 2026-08-15T10:00:00Z excludes the admitted-but-not-operative successor",
  "observed_value": {
    "as_of": "2026-08-15T10:00:00Z",
    "canonical_byte_count": 185,
    "computed_digest": "407a7c8fb4db1797d6e252ba22f24b4afd73b06b408e4751b4d401d709041b46",
    "published_vector": "EPOCH-A",
    "comparison_result": "EQUAL"
  },
  "observed_reason_code": "NOT_APPLICABLE",
  "observed_decision": "NOT_APPLICABLE",
  "outputs": [],
  "not_produced": [],
  "evidence_refs": ["INTEGRATION-SLICE-001-DIGEST-DERIVATION-v0.4.md#EPOCH-A"],
  "observed_at": "2026-08-16T00:00:00Z",
  "node_accounting": {
    "outcome": "passed",
    "runner": "pytest",
    "duration_seconds": 0.004,
    "non_load_bearing": true
  }
}
```

```
canonical byte count  1603
digest                5f6d32dddf0be0b9d26845b4446071205416132c893f9a44115e85fd1bd2ef95
```

The byte count is identical to CLASS-9-FIXTURE-1 because only one 64-character
hex value changed; the digest differs, which is the whole point of binding the
projection identity.

## 4. CLASS 10 — `criterion_ledger_digest` (algorithm unchanged)

```
domain    one CriterionEvidenceLedger per projection v0.2 §3
excluded  ledger_digest
rule      ledger_digest = sha256(canonical(CriterionEvidenceLedger minus ledger_digest))

observations[]     EXACT FROZEN 41-CRITERION ORDER — never lexicographically re-sorted
criterion_order[]  the same order
```

The canonical rule sorts **object keys**, never **array elements**. An
implementation that sorts `observations[]` or `criterion_order[]` produces a
different digest and is malformed.

Each entry contains exactly five fields:
`{criterion_id, observation_path, persisted_file_bytes, persisted_file_sha256, observation_digest}`.

### Reference vector CLASS-10-FIXTURE-2

```
fixture_class  DIGEST_FIXTURE_ONLY
result_bearing FALSE
```

Serialization fixture only. **No criterion was executed**, and no observation file
exists behind these identities.

Header fields, literally:

```
record_class                          CDC_INTEGRATION_SLICE_001_CRITERION_EVIDENCE_LEDGER
schema_version                        INTEGRATION-SLICE-001-CRITERION-EVIDENCE-LEDGER-v0.1
fixture_class                         DIGEST_FIXTURE_ONLY
result_bearing                        false
execution_id                          CDC-INTEGRATION-SLICE-001-DIGEST-FIXTURE
trace_id                              CDC-INTEGRATION-SLICE-001-DIGEST-FIXTURE-TRACE
semantic_design_sha256                03ca22e960fa677af0328d2c9595c7842015cf68ca525f8e94c2564dc4afc173
criterion_evidence_projection_sha256  7adcc39f5656fa3fdc837bf3049a7a4a1be38947aed41b2fc0ccc23cc4781298
implementation_commit                 fa96f5c3590f54118cd926a84370be6022a80b35
implementation_tree                   65a704cd9c70aef983b62ecc8176793e20004772
criteria_total                        41
pytest_accounting_ref                 accounting/pytest-criteria-report.xml
criterion_order                       the 41 ids below, in this exact sequence
```

`observation_path` for every entry is `observations/<criterion_id>.json`.

The 41 entries, in frozen order — `criterion_id`, `persisted_file_bytes`,
`persisted_file_sha256`, `observation_digest`:

```
T-EARLY-01   1034  374f91af2e97fb58c55e16c98773e999ab0395000c79db41576ea7a0be69d6fd  9b529d5e4b9da7ba5d71800431791f5ad39a287a34e8536be3ac7c73d48468d4
T-EARLY-02   1034  25d96854be38f2534e3cb328177b4fa9b20ac8c8cb7abbf3bcf19aae4d0c4974  4417b851e5c36a5508c641bf7c3f8176b993a658fe4d43e2fc47089e8c2e5881
T-EARLY-03   1034  c4289844c4d86795b2dc185d9b5358ef1b96384eff094653d00bd99b5dd31871  5827bd68bdc93bbbbc55db711ac165b68c2edb9a332cb59480508df498df17bc
T-EARLY-04   1034  beb792071c7ad8ffd445469699dfc83bc7b8174e2a4907de06b05d76216b093f  bcabc5ae191a6667669fe1ac58c69413fdea6f015d3567f27a79305cd12362cf
T-EARLY-05   1034  d03ccdf0ac124ba7500d5c3ada8a38e28996b319991828ce09b7cc889f284e4c  a9d8803612874279f2dd0c94c38b344a02562f2e2ffdaddbd87463463bd1f340
T-POS-01     1032  cc80253e99d60d415be53cd8891c8e85ad513b1dc9ad275e66e91d5b0918ec73  2c603631f2324354dd4dc79206cd5567e11712f7af7bfb8c4f9d24275f351158
T-POS-02     1032  62e7b94709fc911e27db6e9dd8be7a6580b3e28d6dc87120406b9b2c7ed96e6f  4a113379b066152337428f7d5e7c9292ba1b3e90ced93cb8dbb4385b6862b796
T-POS-03     1032  b534d374267b56ad7227cba49ab7500a5a4625989c76b56fa7523935a1ea387a  7c5377a1073aaf1efebc9db8746efc2dbd38a1fdb736e86cbd6d03263f333819
T-POS-04     1032  73ca43981b922b6bf6ee54eadafebef989f4b85434b05eeb73a008937f008f0e  7660ac75b12e484b6ee5b80e6efb6b22d959599455f747590bb737b79a8264c2
T-POS-05     1032  e5643a14ebebc26e98d19a9ddd756024a92866b9bafd34dbd4c8cdc4db729013  713546fb46ff5d34d2fd6ebba907a0e77354862480eadc669162f320b8d8f955
T-POS-06     1032  a9d4993fca953ed1e2c74812de649a818b0a75f142d0108832cb396b801010cc  8c492a9fabafab4402f51abfa8c452a9b3c1a13ace8cdc720a6b0d6453e092e1
T-CASE-A     1032  c8a82dae81fc579a0002409912eaaef240130f2094c1f0f13e943dea74fee1b6  095f6b9bf6eb6138ab6232be8eb55a6a4508e8ce66d3c7fa3032bca786e3b606
T-CASE-B     1032  e45ca7cc22d95aaac6b1ac087af7be8975b5d2c8ee578efc2d11ce7f57b10b1d  7c3267c26a8b9a0b70539d32384821ee0228f9186d190480f1aab8b951e2e0a3
T-CASE-C     1032  3a53d7ae8e59926523e148e740091a2e9d67d2285d7cdf763b5b0d0d45f3ac51  a9620831b60d956599fa8829504127624f37a339c7140b650ff2ff39760cae67
T-CASE-D     1032  455eb91c041fe979246f783862f4231858b862e679787c1751fc7890584c6790  d678b29ad1cab46bbe87853ad8d84a99453c1b61578a7b41e9053fe391ee92c0
T-CASE-E     1032  af9978a43e8a82f5e52544d27e9f6110dd19751e039b1da9b4d119e6c59efff8  3e535aaaa26a5a41fdef202e46f8e77f52dd2763561f9e2a47bc0a79beb3f311
T-CASE-F     1032  483e57a09d611536fcf109fc9a42bf083cb4db1f9970894f2f9e150d83ba6de2  0551b4bc2d888e8642b62c374384c32d55a545758ee3c1be86fd116452a6769b
T-CASE-G     1032  2e293088d5982e0d9d6e5f333f64e9058d17dc7c3beb9f799a76026db76ecbc4  036a7ed2a6eb6749711527fbeb6257acd91424f32fe128a41b178f35548612c0
T-CASE-H     1032  661d97b472ff126eb4f6042392cfa2c4806352d7705a33e7c56db12912d4b11a  2614be16e1aaebd4a8b409f56049e2991e060bc6cf44c82f5095799525137df8
T-CASE-I     1032  5b60f8529c8885c6a466b729b99c5282033b0b50e45d1e2db6c7a4ab9d5a1410  c3e14b97dd7dee2cb15f5bd5b41de486cf88b898489cb7bbecdbe4cd5ed3f39d
T-CASE-J     1032  6de948aa456d177bfbafaede3642ff49243ee8b359f63f238a4613870db2613d  b6944bf0a87a980f1118e4a5a8ab03c64d62b12077be5769af4534e2ea55a888
T-CASE-K     1032  60c2ec662634a873e75a6296719b9628a231fb9b20f3365a2b29836b73af02f7  78a32882ea1fde51d7a76cca046f0d82e50d0d41ac99f4ac65b778693a254de4
T-CASE-L     1032  07cd2499a60e53e85b311047b814d474a70472310728d130646b004431d216b5  3953b7737e0e96a34227694b2d7a198475446e63fc66c6ed6780ff02ee4834a4
T-CASE-M     1032  b0b20ae4bea406af53e8f165292eefde2a5693e28e870e666c54c325033e7e00  44d6113625db8594b54e2644bf43927d348fbd252e8d0d615c7fee2187edb63c
T-CASE-N     1032  0403be1389c3ca082d1e6d9f77579767847a84acef64c721b44acdbbea4ab4e4  1697b434f803514845abf6858fae395e8e65d4b823d16ae14ff494b90cfe2e37
T-CASE-O     1032  e727b1fd7f2182ee0b29f8e19be8d8ba366d91c0ab98c9fd2c51c15ba3166bce  6fb51378c86f3402895e368928daf799f21cb44f156c7825fee6cb2a6a3ca518
T-CASE-P     1032  53370a6588a4f561b59921b9e3b14434dd6732da82370d33ad69ee11ebe99312  14197ad2d8546fe54c970e29fd7a747282bf94839eb5ea80d973b96a51c117aa
T-CASE-Q     1032  593fbd34604717a7139a1f79365805b009fc5c229c0a69db3467de6870ef2dda  7085f0ed610b5bb7c64a36ecba5bba7f1cc076708f4eb4258b396ad26fafa72b
T-CASE-R     1032  554d8074f41e1830d7239d991cd3c6c9e456462ab1f09d771f0d66c6850332db  16699f30b452a105e4cea1026922c8e062fb9300f4771e718d67fe2004601d0b
T-CASE-S     1032  226caa9541fe8134768878a817c5f0908692cf9dc98f5c6428e110131cad1a5e  d1b2a782e9e746c9bf502c495735e369a457d93ef379112ca6293a3b559cf11c
T-DIG-01     1032  4c81b8c4ff00afd7aabcbb3e622ab487c330cb6d203804cd8d2fd2d8792a231c  5060bcb8fabc1b37dcc6523f0cf49c85fa721cb62137aa99b51067e3694bfc74
T-DIG-02     1032  d64a2d4b638247469d09e89a11066a7d2d94ffaefe07dcef12de383b9cb18f9d  8c0ccb7c744ee81ea7b9b249c73635f00ea40524180d8adf6acdd6e12bf0aeb2
T-DIG-03     1032  cc1025247e2c98b5b9f77a22a9b1d127f696e483d69f75949914b3df38f3cfd7  301be8a2e7c60c93bb6b7f4698c719a28db0f9f0eb4b8ef1faf0cd3e28e4619e
T-DIG-04     1032  fdf3d5ca9dbbacf9289163af77b8579dc92b7283ee5889cd2fca4128b3b318fd  8ae65747c60d8e6531caf79c465610bbd2bc98766a62b4dd4eef0f5a847de656
T-DIG-05     1032  98bc73924acd76ba46052539ae51b3866c2b0734ce8dfa12a9053b214f43b59d  e33995ce44e2c41ca1a882e0f8d40473b74061072e3fd7f0229cf060bd9e3c09
T-DIG-06     1032  0e593c4942bf50e33bf50c9e38289406bb58e4f99a197abcd237ca8f594a4ca1  c67c3e1ed230c366f2c99892bffb9144946ed71f1538501015b4d46060cdd68e
T-DIG-07     1032  b8049c680f0cdb77e0e71d0d0b43d9fe44ba5b726e9643f1805d8446b77e73a6  1cbb68788f58062c28b26d18c3b174e07a8e0e24f43888b9a8144e7ad54a65c3
T-DIG-08     1032  69e069f83ecb7c239b5211e83f061f56c20587d0686a9bc614f3092df8f892b4  451e8aadeebac650071f56f763baa320c0fd8950f0e92e6cac7fea905a25226d
T-EPOCH-A    1033  cdd98dbcf196488d1f70c8449881470bcd6e14cf3dfd30bd3eace30170ecf5e1  d4ae87b01628d8a586d45c1842bcc59aa9fa75d0940f39470814c55c6d3337ea
T-EPOCH-B    1033  4fbbba92c0c64456469f4ade5d46fbd5e926fc1b6ab0f981c280db1d03490fc0  2943487aa83276a82097c9130aca99090d19d5d59fed49134bd3cd6dfb39f69e
T-EPOCH-C    1033  dfbe76677a0d6744a5acc224f12910c195c67c291c61648156f2702159cf6662  276c9c7ed9adaa375828427e2c3b3ddcacfc1395c2d5c377adc6a06b7a3d7909
```

```
canonical byte count  12865
digest                29c8459ce43ae21d35a0f54f1addaa45413f153efda6fec2b1329d701365802d
```

Entry values are unchanged from CLASS-10-FIXTURE-1; only the bound projection
identity in the header moved, so the byte count is identical and the digest is
not. As a redundant cross-check only — never as a substitute for the literal
table — the entries were generated by
`persisted_file_sha256 = sha256("FIXTURE-FILE:" + criterion_id)`,
`observation_digest = sha256("FIXTURE-OBSERVATION:" + criterion_id)` and
`persisted_file_bytes = 1024 + len(criterion_id)`.

## 5. Persisted-file identity rules — unchanged

```
issuance_authorization_digest = sha256(exact persisted bytes of the authorization file)
attempt_record_digest         = sha256(exact persisted bytes of the attempt record file)

write ordering: authorization persisted → attempt record written and FROZEN →
                RelianceIssuanceRecord written, binding both
```

Projection v0.3 §3 records the evidential consequence: this ordering is
established by the digest chain itself, and governed timestamps — where they
exist — corroborate it. Filesystem metadata may never substitute for a governed
timestamp.

## 6. Counts and freeze

```
canonical digest classes              10   unchanged
persisted-file identity rules          2   unchanged, plus the general rule
semantic test count                   41   unchanged
reason-code count                     36   unchanged
semantic design v0.4                        unchanged
criterion universe and order                unchanged
```

Any class introduced later requires a versioned successor published before the
execution that produces it. A vector that cannot be recomputed from the document
alone is not a vector, it is an assertion.
