"""Generate Quorix tasks for the retrieval-vs-reasoning experiment.

This script produces JSONL task files under ``tasks/`` and reference solution
files under ``solutions/quorix/``. Each task is tagged with a level (L1/L2/L3),
gold/distractor snippet names, visible/hidden tests, and a reference
implementation.
"""

from __future__ import annotations

import importlib.util
import json
import random
import sys
import traceback
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths and random seed
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
LIBS_DIR = ROOT / "libs" / "quorix"
TASKS_DIR = ROOT / "tasks"
SOLUTIONS_DIR = ROOT / "solutions" / "quorix"

TASKS_DIR.mkdir(parents=True, exist_ok=True)
SOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)

random.seed(42)

# ---------------------------------------------------------------------------
# Load the real Quorix library so we can call it while generating tests
# ---------------------------------------------------------------------------

spec = importlib.util.spec_from_file_location("quorix", LIBS_DIR / "quorix.py")
quorix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quorix)


# ---------------------------------------------------------------------------
# Random example generators
# ---------------------------------------------------------------------------

_ROLES = ["intern", "engineer", "manager", "director", "admin"]
_DEPARTMENTS = ["eng", "hr", "sales", "ops", "legal"]
_SENSITIVITIES = ["low", "medium", "high", "critical"]
_ACTIONS = ["read", "write", "delete", "admin"]
_RESOURCE_TYPES = ["doc", "report", "file", "record", "profile", "ledger"]
_CONDITION_FIELDS = ["role", "department", "level", "type", "sensitivity", "owner", "action"]


def _rand_role(exclude: str | None = None) -> str:
    choices = [r for r in _ROLES if r != exclude]
    return random.choice(choices)


def _rand_department(exclude: str | None = None) -> str:
    choices = [d for d in _DEPARTMENTS if d != exclude]
    return random.choice(choices)


def _rand_sensitivity(exclude: str | None = None) -> str:
    choices = [s for s in _SENSITIVITIES if s != exclude]
    return random.choice(choices)


def _rand_action(exclude: str | None = None) -> str:
    choices = [a for a in _ACTIONS if a != exclude]
    return random.choice(choices)


def _rand_resource_type() -> str:
    return random.choice(_RESOURCE_TYPES)


def _rand_level() -> int:
    return random.randint(1, 5)


def _subject(
    role: str | None = None,
    department: str | None = None,
    level: int | None = None,
) -> str:
    return quorix.format_subject(
        role or _rand_role(),
        department or _rand_department(),
        level if level is not None else _rand_level(),
    )


def _resource(
    type: str | None = None,
    sensitivity: str | None = None,
    owner: str | None = None,
) -> str:
    return quorix.format_resource(
        type or _rand_resource_type(),
        sensitivity or _rand_sensitivity(),
        owner or _rand_department(),
    )


def _policy(condition: str | None = None, effect: str | None = None) -> str:
    return quorix.make_policy(
        condition or _rand_simple_condition(),
        effect or random.choice(["allow", "deny"]),
    )


def _rand_simple_condition() -> str:
    """Return a single comparison condition."""
    field = random.choice(_CONDITION_FIELDS)
    if field == "level":
        op = random.choice(["==", "!=", "<", "<=", ">", ">="])
        value = random.randint(1, 5)
        return f"level {op} {value}"
    if field in ("role", "department", "type", "sensitivity", "owner", "action"):
        op = random.choice(["==", "!="])
        value_pool = {
            "role": _ROLES,
            "department": _DEPARTMENTS,
            "type": _RESOURCE_TYPES,
            "sensitivity": _SENSITIVITIES,
            "owner": _DEPARTMENTS,
            "action": _ACTIONS,
        }[field]
        value = random.choice(value_pool)
        return f'{field} {op} "{value}"'
    return 'role == "manager"'


def _rand_compound_condition() -> str:
    c1 = _rand_simple_condition()
    c2 = _rand_simple_condition()
    joiner = random.choice(["and", "or"])
    return f"{c1} {joiner} {c2}"


def _context(subject: str, resource: str, action: str) -> dict[str, Any]:
    s = quorix.parse_subject(subject)
    r = quorix.parse_resource(resource)
    return {
        "role": s["role"],
        "department": s["department"],
        "level": s["level"],
        "type": r["type"],
        "sensitivity": r["sensitivity"],
        "owner": r["owner"],
        "action": action,
    }


# ---------------------------------------------------------------------------
# Task container
# ---------------------------------------------------------------------------

tasks: list[dict[str, Any]] = []


def _quote(s: str) -> str:
    """Escape a string for inclusion in an assert expression."""
    return json.dumps(s)


def _verify_solution(task_id: str, code: str, visible_tests: list[str], hidden_tests: list[str]) -> None:
    """Execute the reference solution and all tests in a fresh namespace.

    Raises RuntimeError if any assertion fails.
    """
    namespace: dict[str, Any] = {}
    for name in dir(quorix):
        if not name.startswith("_"):
            namespace[name] = getattr(quorix, name)
    try:
        exec(code, namespace)
    except Exception as exc:
        raise RuntimeError(f"{task_id}: reference solution failed to compile/exec: {exc}") from exc

    if "solve" not in namespace:
        raise RuntimeError(f"{task_id}: reference solution did not define solve")

    for expr in visible_tests + hidden_tests:
        try:
            exec(expr, namespace)
        except AssertionError as exc:
            raise RuntimeError(f"{task_id}: test failed: {expr}") from exc
        except Exception as exc:
            raise RuntimeError(f"{task_id}: test raised exception: {expr}\n{traceback.format_exc()}") from exc


def add_task(
    task_id: str,
    level: str,
    category: str,
    signature: str,
    prompt: str,
    visible_tests: list[str],
    hidden_tests: list[str],
    gold_snippets: list[str],
    distractor_snippets: list[str],
    reasoning_steps: int,
    reference_code: str,
) -> None:
    _verify_solution(task_id, reference_code, visible_tests, hidden_tests)

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
        "reference_solution_path": f"solutions/quorix/{task_id}.py",
    }
    tasks.append(task)

    solution_path = SOLUTIONS_DIR / f"{task_id}.py"
    solution_path.write_text(reference_code, encoding="utf-8")


# ---------------------------------------------------------------------------
# L1: Direct reuse (10 templates x 5 variants)
# ---------------------------------------------------------------------------


def _l1_subject_field(tid: str, field: str) -> None:
    subject = _subject()
    value = quorix.parse_subject(subject)[field]
    if field == "level":
        expected_repr = str(value)
    else:
        expected_repr = _quote(value)

    fixed_subjects = [
        "role=admin;department=ops;level=5",
        "role=engineer;department=hr;level=2",
        "role=manager;department=sales;level=3",
    ]

    hidden = []
    for sub in fixed_subjects:
        val = quorix.parse_subject(sub)[field]
        hidden.append(f"assert solve({_quote(sub)}) == " + (str(val) if field == "level" else _quote(val)))
    hidden.append("assert solve('role=intern;department=eng;level=1') == " + ("1" if field == "level" else _quote(quorix.parse_subject("role=intern;department=eng;level=1")[field])))
    hidden.append("assert solve('role=director;department=legal;level=5') == " + ("5" if field == "level" else _quote(quorix.parse_subject("role=director;department=legal;level=5")[field])))

    second_subject = "role=intern;department=eng;level=1"
    second_value = quorix.parse_subject(second_subject)[field]
    second_expected = str(second_value) if field == "level" else _quote(second_value)

    add_task(
        task_id=tid,
        level="L1",
        category="direct_reuse",
        signature="def solve(subject: str) -> str:",
        prompt=f"Implement solve(subject). Parse the Quorix subject string and return its '{field}' field.",
        visible_tests=[
            f"assert solve({_quote(subject)}) == {expected_repr}",
            f"assert solve({_quote(second_subject)}) == {second_expected}",
        ],
        hidden_tests=hidden,
        gold_snippets=["parse_subject"],
        distractor_snippets=["parse_subject_missing_level"],
        reasoning_steps=1,
        reference_code=f'''def solve(subject: str) -> str:
    return parse_subject(subject)["{field}"]
''',
    )


def _l1_resource_field(tid: str, field: str) -> None:
    resource = _resource()
    value = quorix.parse_resource(resource)[field]
    expected_repr = _quote(value)

    res2 = _resource()
    val2 = quorix.parse_resource(res2)[field]
    res3 = _resource(sensitivity="critical")
    val3 = quorix.parse_resource(res3)[field]

    second_resource = "type=report;sensitivity=high;owner=hr"
    second_expected = _quote(quorix.parse_resource(second_resource)[field])

    add_task(
        task_id=tid,
        level="L1",
        category="direct_reuse",
        signature="def solve(resource: str) -> str:",
        prompt=f"Implement solve(resource). Parse the Quorix resource string and return its '{field}' field.",
        visible_tests=[
            f"assert solve({_quote(resource)}) == {expected_repr}",
            f"assert solve({_quote(second_resource)}) == {second_expected}",
        ],
        hidden_tests=[
            f"assert solve({_quote(res2)}) == {_quote(val2)}",
            f"assert solve({_quote(res3)}) == {_quote(val3)}",
            "assert solve('type=ledger;sensitivity=low;owner=ops') == " + _quote(quorix.parse_resource("type=ledger;sensitivity=low;owner=ops")[field]),
            "assert solve('type=file;sensitivity=critical;owner=sales') == " + _quote(quorix.parse_resource("type=file;sensitivity=critical;owner=sales")[field]),
            "assert solve('type=profile;sensitivity=medium;owner=legal') == " + _quote(quorix.parse_resource("type=profile;sensitivity=medium;owner=legal")[field]),
        ],
        gold_snippets=["parse_resource"],
        distractor_snippets=["parse_resource_wrong_sensitivity"],
        reasoning_steps=1,
        reference_code=f'''def solve(resource: str) -> str:
    return parse_resource(resource)["{field}"]
''',
    )


def _l1_policy_field(tid: str, field: str) -> None:
    policy = _policy()
    value = quorix.parse_policy(policy)[field]
    expected_repr = _quote(value)

    pol2 = _policy()
    pol3 = '(level >= 3 and role == "manager") -> deny'

    second_policy = '(role == "admin") -> allow'
    second_expected = _quote(quorix.parse_policy(second_policy)[field])

    add_task(
        task_id=tid,
        level="L1",
        category="direct_reuse",
        signature="def solve(policy: str) -> str:",
        prompt=f"Implement solve(policy). Parse the Quorix policy string and return its '{field}' part (condition or effect).",
        visible_tests=[
            f"assert solve({_quote(policy)}) == {expected_repr}",
            f"assert solve({_quote(second_policy)}) == {second_expected}",
        ],
        hidden_tests=[
            f"assert solve({_quote(pol2)}) == {_quote(quorix.parse_policy(pol2)[field])}",
            f"assert solve({_quote(pol3)}) == {_quote(quorix.parse_policy(pol3)[field])}",
            'assert solve(\'(sensitivity == "critical") -> deny\') == ' + _quote(quorix.parse_policy('(sensitivity == "critical") -> deny')[field]),
            'assert solve(\'(action == "delete") -> deny\') == ' + _quote(quorix.parse_policy('(action == "delete") -> deny')[field]),
            'assert solve(\'(department == owner) -> allow\') == ' + _quote(quorix.parse_policy('(department == owner) -> allow')[field]),
        ],
        gold_snippets=["parse_policy"],
        distractor_snippets=["parse_policy_inverted_effect"],
        reasoning_steps=1,
        reference_code=f'''def solve(policy: str) -> str:
    return parse_policy(policy)["{field}"]
''',
    )


