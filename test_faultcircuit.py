"""Deterministic adversarial checks with supplied synthetic model classifications."""
import copy
import json
import unittest
from testsupport import load, UserError

A = "0x" + "1" * 40
B = "0x" + "2" * 40
C = "0x" + "3" * 40


class FaultTests(unittest.TestCase):
    def setUp(self):
        self.m, self.c, self.rt = load()
        self.cid = self.open()

    def open(self, threshold=2, window=120, cooldown=30, maximum=240, timeout=600, reporters=None):
        self.rt.as_sender(A)
        return self.c.open_circuit(
            "Synthetic CSV worker", "CSV worker", "Coordinate declared CSV worker runs.",
            "PASS means the exact operation completed with expected output. COMPONENT_FAULT means an internal CSV worker failure. Unrelated caller or external network failures are uncertain.",
            "Run the fixed CSV worker smoke test and verify its expected output.",
            json.dumps([A, B] if reporters is None else reporters), threshold, window, cooldown, maximum, timeout)

    def state(self, cid=None):
        return self.c.get_circuit(self.cid if cid is None else cid)["record"]

    def record(self, run_id):
        return self.c.get_run(run_id)["record"]

    def admit(self, reporter=A, operation="Export the synthetic CSV fixture.", cid=None):
        self.rt.as_sender(reporter)
        return self.c.admit_run(self.cid if cid is None else cid, operation)

    def report(self, run_id, text="The exact admitted operation completed and its expected output matched."):
        self.rt.as_sender(self.record(run_id)["locked"]["reporter"])
        self.c.submit_report(run_id, text)

    def settle(self, run_id, outcome="PASS"):
        if self.record(run_id)["status"] == "ADMITTED":
            self.report(run_id)
        self.rt.as_sender(self.record(run_id)["locked"]["reporter"])
        self.rt.output = outcome if isinstance(outcome, Exception) else {"outcome": outcome}
        return self.c.assess_run(run_id)

    def trip(self):
        for _ in range(self.state()["spec"]["threshold"]):
            self.settle(self.admit(), "COMPONENT_FAULT")
        self.assertEqual(self.state()["state"], "OPEN")

    def probe(self, reporter=A):
        self.rt.clock = max(self.rt.clock, self.c.get_circuit(self.cid)["effective"]["open_until"])
        self.rt.as_sender(reporter)
        return self.c.admit_probe(self.cid)

    def storage(self):
        return copy.deepcopy((self.c.circuits, self.c.runs, self.c.attempts, self.c.run_count, self.c.settlement_count))

    def test_run_admission_and_report_lock_pin_exact_identity_and_bytes(self):
        run_id = self.admit(B)
        record = self.record(run_id)
        self.assertEqual(record["locked"]["reporter"], B)
        self.assertEqual(record["locked"]["deadline"], self.rt.clock + 600)
        self.assertEqual(record["locked"]["policy_hash"], self.state()["policy_hash"])
        text = "  Exact Unicode report 漢🚀 with whitespace.\n"
        self.report(run_id, text)
        self.assertEqual(self.record(run_id)["report"], text)
        self.assertEqual(self.record(run_id)["report_hash"], self.m._hash(text))
        with self.assertRaises(UserError):
            self.c.submit_report(run_id, "Replacement report")
        self.assertEqual(self.record(run_id)["report"], text)

    def test_normal_pass_never_opens_and_releases_its_slot(self):
        run_id = self.admit()
        receipt = self.settle(run_id)
        self.assertEqual(receipt["outcome"], "PASS")
        self.assertEqual(receipt["run_status"], "SETTLED")
        self.assertFalse(receipt["effect"]["closed"])
        self.assertEqual(self.state()["state"], "CLOSED")
        self.assertEqual(self.state()["fault_events"], [])
        self.assertEqual(self.state()["normal_ids"], [])
        self.assertEqual(self.c.get_attempt(run_id, 1), receipt)
        self.assertEqual(self.c.get_stats()["classified_runs"], 1)

    def test_distinct_certified_faults_trip_at_threshold_and_stop_admission(self):
        first = self.admit()
        self.settle(first, "COMPONENT_FAULT")
        self.assertEqual(self.state()["state"], "CLOSED")
        self.assertEqual(len(self.state()["fault_events"]), 1)
        second = self.admit()
        receipt = self.settle(second, "COMPONENT_FAULT")
        state = self.state()
        self.assertEqual(state["state"], "OPEN")
        self.assertEqual(state["generation"], 1)
        self.assertEqual(state["open_until"], self.rt.clock + 30)
        self.assertEqual(state["backoff_level"], 1)
        self.assertEqual([event["run_id"] for event in state["fault_events"]], [first, second])
        self.assertTrue(receipt["effect"]["fault_counted"])
        self.assertTrue(receipt["effect"]["opened"])
        with self.assertRaises(UserError):
            self.admit()

    def test_exact_window_cutoff_excludes_old_fault_but_one_second_inside_counts(self):
        self.settle(self.admit(), "COMPONENT_FAULT")
        self.rt.clock += 120
        self.settle(self.admit(), "COMPONENT_FAULT")
        self.assertEqual(self.state()["state"], "CLOSED")
        self.assertEqual(len(self.state()["fault_events"]), 1)
        cid = self.open()
        self.cid = cid
        self.settle(self.admit(), "COMPONENT_FAULT")
        self.rt.clock += 119
        self.settle(self.admit(), "COMPONENT_FAULT")
        self.assertEqual(self.state()["state"], "OPEN")

    def test_fault_window_uses_certified_settlement_time_not_submission_time(self):
        run_id = self.admit()
        self.report(run_id)
        submitted = self.rt.clock
        self.rt.clock += 17
        receipt = self.settle(run_id, "COMPONENT_FAULT")
        self.assertEqual(receipt["input"]["submitted_at"], submitted)
        self.assertEqual(receipt["assessed_at"], submitted + 17)
        self.assertEqual(self.state()["fault_events"][0]["settled_at"], submitted + 17)

    def test_six_outstanding_normal_runs_and_no_extra_slot_before_settlement(self):
        ids = [self.admit() for _ in range(6)]
        before = self.storage()
        with self.assertRaises(UserError):
            self.admit()
        self.assertEqual(self.storage(), before)
        self.settle(ids[0])
        self.admit()
        self.assertEqual(len(self.state()["normal_ids"]), 6)

    def test_normal_expiry_frees_capacity_without_inventing_fault(self):
        ids = [self.admit() for _ in range(6)]
        self.rt.clock += 600
        self.assertEqual(self.c.get_run(ids[0])["effective_status"], "EXPIRED")
        self.assertEqual(self.record(ids[0])["status"], "ADMITTED")
        fresh = self.admit()
        self.assertEqual(self.state()["normal_ids"], [fresh])
        self.assertEqual(self.state()["fault_events"], [])
        self.assertTrue(all(self.record(i)["status"] == "EXPIRED" for i in ids))

    def test_cooldown_and_unique_probe_reservation_have_exact_boundaries(self):
        self.trip()
        self.rt.clock += 29
        with self.assertRaises(UserError):
            self.c.admit_probe(self.cid)
        self.rt.clock += 1
        probe = self.c.admit_probe(self.cid)
        self.assertEqual(self.state()["state"], "HALF_OPEN")
        self.assertEqual(self.state()["probe_id"], probe)
        before = self.storage()
        with self.assertRaises(UserError):
            self.c.admit_probe(self.cid)
        with self.assertRaises(UserError):
            self.admit()
        self.assertEqual(self.storage(), before)
        self.assertEqual(self.record(probe)["locked"]["operation"], self.state()["spec"]["probe_operation"])

    def test_only_certified_exact_probe_pass_recovers_and_resets_backoff(self):
        self.trip()
        probe = self.probe(B)
        receipt = self.settle(probe)
        self.assertTrue(receipt["effect"]["closed"])
        state = self.state()
        self.assertEqual((state["state"], state["probe_id"], state["generation"]), ("CLOSED", -1, 2))
        self.assertEqual((state["backoff_level"], state["open_until"], state["fault_events"]), (0, 0, []))
        self.admit()

    def test_old_normal_pass_cannot_close_open_circuit(self):
        old = self.admit(B)
        self.trip()
        before = self.state()
        receipt = self.settle(old)
        self.assertTrue(receipt["effect"]["historical_only"])
        self.assertFalse(receipt["effect"]["closed"])
        self.assertEqual(self.state()["state"], "OPEN")
        self.assertEqual(self.state()["open_until"], before["open_until"])

    def test_old_normal_fault_cannot_preempt_active_probe_or_count_in_new_generation(self):
        old = self.admit(B)
        self.trip()
        probe = self.probe()
        before = self.state()
        receipt = self.settle(old, "COMPONENT_FAULT")
        self.assertFalse(receipt["effect"]["fault_counted"])
        self.assertEqual(self.state()["fault_events"], before["fault_events"])
        self.assertEqual(self.state()["state"], "HALF_OPEN")
        self.assertEqual(self.state()["probe_id"], probe)
        self.settle(probe)
        self.assertEqual(self.state()["state"], "CLOSED")

    def test_old_normal_fault_after_probe_success_cannot_reopen_recovered_generation(self):
        old = self.admit(B)
        self.trip()
        self.settle(self.probe())
        receipt = self.settle(old, "COMPONENT_FAULT")
        self.assertTrue(receipt["effect"]["historical_only"])
        self.assertEqual(self.state()["state"], "CLOSED")
        self.assertEqual(self.state()["fault_events"], [])

    def test_probe_fault_and_semantic_ambiguity_both_reopen_without_certifying_new_faults(self):
        self.trip()
        probe = self.probe()
        receipt = self.settle(probe, "UNCERTAIN")
        self.assertTrue(receipt["effect"]["opened"])
        self.assertFalse(receipt["effect"]["fault_counted"])
        self.assertEqual(self.state()["open_until"], self.rt.clock + 60)
        probe = self.probe()
        self.settle(probe, "COMPONENT_FAULT")
        self.assertEqual(self.state()["open_until"], self.rt.clock + 120)

    def test_backoff_caps_without_unbounded_exponent_growth(self):
        self.trip()
        for _ in range(20):
            probe = self.probe()
            self.settle(probe, "COMPONENT_FAULT")
        state = self.state()
        self.assertEqual(state["backoff_level"], self.m.MAX_BACKOFF_LEVEL)
        self.assertEqual(state["open_until"], self.rt.clock + 240)

    def test_expired_probe_cooldown_is_anchored_to_deadline_and_new_probe_is_unique(self):
        self.trip()
        old = self.probe()
        deadline = self.record(old)["locked"]["deadline"]
        self.rt.clock = deadline + 100
        stored = self.storage()
        first = self.c.get_circuit(self.cid)
        self.rt.clock += 10
        second = self.c.get_circuit(self.cid)
        self.assertEqual(first["effective"]["open_until"], deadline + 60)
        for field in ["state", "generation", "open_until", "backoff_level", "probe_id"]:
            self.assertEqual(first["effective"][field], second["effective"][field])
        self.assertEqual(self.storage(), stored)
        new = self.c.admit_probe(self.cid)
        self.assertEqual(self.record(old)["status"], "EXPIRED")
        self.assertEqual(self.state()["probe_id"], new)
        before = self.storage()
        with self.assertRaises(UserError):
            self.settle(old)
        self.assertEqual(self.storage(), before)
        self.assertEqual(self.state()["probe_id"], new)

    def test_read_pruning_never_changes_persisted_state_and_noop_sweep_is_stable(self):
        self.settle(self.admit(), "COMPONENT_FAULT")
        self.rt.clock += 120
        before = self.storage()
        view = self.c.get_circuit(self.cid)
        self.assertEqual(len(view["record"]["fault_events"]), 1)
        self.assertEqual(view["effective"]["fault_events"], [])
        self.assertEqual(self.storage(), before)
        self.assertEqual(self.c.expire_runs(self.cid), 0)
        after = self.storage()
        self.assertEqual(self.c.expire_runs(self.cid), 0)
        self.assertEqual(self.storage(), after)

    def test_expiry_refresh_before_rejected_admission_never_partially_persists(self):
        self.trip()
        probe = self.probe()
        self.rt.clock = self.record(probe)["locked"]["deadline"]
        before = self.storage()
        with self.assertRaises(UserError):
            self.admit()
        self.assertEqual(self.storage(), before)
        self.c.expire_runs(self.cid)
        self.assertEqual(self.record(probe)["status"], "EXPIRED")
        self.assertEqual(self.state()["state"], "OPEN")

    def test_reporter_cancellation_frees_normal_slot_but_probe_cancel_reopens(self):
        normal = self.admit()
        self.c.cancel_run(normal)
        self.assertEqual(self.state()["fault_events"], [])
        self.assertEqual(self.state()["normal_ids"], [])
        self.trip()
        probe = self.probe()
        self.c.cancel_run(probe)
        self.assertEqual(self.record(probe)["status"], "CANCELED")
        self.assertEqual(self.state()["state"], "OPEN")
        self.assertEqual(self.state()["open_until"], self.rt.clock + 60)

    def test_report_lock_prevents_cancellation_and_verdict_shopping(self):
        normal = self.admit()
        self.report(normal)
        with self.assertRaises(UserError):
            self.c.cancel_run(normal)
        self.settle(normal, "UNCERTAIN")
        for call in [lambda: self.c.assess_run(normal), lambda: self.c.submit_report(normal, "Better story")]:
            with self.assertRaises(UserError):
                call()
        self.assertEqual(self.state()["fault_events"], [])

    def test_once_only_fault_settlement_cannot_count_same_run_twice(self):
        normal = self.admit()
        self.settle(normal, "COMPONENT_FAULT")
        before = self.storage()
        with self.assertRaises(UserError):
            self.c.assess_run(normal)
        self.assertEqual(self.storage(), before)
        self.assertEqual(len(self.state()["fault_events"]), 1)

    def test_normal_unreadable_retries_end_without_inventing_component_fault(self):
        normal = self.admit()
        for attempt in range(1, 4):
            receipt = self.settle(normal, RuntimeError("temporary model error"))
            self.assertEqual(receipt["attempt"], attempt)
            self.assertFalse(receipt["inspection"]["semantic_complete"])
            self.assertEqual(self.c.get_attempt(normal, attempt), receipt)
        self.assertEqual(self.record(normal)["status"], "UNRESOLVED_FINAL")
        self.assertEqual(self.state()["state"], "CLOSED")
        self.assertEqual(self.state()["fault_events"], [])
        self.assertEqual(self.state()["normal_ids"], [])
        with self.assertRaises(UserError):
            self.c.assess_run(normal)

    def test_unreadable_probe_stays_reserved_until_final_retry_then_reopens(self):
        self.trip()
        probe = self.probe()
        for attempt in range(1, 4):
            receipt = self.settle(probe, RuntimeError("temporary"))
            if attempt < 3:
                self.assertEqual(self.state()["state"], "HALF_OPEN")
                self.assertEqual(self.state()["probe_id"], probe)
            else:
                self.assertEqual(receipt["run_status"], "UNRESOLVED_FINAL")
                self.assertEqual(self.state()["state"], "OPEN")
        self.assertEqual(self.state()["open_until"], self.rt.clock + 60)

    def test_report_deadline_is_exclusive_for_submission_assessment_and_cancel(self):
        unreported = self.admit()
        reported = self.admit()
        self.report(reported)
        self.rt.clock += 600
        for call in [lambda: self.c.submit_report(unreported, "Late"), lambda: self.c.assess_run(reported),
                     lambda: self.c.cancel_run(unreported)]:
            with self.assertRaises(UserError):
                call()
        self.assertEqual(self.c.expire_runs(self.cid), 2)

    def test_retirement_is_owner_only_irreversible_and_historical_pass_cannot_close(self):
        self.trip()
        probe = self.probe(B)
        self.rt.as_sender(B)
        with self.assertRaises(UserError):
            self.c.retire_circuit(self.cid)
        self.rt.as_sender(A)
        self.c.retire_circuit(self.cid)
        receipt = self.settle(probe)
        self.assertTrue(receipt["effect"]["historical_only"])
        self.assertFalse(receipt["effect"]["closed"])
        self.assertEqual(self.state()["state"], "RETIRED")
        self.assertEqual(self.state()["probe_id"], -1)
        for call in [lambda: self.admit(), lambda: self.c.admit_probe(self.cid), lambda: self.c.retire_circuit(self.cid)]:
            with self.assertRaises(UserError):
                call()

    def test_retired_normal_fault_is_audit_only_without_budget_mutation(self):
        run_id = self.admit()
        self.c.retire_circuit(self.cid)
        receipt = self.settle(run_id, "COMPONENT_FAULT")
        self.assertFalse(receipt["effect"]["fault_counted"])
        self.assertEqual(self.state()["fault_events"], [])
        self.assertEqual(self.state()["state"], "RETIRED")

    def test_unauthorized_admission_and_cross_reporter_operations_fail(self):
        self.rt.as_sender(C)
        with self.assertRaises(UserError):
            self.c.admit_run(self.cid, "Operation")
        run_id = self.admit(B)
        self.rt.as_sender(A)
        for call in [lambda: self.c.submit_report(run_id, "Someone else's result"), lambda: self.c.cancel_run(run_id)]:
            with self.assertRaises(UserError):
                call()
        self.report(run_id)
        self.rt.as_sender(A)
        with self.assertRaises(UserError):
            self.c.assess_run(run_id)

    def test_frozen_policy_and_namespaces_remain_distinct(self):
        other = self.open()
        self.trip()
        self.assertEqual(self.state(other)["state"], "CLOSED")
        self.assertNotEqual(self.state(other)["policy_hash"], self.state()["policy_hash"])
        self.admit(cid=other)

    def test_independent_disagreement_and_receipt_tampering_commit_nothing(self):
        run_id = self.admit()
        self.report(run_id)
        self.rt.output = {"outcome": "PASS"}
        self.rt.validator_output = {"outcome": "COMPONENT_FAULT"}
        before = self.storage()
        with self.assertRaises(AssertionError):
            self.c.assess_run(run_id)
        self.assertEqual(self.storage(), before)
        self.rt.validator_output = None
        self.rt.mutate = lambda receipt: dict(receipt, summary="A fabricated extra narrative")
        with self.assertRaises(AssertionError):
            self.c.assess_run(run_id)
        self.assertEqual(self.storage(), before)

    def test_every_leaf_of_complete_consequential_receipt_is_independently_bound(self):
        self.cid = self.open(threshold=1)
        run_id = self.admit()
        self.report(run_id)
        self.rt.output = {"outcome": "COMPONENT_FAULT"}
        circuit, updates = self.c._refresh(self.c._circuit(self.cid), self.rt.clock)
        baseline = self.m._build_receipt(circuit, self.record(run_id), 1, self.rt.clock, [])

        def paths(value, prefix=()):
            if isinstance(value, dict) and value:
                for key, item in value.items():
                    yield from paths(item, prefix + (key,))
            elif isinstance(value, list) and value:
                for i, item in enumerate(value):
                    yield from paths(item, prefix + (i,))
            else:
                yield prefix

        before = self.storage()
        for path in paths(baseline):
            def mutate(value, path=path):
                target = value
                for key in path[:-1]:
                    target = target[key]
                old = target[path[-1]]
                target[path[-1]] = (not old if type(old) is bool else old + 1 if type(old) is int
                                      else old + [-9] if isinstance(old, list) else {"unexpected": True}
                                      if isinstance(old, dict) else str(old) + " tampered")
                return value
            self.rt.mutate = mutate
            with self.subTest(path=path), self.assertRaises(AssertionError):
                self.c.assess_run(run_id)
            self.assertEqual(self.storage(), before)
        self.rt.mutate = None

    def test_malformed_enum_extra_keys_and_nonobject_outputs_fail_closed(self):
        run_id = self.admit()
        self.report(run_id)
        for raw in [{"outcome": "PASS", "reason": "extra"}, {"outcome": "OTHER"}, []]:
            self.rt.output = raw
            receipt = self.c.assess_run(run_id)
            self.assertEqual(receipt["outcome"], "UNRESOLVED")
            self.assertFalse(receipt["inspection"]["semantic_complete"])
        self.assertEqual(self.record(run_id)["status"], "UNRESOLVED_FINAL")

    def test_full_unicode_and_escaped_report_is_in_both_independent_prompts(self):
        text = ("漢🚀 quoted \"source\"\n" * 150)[:2400]
        run_id = self.admit(operation="Read only the complete synthetic fixture 漢🚀.")
        self.report(run_id, text)
        receipt = self.settle(run_id, "UNCERTAIN")
        for entry in self.rt.prompts[-2:]:
            self.assertIn(self.m._json(text), entry["prompt"])
            self.assertIn("UNTRUSTED DATA", entry["prompt"])
            self.assertIn(self.m._json(self.record(run_id)["locked"]), entry["prompt"])
        prompt = self.rt.prompts[-1]["prompt"]
        self.assertEqual(receipt["inspection"]["prompt_chars"], len(prompt))
        self.assertEqual(receipt["inspection"]["prompt_utf8_bytes"], len(prompt.encode("utf-8")))
        self.assertFalse(receipt["inspection"]["prompt_truncated"])

    def test_budget_failure_does_not_lock_partial_report_or_apply_refresh(self):
        run_id = self.admit()
        self.m.MAX_PROMPT_BYTES = 100
        before = self.storage()
        with self.assertRaisesRegex(UserError, "inspection budget"):
            self.report(run_id, "漢🚀" * 500)
        self.assertEqual(self.storage(), before)
        self.assertEqual(self.rt.calls, 0)

    def test_longest_escaped_fields_fail_closed_without_hidden_cutoff(self):
        cid = self.c.open_circuit("\u0001" * 100, "\u0002" * 120, "\u0003" * 500, "\u0004" * 800,
                                  "\u0005" * 600, json.dumps([A]), 2, 120, 30, 240, 600)
        run_id = self.admit(operation="\u0006" * 600, cid=cid)
        before = self.storage()
        with self.assertRaisesRegex(UserError, "inspection budget"):
            self.report(run_id, "\u0007" * 2400)
        self.assertEqual(self.storage(), before)
        self.assertEqual(self.rt.calls, 0)

    def test_maximum_accepted_source_fields_are_all_present_in_both_complete_prompts(self):
        for character in ["x", "😀", '"', "\n"]:
            with self.subTest(character=repr(character)):
                field = lambda length: "Source " + character * (length - 7)
                title, component, purpose, policy, probe_op, operation, report = [
                    field(length) for length in [100, 120, 500, 800, 600, 600, 2400]]
                cid = self.c.open_circuit(title, component, purpose, policy, probe_op, json.dumps([A]),
                                          2, 120, 30, 240, 600)
                run_id = self.admit(operation=operation, cid=cid)
                self.report(run_id, report)
                receipt = self.settle(run_id, "UNCERTAIN")
                for entry in self.rt.prompts[-2:]:
                    prompt = entry["prompt"]
                    for value in [title, component, purpose, policy, probe_op, operation, report]:
                        self.assertIn(self.m._json(value), prompt)
                    self.assertLessEqual(len(prompt), self.m.MAX_PROMPT_CHARS)
                    self.assertLessEqual(len(prompt.encode("utf-8")), self.m.MAX_PROMPT_BYTES)
                self.assertFalse(receipt["inspection"]["prompt_truncated"])

    def test_invalid_ids_addresses_bool_parameters_and_surrogates_fail_before_model(self):
        for identifier in [True, -1, "0"]:
            with self.assertRaises(UserError):
                self.c.get_circuit(identifier)
        for reporters in [[], [A, A.upper()], ["bad"], ["0x" + "0" * 40], [A] * 9]:
            with self.assertRaises(UserError):
                self.open(reporters=reporters)
        for arguments in [{"threshold": True}, {"threshold": 7}, {"window": 59}, {"cooldown": 29},
                          {"maximum": 29}, {"cooldown": 240, "maximum": 30}, {"timeout": 3601}]:
            with self.assertRaises(UserError):
                self.open(**arguments)
        for operation in ["", " ", "x" * 601, "\ud800"]:
            with self.assertRaises(UserError):
                self.admit(operation=operation)
        self.assertEqual(self.rt.calls, 0)

    def test_clock_is_captured_before_model_callbacks_and_source_helper_is_exercised(self):
        run_id = self.admit()
        self.report(run_id)
        self.rt.clock += 11
        reads = self.rt.clock_reads
        receipt = self.c.assess_run(run_id)
        self.assertEqual(self.rt.clock_reads, reads + 1)
        self.assertEqual(receipt["assessed_at"], self.rt.clock)
        with self.assertRaisesRegex(AssertionError, "clock may not be read"):
            self.rt.run(lambda: self.m._now(), lambda result: True)
        self.assertFalse(self.rt.in_nondet)

    def test_backward_time_cannot_erase_a_fault_or_renew_a_pending_run(self):
        first, second = self.admit(), self.admit()
        self.report(first)
        self.report(second)
        start = self.rt.clock
        self.rt.clock = start + 50
        self.settle(first, "COMPONENT_FAULT")
        before = self.storage()
        self.rt.clock = start + 40
        self.rt.output = {"outcome": "COMPONENT_FAULT"}
        for call in [lambda: self.c.assess_run(second), lambda: self.c.get_circuit(self.cid),
                     lambda: self.c.get_run(second), lambda: self.c.expire_runs(self.cid)]:
            with self.assertRaisesRegex(UserError, "time moved backward"):
                call()
        self.assertEqual(self.storage(), before)
        self.rt.clock = start + 51
        self.c.assess_run(second)
        self.assertEqual(self.state()["state"], "OPEN")
        self.assertEqual([event["run_id"] for event in self.state()["fault_events"]], [first, second])
        self.assertEqual(self.state()["last_observed_at"], start + 51)


if __name__ == "__main__":
    unittest.main()
