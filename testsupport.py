"""Controlled-output SDK substitute. No GenVM, model benchmark or external calls."""
import copy
from datetime import datetime, timezone
import importlib.util
import pathlib
import sys
import types


class UserError(Exception):
    pass


class Return:
    def __init__(self, calldata):
        self.calldata = calldata


class Runtime:
    def __init__(self):
        self.sender = "0x" + "1" * 40
        self.clock = 1_800_000_000
        self.output = {"outcome": "PASS"}
        self.validator_output = None
        self.mutate = None
        self.calls = 0
        self.prompts = []
        self.in_nondet = False
        self.phase = "leader"
        self.clock_reads = 0
        self.fake = None

    def as_sender(self, address):
        self.sender = address
        self.fake.message.sender_address = address

    def prompt(self, prompt, response_format=None):
        assert response_format == "json"
        self.calls += 1
        self.prompts.append({"phase": self.phase, "prompt": prompt})
        result = self.validator_output if self.phase == "validator" and self.validator_output is not None else self.output
        if isinstance(result, Exception):
            raise result
        return copy.deepcopy(result)

    def run(self, leader, validator):
        self.in_nondet = True
        try:
            self.phase = "leader"
            result = leader()
            if self.mutate:
                result = self.mutate(copy.deepcopy(result))
            self.phase = "validator"
            if not validator(Return(result)):
                raise AssertionError("Independent validator rejected complete receipt")
            return result
        finally:
            self.phase = "leader"
            self.in_nondet = False


def load():
    runtime = Runtime()
    fake = types.ModuleType("genlayer")
    fake.contract = types.SimpleNamespace(Contract=object)
    fake.storage = types.SimpleNamespace(TreeMap=dict)
    fake.public = types.SimpleNamespace(write=lambda f: f, view=lambda f: f)
    fake.message = types.SimpleNamespace(sender_address=runtime.sender)
    fake.nondet = types.SimpleNamespace(exec_prompt=runtime.prompt)
    fake.vm = types.SimpleNamespace(UserError=UserError, Return=Return, run_nondet_default=runtime.run)
    types_module = types.ModuleType("genlayer.types")
    types_module.u64 = int
    types_module.__all__ = ["u64"]
    previous = {name: sys.modules.get(name) for name in ["genlayer", "genlayer.types"]}
    sys.modules["genlayer"] = fake
    sys.modules["genlayer.types"] = types_module
    spec = importlib.util.spec_from_file_location("FaultCircuit", pathlib.Path(__file__).with_name("FaultCircuit.py"))
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    finally:
        for name, old in previous.items():
            if old is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = old

    class TransactionDateTime:
        @staticmethod
        def now(tz=None):
            if runtime.in_nondet:
                raise AssertionError("Deterministic clock may not be read inside model callbacks")
            assert tz is timezone.utc
            runtime.clock_reads += 1
            return datetime.fromtimestamp(runtime.clock, tz)

    module.datetime = TransactionDateTime
    runtime.fake = fake
    contract = module.FaultCircuit()
    for name, annotation in module.FaultCircuit.__annotations__.items():
        if getattr(annotation, "__origin__", None) is dict:
            setattr(contract, name, {})
    return module, contract, runtime