def _l1_evaluate_condition(tid: str) -> None:
    subject = _subject()
    resource = _resource()
    action = _rand_action()
    ctx = _context(subject, resource, action)
    condition = _rand_simple_condition()
    expected = quorix.evaluate_condition(condition, ctx)

    second_condition = 'role == "manager"'
    second_ctx = {"role": "manager", "level": 3}
    second_expected = quorix.evaluate_condition(second_condition, second_ctx)

    add_task(
        task_id=tid,
        level="L1",
        category="direct_reuse",
        signature="def solve(condition: str, context: dict) -> bool:",
        prompt="Implement solve(condition, context). Evaluate the given Quorix condition string against the provided context dictionary and return the boolean result.",
        visible_tests=[
            f"assert solve({_quote(condition)}, {ctx}) is {expected}",
            f"assert solve({_quote(second_condition)}, {second_ctx}) is {second_expected}",
        ],
        hidden_tests=[
            f"assert solve({_quote('level >= 4')}, {{'role': 'engineer', 'level': 2}}) is False",
            f"assert solve({_quote('sensitivity == \"high\"')}, {{'sensitivity': 'high', 'action': 'read'}}) is True",
            f"assert solve({_quote('department == \"hr\"')}, {{'department': 'eng', 'owner': 'hr'}}) is False",
            f"assert solve({_quote('action != \"delete\"')}, {{'action': 'read'}}) is True",
            f"assert solve({_quote('level == 5')}, {{'level': 5, 'role': 'admin'}}) is True",
        ],
        gold_snippets=["evaluate_condition"],
        distractor_snippets=["evaluate_condition_or_instead_of_and"],
        reasoning_steps=1,
        reference_code='''def solve(condition: str, context: dict) -> bool:
    return evaluate_condition(condition, context)
''',
    )


def _l1_authorize(tid: str) -> None:
    subject = _subject()
    resource = _resource()
    action = _rand_action()
    policies = [_policy() for _ in range(random.randint(1, 3))]
    expected = quorix.authorize(subject, resource, action, policies)

    second_subject = "role=engineer;department=eng;level=2"
    second_resource = "type=report;sensitivity=medium;owner=eng"
    second_action = "read"
    second_policies = ['(department == owner) -> allow']
    second_expected = quorix.authorize(second_subject, second_resource, second_action, second_policies)

    add_task(
        task_id=tid,
        level="L1",
        category="direct_reuse",
        signature="def solve(subject: str, resource: str, action: str, policies: list[str]) -> bool:",
        prompt="Implement solve(subject, resource, action, policies). Use the Quorix authorization engine to decide whether the action is allowed.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {_quote(resource)}, {_quote(action)}, {policies}) is {expected}",
            f"assert solve({_quote(second_subject)}, {_quote(second_resource)}, {_quote(second_action)}, {second_policies}) is {second_expected}",
        ],
        hidden_tests=[
            f"assert solve({_quote(_subject(role='admin'))}, {_quote(_resource())}, 'read', ['(role == \"admin\") -> allow']) is True",
            f"assert solve({_quote(_subject(role='intern'))}, {_quote(_resource(sensitivity='critical'))}, 'write', ['(role == \"manager\") -> allow', '(sensitivity == \"critical\") -> deny']) is False",
            "assert solve('role=manager;department=sales;level=4', 'type=doc;sensitivity=high;owner=hr', 'delete', ['(level >= 5) -> allow']) is False",
            "assert solve('role=director;department=legal;level=5', 'type=ledger;sensitivity=critical;owner=legal', 'admin', ['(role == \"admin\") -> allow']) is False",
            "assert solve('role=admin;department=ops;level=5', 'type=file;sensitivity=low;owner=ops', 'delete', ['(role == \"admin\") -> allow']) is True",
        ],
        gold_snippets=["authorize", "parse_subject", "parse_resource", "parse_policy"],
        distractor_snippets=["authorize_allow_all", "authorize_deny_all"],
        reasoning_steps=1,
        reference_code='''def solve(subject: str, resource: str, action: str, policies: list[str]) -> bool:
    return authorize(subject, resource, action, policies)
''',
    )


def _l1_resolve_policies(tid: str) -> None:
    policies = [_policy() for _ in range(random.randint(2, 4))]
    ordered = quorix.resolve_policies(policies)
    expected = [p["effect"] for p in ordered]

    second_policies = ['(role == "admin") -> allow', '(sensitivity == "critical") -> deny']
    second_expected = [p["effect"] for p in quorix.resolve_policies(second_policies)]

    add_task(
        task_id=tid,
        level="L1",
        category="direct_reuse",
        signature="def solve(policies: list[str]) -> list[str]:",
        prompt="Implement solve(policies). Sort the Quorix policies so that deny policies come before allow policies, and return the list of effects in order.",
        visible_tests=[
            f"assert solve({policies}) == {expected}",
            f"assert solve({second_policies}) == {second_expected}",
        ],
        hidden_tests=[
            "assert solve(['(action == \"read\") -> allow']) == ['allow']",
            "assert solve([]) == []",
            "assert solve(['(level >= 3) -> deny', '(department == \"eng\") -> deny', '(role == \"intern\") -> allow']) == ['deny', 'deny', 'allow']",
            "assert solve(['(owner == \"hr\") -> allow', '(type == \"doc\") -> deny']) == ['deny', 'allow']",
            "assert solve(['(role == \"manager\") -> deny', '(role == \"engineer\") -> allow']) == ['deny', 'allow']",
        ],
        gold_snippets=["resolve_policies", "parse_policy"],
        distractor_snippets=["resolve_policies_allow_first"],
        reasoning_steps=1,
        reference_code='''def solve(policies: list[str]) -> list[str]:
    return [p["effect"] for p in resolve_policies(policies)]
''',
    )


def _l1_audit_access(tid: str) -> None:
    subject = _subject()
    resource = _resource()
    action = _rand_action()
    decision = random.choice([True, False])
    expected = quorix.audit_access(subject, resource, action, decision)

    second_subject = "role=admin;department=ops;level=5"
    second_resource = "type=report;sensitivity=high;owner=ops"
    second_action = "read"
    second_decision = True
    second_expected = quorix.audit_access(second_subject, second_resource, second_action, second_decision)

    add_task(
        task_id=tid,
        level="L1",
        category="direct_reuse",
        signature="def solve(subject: str, resource: str, action: str, decision: bool) -> str:",
        prompt="Implement solve(subject, resource, action, decision). Generate the Quorix audit log string for the access attempt.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {_quote(resource)}, {_quote(action)}, {decision}) == {_quote(expected)}",
            f"assert solve({_quote(second_subject)}, {_quote(second_resource)}, {_quote(second_action)}, {second_decision}) == {_quote(second_expected)}",
        ],
        hidden_tests=[
            "assert 'DENY' in solve('role=intern;department=eng;level=1', 'type=doc;sensitivity=medium;owner=hr', 'write', False)",
            "assert 'engineer' in solve('role=engineer;department=eng;level=2', 'type=file;sensitivity=low;owner=eng', 'read', True)",
            "assert 'manager' in solve('role=manager;department=sales;level=4', 'type=ledger;sensitivity=critical;owner=sales', 'delete', False)",
            "assert solve('role=director;department=legal;level=5', 'type=profile;sensitivity=high;owner=legal', 'admin', True).endswith('ALLOW')",
            "assert solve('role=intern;department=hr;level=1', 'type=report;sensitivity=low;owner=hr', 'read', False).endswith('DENY')",
        ],
        gold_snippets=["audit_access"],
        distractor_snippets=["audit_access_no_decision"],
        reasoning_steps=1,
        reference_code='''def solve(subject: str, resource: str, action: str, decision: bool) -> str:
    return audit_access(subject, resource, action, decision)
''',
    )


def _l1_suggest_role(tid: str) -> None:
    actions = [random.choice(_ACTIONS) for _ in range(random.randint(2, 5))]
    history = [{"action": a} for a in actions]
    expected = quorix.suggest_role(history)

    second_history = [{"action": "read"}, {"action": "read"}, {"action": "write"}]
    second_expected = quorix.suggest_role(second_history)

    add_task(
        task_id=tid,
        level="L1",
        category="direct_reuse",
        signature="def solve(history: list[dict]) -> str:",
        prompt="Implement solve(history). Suggest a Quorix role based on the most frequent action in the access history.",
        visible_tests=[
            f"assert solve({history}) == {_quote(expected)}",
            f"assert solve({second_history}) == {_quote(second_expected)}",
        ],
        hidden_tests=[
            "assert solve([]) == 'intern'",
            "assert solve([{'action': 'write'}, {'action': 'write'}, {'action': 'delete'}]) == 'manager'",
            "assert solve([{'action': 'delete'}, {'action': 'delete'}, {'action': 'admin'}]) == 'admin'",
            "assert solve([{'action': 'admin'}, {'action': 'admin'}, {'action': 'read'}]) == 'director'",
            "assert solve([{'action': 'read'}, {'action': 'write'}, {'action': 'write'}]) == 'manager'",
        ],
        gold_snippets=["suggest_role"],
        distractor_snippets=["suggest_role_inverted_mapping"],
        reasoning_steps=1,
        reference_code='''def solve(history: list[dict]) -> str:
    return suggest_role(history)
''',
    )


