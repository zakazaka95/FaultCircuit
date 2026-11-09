# FaultCircuit

FaultCircuit combines independent semantic classification of declared agent-run
reports with deterministic failure budgets and single-probe recovery.

**Deployed on Studio Devnet, chain 61997.** The complete deployed source matches
the tracked `FaultCircuit.py`. See [DEPLOYMENT.md](DEPLOYMENT.md) for the exact
address, source fingerprints and observed execution records. The synthetic network
demo settled two component faults to open the circuit, then one fixed recovery
probe PASS to close it at generation 2 with a cleared fault window.

## Why the primitive exists

A cooperating runtime may want to stop admitting ordinary work after repeated
component failures, then recover through one controlled smoke test. Natural-language
reports can describe success, an internal component failure, or an unrelated and
unclear error in many ways. A counter alone cannot interpret that distinction;
a model should not control counts, retry slots, deadlines or recovery state.

An owner freezes a component, purpose, classification policy, reporter list and
fixed recovery operation. GenLayer independently interprets one complete locked
report. Contract code handles all operational consequences. It holds no funds and
does not execute or stop any external program.

## State and admission

```text
CLOSED -- threshold certified faults --> OPEN
OPEN -- cooldown elapsed + one probe admission --> HALF_OPEN
HALF_OPEN -- exact probe's certified PASS --> CLOSED
HALF_OPEN -- fault / uncertainty / final unreadable / cancel / expiry --> OPEN
Any state -- owner retirement --> RETIRED (irreversible)
```

- Up to **six outstanding normal runs** are tracked per circuit, across all
  generations, plus at most **one recovery probe**. Ordinary admission requires
  CLOSED state and a free normal slot. OPEN does not automatically become healthy
  when a timer finishes; it only becomes eligible to admit a probe.
- Every run gets a contract-issued ID and immutable reporter, operation, policy
  hash, generation, admission time and deadline. Probe operation text is fixed by
  the owner at circuit creation; reporters cannot replace it with an easier test.
- A reporter may lock one complete report before the deadline. Its exact UTF-8
  text and hash cannot be replaced. Assessment also must occur strictly before
  that deadline. Reporter identity authenticates authority, not telemetry truth.
- Normal expiry frees a slot without fabricating a certified component fault.
  A normal run may be canceled only before its report is locked; cancellation
  frees its slot and does not count a fault. Canceling the active unreported probe
  fails recovery and reopens cooldown. Locked reports cannot be canceled.

## Classification, settlement and generations

The complete policy, admitted operation and locked report are supplied to each
independent execution. Strict semantic outcomes are:

| Outcome | Meaning and consequence |
| --- | --- |
| PASS | The supplied report clearly supports the exact operation under policy. A normal PASS never closes an open circuit. Only the current reserved probe can recover it. |
| COMPONENT_FAULT | The report clearly attributes a relevant failure to the named component. A current-generation normal fault may count toward the threshold. |
| UNCERTAIN | The evidence is insufficient, contradictory or does not responsibly establish either conclusion. It is final for that report; an uncertain probe reopens cooldown. |

Malformed or unavailable model output gives technical `UNRESOLVED`, with up to
three accepted attempts against the same locked report. The third ends
`UNRESOLVED_FINAL`; a probe then reopens, while a normal run frees its slot without
counting an unproven fault. Independent-model disagreement cannot commit a
receipt and does not consume an accepted attempt. No convergence is guaranteed.

The leader and validator independently rebuild the **entire canonical receipt**:
all source text and hashes, policy and run identity, submitted and assessed times,
attempt, prompt coverage, effective state before settlement, maintenance records,
fault window, generation, revision and complete deterministic transition. Exact
canonical JSON equality is required. A verdict or partial-field match is insufficient.
Acceptance atomically settles the run and applies the transition; there is no
separate loosely bound reset authorization.

Opening/reopening increments the generation. A successful probe increments it
again and resets the window/backoff. Already-admitted older normal runs retain
their slots until settlement, cancellation or expiry. Their reports can settle
for audit, but their PASS cannot close and their fault cannot count in a newer
generation. Retired runs can likewise finish their audit record without restoring
admission or modifying the retired failure budget. Results cannot settle twice.

## Exact window, time and recovery rules

Faults count by **accepted classification-settlement transaction time**, not
claimed incident time or report submission time. At time `now`, a fault is in the
window exactly when `now - window_seconds < settled_at <= now`. The list is bounded
by the threshold, at most six events. Counts identify distinct contract-issued
declared runs; they do not prove distinct authentic real-world incidents.

