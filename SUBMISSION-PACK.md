# FaultCircuit Portal package

Category: **Builder Ã¢â€ â€™ Intelligent Contracts**. Use the actual contribution date.
Source-matched deployment and the synthetic fault-budget/recovery demo are complete.
Submission has not yet been sent.

## Title

FaultCircuit: Consensus-Settled Failure Budgets and Single-Probe Recovery

## Notes / Description

FaultCircuit is a reusable circuit breaker for cooperating agent runtimes. An owner freezes a component policy, reporters, rolling fault threshold and recovery probe. Contract-issued runs pin the operation, reporter and deadline; each locks one complete report. Independent GenLayer validators classify PASS, COMPONENT_FAULT or UNCERTAIN and rebuild the full receipt, including circuit generation, fault window and deterministic transition. Certified current-generation faults open the circuit and stop ordinary admissions. After cooldown exactly one half-open probe is admitted. Only its certified PASS closes; fault, ambiguity, cancellation or expiry reopen with capped backoff. Older normal outcomes remain audit-only across generations. Reports cannot be rewritten, retries are bounded and backward timestamps fail closed. It holds no funds and executes no external work. Includes 37 adversarial local tests and a Studio walkthrough; reporter authority does not authenticate telemetry.

## Formal evidence

| Evidence type | URL / release step |
| --- | --- |
| GitHub Repository | https://github.com/zakazaka95/FaultCircuit |
| GitHub File | https://github.com/zakazaka95/FaultCircuit/blob/01817a93863ec371290a0d4d107cdb44191c2ba3/FaultCircuit.py |
| GenLayer Explorer Contract | https://explorer-studio-dev.genlayer.com/address/0x9E2A84A68A93d6E1C8944e2a009fCaaaDdC762C8 |
| Other | https://explorer-studio-dev.genlayer.com/tx/0xa10e0ba92ae02eb059dc277e89a7fc54c283b78e6431efa92b76adb50f4c635a |

The description is 989 characters. Local evidence includes 37 passing deterministic tests
with controlled model outputs. Native schema, deployment and complete source
comparison passed; the synthetic live demo finalized successfully. See [DEPLOYMENT.md](DEPLOYMENT.md) for actual network observations;
walkthrough expectations and local tests are not claimed as live-model accuracy.