def _l1_format_entity(tid: str, entity: str) -> None:
    if entity == "subject":
        role = _rand_role()
        dept = _rand_department()
        level = _rand_level()
        expected = quorix.format_subject(role, dept, level)
        prompt = "Implement solve(role, department, level). Format the inputs as a valid Quorix subject string."
        signature = "def solve(role: str, department: str, level: int) -> str:"
        visible = f"assert solve({_quote(role)}, {_quote(dept)}, {level}) == {_quote(expected)}"
        hidden = [
            "assert solve('intern', 'eng', 1) == 'role=intern;department=eng;level=1'",
            "assert solve('admin', 'ops', 5) == 'role=admin;department=ops;level=5'",
            "assert solve('manager', 'sales', 3) == 'role=manager;department=sales;level=3'",
            "assert solve('director', 'legal', 4) == 'role=director;department=legal;level=4'",
            "assert solve('engineer', 'hr', 2) == 'role=engineer;department=hr;level=2'",
            "assert solve('intern', 'sales', 1) == 'role=intern;department=sales;level=1'",
        ]
        code = '''def solve(role: str, department: str, level: int) -> str:
    return format_subject(role, department, level)
'''
        distractor = "format_subject_missing_level"
    else:
        type_ = _rand_resource_type()
        sens = _rand_sensitivity()
        owner = _rand_department()
        expected = quorix.format_resource(type_, sens, owner)
        prompt = "Implement solve(type, sensitivity, owner). Format the inputs as a valid Quorix resource string."
        signature = "def solve(type: str, sensitivity: str, owner: str) -> str:"
        visible = f"assert solve({_quote(type_)}, {_quote(sens)}, {_quote(owner)}) == {_quote(expected)}"
        hidden = [
            "assert solve('report', 'high', 'hr') == 'type=report;sensitivity=high;owner=hr'",
            "assert solve('doc', 'low', 'eng') == 'type=doc;sensitivity=low;owner=eng'",
            "assert solve('file', 'critical', 'ops') == 'type=file;sensitivity=critical;owner=ops'",
            "assert solve('profile', 'medium', 'sales') == 'type=profile;sensitivity=medium;owner=sales'",
            "assert solve('ledger', 'high', 'legal') == 'type=ledger;sensitivity=high;owner=legal'",
            "assert solve('record', 'low', 'ops') == 'type=record;sensitivity=low;owner=ops'",
        ]
        code = '''def solve(type: str, sensitivity: str, owner: str) -> str:
    return format_resource(type, sensitivity, owner)
'''
        distractor = "format_resource_wrong_sensitivity"

    visible_tests = [
        visible,
        hidden[0],
    ]

    add_task(
        task_id=tid,
        level="L1",
        category="direct_reuse",
        signature=signature,
        prompt=prompt,
        visible_tests=visible_tests,
        hidden_tests=hidden[1:],
        gold_snippets=[f"format_{entity}"],
        distractor_snippets=[distractor],
        reasoning_steps=1,
        reference_code=code,
    )


def _l1_check_property(tid: str, helper: str) -> None:
    """Helper is one of: is_admin, is_sensitive, action_priority, subject_has_role,
    subject_level_at_least, resource_owned_by."""
    if helper == "is_admin":
        subject = _subject(role="admin")
        expected = True
        sig = "def solve(subject: str) -> bool:"
        prompt = "Implement solve(subject). Return True if the subject has the admin role."
        code = '''def solve(subject: str) -> bool:
    return is_admin(subject)
'''
        hidden = [
            "assert solve('role=admin;department=ops;level=5') is True",
            "assert solve('role=engineer;department=eng;level=2') is False",
            "assert solve('role=manager;department=sales;level=4') is False",
            "assert solve('role=director;department=legal;level=5') is False",
            "assert solve('role=intern;department=hr;level=1') is False",
        ]
        distractor = "is_admin_inverted"
    elif helper == "is_sensitive":
        resource = _resource(sensitivity="high")
        sig = "def solve(resource: str) -> bool:"
        prompt = "Implement solve(resource). Return True if the resource sensitivity is at least 'medium'."
        code = '''def solve(resource: str) -> bool:
    return is_sensitive(resource, "medium")
'''
        expected = quorix.is_sensitive(resource, "medium")
        hidden = [
            "assert solve('type=report;sensitivity=low;owner=eng') is False",
            "assert solve('type=report;sensitivity=medium;owner=eng') is True",
            "assert solve('type=report;sensitivity=high;owner=eng') is True",
            "assert solve('type=report;sensitivity=critical;owner=eng') is True",
            "assert solve('type=doc;sensitivity=low;owner=hr') is False",
        ]
        distractor = "is_sensitive_wrong_threshold"
    elif helper == "action_priority":
        action = "delete"
        sig = "def solve(action: str) -> int:"
        prompt = "Implement solve(action). Return the Quorix priority value for the given action."
        code = '''def solve(action: str) -> int:
    return action_priority(action)
'''
        expected = quorix.action_priority(action)
        hidden = [
            "assert solve('read') == 1",
            "assert solve('write') == 2",
            "assert solve('delete') == 3",
            "assert solve('admin') == 4",
            "assert solve('write') > solve('read')",
        ]
        distractor = "action_priority_swapped"
    elif helper == "subject_has_role":
        role = _rand_role()
        subject = _subject(role=role)
        sig = "def solve(subject: str, role: str) -> bool:"
        prompt = "Implement solve(subject, role). Return True if the subject's role equals the given role."
        code = '''def solve(subject: str, role: str) -> bool:
    return subject_has_role(subject, role)
'''
        expected = True
        hidden = [
            "assert solve('role=manager;department=eng;level=3', 'manager') is True",
            "assert solve('role=engineer;department=hr;level=2', 'manager') is False",
            "assert solve('role=admin;department=ops;level=5', 'admin') is True",
            "assert solve('role=intern;department=sales;level=1', 'director') is False",
            "assert solve('role=director;department=legal;level=5', 'director') is True",
        ]
        distractor = "subject_has_role_case_insensitive"
    elif helper == "subject_level_at_least":
        subject = _subject(level=4)
        min_level = 3
        sig = "def solve(subject: str, min_level: int) -> bool:"
        prompt = "Implement solve(subject, min_level). Return True if the subject's level is at least min_level."
        code = '''def solve(subject: str, min_level: int) -> bool:
    return subject_level_at_least(subject, min_level)
'''
        expected = True
        hidden = [
            "assert solve('role=manager;department=eng;level=3', 3) is True",
            "assert solve('role=intern;department=eng;level=1', 2) is False",
            "assert solve('role=director;department=legal;level=5', 5) is True",
            "assert solve('role=engineer;department=hr;level=2', 3) is False",
            "assert solve('role=admin;department=ops;level=5', 4) is True",
        ]
        distractor = "subject_level_at_least_off_by_one"
    else:  # resource_owned_by
        owner = _rand_department()
        resource = _resource(owner=owner)
        sig = "def solve(resource: str, department: str) -> bool:"
        prompt = "Implement solve(resource, department). Return True if the resource is owned by the given department."
        code = '''def solve(resource: str, department: str) -> bool:
    return resource_owned_by(resource, department)
'''
        expected = True
        hidden = [
            "assert solve('type=report;sensitivity=high;owner=eng', 'eng') is True",
            "assert solve('type=report;sensitivity=high;owner=hr', 'eng') is False",
            "assert solve('type=doc;sensitivity=low;owner=sales', 'sales') is True",
            "assert solve('type=file;sensitivity=critical;owner=ops', 'legal') is False",
            "assert solve('type=ledger;sensitivity=medium;owner=legal', 'legal') is True",
        ]
        distractor = "resource_owned_by_inverted"

    # Build two visible tests carefully to avoid referencing unbound variables.
    if helper == "subject_has_role":
        visible_tests = [
            f"assert solve({_quote(subject)}, {_quote(role)}) is {expected}",
            "assert solve('role=engineer;department=hr;level=2', 'manager') is False",
        ]
    elif helper == "subject_level_at_least":
        visible_tests = [
            f"assert solve({_quote(subject)}, {min_level}) is {expected}",
            "assert solve('role=intern;department=eng;level=1', 2) is False",
        ]
    elif helper == "resource_owned_by":
        visible_tests = [
            f"assert solve({_quote(resource)}, {_quote(owner)}) is {expected}",
            "assert solve('type=report;sensitivity=high;owner=hr', 'eng') is False",
        ]
    elif helper == "is_admin":
        visible_tests = [
            f"assert solve({_quote(subject)}) is {expected}",
            "assert solve('role=engineer;department=eng;level=2') is False",
        ]
    elif helper == "is_sensitive":
        visible_tests = [
            f"assert solve({_quote(resource)}) is {expected}",
            "assert solve('type=report;sensitivity=low;owner=eng') is False",
        ]
    elif helper == "action_priority":
        visible_tests = [
            f"assert solve({_quote(action)}) == {expected}",
            "assert solve('read') == 1",
        ]
    else:
        visible_tests = []

    add_task(
        task_id=tid,
        level="L1",
        category="direct_reuse",
        signature=sig,
        prompt=prompt,
        visible_tests=visible_tests,
        hidden_tests=hidden,
        gold_snippets=[helper],
        distractor_snippets=[distractor],
        reasoning_steps=1,
        reference_code=code,
    )


def _l1_count_matching_policies(tid: str) -> None:
    subject = _subject()
    resource = _resource()
    action = _rand_action()
    policies = [_policy() for _ in range(random.randint(1, 3))]
    expected = quorix.count_matching_policies(subject, resource, action, policies)

    second_subject = "role=admin;department=ops;level=5"
    second_resource = "type=doc;sensitivity=low;owner=ops"
    second_action = "admin"
    second_policies = ['(role == "admin") -> allow']
    second_expected = quorix.count_matching_policies(second_subject, second_resource, second_action, second_policies)

    add_task(
        task_id=tid,
        level="L1",
        category="direct_reuse",
        signature="def solve(subject: str, resource: str, action: str, policies: list[str]) -> int:",
        prompt="Implement solve(subject, resource, action, policies). Count how many of the policies match the given subject, resource, and action.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {_quote(resource)}, {_quote(action)}, {policies}) == {expected}",
            f"assert solve({_quote(second_subject)}, {_quote(second_resource)}, {_quote(second_action)}, {second_policies}) == {second_expected}",
        ],
        hidden_tests=[
            "assert solve('role=intern;department=hr;level=1', 'type=file;sensitivity=critical;owner=sales', 'write', ['(level >= 2) -> allow']) == 0",
            "assert solve('role=engineer;department=eng;level=2', 'type=report;sensitivity=medium;owner=eng', 'read', []) == 0",
            "assert solve('role=director;department=legal;level=5', 'type=ledger;sensitivity=high;owner=legal', 'delete', ['(level >= 4) -> allow', '(action == \"delete\") -> allow', '(owner == \"hr\") -> deny']) == 2",
            "assert solve('role=manager;department=sales;level=3', 'type=file;sensitivity=medium;owner=sales', 'write', ['(role == \"manager\") -> allow', '(department == owner) -> allow']) == 2",
            "assert solve('role=intern;department=eng;level=1', 'type=report;sensitivity=low;owner=eng', 'read', ['(role == \"manager\") -> allow', '(level >= 2) -> allow']) == 0",
        ],
        gold_snippets=["count_matching_policies", "parse_subject", "parse_resource", "parse_policy", "evaluate_condition"],
        distractor_snippets=["count_matching_policies_ignore_effect"],
        reasoning_steps=1,
        reference_code='''def solve(subject: str, resource: str, action: str, policies: list[str]) -> int:
    return count_matching_policies(subject, resource, action, policies)
''',
    )


