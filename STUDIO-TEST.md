# FaultCircuit Studio walkthrough

The exact tracked source has been deployed and source-matched. Use synthetic
declarations only, value **0 GEN**, Normal / Full Consensus and simulation
disabled. [DEPLOYMENT.md](DEPLOYMENT.md) records actual results separately; the
expected values below are procedures, including optional paths not claimed as
executed.

Before release, check the current official Studio network and runner compatibility.
Import the exact tracked source, deploy without constructor arguments, and compare
the full Explorer Code view with that source. Record actual GenVM execution and
persisted state; an Accepted transaction can still contain an execution error.
Do not switch Studio contract tabs while Send displays **Sending...**.

## 1. Create the synthetic circuit

Read `get_stats`: version `1.0.0`, schema `faultcircuit-v1`, counters zero on a
fresh deployment. Copy the actual Studio account's public address for reporters.

Call `open_circuit`:

```text
title: Synthetic CSV worker circuit
component: CSV worker
purpose: Coordinate synthetic CSV worker runs and recover through a fixed smoke test.
classification_policy: PASS requires the report to show the exact admitted parse operation completed with header name and two output rows. COMPONENT_FAULT requires an explicit internal CSV worker parser failure. Caller input errors or external network failures alone are uncertain.
probe_operation: Parse the fixed valid CSV smoke-test fixture and verify header name, two output rows, and no internal parser error.
reporters_json: ["<actual copied Studio account address>"]
threshold: 2
window_seconds: 600
base_cooldown_seconds: 30
max_cooldown_seconds: 240
run_timeout_seconds: 1800
```

Never use a textual placeholder as an address. Use the returned circuit ID,
normally `0` on a fresh instance. `get_circuit` should show CLOSED, generation `0`,
no pending runs or fault events, and the frozen policy/reporters/hash. This first
write exercises the actual clock adapter; a successful constructor alone does not.

## 2. Settle two distinct declared faults

Call `admit_run(circuit_id, operation)` with:

```text
operation: Parse the valid synthetic CSV fixture and produce header name with two output rows.
```

Use the returned run ID, normally `0`. Call `submit_report` with the complete
synthetic failure report:

```text
This is a declared synthetic run report. The CSV worker received the specified valid fixture. Its internal parser raised InternalParserFailure before producing any output rows. The expected header name and two rows were not produced. No caller validation error or external network dependency caused this failure.
```

Read `get_run` and verify immutable operation, reporter, deadline, exact report
and report hash. Call `assess_run(run_id)` before the deadline. A faithful
classification should be COMPONENT_FAULT with `semantic_complete: true`, a full
untruncated prompt and `effect.fault_counted: true`. The first fault should leave
CLOSED with one fault-window event and the run SETTLED.

Admit a **new** run ID for the same synthetic operation, lock its own complete
declared failure report, and assess it within 600 seconds of the first accepted
fault settlement. If both are certified, the second reaches threshold: OPEN,
generation `1`, backoff level `1` and `open_until = assessed_at + 30`. This counts
two issued declared runs; it does not establish two authentic external incidents.

Try ordinary admission while OPEN. It should reject without creating a run.
Reassessing either settled run must reject; one ID cannot count twice.

Model output is not guaranteed. If models return UNCERTAIN, another classification
or no consensus, preserve that actual result. Do not replace a locked report,
use Leader Only mode or label a leader's output as a stored accepted result.

## 3. Admit exactly one recovery probe

Wait until the stored cooldown boundary, then call `admit_probe(circuit_id)`.
It takes no caller-chosen operation; the run uses the owner's exact frozen smoke
test. `get_circuit` should show HALF_OPEN with that exact probe ID. A second probe
and ordinary admission should both reject while it is reserved.

Lock the probe's declared synthetic success report:

```text
This is a declared synthetic smoke-test report. The exact frozen valid CSV fixture was parsed by the CSV worker. The output header was name and exactly two expected data rows were produced. Every fixed smoke-test check matched; no internal parser error occurred.
```

Assess the probe before its deadline. Only a certified PASS for this reserved
probe should close the circuit, increment generation, clear the fault window,
clear the probe ID and reset backoff level/open-until to zero. Read the persisted
run, circuit and receipt to verify those separate fields. Normal PASS cannot
substitute for the reserved probe.

## 4. Optional refusal and lifecycle cases

These are not claimed as executed until recorded:

- Leave a normal run outstanding before opening. Its later PASS or fault should
  settle for audit only and must not close OPEN, preempt HALF_OPEN or count in a
  newer generation.
- A probe COMPONENT_FAULT or UNCERTAIN should reopen with doubled, capped
  cooldown. Three accepted technical-unreadable attempts likewise fail recovery.
- Let a probe expire. Its effective reopening is anchored to its deadline plus
  the next cooldown, not the time someone eventually processes expiry. A read
  previews that state without writing it. `expire_runs` or another successful
  write persists the maintenance.
- A normal timeout removes its slot without inventing a certified fault.
- Reporter cancellation before report lock frees a normal slot; canceling the
  active probe reopens. After lock, cancellation and replacement are forbidden.
- Only the run's reporter may submit, assess or cancel; only the owner retires.
  Historical settlement after retirement must never restore healthy admission.
- At six outstanding normals, the seventh rejects. A recovery probe has its own
  single slot, so those older runs do not bypass the one-probe condition.

For exact numeric window/expiry boundaries, backward transaction time and complete
receipt tampering, use the controlled local tests. Do not claim a real network
negative case merely because its local test passes.

## Evidence to capture after go

Record the exact published source commit, raw source hash, current network,
actual Explorer contract address, deployment and semantic transaction hashes,
GenVM outcomes and resulting stored run/circuit receipts. Source changes require
a matching deployment. Document any normalization separately if comparing rendered
Explorer code with raw files. Attach the repository, immutable `.py` source,
actual `/address/` contract link and successful assessment transaction as separate
Portal evidence cards. No future address or success may be invented.
