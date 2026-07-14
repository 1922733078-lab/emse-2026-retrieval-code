"""Semi-automatic generator for Fluxon tasks.

Produces 150 synthetic tasks (50 L1, 50 L2, 50 L3) using a fixed random seed.
Each task includes visible/hidden tests, gold/distractor snippet names, and a
reference solution.  All tests are executed against the reference solution
before the task is accepted.
"""

from __future__ import annotations

import inspect
import json
import random
import sys
import textwrap
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "libs" / "fluxon"))
sys.path.insert(0, str(ROOT / "retrieval_contexts" / "distractor"))

import fluxon
import fluxon_distractor

TASKS_DIR = ROOT / "tasks"
SOLUTIONS_DIR = ROOT / "solutions" / "fluxon"
TASKS_DIR.mkdir(parents=True, exist_ok=True)
SOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)

_VALID_VERSIONS = [1, 2, 3]
_VALID_CHANNELS = ["alpha", "beta", "gamma"]
_LETTERS = "ABCDEFG"

PUBLIC_FUNCS: dict[str, Callable[..., Any]] = {
    name: getattr(fluxon, name)
    for name in dir(fluxon)
    if not name.startswith("_") and callable(getattr(fluxon, name))
}

DISTRACTOR_FUNCS: dict[str, Callable[..., Any]] = {
    name: getattr(fluxon_distractor, name)
    for name in dir(fluxon_distractor)
    if not name.startswith("_") and callable(getattr(fluxon_distractor, name))
}


# ---------------------------------------------------------------------------
# Random example helpers
# ---------------------------------------------------------------------------

def _token(letter: str | None = None, digit: int | None = None) -> str:
    letter = letter or random.choice(_LETTERS)
    digit = digit if digit is not None else random.randint(0, 9)
    return f"{letter}{digit}"


def _payload(length: int | None = None, tokens: list[str] | None = None) -> str:
    if tokens is not None:
        return "-".join(tokens)
    length = length if length is not None else random.randint(1, 4)
    return "-".join(_token() for _ in range(length))


def _packet(
    version: int | None = None,
    channel: str | None = None,
    payload: str | None = None,
) -> str:
    version = version if version is not None else random.choice(_VALID_VERSIONS)
    channel = channel or random.choice(_VALID_CHANNELS)
    payload = payload if payload is not None else _payload()
    checksum = fluxon.compute_fluxon_checksum(payload, version)
    return fluxon.format_fluxon_packet(version, channel, payload, checksum)


def _frame(packet: str | None = None) -> str:
    packet = packet or _packet()
    return f"[FXN:{packet}:END]"


def _bad_checksum(packet: str) -> str:
    rec = fluxon.parse_fluxon_packet(packet)
    wrong = (rec["checksum"] + random.randint(1, 50)) % 200
    if wrong == rec["checksum"]:
        wrong = (wrong + 1) % 200
    return fluxon.format_fluxon_packet(
        rec["version"], rec["channel"], rec["payload"], wrong
    )


def _invalid_version_packet() -> str:
    return f"FXN::{random.choice([4, 5, 6])}::alpha::A1::{random.randint(0, 99)}"


def _invalid_channel_packet() -> str:
    return f"FXN::2::delta::A1::{random.randint(0, 99)}"


def _malformed() -> str:
    return random.choice(["not-a-packet", "FXN::alpha::A1", "[FXN:bad:END]"])


def _payload_with_duplicates(length: int = 4) -> str:
    """Return a payload containing at least one duplicated token."""
    base = [_token() for _ in range(max(1, length - 1))]
    dup = random.choice(base)
    base.append(dup)
    random.shuffle(base)
    return "-".join(base)


def _payload_unique(length: int = 4) -> str:
    tokens: set[str] = set()
    while len(tokens) < length:
        tokens.add(_token())
    return "-".join(sorted(tokens))


# ---------------------------------------------------------------------------
# Test formatting
# ---------------------------------------------------------------------------

def _format_assert(call: str, expected: Any) -> str:
    if isinstance(expected, bool):
        return f"assert {call} is {expected}"
    if expected is None:
        return f"assert {call} is None"
    if isinstance(expected, float):
        return f"assert abs({call} - {expected!r}) < 1e-9"
    return f"assert {call} == {expected!r}"


def _call_string(signature: str, inputs: tuple[Any, ...]) -> str:
    # Signature looks like "def solve(packet: str) -> int:"
    params = signature.split("(")[1].split(")")[0].split(",")
    param_names = [p.split(":")[0].strip() for p in params if p.strip()]
    args = ", ".join(repr(v) for v in inputs)
    return f"solve({args})"


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def _verify_task(task: dict[str, Any]) -> None:
    ns: dict[str, Any] = {**PUBLIC_FUNCS, "__builtins__": __builtins__}
    solution_path = SOLUTIONS_DIR / f"{task['task_id']}.py"
    code = solution_path.read_text(encoding="utf-8")
    try:
        exec(code, ns)
    except Exception as exc:
        raise RuntimeError(f"{task['task_id']}: solution failed to compile: {exc}\n{code}") from exc

    for test in task["visible_tests"] + task["hidden_tests"]:
        try:
            exec(test, ns)
        except AssertionError as exc:
            raise RuntimeError(
                f"{task['task_id']}: test assertion failed: {test}\n{exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(
                f"{task['task_id']}: test raised {type(exc).__name__}: {test}\n{exc}"
            ) from exc


# ---------------------------------------------------------------------------
# Generic task builder
# ---------------------------------------------------------------------------

def _build_task(
    task_id: str,
    level: str,
    category: str,
    signature: str,
    prompt: str,
    solve_body: str,
    make_input: Callable[[], tuple[Any, ...]],
    oracle: Callable[..., Any],
    gold_snippets: list[str],
    distractor_snippets: list[str],
    reasoning_steps: int,
    visible_count: int = 2,
    hidden_count: int = 5,
) -> dict[str, Any]:
    visible_tests: list[str] = []
    hidden_tests: list[str] = []

    while len(visible_tests) < visible_count:
        inputs = make_input()
        try:
            expected = oracle(*inputs)
        except Exception:
            continue
        call = _call_string(signature, inputs)
        visible_tests.append(_format_assert(call, expected))

    while len(hidden_tests) < hidden_count:
        inputs = make_input()
        try:
            expected = oracle(*inputs)
        except Exception:
            continue
        call = _call_string(signature, inputs)
        hidden_tests.append(_format_assert(call, expected))

    indented_body = solve_body.replace("\n", "\n    ")
    reference_code = f"{signature}\n    {indented_body}\n"

    task = {
        "task_id": task_id,
        "level": level,
        "category": category,
        "signature": signature,
        "prompt": prompt,
        "visible_tests": visible_tests,
        "hidden_tests": hidden_tests,
        "gold_snippets": gold_snippets,
        "distractor_snippets": distractor_snippets,
        "reasoning_steps": reasoning_steps,
        "reference_solution_path": f"solutions/fluxon/{task_id}.py",
    }

    solution_path = SOLUTIONS_DIR / f"{task_id}.py"
    solution_path.write_text(reference_code, encoding="utf-8")
    _verify_task(task)
    return task