def _l1_list_allowed_actions(tid: str) -> None:
    subject = _subject(role="admin")
    resource = _resource()
    policies = ['(role == "admin") -> allow']
    expected = quorix.list_allowed_actions(subject, resource, policies)

    second_subject = "role=intern;department=eng;level=1"
    second_resource = "type=doc;sensitivity=low;owner=eng"
    second_policies = ['(role == "admin") -> allow']
    second_expected = quorix.list_allowed_actions(second_subject, second_resource, second_policies)

    add_task(
        task_id=tid,
        level="L1",
        category="direct_reuse",
        signature="def solve(subject: str, resource: str, policies: list[str]) -> list[str]:",
        prompt="Implement solve(subject, resource, policies). Return the list of actions that the Quorix engine allows for the subject on the resource.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {_quote(resource)}, {policies}) == {expected}",
            f"assert solve({_quote(second_subject)}, {_quote(second_resource)}, {second_policies}) == {second_expected}",
        ],
        hidden_tests=[
            "assert solve('role=manager;department=sales;level=3', 'type=file;sensitivity=medium;owner=sales', ['(level >= 3) -> allow']) == ['read', 'write', 'delete', 'admin']",
            "assert solve('role=engineer;department=hr;level=2', 'type=ledger;sensitivity=high;owner=hr', ['(action == \"read\") -> allow', '(action == \"write\") -> deny']) == ['read']",
            "assert solve('role=director;department=legal;level=5', 'type=profile;sensitivity=critical;owner=legal', []) == []",
            "assert solve('role=admin;department=ops;level=5', 'type=report;sensitivity=high;owner=ops', ['(role == \"admin\") -> allow', '(action == \"admin\") -> deny']) == ['read', 'write', 'delete']",
            "assert solve('role=manager;department=eng;level=3', 'type=file;sensitivity=low;owner=hr', ['(department == owner) -> allow']) == []",
        ],
        gold_snippets=["list_allowed_actions", "authorize"],
        distractor_snippets=["list_allowed_actions_all_actions"],
        reasoning_steps=1,
        reference_code='''def solve(subject: str, resource: str, policies: list[str]) -> list[str]:
    return list_allowed_actions(subject, resource, policies)
''',
    )


def _l1_make_policy(tid: str) -> None:
    condition = _rand_simple_condition()
    effect = random.choice(["allow", "deny"])
    expected = quorix.make_policy(condition, effect)

    second_condition = 'role == "manager"'
    second_effect = "allow"
    second_expected = quorix.make_policy(second_condition, second_effect)

    add_task(
        task_id=tid,
        level="L1",
        category="direct_reuse",
        signature="def solve(condition: str, effect: str) -> str:",
        prompt="Implement solve(condition, effect). Format the condition and effect as a valid Quorix policy string.",
        visible_tests=[
            f"assert solve({_quote(condition)}, {_quote(effect)}) == {_quote(expected)}",
            f"assert solve({_quote(second_condition)}, {_quote(second_effect)}) == {_quote(second_expected)}",
        ],
        hidden_tests=[
            'assert solve(\'sensitivity == "critical"\', "deny") == \'(sensitivity == "critical") -> deny\'',
            'assert solve(\'level >= 3\', "allow") == \'(level >= 3) -> allow\'',
            'assert solve(\'action == "delete"\', "deny") == \'(action == "delete") -> deny\'',
            'assert solve(\'department == owner\', "allow") == \'(department == owner) -> allow\'',
            'assert solve(\'role == "admin"\', "deny") == \'(role == "admin") -> deny\'',
        ],
        gold_snippets=["make_policy"],
        distractor_snippets=["make_policy_inverted_effect"],
        reasoning_steps=1,
        reference_code='''def solve(condition: str, effect: str) -> str:
    return make_policy(condition, effect)
''',
    )


def l1_tasks() -> None:
    counter = 1
    # Subject fields
    for field in ["role", "department", "level"]:
        for _ in range(2):
            _l1_subject_field(f"quorix_l1_{counter:03d}", field)
            counter += 1
    # Resource fields
    for field in ["type", "sensitivity", "owner"]:
        for _ in range(2):
            _l1_resource_field(f"quorix_l1_{counter:03d}", field)
            counter += 1
    # Policy fields
    for field in ["condition", "effect"]:
        for _ in range(2):
            _l1_policy_field(f"quorix_l1_{counter:03d}", field)
            counter += 1
    # Evaluate condition
    for _ in range(3):
        _l1_evaluate_condition(f"quorix_l1_{counter:03d}")
        counter += 1
    # Authorize
    for _ in range(5):
        _l1_authorize(f"quorix_l1_{counter:03d}")
        counter += 1
    # Resolve policies
    for _ in range(3):
        _l1_resolve_policies(f"quorix_l1_{counter:03d}")
        counter += 1
    # Audit access
    for _ in range(3):
        _l1_audit_access(f"quorix_l1_{counter:03d}")
        counter += 1
    # Suggest role
    for _ in range(4):
        _l1_suggest_role(f"quorix_l1_{counter:03d}")
        counter += 1
    # Format subject/resource
    for entity in ["subject", "resource"]:
        for _ in range(2):
            _l1_format_entity(f"quorix_l1_{counter:03d}", entity)
            counter += 1
    # Check property
    for helper in ["is_admin", "is_sensitive", "action_priority", "subject_has_role", "subject_level_at_least", "resource_owned_by"]:
        _l1_check_property(f"quorix_l1_{counter:03d}", helper)
        counter += 1
    # Count matching policies
    for _ in range(2):
        _l1_count_matching_policies(f"quorix_l1_{counter:03d}")
        counter += 1
    # List allowed actions
    for _ in range(2):
        _l1_list_allowed_actions(f"quorix_l1_{counter:03d}")
        counter += 1
    # Make policy
    for _ in range(2):
        _l1_make_policy(f"quorix_l1_{counter:03d}")
        counter += 1


# ---------------------------------------------------------------------------
# L2: Adaptive modification (10 templates x 5 variants)
# ---------------------------------------------------------------------------


def _l2_check_role_and_level(tid: str) -> None:
    role = _rand_role()
    min_level = random.randint(2, 4)
    subject_ok = _subject(role=role, level=min_level)
    subject_bad_role = _subject(role=_rand_role(exclude=role), level=min_level)
    subject_bad_level = _subject(role=role, level=min_level - 1)

    add_task(
        task_id=tid,
        level="L2",
        category="adaptive_modification",
        signature="def solve(subject: str, required_role: str, min_level: int) -> bool:",
        prompt="Implement solve(subject, required_role, min_level). Return True if the subject has the required role and a level at least min_level.",
        visible_tests=[
            f"assert solve({_quote(subject_ok)}, {_quote(role)}, {min_level}) is True",
            f"assert solve({_quote(subject_bad_role)}, {_quote(role)}, {min_level}) is False",
        ],
        hidden_tests=[
            f"assert solve({_quote(subject_bad_level)}, {_quote(role)}, {min_level}) is False",
            "assert solve('role=manager;department=eng;level=3', 'manager', 3) is True",
            "assert solve('role=manager;department=eng;level=2', 'manager', 3) is False",
            "assert solve('role=engineer;department=hr;level=4', 'manager', 3) is False",
            "assert solve('role=director;department=legal;level=5', 'director', 4) is True",
        ],
        gold_snippets=["subject_has_role", "subject_level_at_least", "parse_subject"],
        distractor_snippets=["subject_has_role_case_insensitive", "subject_level_at_least_off_by_one"],
        reasoning_steps=2,
        reference_code='''def solve(subject: str, required_role: str, min_level: int) -> bool:
    return subject_has_role(subject, required_role) and subject_level_at_least(subject, min_level)
''',
    )


def _l2_check_department_match(tid: str) -> None:
    dept = _rand_department()
    subject = _subject(department=dept)
    resource = _resource(owner=dept)
    resource_other = _resource(owner=_rand_department(exclude=dept))

    add_task(
        task_id=tid,
        level="L2",
        category="adaptive_modification",
        signature="def solve(subject: str, resource: str) -> bool:",
        prompt="Implement solve(subject, resource). Return True if the subject's department matches the resource's owner department.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {_quote(resource)}) is True",
            f"assert solve({_quote(subject)}, {_quote(resource_other)}) is False",
        ],
        hidden_tests=[
            "assert solve('role=engineer;department=eng;level=2', 'type=report;sensitivity=medium;owner=eng') is True",
            "assert solve('role=engineer;department=eng;level=2', 'type=report;sensitivity=medium;owner=hr') is False",
            "assert solve('role=manager;department=sales;level=3', 'type=doc;sensitivity=low;owner=sales') is True",
            "assert solve('role=intern;department=hr;level=1', 'type=file;sensitivity=high;owner=ops') is False",
            "assert solve('role=admin;department=ops;level=5', 'type=ledger;sensitivity=critical;owner=ops') is True",
        ],
        gold_snippets=["parse_subject", "parse_resource"],
        distractor_snippets=["parse_subject_missing_level", "parse_resource_wrong_sensitivity"],
        reasoning_steps=2,
        reference_code='''def solve(subject: str, resource: str) -> bool:
    return parse_subject(subject)["department"] == parse_resource(resource)["owner"]
''',
    )


def _l2_authorize_with_default(tid: str) -> None:
    subject = _subject()
    resource = _resource()
    action = _rand_action()
    policies = ['(role == "ghost") -> allow']

    second_subject = "role=intern;department=eng;level=1"
    second_resource = "type=report;sensitivity=high;owner=hr"
    second_action = "read"
    second_policies = ['(role == "intern") -> deny']
    second_expected = quorix.authorize(second_subject, second_resource, second_action, second_policies, default=True)

    add_task(
        task_id=tid,
        level="L2",
        category="adaptive_modification",
        signature="def solve(subject: str, resource: str, action: str, policies: list[str]) -> bool:",
        prompt="Implement solve(subject, resource, action, policies). Use Quorix authorization with a default decision of True when no policy matches.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {_quote(resource)}, {_quote(action)}, {policies}) is True",
            f"assert solve({_quote(second_subject)}, {_quote(second_resource)}, {_quote(second_action)}, {second_policies}) is {second_expected}",
        ],
        hidden_tests=[
            "assert solve('role=intern;department=eng;level=1', 'type=report;sensitivity=high;owner=hr', 'read', ['(role == \"manager\") -> allow']) is True",
            "assert solve('role=admin;department=ops;level=5', 'type=doc;sensitivity=low;owner=ops', 'delete', []) is True",
            "assert solve('role=manager;department=sales;level=3', 'type=file;sensitivity=medium;owner=sales', 'write', ['(sensitivity == \"critical\") -> deny']) is True",
            "assert solve('role=engineer;department=hr;level=2', 'type=ledger;sensitivity=critical;owner=hr', 'admin', ['(sensitivity == \"critical\") -> deny']) is False",
            "assert solve('role=director;department=legal;level=5', 'type=profile;sensitivity=high;owner=legal', 'read', ['(role == \"admin\") -> allow']) is True",
        ],
        gold_snippets=["authorize", "parse_policy"],
        distractor_snippets=["authorize_allow_all", "authorize_deny_all"],
        reasoning_steps=2,
        reference_code='''def solve(subject: str, resource: str, action: str, policies: list[str]) -> bool:
    return authorize(subject, resource, action, policies, default=True)
''',
    )


