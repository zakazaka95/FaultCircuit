# FaultCircuit deployment and verification record

Released from the tracked source on Studio Devnet, chain **61997**, using
`https://studio-dev.genlayer.com/api`. Deployment occurred at `2026-11-09T23:49:33.678Z`
(UTC; November 10 locally). All calls use zero GEN value and synthetic records.
Network fees use test-network funds. Leader-only execution is disabled.

| Item | Observed record |
| --- | --- |
| Source version / receipt schema | `1.0.0` / `faultcircuit-v1` |
| Exact tracked source-file SHA-256 | `d747f66c1bf4bb04e1369a3ec950396fc3021c368fdc9f85c9c3170da11845e9` |
| Complete deployed-source comparison | Passed; normalize CRLF to LF and trim outer whitespace only |
| Normalized deployed-source SHA-256 | `37257c7f05956c52b84adc632e18eec13363e68f808c73503bb21f3facccad64` |
| Native SDK schema | Passed for this source and no-argument constructor |
| Deployment execution | FINALIZED with successful GenVM execution, confirmed by persisted `get_stats()` |
| Contract address | [`0x9E2A84A68A93d6E1C8944e2a009fCaaaDdC762C8`](https://explorer-studio-dev.genlayer.com/address/0x9E2A84A68A93d6E1C8944e2a009fCaaaDdC762C8) |
| Deployment transaction | [`0xedede297768463452026f8b7d2bae247f4013063191375a1b508fa93f23fc32b`](https://explorer-studio-dev.genlayer.com/tx/0xedede297768463452026f8b7d2bae247f4013063191375a1b508fa93f23fc32b) |
| Public repository | [zakazaka95/FaultCircuit](https://github.com/zakazaka95/FaultCircuit) |
| Immutable tracked source | [`FaultCircuit.py` at `01817a93863ec371290a0d4d107cdb44191c2ba3`](https://github.com/zakazaka95/FaultCircuit/blob/01817a93863ec371290a0d4d107cdb44191c2ba3/FaultCircuit.py) |
| Local tests | 37 deterministic adversarial tests passed with controlled model/storage outputs |
| Live semantic demo | Two certified COMPONENT_FAULT runs opened the circuit; one fixed certified PASS probe recovered it to CLOSED generation 2 |
| Portal status | Submission not yet sent; no acceptance or points claimed |

The source pins
`py-genlayer:babwp9t37jw9g4j2bccgn14g6x7x9s1f7dsmh7emvz735pz4zxa0`.
Its compatible `datetime.now(timezone.utc)` clock is read only in deterministic
public methods, outside model callbacks.

The raw source fingerprint and the normalized deployed-source fingerprint are
separate measurements. Normalized complete text equality is not described as raw
byte equality. A consensus ACCEPTED label alone is insufficient: method execution
must succeed and the resulting state must be readable from the contract.

[STUDIO-TEST.md](STUDIO-TEST.md) provides the reproducible procedure. Local tests
are not live-model accuracy benchmarks. Declared synthetic premises or run reports
are not authenticated external facts or real-world telemetry.

## Observed synthetic network demonstration

Completed at `2026-11-09T23:57:11.581Z` UTC. Deployment and all ten demo writes
finalized with successful execution. Each assessment bound a complete canonical
receipt with semantic coverage complete and prompt truncation false. This is a
small observed demonstration, not a model-accuracy or telemetry-authenticity
benchmark.

| Stage | Successful finalized transaction |
| --- | --- |
| `fault-run-1-assess` | [`0x5de81b0da02d66286798620c26846612967f14ab4f8e54425748f86570da0288`](https://explorer-studio-dev.genlayer.com/tx/0x5de81b0da02d66286798620c26846612967f14ab4f8e54425748f86570da0288) |
| `fault-run-2-assess` | [`0x9936ed7ac9415115d4a0c7365305d861998457b8eb3cc2e2e8cbc8568a326d7f`](https://explorer-studio-dev.genlayer.com/tx/0x9936ed7ac9415115d4a0c7365305d861998457b8eb3cc2e2e8cbc8568a326d7f) |
| `probe-admit` | [`0x8423db1c7fc161cbb7a44fc7254fdd188fa192cc5d54919df28f8e431bad6f3c`](https://explorer-studio-dev.genlayer.com/tx/0x8423db1c7fc161cbb7a44fc7254fdd188fa192cc5d54919df28f8e431bad6f3c) |
| `probe-assess` | [`0xa10e0ba92ae02eb059dc277e89a7fc54c283b78e6431efa92b76adb50f4c635a`](https://explorer-studio-dev.genlayer.com/tx/0xa10e0ba92ae02eb059dc277e89a7fc54c283b78e6431efa92b76adb50f4c635a) |

Circuit `0` admitted two distinct normal runs, `0` and `1`. Each exact locked
synthetic report was classified `COMPONENT_FAULT` and counted once. The first
left the circuit CLOSED; the second reached the threshold of two within the
600-second window and opened generation `1` with backoff level `1` and a
30-second cooldown. Ordinary admission was then disallowed.

After the real stored cooldown elapsed, fixed probe run `2` was admitted. The
stored state was HALF_OPEN, the exact frozen probe operation was retained and
both ordinary and additional probe admission flags were false. Its certified
`PASS` settled it and restored CLOSED at generation `2`, with fault events empty,
probe ID `-1`, cooldown `0`, backoff `0` and ordinary admission allowed again.
These are persisted state observations; no claim is made that an outside CSV
worker actually executed or was healthy. Authorized reports are synthetic
declarations, not authenticated telemetry.

Full run receipts, circuit readbacks, transaction URLs and finalization results
are retained in [evidence/demo-result.json](evidence/demo-result.json). Native
schema and source/deployment details are in [evidence/schema-check-sdk.json](evidence/schema-check-sdk.json)
and [evidence/deployment.json](evidence/deployment.json). The reproducible
37-test CI run passed: [Contract tests](https://github.com/zakazaka95/FaultCircuit/actions/runs/42723978467).
Optional walkthrough cases not listed here remain procedures, rather than claims
of additional live execution.
