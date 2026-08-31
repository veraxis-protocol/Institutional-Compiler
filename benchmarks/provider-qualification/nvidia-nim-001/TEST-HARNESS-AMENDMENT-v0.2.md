# NVIDIA Provider Qualification 001 — Test Harness Amendment v0.2

Status: PRE-LIVE SUCCESSOR FREEZE.

The v0.1 plan, v0.1 freeze, provider instrument, provider path, three probes, thresholds, retry policy and pacing are byte-preserved. No NVIDIA provider call was made under v0.1.

The original pytest harness dynamically imported the provider instrument inside the pytest interpreter. Repository test state can monkeypatch socket symbols before `urllib.request` imports `ssl`, producing a Python stdlib import failure unrelated to the provider qualification logic.

v0.2 changes only the contract-test isolation strategy: dynamic instrument checks execute in clean child Python processes.

- v0.1 freeze sha256: `178460718744b7d4f16ca1df0c6c33bd8f0089adcfda09e838690c5a80b8f700`
- instrument sha256 unchanged: `144393892d05fe4d2eb2d70f110164023c36e3d69e393c874227a432b2bb426f`
- plan sha256 unchanged: `a72370f16e93048466ecc25d9d03b8d85d43e055b1f8d2d467750116c779c02e`
- v0.2 contract test sha256: `a67ce0d7dc0cf8ad362ce890454ada4edd27d11b8150d0ff67a331cf0a6a14e3`
- semantic change: FALSE
- provider call made: FALSE
- independent validation claim: FALSE