def _l2_authorize_and_audit(tid: str) -> None:
    subject = _subject()
    resource = _resource()
    action = _rand_action()
    policies = [_policy() for _ in range(random.randint(1, 2))]
    decision = quorix.authorize(subject, resource, action, policies)
    log = quorix.audit_access(subject, resource, action, decision)

    second_subject = "role=admin;department=ops;level=5"
    second_resource = "type=report;sensitivity=high;owner=ops"
    second_action = "read"
    second_policies = ['(role == "admin") -> allow']
    second_log = quorix.audit_access(second_subject, second_resource, second_action, quorix.authorize(second_subject, second_resource, second_action, second_policies))

    add_task(
        task_id=tid,
        level="L2",
        category="adaptive_modification",
        signature="def solve(subject: str, resource: str, action: str, policies: list[str]) -> str:",
        prompt="Implement solve(subject, resource, action, policies). Authorize the action and return the corresponding audit log string.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {_quote(resource)}, {_quote(action)}, {policies}) == {_quote(log)}",
            f"assert solve({_quote(second_subject)}, {_quote(second_resource)}, {_quote(second_action)}, {second_policies}) == {_quote(second_log)}",
        ],
        hidden_tests=[
            "assert 'DENY' in solve('role=intern;department=eng;level=1', 'type=doc;sensitivity=medium;owner=hr', 'write', ['(level >= 3) -> allow'])",
            "assert 'manager' in solve('role=manager;department=sales;level=3', 'type=file;sensitivity=low;owner=sales', 'read', ['(department == owner) -> allow'])",
            "assert 'engineer' in solve('role=engineer;department=eng;level=2', 'type=ledger;sensitivity=high;owner=eng', 'delete', ['(action == \"delete\") -> deny'])",
            "assert solve('role=director;department=legal;level=5', 'type=profile;sensitivity=critical;owner=legal', 'admin', []).endswith('DENY')",
            "assert solve('role=intern;department=hr;level=1', 'type=report;sensitivity=low;owner=hr', 'read', ['(level >= 2) -> allow']).endswith('DENY')",
        ],
        gold_snippets=["authorize", "audit_access"],
        distractor_snippets=["authorize_allow_all", "audit_access_no_decision"],
        reasoning_steps=3,
        reference_code='''def solve(subject: str, resource: str, action: str, policies: list[str]) -> str:
    decision = authorize(subject, resource, action, policies)
    return audit_access(subject, resource, action, decision)
''',
    )


def _l2_suggest_and_qualify(tid: str) -> None:
    history = [{"action": "write"}, {"action": "write"}, {"action": "read"}]

    def _expected(hist: list[dict]) -> str:
        if not hist:
            return "intern"
        counts: dict[str, int] = {}
        for entry in hist:
            action = entry.get("action", "read")
            counts[action] = counts.get(action, 0) + 1
        top_action = max(counts, key=counts.get)
        role = quorix.suggest_role(hist)
        return role if quorix.action_priority(top_action) >= 2 else "intern"

    qualified = _expected(history)
    second_history = [{"action": "read"}, {"action": "read"}]
    second_qualified = _expected(second_history)

    add_task(
        task_id=tid,
        level="L2",
        category="adaptive_modification",
        signature="def solve(history: list[dict]) -> str:",
        prompt="Implement solve(history). Suggest a role based on the most frequent action, but return 'intern' if that action's priority is below 2.",
        visible_tests=[
            f"assert solve({history}) == {_quote(qualified)}",
            f"assert solve({second_history}) == {_quote(second_qualified)}",
        ],
        hidden_tests=[
            "assert solve([{'action': 'write'}, {'action': 'write'}]) == 'manager'",
            "assert solve([{'action': 'delete'}, {'action': 'delete'}]) == 'admin'",
            "assert solve([{'action': 'admin'}, {'action': 'admin'}]) == 'director'",
            "assert solve([]) == 'intern'",
            "assert solve([{'action': 'read'}, {'action': 'write'}, {'action': 'write'}]) == 'manager'",
        ],
        gold_snippets=["suggest_role", "action_priority"],
        distractor_snippets=["suggest_role_inverted_mapping", "action_priority_swapped"],
        reasoning_steps=3,
        reference_code='''def solve(history: list[dict]) -> str:
    if not history:
        return "intern"
    counts = {}
    for entry in history:
        action = entry.get("action", "read")
        counts[action] = counts.get(action, 0) + 1
    top_action = max(counts, key=counts.get)
    role = suggest_role(history)
    return role if action_priority(top_action) >= 2 else "intern"
''',
    )


def _l2_count_then_decide(tid: str) -> None:
    subject = _subject()
    resource = _resource()
    action = _rand_action()
    policies = [_policy() for _ in range(random.randint(1, 3))]
    count = quorix.count_matching_policies(subject, resource, action, policies)
    expected = count >= 1

    second_subject = "role=admin;department=ops;level=5"
    second_resource = "type=file;sensitivity=critical;owner=ops"
    second_action = "delete"
    second_policies = ['(sensitivity == "critical") -> deny']
    second_expected = quorix.count_matching_policies(second_subject, second_resource, second_action, second_policies) >= 1

    add_task(
        task_id=tid,
        level="L2",
        category="adaptive_modification",
        signature="def solve(subject: str, resource: str, action: str, policies: list[str]) -> bool:",
        prompt="Implement solve(subject, resource, action, policies). Return True if at least one policy matches the request, ignoring whether it allows or denies.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {_quote(resource)}, {_quote(action)}, {policies}) is {expected}",
            f"assert solve({_quote(second_subject)}, {_quote(second_resource)}, {_quote(second_action)}, {second_policies}) is {second_expected}",
        ],
        hidden_tests=[
            "assert solve('role=intern;department=hr;level=1', 'type=doc;sensitivity=low;owner=sales', 'write', ['(level >= 2) -> allow']) is False",
            "assert solve('role=engineer;department=eng;level=2', 'type=ledger;sensitivity=medium;owner=eng', 'admin', []) is False",
            "assert solve('role=director;department=legal;level=5', 'type=profile;sensitivity=high;owner=hr', 'read', ['(owner == \"hr\") -> allow', '(level >= 4) -> allow']) is True",
            "assert solve('role=manager;department=sales;level=3', 'type=file;sensitivity=medium;owner=sales', 'write', ['(role == \"engineer\") -> allow', '(department == owner) -> allow']) is True",
            "assert solve('role=intern;department=eng;level=1', 'type=report;sensitivity=low;owner=eng', 'read', ['(role == \"manager\") -> allow', '(level >= 2) -> allow']) is False",
        ],
        gold_snippets=["count_matching_policies"],
        distractor_snippets=["count_matching_policies_ignore_effect"],
        reasoning_steps=2,
        reference_code='''def solve(subject: str, resource: str, action: str, policies: list[str]) -> bool:
    return count_matching_policies(subject, resource, action, policies) >= 1
''',
    )


def _l2_list_allowed_and_prioritize(tid: str) -> None:
    subject = _subject(role="manager", level=3)
    resource = _resource()
    policies = ['(role == "manager" and level >= 3) -> allow', '(action == "delete") -> deny']
    allowed = quorix.list_allowed_actions(subject, resource, policies)
    expected = max(allowed, key=quorix.action_priority) if allowed else None

    second_subject = "role=admin;department=ops;level=5"
    second_resource = "type=report;sensitivity=high;owner=ops"
    second_policies = ['(role == "admin") -> allow']
    second_allowed = quorix.list_allowed_actions(second_subject, second_resource, second_policies)
    second_expected = max(second_allowed, key=quorix.action_priority) if second_allowed else None

    add_task(
        task_id=tid,
        level="L2",
        category="adaptive_modification",
        signature="def solve(subject: str, resource: str, policies: list[str]) -> str | None:",
        prompt="Implement solve(subject, resource, policies). Return the allowed action with the highest priority, or None if no action is allowed.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {_quote(resource)}, {policies}) == {_quote(expected)}",
            f"assert solve({_quote(second_subject)}, {_quote(second_resource)}, {second_policies}) == {_quote(second_expected)}",
        ],
        hidden_tests=[
            "assert solve('role=intern;department=eng;level=1', 'type=doc;sensitivity=low;owner=hr', ['(level >= 3) -> allow']) is None",
            "assert solve('role=manager;department=sales;level=3', 'type=file;sensitivity=medium;owner=sales', ['(action == \"read\") -> allow', '(action == \"write\") -> allow']) == 'write'",
            "assert solve('role=engineer;department=hr;level=2', 'type=ledger;sensitivity=high;owner=hr', ['(action == \"read\") -> allow', '(action == \"delete\") -> deny']) == 'read'",
            "assert solve('role=director;department=legal;level=5', 'type=profile;sensitivity=critical;owner=legal', ['(action == \"admin\") -> deny']) is None",
            "assert solve('role=admin;department=ops;level=5', 'type=report;sensitivity=high;owner=ops', ['(role == \"admin\") -> allow', '(action == \"admin\") -> deny']) == 'delete'",
        ],
        gold_snippets=["list_allowed_actions", "action_priority"],
        distractor_snippets=["list_allowed_actions_all_actions", "action_priority_swapped"],
        reasoning_steps=3,
        reference_code='''def solve(subject: str, resource: str, policies: list[str]) -> str | None:
    allowed = list_allowed_actions(subject, resource, policies)
    return max(allowed, key=action_priority) if allowed else None
''',
    )


def _l2_format_then_parse(tid: str) -> None:
    role = _rand_role()
    dept = _rand_department()
    level = _rand_level()

    add_task(
        task_id=tid,
        level="L2",
        category="adaptive_modification",
        signature="def solve(role: str, department: str, level: int) -> dict:",
        prompt="Implement solve(role, department, level). Format the values as a Quorix subject string and return the parsed dictionary.",
        visible_tests=[
            f"assert solve({_quote(role)}, {_quote(dept)}, {level}) == {{'role': {_quote(role)}, 'department': {_quote(dept)}, 'level': {level}}}",
            "assert solve('intern', 'eng', 1) == {'role': 'intern', 'department': 'eng', 'level': 1}",
        ],
        hidden_tests=[
            "assert solve('admin', 'ops', 5) == {'role': 'admin', 'department': 'ops', 'level': 5}",
            "assert solve('manager', 'sales', 3) == {'role': 'manager', 'department': 'sales', 'level': 3}",
            "assert solve('director', 'legal', 4) == {'role': 'director', 'department': 'legal', 'level': 4}",
            "assert solve('engineer', 'hr', 2) == {'role': 'engineer', 'department': 'hr', 'level': 2}",
            "assert solve('intern', 'sales', 1) == {'role': 'intern', 'department': 'sales', 'level': 1}",
        ],
        gold_snippets=["format_subject", "parse_subject"],
        distractor_snippets=["format_subject_missing_level", "parse_subject_missing_level"],
        reasoning_steps=2,
        reference_code='''def solve(role: str, department: str, level: int) -> dict:
    return parse_subject(format_subject(role, department, level))
''',
    )