The first opening uses the base cooldown. Each failed recovery increments a
capped backoff level and uses `min(maximum, base * 2^(level-1))`; level is capped
at 16. A certified probe PASS resets level to zero. Semantic probe failure,
ambiguity, cancellation and final technical failure start cooldown at their
processing timestamp. **Expired probe cooldown starts at its fixed run deadline**,
so delayed expiry processing cannot keep moving the recovery boundary forward.

Time comes from the deterministic transaction's compatible WASI
`datetime.now(timezone.utc)` path and is captured before model callbacks.
Every successful circuit write records `last_observed_at`; a transaction/view
with older time fails closed before pruning or granting a current permission.

`get_circuit` returns stored `record` and a copied, refreshed `effective` diagnostic.
Views never persist expiry or window pruning. A later successful write applies
that maintenance atomically. The receipt's `state_before` is **after this staged
refresh**, rather than the raw stored record. Even `expire_runs` returning zero
can advance the stored observation time/revision at a later timestamp; only a
same-time no-op is byte-stable. Pending `get_run` diagnostics also reject backward
time. Finalized historical records remain readable.

## Public API

```text
open_circuit(title, component, purpose, classification_policy, probe_operation,
             reporters_json, threshold, window_seconds, base_cooldown_seconds,
             max_cooldown_seconds, run_timeout_seconds) -> circuit_id
admit_run(circuit_id, operation) -> run_id
admit_probe(circuit_id) -> run_id
submit_report(run_id, report_text)
assess_run(run_id) -> complete_receipt
cancel_run(run_id)
expire_runs(circuit_id) -> number_of_expired_runs_processed
retire_circuit(circuit_id)

get_circuit(circuit_id) -> stored record, effective diagnostic, admission flags
get_run(run_id) -> stored record, effective status
get_attempt(run_id, attempt) -> immutable accepted receipt
get_stats() -> version, schema, counts and bounds
```

Only immutable allowlisted reporters can admit work. Each admitted reporter alone
can submit, assess or cancel that run. Anyone may process already-expired runs.
Only the owner may retire, and there is no administrative force-close/reset method.

Bounds: 1â€“8 reporters; threshold 1â€“6; window 60â€“86,400 seconds; base cooldown
30â€“3,600; maximum cooldown between base and 86,400; run timeout 60â€“3,600.
Titles are at most 100 characters, component 120, purpose 500, classification
policy 800, fixed probe and ordinary operation 600 each, report 2,400.
Complete JSON-escaped prompts must fit **18,000 characters and 24,000 UTF-8 bytes**.
No source is sliced. Per-field maxima do not promise admission if escaping exceeds
the total budget. Invalid Unicode, booleans as numeric IDs, and duplicate reporters
are rejected before model execution.

## Local verification and release evidence

From this directory:

```text
python -m unittest -v test_faultcircuit.py
```

The **37 local tests** exercise deterministic transitions and controlled model
outputs: exact window/cooldown boundaries, late generations, unique probes,
expiry, cancellation, retirement, replay, all receipt leaves, model disagreement,
backward time, rollback-free staged maintenance and full maximum input coverage.
They are not a model-accuracy benchmark or actual GenVM execution.

[STUDIO-TEST.md](STUDIO-TEST.md) gives the reproducible network path.
[DEPLOYMENT.md](DEPLOYMENT.md) records native schema inspection, successful
deployment execution, complete source equality and actual demo observations.
[SUBMISSION-PACK.md](SUBMISSION-PACK.md) contains the Portal description.

## Integration limits and related work

Executors must pin the exact deployed contract, circuit ID and immutable policy
hash. Separate circuits do not share a failure budget. Enforce admission, current
generation, exact reporter/operation and deadline in the cooperating runtime;
an old token is not a new execution permit after the circuit changes. Opening or
retiring the contract does not terminate code already running elsewhere.

Authorized reporters can fabricate, omit or reuse logs across separately issued
runs. This contract does not authenticate external artifacts or discover hidden
incidents. The owner selects trustworthy reporters and a meaningful fixed probe.
All inputs and receipts become public; use synthetic or public developer data.
Independent models can be wrong or disagree. A safe state transition is not proof
that the external component is healthy or safe for production.

Circuit breaking is an established pattern. The [GenLayer GitHub topic](https://github.com/topics/genlayer)
also lists [Sentinel](https://github.com/Misagh95/sentinel) as an autonomous circuit
breaker. No first-of-its-kind claim is made. FaultCircuit's stated scope is bounded
declared run admissions, once-only full-receipt fault settlement, rolling budgets,
generation separation and a unique fixed recovery probe, rather than a generic
emergency price pause. This is a scope description, not an audit of related code.