# ---------------------------------------------------------------------------
# L1 templates (direct reuse)
# ---------------------------------------------------------------------------

def _l1_tasks() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []

    specs = [
        {
            "name": "checksum_from_packet",
            "signature": "def solve(packet: str) -> int:",
            "prompts": [
                "Implement solve(packet). Given a Fluxon packet string, return its checksum computed from the payload and version.",
                "Implement solve(packet). Return the checksum of the given Fluxon packet.",
                "Implement solve(packet). Parse the packet and compute its checksum.",
                "Implement solve(packet). Output the Fluxon checksum for the packet.",
                "Implement solve(packet). Calculate the checksum from the packet's payload.",
            ],
            "solve_body": 'record = parse_fluxon_packet(packet)\nreturn compute_fluxon_checksum(record["payload"], record["version"])',
            "make_input": lambda: (_packet(),),
            "oracle": lambda packet: fluxon.compute_fluxon_checksum(
                fluxon.parse_fluxon_packet(packet)["payload"],
                fluxon.parse_fluxon_packet(packet)["version"],
            ),
            "gold": ["compute_fluxon_checksum", "parse_fluxon_packet"],
            "distractor": ["compute_fluxon_checksum_wrong_mod", "parse_fluxon_packet_wrong_key"],
            "reasoning": 1,
        },
        {
            "name": "validate_packet",
            "signature": "def solve(packet: str) -> bool:",
            "prompts": [
                "Implement solve(packet). Return True if the Fluxon packet is valid (format and checksum are correct).",
                "Implement solve(packet). Verify that the packet is well-formed and has a correct checksum.",
                "Implement solve(packet). Return whether the given Fluxon packet passes validation.",
                "Implement solve(packet). Check the packet's format and checksum validity.",
                "Implement solve(packet). Determine if the packet is a valid Fluxon packet.",
            ],
            "solve_body": "return validate_fluxon_packet(packet)",
            "make_input": lambda: (random.choice([
                _packet(),
                _bad_checksum(_packet()),
                _invalid_version_packet(),
                _invalid_channel_packet(),
                _malformed(),
            ]),),
            "oracle": lambda packet: fluxon.validate_fluxon_packet(packet),
            "gold": ["validate_fluxon_packet"],
            "distractor": ["validate_fluxon_packet_empty_v3", "validate_fluxon_batch_any_true"],
            "reasoning": 1,
        },
        {
            "name": "parse_version",
            "signature": "def solve(packet: str) -> int:",
            "prompts": [
                "Implement solve(packet). Return the protocol version number of the Fluxon packet.",
                "Implement solve(packet). Extract and return the version field from the packet.",
                "Implement solve(packet). Return the version integer of the given packet.",
                "Implement solve(packet). Parse the packet and return its version.",
                "Implement solve(packet). What is the version of this Fluxon packet?",
            ],
            "solve_body": 'return parse_fluxon_packet(packet)["version"]',
            "make_input": lambda: (_packet(),),
            "oracle": lambda packet: fluxon.parse_fluxon_packet(packet)["version"],
            "gold": ["parse_fluxon_packet"],
            "distractor": ["parse_fluxon_packet_wrong_key"],
            "reasoning": 1,
        },
        {
            "name": "parse_channel",
            "signature": "def solve(packet: str) -> str:",
            "prompts": [
                "Implement solve(packet). Return the channel of the Fluxon packet.",
                "Implement solve(packet). Extract and return the packet's channel.",
                "Implement solve(packet). Return the channel name from the packet.",
                "Implement solve(packet). Parse the packet and return its channel.",
                "Implement solve(packet). What channel does this packet use?",
            ],
            "solve_body": 'return parse_fluxon_packet(packet)["channel"]',
            "make_input": lambda: (_packet(),),
            "oracle": lambda packet: fluxon.parse_fluxon_packet(packet)["channel"],
            "gold": ["parse_fluxon_packet"],
            "distractor": ["parse_fluxon_packet_wrong_key"],
            "reasoning": 1,
        },
        {
            "name": "count_tokens",
            "signature": "def solve(packet: str) -> int:",
            "prompts": [
                "Implement solve(packet). Return the number of tokens in the packet's payload.",
                "Implement solve(packet). Count how many tokens the payload contains.",
                "Implement solve(packet). Return the payload token count.",
                "Implement solve(packet). How many tokens are in the packet payload?",
                "Implement solve(packet). Count the tokens after parsing the packet.",
            ],
            "solve_body": 'record = parse_fluxon_packet(packet)\nreturn len(split_fluxon_payload(record["payload"]))',
            "make_input": lambda: (_packet(payload=_payload(length=random.randint(0, 5))),),
            "oracle": lambda packet: len(
                fluxon.split_fluxon_payload(fluxon.parse_fluxon_packet(packet)["payload"])
            ),
            "gold": ["parse_fluxon_packet", "split_fluxon_payload"],
            "distractor": ["split_fluxon_payload_off_by_one", "parse_fluxon_packet_wrong_key"],
            "reasoning": 1,
        },
        {
            "name": "is_legacy",
            "signature": "def solve(packet: str) -> bool:",
            "prompts": [
                "Implement solve(packet). Return True if the packet is a legacy (version 1) packet.",
                "Implement solve(packet). Determine whether the packet uses version 1.",
                "Implement solve(packet). Return whether this is a legacy Fluxon packet.",
                "Implement solve(packet). Check if the packet's version equals 1.",
                "Implement solve(packet). Is the given packet a legacy packet?",
            ],
            "solve_body": "return is_legacy_packet(packet)",
            "make_input": lambda: (_packet(version=random.choice([1, 1, 2, 3])),),
            "oracle": lambda packet: fluxon.is_legacy_packet(packet),
            "gold": ["is_legacy_packet"],
            "distractor": ["is_legacy_packet_inverted", "parse_fluxon_packet_wrong_key"],
            "reasoning": 1,
        },
        {
            "name": "decode_frame",
            "signature": "def solve(frame: str) -> str:",
            "prompts": [
                "Implement solve(frame). Decode a Fluxon frame like '[FXN:...:END]' and return the inner packet string.",
                "Implement solve(frame). Extract the packet contained inside a Fluxon frame.",
                "Implement solve(frame). Given a frame wrapper, return the packet it contains.",
                "Implement solve(frame). Remove the frame header and trailer and return the packet.",
                "Implement solve(frame). Decode the frame into its inner packet string.",
            ],
            "solve_body": "return decode_fluxon_frame(frame)",
            "make_input": lambda: (_frame(_packet()),),
            "oracle": lambda frame: fluxon.decode_fluxon_frame(frame),
            "gold": ["decode_fluxon_frame"],
            "distractor": ["decode_fluxon_frame_strip_brackets"],
            "reasoning": 1,
        },
        {
            "name": "sum_token_values",
            "signature": "def solve(packet: str) -> int:",
            "prompts": [
                "Implement solve(packet). Return the sum of the numeric values of all tokens in the payload.",
                "Implement solve(packet). Compute the total numeric value of the payload tokens.",
                "Implement solve(packet). Sum the values of every token in the packet.",
                "Implement solve(packet). Return the combined value of all payload tokens.",
                "Implement solve(packet). Add up the numeric values of the tokens.",
            ],
            "solve_body": 'record = parse_fluxon_packet(packet)\nreturn sum(token_value(t) for t in split_fluxon_payload(record["payload"]))',
            "make_input": lambda: (_packet(),),
            "oracle": lambda packet: sum(
                fluxon.token_value(t)
                for t in fluxon.split_fluxon_payload(
                    fluxon.parse_fluxon_packet(packet)["payload"]
                )
            ),
            "gold": ["parse_fluxon_packet", "split_fluxon_payload", "token_value"],
            "distractor": ["token_value_digit_only", "split_fluxon_payload_off_by_one"],
            "reasoning": 1,
        },
        {
            "name": "normalize_raw",
            "signature": "def solve(raw: float, channel: str) -> float:",
            "prompts": [
                "Implement solve(raw, channel). Normalize the raw value according to the Fluxon channel rules.",
                "Implement solve(raw, channel). Apply channel-specific normalization to the raw value.",
                "Implement solve(raw, channel). Return the normalized value for the given channel.",
                "Implement solve(raw, channel). Normalize raw by the alpha/beta/gamma channel rules.",
                "Implement solve(raw, channel). Convert a raw value into its channel-normalized form.",
            ],
            "solve_body": "return normalize_channel_value(raw, channel)",
            "make_input": lambda: (float(random.randint(0, 200)), random.choice(_VALID_CHANNELS)),
            "oracle": lambda raw, channel: fluxon.normalize_channel_value(raw, channel),
            "gold": ["normalize_channel_value"],
            "distractor": ["normalize_channel_value_swapped"],
            "reasoning": 1,
        },
        {
            "name": "repair_packet",
            "signature": "def solve(packet: str) -> str:",
            "prompts": [
                "Implement solve(packet). Repair the malformed Fluxon packet and return the repaired packet string.",
                "Implement solve(packet). Fix the packet using the Fluxon repair routine.",
                "Implement solve(packet). Return a repaired version of the given packet.",
                "Implement solve(packet). Apply the packet repair utility and return the result.",
                "Implement solve(packet). Repair checksum and structural problems in the packet.",
            ],
            "solve_body": "return repair_fluxon_packet(packet)",
            "make_input": lambda: (random.choice([
                _bad_checksum(_packet()),
                _packet(),
                _malformed(),
            ]),),
            "oracle": lambda packet: fluxon.repair_fluxon_packet(packet),
            "gold": ["repair_fluxon_packet"],
            "distractor": ["repair_fluxon_packet_no_checksum"],
            "reasoning": 1,
        },
    ]

    for spec in specs:
        for variant in range(5):
            task_id = f"fluxon_l1_{len(tasks) + 1:03d}"
            prompt = spec["prompts"][variant % len(spec["prompts"])]
            task = _build_task(
                task_id=task_id,
                level="L1",
                category="direct_reuse",
                signature=spec["signature"],
                prompt=prompt,
                solve_body=spec["solve_body"],
                make_input=spec["make_input"],
                oracle=spec["oracle"],
                gold_snippets=spec["gold"],
                distractor_snippets=spec["distractor"],
                reasoning_steps=spec["reasoning"],
            )
            tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------