def _l2_sensitive_resource_authorize(tid: str) -> None:
    subject = _subject(level=3)
    resource = _resource(sensitivity="high")
    action = "read"
    policies = ['(level >= 3 and sensitivity == "high") -> allow', '(sensitivity == "critical") -> deny']
    expected = quorix.authorize(subject, resource, action, policies)

    second_subject = "role=manager;department=eng;level=4"
    second_resource = "type=report;sensitivity=low;owner=eng"
    second_action = "read"
    second_policies = ['(level >= 3) -> allow']
    second_expected = False

    add_task(
        task_id=tid,
        level="L2",
        category="adaptive_modification",
        signature="def solve(subject: str, resource: str, action: str, policies: list[str]) -> bool:",
        prompt="Implement solve(subject, resource, action, policies). Authorize the action only if the resource is sensitive (at least medium); otherwise return False without evaluating policies.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {_quote(resource)}, {_quote(action)}, {policies}) is {expected}",
            f"assert solve({_quote(second_subject)}, {_quote(second_resource)}, {_quote(second_action)}, {second_policies}) is {second_expected}",
        ],
        hidden_tests=[
            "assert solve('role=manager;department=eng;level=4', 'type=report;sensitivity=high;owner=eng', 'read', ['(level >= 3) -> allow']) is True",
            "assert solve('role=intern;department=hr;level=1', 'type=doc;sensitivity=medium;owner=hr', 'write', ['(level >= 2) -> allow']) is False",
            "assert solve('role=admin;department=ops;level=5', 'type=file;sensitivity=critical;owner=ops', 'delete', ['(role == \"admin\") -> allow']) is True",
            "assert solve('role=director;department=legal;level=5', 'type=ledger;sensitivity=low;owner=legal', 'admin', ['(role == \"admin\") -> allow']) is False",
            "assert solve('role=engineer;department=eng;level=2', 'type=report;sensitivity=medium;owner=eng', 'read', ['(department == owner) -> allow']) is True",
        ],
        gold_snippets=["is_sensitive", "authorize", "parse_resource"],
        distractor_snippets=["is_sensitive_wrong_threshold", "authorize_allow_all"],
        reasoning_steps=3,
        reference_code='''def solve(subject: str, resource: str, action: str, policies: list[str]) -> bool:
    if not is_sensitive(resource, "medium"):
        return False
    return authorize(subject, resource, action, policies)
''',
    )


def _l2_policy_analysis(tid: str) -> None:
    policies = ['(role == "admin") -> allow', '(sensitivity == "critical") -> deny', '(level >= 3) -> allow']
    ordered = quorix.resolve_policies(policies)
    expected = ordered[0]["effect"]

    second_policies = ['(role == "admin") -> allow', '(sensitivity == "critical") -> deny']
    second_expected = quorix.resolve_policies(second_policies)[0]["effect"]

    add_task(
        task_id=tid,
        level="L2",
        category="adaptive_modification",
        signature="def solve(policies: list[str]) -> str:",
        prompt="Implement solve(policies). Sort the policies so deny policies come first, then return the effect of the first policy.",
        visible_tests=[
            f"assert solve({policies}) == {_quote(expected)}",
            f"assert solve({second_policies}) == {_quote(second_expected)}",
        ],
        hidden_tests=[
            "assert solve(['(role == \"admin\") -> allow']) == 'allow'",
            "assert solve(['(action == \"delete\") -> deny', '(level >= 2) -> allow']) == 'deny'",
            "assert solve([]) == ''",
            "assert solve(['(owner == \"hr\") -> deny', '(department == \"eng\") -> deny', '(role == \"intern\") -> allow']) == 'deny'",
            "assert solve(['(role == \"manager\") -> allow', '(role == \"manager\") -> deny']) == 'deny'",
        ],
        gold_snippets=["resolve_policies", "parse_policy"],
        distractor_snippets=["resolve_policies_allow_first"],
        reasoning_steps=3,
        reference_code='''def solve(policies: list[str]) -> str:
    ordered = resolve_policies(policies)
    return ordered[0]["effect"] if ordered else ""
''',
    )


def l2_tasks() -> None:
    templates = [
        _l2_check_role_and_level,
        _l2_check_department_match,
        _l2_authorize_with_default,
        _l2_authorize_and_audit,
        _l2_suggest_and_qualify,
        _l2_count_then_decide,
        _l2_list_allowed_and_prioritize,
        _l2_format_then_parse,
        _l2_sensitive_resource_authorize,
        _l2_policy_analysis,
    ]
    counter = 1
    for template in templates:
        for _ in range(5):
            template(f"quorix_l2_{counter:03d}")
            counter += 1


# ---------------------------------------------------------------------------
# L3: Composition reasoning (10 templates x 5 variants)
# ---------------------------------------------------------------------------


def _l3_bulk_authorize_count(tid: str) -> None:
    subject = _subject(role="manager", level=3)
    resources = [_resource() for _ in range(3)]
    action = "read"
    policies = ['(role == "manager" and level >= 3) -> allow', '(sensitivity == "critical") -> deny']
    expected = sum(1 for r in resources if quorix.authorize(subject, r, action, policies))

    second_subject = "role=admin;department=ops;level=5"
    second_resources = ["type=report;sensitivity=low;owner=ops", "type=doc;sensitivity=high;owner=hr"]
    second_action = "read"
    second_policies = ['(role == "admin") -> allow']
    second_expected = sum(1 for r in second_resources if quorix.authorize(second_subject, r, second_action, second_policies))

    add_task(
        task_id=tid,
        level="L3",
        category="composition_reasoning",
        signature="def solve(subject: str, resources: list[str], action: str, policies: list[str]) -> int:",
        prompt="Implement solve(subject, resources, action, policies). Count how many resources the subject is allowed to perform the action on.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {resources}, {_quote(action)}, {policies}) == {expected}",
            f"assert solve({_quote(second_subject)}, {second_resources}, {_quote(second_action)}, {second_policies}) == {second_expected}",
        ],
        hidden_tests=[
            "assert solve('role=intern;department=eng;level=1', ['type=report;sensitivity=low;owner=eng'], 'read', ['(level >= 2) -> allow']) == 0",
            "assert solve('role=manager;department=sales;level=3', ['type=file;sensitivity=critical;owner=sales', 'type=ledger;sensitivity=medium;owner=sales'], 'write', ['(sensitivity == \"critical\") -> deny', '(level >= 3) -> allow']) == 1",
            "assert solve('role=engineer;department=hr;level=2', [], 'read', ['(role == \"engineer\") -> allow']) == 0",
            "assert solve('role=director;department=legal;level=5', ['type=profile;sensitivity=high;owner=legal', 'type=report;sensitivity=low;owner=eng'], 'admin', ['(role == \"admin\") -> allow']) == 0",
            "assert solve('role=manager;department=eng;level=3', ['type=report;sensitivity=low;owner=eng', 'type=doc;sensitivity=high;owner=eng'], 'read', ['(department == owner) -> allow']) == 2",
        ],
        gold_snippets=["authorize", "parse_subject", "parse_resource"],
        distractor_snippets=["authorize_allow_all", "authorize_deny_all"],
        reasoning_steps=4,
        reference_code='''def solve(subject: str, resources: list[str], action: str, policies: list[str]) -> int:
    return sum(1 for resource in resources if authorize(subject, resource, action, policies))
''',
    )


def _l3_filter_allowed(tid: str) -> None:
    subject = _subject(role="engineer", level=2)
    resources = [_resource() for _ in range(4)]
    action = "read"
    policies = ['(department == owner) -> allow', '(sensitivity == "critical") -> deny']
    expected = [r for r in resources if quorix.authorize(subject, r, action, policies)]

    second_subject = "role=admin;department=ops;level=5"
    second_resources = ["type=report;sensitivity=low;owner=ops", "type=doc;sensitivity=high;owner=hr"]
    second_action = "read"
    second_policies = ['(role == "admin") -> allow']
    second_expected = [r for r in second_resources if quorix.authorize(second_subject, r, second_action, second_policies)]

    add_task(
        task_id=tid,
        level="L3",
        category="composition_reasoning",
        signature="def solve(subject: str, resources: list[str], action: str, policies: list[str]) -> list[str]:",
        prompt="Implement solve(subject, resources, action, policies). Return the list of resources (in the original order) on which the action is allowed.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {resources}, {_quote(action)}, {policies}) == {expected}",
            f"assert solve({_quote(second_subject)}, {second_resources}, {_quote(second_action)}, {second_policies}) == {second_expected}",
        ],
        hidden_tests=[
            "assert solve('role=intern;department=eng;level=1', ['type=report;sensitivity=low;owner=eng'], 'read', ['(level >= 2) -> allow']) == []",
            "assert solve('role=manager;department=sales;level=3', ['type=file;sensitivity=critical;owner=sales', 'type=ledger;sensitivity=medium;owner=sales'], 'write', ['(department == owner) -> allow', '(sensitivity == \"critical\") -> deny']) == ['type=ledger;sensitivity=medium;owner=sales']",
            "assert solve('role=engineer;department=hr;level=2', [], 'read', ['(role == \"engineer\") -> allow']) == []",
            "assert solve('role=director;department=legal;level=5', ['type=profile;sensitivity=high;owner=legal'], 'admin', ['(role == \"admin\") -> allow']) == []",
            "assert solve('role=manager;department=eng;level=3', ['type=report;sensitivity=low;owner=eng', 'type=doc;sensitivity=high;owner=hr'], 'read', ['(department == owner) -> allow']) == ['type=report;sensitivity=low;owner=eng']",
        ],
        gold_snippets=["authorize", "parse_resource"],
        distractor_snippets=["authorize_allow_all", "authorize_deny_all"],
        reasoning_steps=4,
        reference_code='''def solve(subject: str, resources: list[str], action: str, policies: list[str]) -> list[str]:
    return [resource for resource in resources if authorize(subject, resource, action, policies)]
''',
    )


def _l3_bulk_audit(tid: str) -> None:
    subject = _subject()
    resource = _resource()
    action = _rand_action()
    policies = [_policy() for _ in range(random.randint(1, 2))]
    decision = quorix.authorize(subject, resource, action, policies)
    log = quorix.audit_access(subject, resource, action, decision)

    second_subject = "role=admin;department=ops;level=5"
    second_resource = "type=report;sensitivity=high;owner=ops"
    second_action = "read"
    second_policies = ['(role == "admin") -> allow']
    second_log = quorix.audit_access(second_subject, second_resource, second_action, quorix.authorize(second_subject, second_resource, second_action, second_policies))

    add_task(
        task_id=tid,
        level="L3",
        category="composition_reasoning",
        signature="def solve(subject: str, resource: str, action: str, policies: list[str]) -> list[str]:",
        prompt="Implement solve(subject, resource, action, policies). Evaluate authorization for the action and also for the next more privileged action (if any), returning a list of audit log strings. The more privileged action is the one with the next higher priority after the given action; if there is none, return a list with only the original audit log.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {_quote(resource)}, {_quote(action)}, {policies})[0] == {_quote(log)}",
            f"assert solve({_quote(second_subject)}, {_quote(second_resource)}, {_quote(second_action)}, {second_policies})[0] == {_quote(second_log)}",
        ],
        hidden_tests=[
            "assert len(solve('role=admin;department=ops;level=5', 'type=report;sensitivity=high;owner=ops', 'read', ['(role == \"admin\") -> allow'])) == 2",
            "assert len(solve('role=manager;department=sales;level=3', 'type=file;sensitivity=medium;owner=sales', 'admin', ['(role == \"admin\") -> allow'])) == 1",
            "assert all(isinstance(x, str) for x in solve('role=engineer;department=eng;level=2', 'type=doc;sensitivity=low;owner=eng', 'read', ['(department == owner) -> allow']))",
            "assert solve('role=intern;department=hr;level=1', 'type=ledger;sensitivity=high;owner=hr', 'write', ['(level >= 2) -> allow'])[0].endswith('DENY')",
            "assert 'ALLOW' in solve('role=director;department=legal;level=5', 'type=profile;sensitivity=high;owner=legal', 'read', ['(level >= 4) -> allow'])[0]",
        ],
        gold_snippets=["authorize", "audit_access", "action_priority", "list_allowed_actions"],
        distractor_snippets=["authorize_allow_all", "audit_access_no_decision", "action_priority_swapped"],
        reasoning_steps=5,
        reference_code='''def solve(subject: str, resource: str, action: str, policies: list[str]) -> list[str]:
    actions = ["read", "write", "delete", "admin"]
    idx = actions.index(action)
    selected = actions[idx:idx + 2] if idx + 1 < len(actions) else [action]
    return [audit_access(subject, resource, a, authorize(subject, resource, a, policies)) for a in selected]
''',
    )


def _l3_role_suggestion_aggregate(tid: str) -> None:
    histories = [
        [{"action": "read"}, {"action": "write"}],
        [{"action": "write"}, {"action": "write"}],
    ]
    suggestions = [quorix.suggest_role(h) for h in histories]

    def _most_common(items: list[str]) -> str:
        counts = {item: items.count(item) for item in items}
        max_count = max(counts.values())
        for item in items:
            if counts[item] == max_count:
                return item
        return items[0]

    expected = _most_common(suggestions) if suggestions else "intern"
    second_histories = [[{"action": "read"}], [{"action": "read"}]]
    second_expected = _most_common([quorix.suggest_role(h) for h in second_histories])

    add_task(
        task_id=tid,
        level="L3",
        category="composition_reasoning",
        signature="def solve(histories: list[list[dict]]) -> str:",
        prompt="Implement solve(histories). Suggest a role for each access history and return the most common suggestion. If there is a tie, return the one that appears first in the suggestion list. Return 'intern' for empty input.",
        visible_tests=[
            f"assert solve({histories}) == {_quote(expected)}",
            f"assert solve({second_histories}) == {_quote(second_expected)}",
        ],
        hidden_tests=[
            "assert solve([]) == 'intern'",
            "assert solve([[{'action': 'write'}], [{'action': 'delete'}]]) == 'manager'",
            "assert solve([[{'action': 'admin'}, {'action': 'admin'}], [{'action': 'admin'}]]) == 'director'",
            "assert solve([[{'action': 'delete'}, {'action': 'delete'}], [{'action': 'write'}, {'action': 'write'}]]) == 'admin'",
            "assert solve([[{'action': 'read'}, {'action': 'write'}, {'action': 'write'}], [{'action': 'write'}]]) == 'manager'",
        ],
        gold_snippets=["suggest_role"],
        distractor_snippets=["suggest_role_inverted_mapping"],
        reasoning_steps=4,
        reference_code='''def solve(histories: list[list[dict]]) -> str:
    if not histories:
        return "intern"
    suggestions = [suggest_role(h) for h in histories]
    counts = {role: suggestions.count(role) for role in suggestions}
    max_count = max(counts.values())
    for role in suggestions:
        if counts[role] == max_count:
            return role
    return suggestions[0]
''',
    )


def _l3_find_best_subject(tid: str) -> None:
    subjects = [
        "role=intern;department=eng;level=1",
        "role=manager;department=sales;level=3",
        "role=admin;department=ops;level=5",
    ]
    resource = _resource()
    policies = ['(role == "admin") -> allow', '(level >= 3 and role == "manager") -> allow']
    allowed_counts = [len(quorix.list_allowed_actions(s, resource, policies)) for s in subjects]
    best_idx = allowed_counts.index(max(allowed_counts)) if max(allowed_counts) > 0 else -1
    expected = subjects[best_idx] if best_idx >= 0 else None

    second_subjects = ["role=admin;department=ops;level=5"]
    second_resource = "type=report;sensitivity=low;owner=ops"
    second_policies = ['(role == "admin") -> allow']
    second_expected = "role=admin;department=ops;level=5"

    add_task(
        task_id=tid,
        level="L3",
        category="composition_reasoning",
        signature="def solve(subjects: list[str], resource: str, policies: list[str]) -> str | None:",
        prompt="Implement solve(subjects, resource, policies). Return the subject string that is allowed to perform the most distinct actions on the resource. In case of a tie, return the first such subject. Return None if no subject is allowed any action.",
        visible_tests=[
            f"assert solve({subjects}, {_quote(resource)}, {policies}) == {_quote(expected) if expected is not None else 'None'}",
            f"assert solve({second_subjects}, {_quote(second_resource)}, {second_policies}) == {_quote(second_expected)}",
        ],
        hidden_tests=[
            "assert solve(['role=intern;department=eng;level=1'], 'type=doc;sensitivity=low;owner=eng', ['(level >= 2) -> allow']) is None",
            "assert solve(['role=manager;department=sales;level=3', 'role=engineer;department=hr;level=2'], 'type=file;sensitivity=medium;owner=sales', ['(level >= 2) -> allow']) == 'role=manager;department=sales;level=3'",
            "assert solve([], 'type=ledger;sensitivity=high;owner=legal', ['(role == \"admin\") -> allow']) is None",
            "assert solve(['role=director;department=legal;level=5', 'role=admin;department=ops;level=5'], 'type=profile;sensitivity=critical;owner=legal', ['(role == \"admin\") -> allow']) == 'role=admin;department=ops;level=5'",
            "assert solve(['role=engineer;department=eng;level=2', 'role=manager;department=eng;level=3'], 'type=report;sensitivity=low;owner=eng', ['(department == owner) -> allow']) == 'role=engineer;department=eng;level=2'",
        ],
        gold_snippets=["list_allowed_actions", "authorize", "parse_subject"],
        distractor_snippets=["list_allowed_actions_all_actions", "authorize_allow_all"],
        reasoning_steps=5,
        reference_code='''def solve(subjects: list[str], resource: str, policies: list[str]) -> str | None:
    best = None
    best_count = -1
    for subject in subjects:
        count = len(list_allowed_actions(subject, resource, policies))
        if count > best_count:
            best_count = count
            best = subject
    return best if best_count > 0 else None
''',
    )


def _l3_policy_conflict_detector(tid: str) -> None:
    policies = [
        '(role == "manager") -> allow',
        '(role == "manager") -> deny',
        '(sensitivity == "critical") -> deny',
    ]
    # A pair conflicts if both an allow and a deny can match the same concrete context.
    expected = True  # manager allow + manager deny conflict

    second_policies = ['(role == "engineer") -> allow', '(role == "engineer") -> deny']
    second_expected = True

    add_task(
        task_id=tid,
        level="L3",
        category="composition_reasoning",
        signature="def solve(policies: list[str]) -> bool:",
        prompt="Implement solve(policies). Return True if there exists at least one role that appears in both an allow policy and a deny policy (a potential conflict).",
        visible_tests=[
            f"assert solve({policies}) is {expected}",
            f"assert solve({second_policies}) is {second_expected}",
        ],
        hidden_tests=[
            "assert solve(['(role == \"admin\") -> allow', '(role == \"intern\") -> deny']) is False",
            "assert solve([]) is False",
            "assert solve(['(role == \"manager\") -> allow', '(role == \"manager\") -> deny', '(role == \"director\") -> allow']) is True",
            "assert solve(['(department == \"eng\") -> allow', '(role == \"engineer\") -> deny']) is False",
            "assert solve(['(role == \"director\") -> allow', '(role == \"director\") -> deny', '(role == \"director\") -> deny']) is True",
        ],
        gold_snippets=["parse_policy", "evaluate_condition", "resolve_policies"],
        distractor_snippets=["parse_policy_inverted_effect", "resolve_policies_allow_first"],
        reasoning_steps=5,
        reference_code='''def solve(policies: list[str]) -> bool:
    allows = set()
    denies = set()
    for policy in policies:
        p = parse_policy(policy)
        # Extract a role literal from a simple condition like 'role == "manager"'.
        import re
        m = re.search(r'role\\s*==\\s*"([^"]+)"', p["condition"])
        if m:
            role = m.group(1)
            if p["effect"] == "allow":
                allows.add(role)
            else:
                denies.add(role)
    return bool(allows & denies)
''',
    )