# L2 templates (adaptive modification)
# ---------------------------------------------------------------------------

def _l2_tasks() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []

    def legacy_beta_case() -> tuple[str]:
        case = random.choice([
            "valid_random",
            "v2_beta_bad",
            "legacy_beta_2_bad",
            "legacy_beta_3_bad",
            "legacy_alpha_valid",
        ])
        if case == "valid_random":
            return (_packet(),)
        if case == "v2_beta_bad":
            return (_bad_checksum(_packet(version=2, channel="beta", payload=_payload(length=2))),)
        if case == "legacy_beta_2_bad":
            return (_bad_checksum(_packet(version=1, channel="beta", payload=_payload(length=2))),)
        if case == "legacy_beta_3_bad":
            return (_bad_checksum(_packet(version=1, channel="beta", payload=_payload(length=3))),)
        return (_packet(version=1, channel="alpha"),)

    def legacy_beta_oracle(packet: str) -> bool:
        rec = fluxon.parse_fluxon_packet(packet)
        if rec["version"] == 1 and rec["channel"] == "beta":
            if len(fluxon.split_fluxon_payload(rec["payload"])) == 2:
                return True
        return fluxon.validate_fluxon_packet(packet)

    def gamma_v2_case() -> tuple[str]:
        case = random.choice([
            "valid_gamma_v2",
            "valid_gamma_v3",
            "v1_gamma_valid",
            "v2_alpha_valid",
            "gamma_bad_checksum",
        ])
        if case == "valid_gamma_v2":
            return (_packet(version=2, channel="gamma"),)
        if case == "valid_gamma_v3":
            return (_packet(version=3, channel="gamma"),)
        if case == "v1_gamma_valid":
            return (_packet(version=1, channel="gamma"),)
        if case == "v2_alpha_valid":
            return (_packet(version=2, channel="alpha"),)
        return (_bad_checksum(_packet(version=2, channel="gamma")),)

    def gamma_v2_oracle(packet: str) -> bool:
        if not fluxon.validate_fluxon_packet(packet):
            return False
        rec = fluxon.parse_fluxon_packet(packet)
        return rec["version"] >= 2 and rec["channel"] == "gamma"

    def checksum_then_normalize_case() -> tuple[str]:
        return (_packet(),)

    def checksum_then_normalize_oracle(packet: str) -> float:
        rec = fluxon.parse_fluxon_packet(packet)
        cs = fluxon.compute_fluxon_checksum(rec["payload"], rec["version"])
        return fluxon.normalize_channel_value(cs, rec["channel"])

    def valid_norm_sum_case() -> tuple[str]:
        return (random.choice([
            _packet(),
            _bad_checksum(_packet()),
        ]),)

    def valid_norm_sum_oracle(packet: str) -> float:
        if not fluxon.validate_fluxon_packet(packet):
            return -1.0
        rec = fluxon.parse_fluxon_packet(packet)
        total = sum(
            fluxon.token_value(t)
            for t in fluxon.split_fluxon_payload(rec["payload"])
        )
        return fluxon.normalize_channel_value(total, rec["channel"])

    def merge_two_case() -> tuple[str, str]:
        return (_packet(), _packet())

    def merge_two_oracle(p1: str, p2: str) -> int:
        rec1 = fluxon.parse_fluxon_packet(p1)
        rec2 = fluxon.parse_fluxon_packet(p2)
        merged = fluxon.merge_fluxon_records([rec1, rec2])
        return fluxon.compute_fluxon_checksum(merged["payload"], merged["version"])

    def frame_token_count_case() -> tuple[str]:
        case = random.choice(["valid", "bad_checksum", "empty_payload"])
        if case == "valid":
            return (_frame(_packet(payload=_payload(length=random.randint(1, 4)))),)
        if case == "bad_checksum":
            return (_frame(_bad_checksum(_packet(payload=_payload(length=2)))),)
        return (_frame(_packet(payload="")),)

    def frame_token_count_oracle(frame: str) -> int:
        packet = fluxon.decode_fluxon_frame(frame)
        if not fluxon.validate_fluxon_packet(packet):
            return -1
        rec = fluxon.parse_fluxon_packet(packet)
        return len(fluxon.split_fluxon_payload(rec["payload"]))

    def repair_validate_case() -> tuple[str]:
        return (random.choice([
            _bad_checksum(_packet()),
            _packet(),
            _malformed(),
        ]),)

    def repair_validate_oracle(packet: str) -> bool:
        return fluxon.validate_fluxon_packet(fluxon.repair_fluxon_packet(packet))

    def avg_norm_case() -> tuple[str]:
        return (_packet(payload=_payload(length=random.randint(1, 5))),)

    def avg_norm_oracle(packet: str) -> float:
        rec = fluxon.parse_fluxon_packet(packet)
        values = [
            fluxon.token_value(t)
            for t in fluxon.split_fluxon_payload(rec["payload"])
        ]
        avg = sum(values) / len(values) if values else 0.0
        return fluxon.normalize_channel_value(avg, rec["channel"])

    def duplicate_tokens_case() -> tuple[str]:
        if random.choice([True, False]):
            payload = _payload_with_duplicates(length=random.randint(2, 5))
        else:
            payload = _payload_unique(length=random.randint(2, 5))
        return (_packet(payload=payload),)

    def duplicate_tokens_oracle(packet: str) -> bool:
        if not fluxon.validate_fluxon_packet(packet):
            return False
        rec = fluxon.parse_fluxon_packet(packet)
        tokens = fluxon.split_fluxon_payload(rec["payload"])
        return len(tokens) != len(set(tokens))

    def reformat_channel_case() -> tuple[str, str]:
        pkt = _packet()
        rec = fluxon.parse_fluxon_packet(pkt)
        new_channel = random.choice([c for c in _VALID_CHANNELS if c != rec["channel"]])
        return (pkt, new_channel)

    def reformat_channel_oracle(packet: str, new_channel: str) -> str:
        rec = fluxon.parse_fluxon_packet(packet)
        return fluxon.format_fluxon_packet(
            rec["version"], new_channel, rec["payload"]
        )

    specs = [
        {
            "name": "legacy_beta_two_token_ignore",
            "signature": "def solve(packet: str) -> bool:",
            "prompts": [
                "Implement solve(packet). Return True if the packet is valid. For legacy version-1 packets from channel beta, ignore checksum mismatch when the payload has exactly two tokens.",
                "Implement solve(packet). Validate the packet, but waive the checksum check for legacy beta packets with two tokens.",
                "Implement solve(packet). Return validity, treating two-token legacy beta packets as always valid.",
                "Implement solve(packet). Check packet validity with a special rule for two-token beta legacy packets.",
                "Implement solve(packet). Validate packets, except ignore checksums on two-token version-1 beta payloads.",
            ],
            "solve_body": 'record = parse_fluxon_packet(packet)\nif record["version"] == 1 and record["channel"] == "beta":\n    tokens = split_fluxon_payload(record["payload"])\n    if len(tokens) == 2:\n        return True\nreturn validate_fluxon_packet(packet)',
            "make_input": legacy_beta_case,
            "oracle": legacy_beta_oracle,
            "gold": ["validate_fluxon_packet", "parse_fluxon_packet", "split_fluxon_payload"],
            "distractor": ["validate_fluxon_packet_empty_v3", "parse_fluxon_packet_wrong_key", "split_fluxon_payload_off_by_one"],
            "reasoning": 3,
        },
        {
            "name": "valid_gamma_version_ge_two",
            "signature": "def solve(packet: str) -> bool:",
            "prompts": [
                "Implement solve(packet). Return True if and only if the packet is valid, its version is 2 or higher, and its channel is gamma.",
                "Implement solve(packet). Return True only for valid version-2+ packets on the gamma channel.",
                "Implement solve(packet). Check that the packet is valid, version >= 2, and uses channel gamma.",
                "Implement solve(packet). Determine whether the packet is a valid gamma-channel packet with version at least 2.",
                "Implement solve(packet). Accept valid packets only when channel is gamma and version is 2 or 3.",
            ],
            "solve_body": 'if not validate_fluxon_packet(packet):\n    return False\nrecord = parse_fluxon_packet(packet)\nreturn record["version"] >= 2 and record["channel"] == "gamma"',
            "make_input": gamma_v2_case,
            "oracle": gamma_v2_oracle,
            "gold": ["validate_fluxon_packet", "parse_fluxon_packet"],
            "distractor": ["validate_fluxon_packet_empty_v3", "parse_fluxon_packet_wrong_key"],
            "reasoning": 3,
        },
        {
            "name": "checksum_then_normalize",
            "signature": "def solve(packet: str) -> float:",
            "prompts": [
                "Implement solve(packet). Compute the packet's checksum, then normalize that value according to the packet's channel.",
                "Implement solve(packet). Return the checksum normalized by the channel rules.",
                "Implement solve(packet). Compute the checksum and channel-normalize it.",
                "Implement solve(packet). Normalize the packet checksum based on its channel.",
                "Implement solve(packet). First compute the checksum, then apply channel normalization.",
            ],
            "solve_body": 'record = parse_fluxon_packet(packet)\nchecksum = compute_fluxon_checksum(record["payload"], record["version"])\nreturn normalize_channel_value(checksum, record["channel"])',
            "make_input": checksum_then_normalize_case,
            "oracle": checksum_then_normalize_oracle,
            "gold": ["compute_fluxon_checksum", "parse_fluxon_packet", "normalize_channel_value"],
            "distractor": ["compute_fluxon_checksum_wrong_mod", "normalize_channel_value_swapped", "parse_fluxon_packet_wrong_key"],
            "reasoning": 2,
        },
        {
            "name": "valid_norm_sum_or_minus_one",
            "signature": "def solve(packet: str) -> float:",
            "prompts": [
                "Implement solve(packet). If the packet is valid, return the sum of token values normalized by the channel. If invalid, return -1.0.",
                "Implement solve(packet). Return the normalized token-sum for valid packets, otherwise -1.0.",
                "Implement solve(packet). Validate the packet, then return the normalized total token value or -1.0.",
                "Implement solve(packet). For valid packets, output the channel-normalized token sum; for invalid ones, output -1.0.",
                "Implement solve(packet). Normalize the token sum by channel when valid; return -1.0 otherwise.",
            ],
            "solve_body": 'if not validate_fluxon_packet(packet):\n    return -1.0\nrecord = parse_fluxon_packet(packet)\ntotal = sum(token_value(t) for t in split_fluxon_payload(record["payload"]))\nreturn normalize_channel_value(total, record["channel"])',
            "make_input": valid_norm_sum_case,
            "oracle": valid_norm_sum_oracle,
            "gold": ["validate_fluxon_packet", "parse_fluxon_packet", "split_fluxon_payload", "token_value", "normalize_channel_value"],
            "distractor": ["token_value_digit_only", "normalize_channel_value_swapped"],
            "reasoning": 3,
        },
        {
            "name": "merge_two_checksum",
            "signature": "def solve(packet1: str, packet2: str) -> int:",
            "prompts": [
                "Implement solve(packet1, packet2). Merge the two parsed Fluxon records and return the checksum of the merged payload using the merged version.",
                "Implement solve(packet1, packet2). Parse both packets, merge their records, and compute the checksum of the merge.",
                "Implement solve(packet1, packet2). Combine the two packets into one record and return its checksum.",
                "Implement solve(packet1, packet2). Merge the records and compute the merged checksum.",
                "Implement solve(packet1, packet2). Return the checksum for the merged result of the two packets.",
            ],
            "solve_body": 'rec1 = parse_fluxon_packet(packet1)\nrec2 = parse_fluxon_packet(packet2)\nmerged = merge_fluxon_records([rec1, rec2])\nreturn compute_fluxon_checksum(merged["payload"], merged["version"])',
            "make_input": merge_two_case,
            "oracle": merge_two_oracle,
            "gold": ["parse_fluxon_packet", "merge_fluxon_records", "compute_fluxon_checksum"],
            "distractor": ["merge_fluxon_records_wrong_version", "compute_fluxon_checksum_wrong_mod"],
            "reasoning": 3,
        },
        {
            "name": "frame_token_count_or_invalid",
            "signature": "def solve(frame: str) -> int:",
            "prompts": [
                "Implement solve(frame). Decode a Fluxon frame into a packet. If the packet is valid, return the number of tokens; otherwise return -1.",
                "Implement solve(frame). Decode the frame and return the payload token count for valid packets, or -1 for invalid ones.",
                "Implement solve(frame). Extract the packet from the frame, validate it, and return the token count or -1.",
                "Implement solve(frame). Return the token count of a valid framed packet; return -1 if invalid.",
                "Implement solve(frame). Decode, validate, and count tokens in the framed packet, returning -1 on failure.",
            ],
            "solve_body": 'packet = decode_fluxon_frame(frame)\nif not validate_fluxon_packet(packet):\n    return -1\nrecord = parse_fluxon_packet(packet)\nreturn len(split_fluxon_payload(record["payload"]))',
            "make_input": frame_token_count_case,
            "oracle": frame_token_count_oracle,
            "gold": ["decode_fluxon_frame", "validate_fluxon_packet", "parse_fluxon_packet", "split_fluxon_payload"],
            "distractor": ["decode_fluxon_frame_strip_brackets", "validate_fluxon_packet_empty_v3"],
            "reasoning": 3,
        },
        {
            "name": "repair_then_validate",
            "signature": "def solve(packet: str) -> bool:",
            "prompts": [
                "Implement solve(packet). Repair the packet and return whether the repaired packet is valid.",
                "Implement solve(packet). Apply repair and check if the result is valid.",
                "Implement solve(packet). Fix the packet, then validate the repaired string.",
                "Implement solve(packet). Return the validity of the repaired packet.",
                "Implement solve(packet). Repair first, then return True if the repaired packet is valid.",
            ],
            "solve_body": 'repaired = repair_fluxon_packet(packet)\nreturn validate_fluxon_packet(repaired)',
            "make_input": repair_validate_case,
            "oracle": repair_validate_oracle,
            "gold": ["repair_fluxon_packet", "validate_fluxon_packet"],
            "distractor": ["repair_fluxon_packet_no_checksum", "validate_fluxon_packet_empty_v3"],
            "reasoning": 2,
        },
        {
            "name": "average_token_value_normalized",
            "signature": "def solve(packet: str) -> float:",
            "prompts": [
                "Implement solve(packet). Return the average token value in the payload, normalized by the packet's channel.",
                "Implement solve(packet). Compute the mean token value and normalize it by channel.",
                "Implement solve(packet). Average the token values, then apply channel normalization.",
                "Implement solve(packet). Return the channel-normalized average token value.",
                "Implement solve(packet). Calculate the average payload token value and normalize it.",
            ],
            "solve_body": 'record = parse_fluxon_packet(packet)\nvalues = [token_value(t) for t in split_fluxon_payload(record["payload"])]\navg = sum(values) / len(values) if values else 0.0\nreturn normalize_channel_value(avg, record["channel"])',
            "make_input": avg_norm_case,
            "oracle": avg_norm_oracle,
            "gold": ["parse_fluxon_packet", "split_fluxon_payload", "token_value", "normalize_channel_value"],
            "distractor": ["token_value_digit_only", "normalize_channel_value_swapped"],
            "reasoning": 2,
        },
        {
            "name": "duplicate_tokens",
            "signature": "def solve(packet: str) -> bool:",
            "prompts": [
                "Implement solve(packet). Return True if the packet is valid and its payload contains duplicate tokens.",
                "Implement solve(packet). Check whether the valid packet has any repeated payload tokens.",
                "Implement solve(packet). Return True for valid packets with duplicate tokens.",
                "Implement solve(packet). Detect duplicate tokens in a valid packet's payload.",
                "Implement solve(packet). Validate the packet and report whether its tokens contain duplicates.",
            ],
            "solve_body": 'if not validate_fluxon_packet(packet):\n    return False\nrecord = parse_fluxon_packet(packet)\ntokens = split_fluxon_payload(record["payload"])\nreturn len(tokens) != len(set(tokens))',
            "make_input": duplicate_tokens_case,
            "oracle": duplicate_tokens_oracle,
            "gold": ["validate_fluxon_packet", "parse_fluxon_packet", "split_fluxon_payload"],
            "distractor": ["validate_fluxon_packet_empty_v3", "split_fluxon_payload_off_by_one"],
            "reasoning": 2,
        },
        {
            "name": "reformat_channel",
            "signature": "def solve(packet: str, new_channel: str) -> str:",
            "prompts": [
                "Implement solve(packet, new_channel). Reformat the packet with the channel changed to new_channel, recomputing the checksum.",
                "Implement solve(packet, new_channel). Change the packet's channel and return the newly formatted packet.",
                "Implement solve(packet, new_channel). Parse the packet, swap its channel, and format it with a fresh checksum.",
                "Implement solve(packet, new_channel). Produce a packet identical to the input but using new_channel.",
                "Implement solve(packet, new_channel). Reformat with the given channel and an updated checksum.",
            ],
            "solve_body": 'record = parse_fluxon_packet(packet)\nreturn format_fluxon_packet(record["version"], new_channel, record["payload"])',
            "make_input": reformat_channel_case,
            "oracle": reformat_channel_oracle,
            "gold": ["parse_fluxon_packet", "format_fluxon_packet"],
            "distractor": ["parse_fluxon_packet_wrong_key", "compute_fluxon_checksum_wrong_mod"],
            "reasoning": 2,
        },
    ]

    for spec in specs:
        for variant in range(5):
            task_id = f"fluxon_l2_{len(tasks) + 1:03d}"
            prompt = spec["prompts"][variant % len(spec["prompts"])]
            task = _build_task(
                task_id=task_id,
                level="L2",
                category="adaptive_modification",
                signature=spec["signature"],
                prompt=prompt,
                solve_body=spec["solve_body"],
                make_input=spec["make_input"],
                oracle=spec["oracle"],
                gold_snippets=spec["gold"],
                distractor_snippets=spec["distractor"],
                reasoning_steps=spec["reasoning"],
            )
            tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------