def _l3_access_report(tid: str) -> None:
    subject = _subject(role="manager", level=3)
    resources = [
        "type=report;sensitivity=low;owner=eng",
        "type=doc;sensitivity=high;owner=hr",
        "type=file;sensitivity=critical;owner=sales",
    ]
    policies = ['(level >= 3 and sensitivity != "critical") -> allow', '(sensitivity == "critical") -> deny']
    expected = {
        "total": len(resources),
        "allowed": sum(1 for r in resources if quorix.authorize(subject, r, "read", policies)),
        "denied": sum(1 for r in resources if not quorix.authorize(subject, r, "read", policies)),
    }

    second_subject = "role=admin;department=ops;level=5"
    second_resources = ["type=report;sensitivity=low;owner=ops"]
    second_policies = ['(role == "admin") -> allow']
    second_expected = {
        "total": 1,
        "allowed": 1,
        "denied": 0,
    }

    add_task(
        task_id=tid,
        level="L3",
        category="composition_reasoning",
        signature="def solve(subject: str, resources: list[str], policies: list[str]) -> dict:",
        prompt="Implement solve(subject, resources, policies). Return a report dictionary with keys 'total', 'allowed', and 'denied' summarizing read access for the subject across the resources.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {resources}, {policies}) == {expected}",
            f"assert solve({_quote(second_subject)}, {second_resources}, {second_policies}) == {second_expected}",
        ],
        hidden_tests=[
            "assert solve('role=intern;department=eng;level=1', [], ['(level >= 2) -> allow']) == {'total': 0, 'allowed': 0, 'denied': 0}",
            "assert solve('role=engineer;department=hr;level=2', ['type=doc;sensitivity=medium;owner=hr', 'type=file;sensitivity=critical;owner=hr'], ['(department == owner) -> allow', '(sensitivity == \"critical\") -> deny']) == {'total': 2, 'allowed': 1, 'denied': 1}",
            "assert solve('role=director;department=legal;level=5', ['type=ledger;sensitivity=high;owner=legal'], ['(role == \"admin\") -> allow']) == {'total': 1, 'allowed': 0, 'denied': 1}",
            "assert solve('role=manager;department=sales;level=3', ['type=profile;sensitivity=low;owner=sales', 'type=report;sensitivity=high;owner=sales'], ['(level >= 3) -> allow']) == {'total': 2, 'allowed': 2, 'denied': 0}",
            "assert solve('role=engineer;department=eng;level=2', ['type=report;sensitivity=low;owner=eng', 'type=doc;sensitivity=high;owner=hr'], ['(department == owner) -> allow']) == {'total': 2, 'allowed': 1, 'denied': 1}",
        ],
        gold_snippets=["authorize", "parse_subject", "parse_resource"],
        distractor_snippets=["authorize_allow_all", "authorize_deny_all"],
        reasoning_steps=4,
        reference_code='''def solve(subject: str, resources: list[str], policies: list[str]) -> dict:
    allowed = sum(1 for r in resources if authorize(subject, r, "read", policies))
    return {"total": len(resources), "allowed": allowed, "denied": len(resources) - allowed}
''',
    )


def _l3_sensitivity_access_matrix(tid: str) -> None:
    subject = _subject(role="manager", level=3)
    sensitivities = ["low", "medium", "high", "critical"]
    policies = ['(level >= 3 and sensitivity != "critical") -> allow', '(sensitivity == "critical") -> deny']
    expected = {
        s: quorix.authorize(subject, quorix.format_resource("doc", s, "eng"), "read", policies)
        for s in sensitivities
    }

    second_subject = "role=admin;department=ops;level=5"
    second_policies = ['(role == "admin") -> allow']
    second_expected = {
        s: quorix.authorize(second_subject, quorix.format_resource("doc", s, "eng"), "read", second_policies)
        for s in sensitivities
    }

    add_task(
        task_id=tid,
        level="L3",
        category="composition_reasoning",
        signature="def solve(subject: str, policies: list[str]) -> dict[str, bool]:",
        prompt="Implement solve(subject, policies). Return a dictionary mapping each sensitivity level ('low', 'medium', 'high', 'critical') to whether the subject is allowed to read a document with that sensitivity.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {policies}) == {expected}",
            f"assert solve({_quote(second_subject)}, {second_policies}) == {second_expected}",
        ],
        hidden_tests=[
            "assert solve('role=intern;department=eng;level=1', ['(level >= 2) -> allow']) == {'low': False, 'medium': False, 'high': False, 'critical': False}",
            "assert solve('role=manager;department=sales;level=3', ['(level >= 3) -> allow', '(sensitivity == \"critical\") -> deny']) == {'low': True, 'medium': True, 'high': True, 'critical': False}",
            "assert solve('role=engineer;department=hr;level=2', ['(sensitivity != \"critical\") -> allow']) == {'low': True, 'medium': True, 'high': True, 'critical': False}",
            "assert solve('role=director;department=legal;level=5', ['(role == \"director\") -> allow', '(sensitivity == \"critical\") -> deny']) == {'low': True, 'medium': True, 'high': True, 'critical': False}",
            "assert solve('role=manager;department=eng;level=3', ['(department == \"eng\") -> allow', '(sensitivity == \"critical\") -> deny']) == {'low': True, 'medium': True, 'high': True, 'critical': False}",
        ],
        gold_snippets=["authorize", "format_resource", "parse_subject"],
        distractor_snippets=["authorize_allow_all", "format_resource_wrong_sensitivity"],
        reasoning_steps=5,
        reference_code='''def solve(subject: str, policies: list[str]) -> dict[str, bool]:
    sensitivities = ["low", "medium", "high", "critical"]
    return {s: authorize(subject, format_resource("doc", s, "eng"), "read", policies) for s in sensitivities}
''',
    )


def _l3_history_to_policy_suggestion(tid: str) -> None:
    history = [{"action": "write"}, {"action": "write"}, {"action": "read"}]
    role = quorix.suggest_role(history)
    condition = f'role == "{role}"'
    policy = quorix.make_policy(condition, "allow")

    second_history = [{"action": "read"}, {"action": "read"}]
    second_policy = '(role == "engineer") -> allow'

    add_task(
        task_id=tid,
        level="L3",
        category="composition_reasoning",
        signature="def solve(history: list[dict]) -> str:",
        prompt="Implement solve(history). Suggest a Quorix role based on the history, then produce an allow policy that grants read access to subjects with that role.",
        visible_tests=[
            f"assert solve({history}) == {_quote(policy)}",
            f"assert solve({second_history}) == {_quote(second_policy)}",
        ],
        hidden_tests=[
            "assert solve([]) == '(role == \"intern\") -> allow'",
            "assert solve([{'action': 'write'}, {'action': 'write'}]) == '(role == \"manager\") -> allow'",
            "assert solve([{'action': 'delete'}, {'action': 'delete'}]) == '(role == \"admin\") -> allow'",
            "assert solve([{'action': 'admin'}, {'action': 'admin'}]) == '(role == \"director\") -> allow'",
            "assert solve([{'action': 'read'}, {'action': 'write'}, {'action': 'write'}]) == '(role == \"manager\") -> allow'",
        ],
        gold_snippets=["suggest_role", "make_policy"],
        distractor_snippets=["suggest_role_inverted_mapping", "make_policy_inverted_effect"],
        reasoning_steps=4,
        reference_code='''def solve(history: list[dict]) -> str:
    role = suggest_role(history)
    return make_policy(f'role == "{role}"', "allow")
''',
    )


def _l3_multi_resource_action_plan(tid: str) -> None:
    subject = _subject(role="manager", level=3)
    resources = [
        "type=report;sensitivity=low;owner=eng",
        "type=doc;sensitivity=high;owner=hr",
    ]
    policies = ['(level >= 3) -> allow', '(sensitivity == "critical") -> deny']
    expected = {
        r: quorix.list_allowed_actions(subject, r, policies)
        for r in resources
    }

    second_subject = "role=admin;department=ops;level=5"
    second_resources = ["type=report;sensitivity=low;owner=ops"]
    second_policies = ['(role == "admin") -> allow']
    second_expected = {
        r: quorix.list_allowed_actions(second_subject, r, second_policies)
        for r in second_resources
    }

    add_task(
        task_id=tid,
        level="L3",
        category="composition_reasoning",
        signature="def solve(subject: str, resources: list[str], policies: list[str]) -> dict[str, list[str]]:",
        prompt="Implement solve(subject, resources, policies). Return a dictionary mapping each resource string to the list of actions that the subject is allowed to perform on it.",
        visible_tests=[
            f"assert solve({_quote(subject)}, {resources}, {policies}) == {expected}",
            f"assert solve({_quote(second_subject)}, {second_resources}, {second_policies}) == {second_expected}",
        ],
        hidden_tests=[
            "assert solve('role=intern;department=eng;level=1', ['type=doc;sensitivity=low;owner=eng'], ['(level >= 2) -> allow']) == {'type=doc;sensitivity=low;owner=eng': []}",
            "assert solve('role=manager;department=sales;level=3', ['type=file;sensitivity=medium;owner=sales'], ['(action == \"read\") -> allow']) == {'type=file;sensitivity=medium;owner=sales': ['read']}",
            "assert solve('role=director;department=legal;level=5', [], ['(role == \"admin\") -> allow']) == {}",
            "assert solve('role=engineer;department=hr;level=2', ['type=ledger;sensitivity=high;owner=hr', 'type=profile;sensitivity=critical;owner=hr'], ['(sensitivity == \"critical\") -> deny'])['type=profile;sensitivity=critical;owner=hr'] == []",
            "assert solve('role=manager;department=eng;level=3', ['type=report;sensitivity=low;owner=eng'], ['(department == owner) -> allow']) == {'type=report;sensitivity=low;owner=eng': ['read', 'write', 'delete', 'admin']}",
        ],
        gold_snippets=["list_allowed_actions", "authorize", "parse_resource"],
        distractor_snippets=["list_allowed_actions_all_actions", "authorize_allow_all"],
        reasoning_steps=5,
        reference_code='''def solve(subject: str, resources: list[str], policies: list[str]) -> dict[str, list[str]]:
    return {resource: list_allowed_actions(subject, resource, policies) for resource in resources}
''',
    )


def l3_tasks() -> None:
    templates = [
        _l3_bulk_authorize_count,
        _l3_filter_allowed,
        _l3_bulk_audit,
        _l3_role_suggestion_aggregate,
        _l3_find_best_subject,
        _l3_policy_conflict_detector,
        _l3_access_report,
        _l3_sensitivity_access_matrix,
        _l3_history_to_policy_suggestion,
        _l3_multi_resource_action_plan,
    ]
    counter = 1
    for template in templates:
        for _ in range(5):
            template(f"quorix_l3_{counter:03d}")
            counter += 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    l1_tasks()
    l2_tasks()
    l3_tasks()

    by_level: dict[str, list[dict[str, Any]]] = {"L1": [], "L2": [], "L3": []}
    for task in tasks:
        by_level[task["level"]].append(task)

    for level, task_list in by_level.items():
        path = TASKS_DIR / f"quorix_{level.lower()}.jsonl"
        with path.open("w", encoding="utf-8") as f:
            for task in task_list:
                f.write(json.dumps(task, ensure_ascii=False) + "\n")
        print(f"Wrote {len(task_list)} {level} tasks to {path}")

    all_path = TASKS_DIR / "quorix_all.jsonl"
    with all_path.open("w", encoding="utf-8") as f:
        for task in tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")
    print(f"Wrote {len(tasks)} total tasks to {all_path}")


if __name__ == "__main__":
    main()