# L3 templates (composition / reasoning)
# ---------------------------------------------------------------------------

def _l3_tasks() -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []

    def make_frame_list(n: int = 4) -> list[str]:
        frames: list[str] = []
        for _ in range(n):
            if random.random() < 0.25:
                frames.append(_frame(_bad_checksum(_packet())))
            else:
                frames.append(_frame(_packet()))
        return frames

    def make_packet_list(n: int = 4) -> list[str]:
        packets: list[str] = []
        for _ in range(n):
            if random.random() < 0.25:
                packets.append(_bad_checksum(_packet()))
            else:
                packets.append(_packet())
        return packets

    def frames_avg_normalized(frames: list[str]) -> float:
        values: list[float] = []
        for frame in frames:
            packet = fluxon.decode_fluxon_frame(frame)
            if fluxon.validate_fluxon_packet(packet):
                rec = fluxon.parse_fluxon_packet(packet)
                total = sum(
                    fluxon.token_value(t)
                    for t in fluxon.split_fluxon_payload(rec["payload"])
                )
                values.append(fluxon.normalize_channel_value(total, rec["channel"]))
        return sum(values) / len(values) if values else 0.0

    def count_valid_nonlegacy_gamma(packets: list[str]) -> int:
        count = 0
        for packet in packets:
            if not fluxon.validate_fluxon_packet(packet):
                continue
            rec = fluxon.parse_fluxon_packet(packet)
            if rec["channel"] == "gamma" and not fluxon.is_legacy_packet(rec):
                count += 1
        return count

    def merge_valid_checksum(packets: list[str]) -> int:
        valid = [
            fluxon.parse_fluxon_packet(p)
            for p in packets
            if fluxon.validate_fluxon_packet(p)
        ]
        if not valid:
            return 0
        merged = fluxon.merge_fluxon_records(valid)
        return fluxon.compute_fluxon_checksum(merged["payload"], merged["version"])

    def summarize_valid(packets: list[str]) -> dict[str, Any]:
        valid = [
            fluxon.parse_fluxon_packet(p)
            for p in packets
            if fluxon.validate_fluxon_packet(p)
        ]
        return fluxon.summarize_fluxon_records(valid)

    def repair_count_valid(packets: list[str]) -> int:
        return sum(
            1
            for p in packets
            if fluxon.validate_fluxon_packet(fluxon.repair_fluxon_packet(p))
        )

    def channel_max_normalized(packets: list[str]) -> dict[str, float]:
        channel_totals: dict[str, list[float]] = {}
        for packet in packets:
            if not fluxon.validate_fluxon_packet(packet):
                continue
            rec = fluxon.parse_fluxon_packet(packet)
            total = sum(
                fluxon.token_value(t)
                for t in fluxon.split_fluxon_payload(rec["payload"])
            )
            norm = fluxon.normalize_channel_value(total, rec["channel"])
            channel_totals.setdefault(rec["channel"], []).append(norm)
        return {ch: max(vals) for ch, vals in channel_totals.items()}

    def frames_v2_checksums(frames: list[str]) -> list[int]:
        result: list[int] = []
        for frame in frames:
            packet = fluxon.decode_fluxon_frame(frame)
            if fluxon.validate_fluxon_packet(packet):
                rec = fluxon.parse_fluxon_packet(packet)
                if rec["version"] >= 2:
                    result.append(rec["checksum"])
        return result

    def all_valid_and_legacy(packets: list[str]) -> bool:
        if not packets:
            return False
        has_legacy = False
        for packet in packets:
            if not fluxon.validate_fluxon_packet(packet):
                return False
            if fluxon.is_legacy_packet(packet):
                has_legacy = True
        return has_legacy

    def max_token_sum_alphabeta(packets: list[str]) -> str | None:
        best: str | None = None
        best_score = -1
        for packet in packets:
            if not fluxon.validate_fluxon_packet(packet):
                continue
            rec = fluxon.parse_fluxon_packet(packet)
            if rec["channel"] not in {"alpha", "beta"}:
                continue
            score = sum(
                fluxon.token_value(t)
                for t in fluxon.split_fluxon_payload(rec["payload"])
            )
            if score > best_score:
                best_score = score
                best = packet
        return best

    def frames_avg_per_channel(frames: list[str]) -> dict[str, float]:
        groups: dict[str, list[float]] = {}
        for frame in frames:
            packet = fluxon.decode_fluxon_frame(frame)
            if not fluxon.validate_fluxon_packet(packet):
                continue
            rec = fluxon.parse_fluxon_packet(packet)
            total = sum(
                fluxon.token_value(t)
                for t in fluxon.split_fluxon_payload(rec["payload"])
            )
            norm = fluxon.normalize_channel_value(total, rec["channel"])
            groups.setdefault(rec["channel"], []).append(norm)
        return {ch: sum(vals) / len(vals) for ch, vals in groups.items()}

    specs = [
        {
            "name": "frames_avg_normalized",
            "signature": "def solve(frames: list[str]) -> float:",
            "prompts": [
                "Implement solve(frames). For each Fluxon frame, decode it, keep only valid packets, normalize the sum of token values by channel, and return the average normalized value. Return 0.0 if none are valid.",
                "Implement solve(frames). Decode frames, filter valid packets, normalize token sums by channel, and average them.",
                "Implement solve(frames). Return the mean channel-normalized token sum across valid framed packets.",
                "Implement solve(frames). Decode, validate, normalize per channel, and compute the overall average.",
                "Implement solve(frames). Average the normalized token sums of all valid packets from the frames.",
            ],
            "solve_body": 'values = []\nfor frame in frames:\n    packet = decode_fluxon_frame(frame)\n    if validate_fluxon_packet(packet):\n        record = parse_fluxon_packet(packet)\n        total = sum(token_value(t) for t in split_fluxon_payload(record["payload"]))\n        values.append(normalize_channel_value(total, record["channel"]))\nreturn sum(values) / len(values) if values else 0.0',
            "make_input": lambda: (make_frame_list(random.randint(1, 5)),),
            "oracle": frames_avg_normalized,
            "gold": ["decode_fluxon_frame", "validate_fluxon_packet", "parse_fluxon_packet", "split_fluxon_payload", "token_value", "normalize_channel_value"],
            "distractor": ["decode_fluxon_frame_strip_brackets", "validate_fluxon_packet_empty_v3", "normalize_channel_value_swapped"],
            "reasoning": 5,
        },
        {
            "name": "count_valid_nonlegacy_gamma",
            "signature": "def solve(packets: list[str]) -> int:",
            "prompts": [
                "Implement solve(packets). Return the number of packets that are valid, non-legacy, and from channel gamma.",
                "Implement solve(packets). Count valid version-2/3 packets on the gamma channel.",
                "Implement solve(packets). Return how many packets are valid gamma-channel packets that are not legacy.",
                "Implement solve(packets). Count packets that pass validation, use gamma, and have version >= 2.",
                "Implement solve(packets). Find the number of valid non-legacy gamma packets.",
            ],
            "solve_body": 'count = 0\nfor packet in packets:\n    if not validate_fluxon_packet(packet):\n        continue\n    record = parse_fluxon_packet(packet)\n    if record["channel"] == "gamma" and not is_legacy_packet(record):\n        count += 1\nreturn count',
            "make_input": lambda: (make_packet_list(random.randint(1, 5)),),
            "oracle": count_valid_nonlegacy_gamma,
            "gold": ["validate_fluxon_packet", "parse_fluxon_packet", "is_legacy_packet"],
            "distractor": ["is_legacy_packet_inverted", "validate_fluxon_packet_empty_v3"],
            "reasoning": 4,
        },
        {
            "name": "merge_valid_checksum",
            "signature": "def solve(packets: list[str]) -> int:",
            "prompts": [
                "Implement solve(packets). Merge all valid packets into a single record and return the checksum of the merged payload using the merged version. If no packet is valid, return 0.",
                "Implement solve(packets). Filter valid packets, merge them, and compute the merged checksum.",
                "Implement solve(packets). Return the checksum of the merged record formed from valid packets only.",
                "Implement solve(packets). Combine valid records and return the merged payload checksum.",
                "Implement solve(packets). Merge valid packets and output the resulting checksum.",
            ],
            "solve_body": 'valid = [parse_fluxon_packet(p) for p in packets if validate_fluxon_packet(p)]\nif not valid:\n    return 0\nmerged = merge_fluxon_records(valid)\nreturn compute_fluxon_checksum(merged["payload"], merged["version"])',
            "make_input": lambda: (make_packet_list(random.randint(1, 4)),),
            "oracle": merge_valid_checksum,
            "gold": ["parse_fluxon_packet", "validate_fluxon_packet", "merge_fluxon_records", "compute_fluxon_checksum"],
            "distractor": ["merge_fluxon_records_wrong_version", "compute_fluxon_checksum_wrong_mod"],
            "reasoning": 4,
        },
        {
            "name": "summarize_valid",
            "signature": "def solve(packets: list[str]) -> dict:",
            "prompts": [
                "Implement solve(packets). Return a summary of only the valid packets using summarize_fluxon_records.",
                "Implement solve(packets). Filter to valid packets and then summarize them.",
                "Implement solve(packets). Summarize the subset of packets that are valid.",
                "Implement solve(packets). Produce a summary dict for the valid packets only.",
                "Implement solve(packets). Validate packets first, then return their summary.",
            ],
            "solve_body": 'valid = [parse_fluxon_packet(p) for p in packets if validate_fluxon_packet(p)]\nreturn summarize_fluxon_records(valid)',
            "make_input": lambda: (make_packet_list(random.randint(0, 5)),),
            "oracle": summarize_valid,
            "gold": ["validate_fluxon_packet", "parse_fluxon_packet", "summarize_fluxon_records"],
            "distractor": ["summarize_fluxon_records_all_records", "validate_fluxon_packet_empty_v3"],
            "reasoning": 4,
        },
        {
            "name": "repair_count_valid",
            "signature": "def solve(packets: list[str]) -> int:",
            "prompts": [
                "Implement solve(packets). Repair each packet and count how many of the repaired packets are valid.",
                "Implement solve(packets). Apply repair to every packet, then count the valid results.",
                "Implement solve(packets). Repair all packets and return the number that become valid.",
                "Implement solve(packets). Fix each packet and count how many pass validation afterwards.",
                "Implement solve(packets). Return the count of valid packets after repair.",
            ],
            "solve_body": 'return sum(1 for p in packets if validate_fluxon_packet(repair_fluxon_packet(p)))',
            "make_input": lambda: (make_packet_list(random.randint(0, 5)),),
            "oracle": repair_count_valid,
            "gold": ["repair_fluxon_packet", "validate_fluxon_packet"],
            "distractor": ["repair_fluxon_packet_no_checksum", "validate_fluxon_batch_any_true"],
            "reasoning": 4,
        },
        {
            "name": "channel_max_normalized",
            "signature": "def solve(packets: list[str]) -> dict[str, float]:",
            "prompts": [
                "Implement solve(packets). For each channel among valid packets, compute the normalized total token value. Return a dictionary mapping channel to its maximum normalized total. Only include channels that appear.",
                "Implement solve(packets). Group valid packets by channel, normalize token sums, and return the max per channel.",
                "Implement solve(packets). Return the highest normalized token sum seen for each channel.",
                "Implement solve(packets). Compute per-channel maxima of normalized token totals for valid packets.",
                "Implement solve(packets). For every channel present, output the maximum normalized total token value.",
            ],
            "solve_body": 'channel_totals = {}\nfor packet in packets:\n    if not validate_fluxon_packet(packet):\n        continue\n    record = parse_fluxon_packet(packet)\n    total = sum(token_value(t) for t in split_fluxon_payload(record["payload"]))\n    norm = normalize_channel_value(total, record["channel"])\n    channel_totals.setdefault(record["channel"], []).append(norm)\nreturn {ch: max(vals) for ch, vals in channel_totals.items()}',
            "make_input": lambda: (make_packet_list(random.randint(1, 6)),),
            "oracle": channel_max_normalized,
            "gold": ["validate_fluxon_packet", "parse_fluxon_packet", "split_fluxon_payload", "token_value", "normalize_channel_value"],
            "distractor": ["normalize_channel_value_swapped", "group_fluxon_by_channel_missing_key"],
            "reasoning": 5,
        },
        {
            "name": "frames_v2_checksums",
            "signature": "def solve(frames: list[str]) -> list[int]:",
            "prompts": [
                "Implement solve(frames). Decode each frame, keep only valid packets with version 2 or higher, and return a list of their checksums in the original order.",
                "Implement solve(frames). Decode frames, filter valid version-2+ packets, and collect checksums.",
                "Implement solve(frames). Return checksums of valid packets with version >= 2 from the frames.",
                "Implement solve(frames). Decode and keep only valid packets whose version is at least 2, returning checksums.",
                "Implement solve(frames). Extract checksums from valid version-2-or-higher packets in the frames.",
            ],
            "solve_body": 'result = []\nfor frame in frames:\n    packet = decode_fluxon_frame(frame)\n    if validate_fluxon_packet(packet):\n        record = parse_fluxon_packet(packet)\n        if record["version"] >= 2:\n            result.append(record["checksum"])\nreturn result',
            "make_input": lambda: (make_frame_list(random.randint(1, 5)),),
            "oracle": frames_v2_checksums,
            "gold": ["decode_fluxon_frame", "validate_fluxon_packet", "parse_fluxon_packet"],
            "distractor": ["decode_fluxon_frame_strip_brackets", "validate_fluxon_packet_empty_v3"],
            "reasoning": 4,
        },
        {
            "name": "all_valid_and_legacy",
            "signature": "def solve(packets: list[str]) -> bool:",
            "prompts": [
                "Implement solve(packets). Return True if all packets are valid and at least one of them is a legacy packet.",
                "Implement solve(packets). Check that every packet is valid and that at least one is version 1.",
                "Implement solve(packets). Return True only when all packets are valid and a legacy packet is present.",
                "Implement solve(packets). Verify all packets are valid and include at least one legacy packet.",
                "Implement solve(packets). True if the packet list is all valid and contains a legacy packet.",
            ],
            "solve_body": 'if not packets:\n    return False\nhas_legacy = False\nfor packet in packets:\n    if not validate_fluxon_packet(packet):\n        return False\n    if is_legacy_packet(packet):\n        has_legacy = True\nreturn has_legacy',
            "make_input": lambda: (make_packet_list(random.randint(0, 4)),),
            "oracle": all_valid_and_legacy,
            "gold": ["validate_fluxon_packet", "is_legacy_packet"],
            "distractor": ["is_legacy_packet_inverted", "validate_fluxon_packet_empty_v3"],
            "reasoning": 4,
        },
        {
            "name": "max_token_sum_alphabeta",
            "signature": "def solve(packets: list[str]) -> str | None:",
            "prompts": [
                "Implement solve(packets). Among valid packets from channel alpha or beta, return the packet string with the largest sum of token values. If there is no such packet, return None. In case of a tie, return the first occurrence.",
                "Implement solve(packets). Find the valid alpha/beta packet with the highest token-sum score.",
                "Implement solve(packets). Return the alpha or beta packet that has the maximum token value sum, or None.",
                "Implement solve(packets). Select the valid alpha/beta packet with the greatest token sum, breaking ties by first appearance.",
                "Implement solve(packets). Return the packet from alpha or beta channels with the largest token value total.",
            ],
            "solve_body": 'best = None\nbest_score = -1\nfor packet in packets:\n    if not validate_fluxon_packet(packet):\n        continue\n    record = parse_fluxon_packet(packet)\n    if record["channel"] not in {"alpha", "beta"}:\n        continue\n    score = sum(token_value(t) for t in split_fluxon_payload(record["payload"]))\n    if score > best_score:\n        best_score = score\n        best = packet\nreturn best',
            "make_input": lambda: (make_packet_list(random.randint(1, 5)),),
            "oracle": max_token_sum_alphabeta,
            "gold": ["validate_fluxon_packet", "parse_fluxon_packet", "split_fluxon_payload", "token_value"],
            "distractor": ["token_value_digit_only", "validate_fluxon_packet_empty_v3"],
            "reasoning": 5,
        },
        {
            "name": "frames_avg_per_channel",
            "signature": "def solve(frames: list[str]) -> dict[str, float]:",
            "prompts": [
                "Implement solve(frames). Decode each frame, keep valid packets, and compute the average normalized token-sum value for each channel. Return a dict mapping channel to average. Only include channels with at least one valid packet.",
                "Implement solve(frames). Per channel, average the normalized token sums of valid framed packets.",
                "Implement solve(frames). Decode frames and return the average normalized token sum per channel.",
                "Implement solve(frames). Group valid framed packets by channel and average their normalized token sums.",
                "Implement solve(frames). Compute channel averages of normalized token sums from valid frames.",
            ],
            "solve_body": 'groups = {}\nfor frame in frames:\n    packet = decode_fluxon_frame(frame)\n    if not validate_fluxon_packet(packet):\n        continue\n    record = parse_fluxon_packet(packet)\n    total = sum(token_value(t) for t in split_fluxon_payload(record["payload"]))\n    norm = normalize_channel_value(total, record["channel"])\n    groups.setdefault(record["channel"], []).append(norm)\nreturn {ch: sum(vals) / len(vals) for ch, vals in groups.items()}',
            "make_input": lambda: (make_frame_list(random.randint(1, 6)),),
            "oracle": frames_avg_per_channel,
            "gold": ["decode_fluxon_frame", "validate_fluxon_packet", "parse_fluxon_packet", "split_fluxon_payload", "token_value", "normalize_channel_value"],
            "distractor": ["decode_fluxon_frame_strip_brackets", "normalize_channel_value_swapped"],
            "reasoning": 5,
        },
    ]

    for spec in specs:
        for variant in range(5):
            task_id = f"fluxon_l3_{len(tasks) + 1:03d}"
            prompt = spec["prompts"][variant % len(spec["prompts"])]
            task = _build_task(
                task_id=task_id,
                level="L3",
                category="composition_reasoning",
                signature=spec["signature"],
                prompt=prompt,
                solve_body=spec["solve_body"],
                make_input=spec["make_input"],
                oracle=spec["oracle"],
                gold_snippets=spec["gold"],
                distractor_snippets=spec["distractor"],
                reasoning_steps=spec["reasoning"],
            )
            tasks.append(task)
    return tasks


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    tasks: list[dict[str, Any]] = []
    tasks.extend(_l1_tasks())
    tasks.extend(_l2_tasks())
    tasks.extend(_l3_tasks())

    by_level: dict[str, list[dict[str, Any]]] = {"L1": [], "L2": [], "L3": []}
    for task in tasks:
        by_level[task["level"]].append(task)

    for level, task_list in by_level.items():
        path = TASKS_DIR / f"fluxon_{level.lower()}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for task in task_list:
                f.write(json.dumps(task, ensure_ascii=False) + "\n")
        print(f"Wrote {len(task_list)} {level} tasks to {path}")

    all_path = TASKS_DIR / "fluxon_all.jsonl"
    with all_path.open("w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")
    print(f"Wrote {len(tasks)} total tasks to {all_path}")


if __name__ == "__main__":
    main()
