"""Quorix Access Control Engine.

A synthetic, fictional rule engine for evaluating permission policies over
subjects, resources, and actions. It is intentionally unrelated to any real
system so that pretrained models cannot rely on memorized behavior.

String formats::

    Subject:  "role=<role>;department=<dept>;level=<int>"
    Resource: "type=<type>;sensitivity=<low|medium|high>;owner=<dept>"
    Policy:   "(<condition>) -> <allow|deny>"

Supported condition operators: ==, !=, <, <=, >, >=, and, or.
"""

from __future__ import annotations

import ast
import operator
import re
from typing import Any


_VALID_ROLES = {"intern", "engineer", "manager", "director", "admin"}
_VALID_DEPARTMENTS = {"eng", "hr", "sales", "ops", "legal"}
_VALID_SENSITIVITIES = {"low", "medium", "high", "critical"}
_VALID_ACTIONS = {"read", "write", "delete", "admin"}

_POLICY_PATTERN = re.compile(
    r"^\s*\((?P<condition>.*?)\)\s*->\s*(?P<effect>allow|deny)\s*$"
)

_COMPARISON_OPS = {
    "==": operator.eq,
    "!=": operator.ne,
    "<": operator.lt,
    "<=": operator.le,
    ">": operator.gt,
    ">=": operator.ge,
}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------


def _parse_kv_string(text: str) -> dict[str, Any]:
    """Parse a semicolon-separated key=value string into a dictionary."""
    result: dict[str, Any] = {}
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ValueError(f"Invalid key-value segment: {part!r}")
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in ("level",):
            value = int(value)
        result[key] = value
    return result


def parse_subject(subject: str) -> dict[str, Any]:
    """Parse a subject string into a dictionary."""
    rec = _parse_kv_string(subject)
    if "role" not in rec or "department" not in rec or "level" not in rec:
        raise ValueError(f"Subject missing required fields: {subject!r}")
    if rec["role"] not in _VALID_ROLES:
        raise ValueError(f"Invalid role: {rec['role']!r}")
    if rec["department"] not in _VALID_DEPARTMENTS:
        raise ValueError(f"Invalid department: {rec['department']!r}")
    if not 1 <= rec["level"] <= 5:
        raise ValueError(f"Invalid level: {rec['level']!r}")
    return rec


def parse_resource(resource: str) -> dict[str, Any]:
    """Parse a resource string into a dictionary."""
    rec = _parse_kv_string(resource)
    if "type" not in rec or "sensitivity" not in rec or "owner" not in rec:
        raise ValueError(f"Resource missing required fields: {resource!r}")
    if rec["sensitivity"] not in _VALID_SENSITIVITIES:
        raise ValueError(f"Invalid sensitivity: {rec['sensitivity']!r}")
    if rec["owner"] not in _VALID_DEPARTMENTS:
        raise ValueError(f"Invalid owner department: {rec['owner']!r}")
    return rec


def parse_policy(policy: str) -> dict[str, Any]:
    """Parse a policy string into condition/effect parts."""
    match = _POLICY_PATTERN.match(policy)
    if not match:
        raise ValueError(f"Invalid policy format: {policy!r}")
    return {
        "condition": match.group("condition").strip(),
        "effect": match.group("effect").strip(),
    }


# ---------------------------------------------------------------------------
# Condition evaluation
# ---------------------------------------------------------------------------


def _eval_condition_node(
    node: ast.AST, context: dict[str, Any]
) -> Any:
    """Recursively evaluate a parsed condition AST node."""
    if isinstance(node, ast.BoolOp):
        values = [_eval_condition_node(v, context) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
        raise ValueError(f"Unsupported boolean operator: {node.op}")

    if isinstance(node, ast.Compare):
        left = _eval_condition_node(node.left, context)
        if len(node.ops) != 1 or len(node.comparators) != 1:
            raise ValueError("Chained comparisons are not supported")
        op_node = node.ops[0]
        right = _eval_condition_node(node.comparators[0], context)
        for op_symbol, func in _COMPARISON_OPS.items():
            if isinstance(op_node, _operator_class(op_symbol)):
                return func(left, right)
        raise ValueError(f"Unsupported comparison operator: {op_node}")

    if isinstance(node, ast.Constant):
        return node.value

    if isinstance(node, ast.Name):
        if node.id not in context:
            raise ValueError(f"Unknown variable in condition: {node.id}")
        return context[node.id]

    raise ValueError(f"Unsupported expression: {ast.dump(node)}")


def _operator_class(symbol: str) -> type:
    """Return the AST operator class for a symbol."""
    mapping = {
        "==": ast.Eq,
        "!=": ast.NotEq,
        "<": ast.Lt,
        "<=": ast.LtE,
        ">": ast.Gt,
        ">=": ast.GtE,
    }
    return mapping[symbol]


def evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    """Evaluate a policy condition string against a context dictionary.

    Args:
        condition: A condition like ``role == "manager" and level >= 3``.
        context: A dictionary mapping variable names to values.

    Returns:
        True if the condition holds, False otherwise.
    """
    try:
        tree = ast.parse(condition, mode="eval")
    except SyntaxError as exc:
        raise ValueError(f"Invalid condition syntax: {condition!r}") from exc
    result = _eval_condition_node(tree.body, context)
    return bool(result)


# ---------------------------------------------------------------------------
# Authorization
# ---------------------------------------------------------------------------


def authorize(
    subject: str | dict[str, Any],
    resource: str | dict[str, Any],
    action: str,
    policies: list[str] | list[dict[str, Any]],
    default: bool = False,
) -> bool:
    """Decide whether an action is allowed.

    The engine evaluates all matching policies. If any matching policy is a
    ``deny``, the result is ``False``. If at least one matching policy is an
    ``allow`` and no deny matches, the result is ``True``. If no policy
    matches, ``default`` is returned.

    Args:
        subject: Subject string or parsed subject dict.
        resource: Resource string or parsed resource dict.
        action: One of read / write / delete / admin.
        policies: List of policy strings or parsed policy dicts.
        default: Default decision when no policy matches.

    Returns:
        True if allowed, False otherwise.
    """
    if action not in _VALID_ACTIONS:
        raise ValueError(f"Invalid action: {action!r}")
    if isinstance(subject, str):
        subject = parse_subject(subject)
    if isinstance(resource, str):
        resource = parse_resource(resource)

    context = {
        "role": subject["role"],
        "department": subject["department"],
        "level": subject["level"],
        "type": resource["type"],
        "sensitivity": resource["sensitivity"],
        "owner": resource["owner"],
        "action": action,
    }

    allow_match = False
    for policy in policies:
        if isinstance(policy, str):
            policy = parse_policy(policy)
        if evaluate_condition(policy["condition"], context):
            if policy["effect"] == "deny":
                return False
            if policy["effect"] == "allow":
                allow_match = True

    return allow_match or default


def resolve_policies(policies: list[str] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort policies so that deny policies take precedence over allow policies.

    Returns:
        A list of parsed policies with deny entries first.
    """
    parsed = [parse_policy(p) if isinstance(p, str) else p for p in policies]
    return sorted(parsed, key=lambda p: 0 if p["effect"] == "deny" else 1)


# ---------------------------------------------------------------------------
# Audit and suggestion
# ---------------------------------------------------------------------------


def audit_access(
    subject: str | dict[str, Any],
    resource: str | dict[str, Any],
    action: str,
    decision: bool,
) -> str:
    """Generate a short audit log string."""
    if isinstance(subject, str):
        subject = parse_subject(subject)
    if isinstance(resource, str):
        resource = parse_resource(resource)
    outcome = "ALLOW" if decision else "DENY"
    return (
        f"[{subject['role']}/{subject['department']}/L{subject['level']}] "
        f"{action} {resource['type']}:{resource['sensitivity']}:{resource['owner']} -> {outcome}"
    )


def suggest_role(history: list[dict[str, Any]]) -> str:
    """Suggest a role based on the most frequent action in a history.

    The fictional mapping is:
        * read-heavy  -> engineer
        * write-heavy -> manager
        * delete-heavy -> admin
        * admin-heavy -> director
        * empty/unmapped -> intern
    """
    if not history:
        return "intern"
    counts: dict[str, int] = {}
    for entry in history:
        action = entry.get("action", "read")
        counts[action] = counts.get(action, 0) + 1
    top_action = max(counts, key=counts.get)
    mapping = {
        "read": "engineer",
        "write": "manager",
        "delete": "admin",
        "admin": "director",
    }
    return mapping.get(top_action, "intern")


# ---------------------------------------------------------------------------
# Convenience helpers for richer task generation
# ---------------------------------------------------------------------------


def format_subject(role: str, department: str, level: int) -> str:
    """Format a subject string from its components."""
    return f"role={role};department={department};level={level}"


def format_resource(type: str, sensitivity: str, owner: str) -> str:
    """Format a resource string from its components."""
    return f"type={type};sensitivity={sensitivity};owner={owner}"


def make_policy(condition: str, effect: str) -> str:
    """Format a policy string from a condition and an effect."""
    if effect not in ("allow", "deny"):
        raise ValueError(f"Invalid effect: {effect!r}")
    return f"({condition}) -> {effect}"


def is_admin(subject: str | dict[str, Any]) -> bool:
    """Return True if the subject has the admin role."""
    if isinstance(subject, str):
        subject = parse_subject(subject)
    return subject["role"] == "admin"


def subject_has_role(subject: str | dict[str, Any], role: str) -> bool:
    """Return True if the subject's role equals ``role``."""
    if isinstance(subject, str):
        subject = parse_subject(subject)
    return subject["role"] == role


def subject_level_at_least(subject: str | dict[str, Any], min_level: int) -> bool:
    """Return True if the subject's level is at least ``min_level``."""
    if isinstance(subject, str):
        subject = parse_subject(subject)
    return subject["level"] >= min_level


def resource_owned_by(resource: str | dict[str, Any], department: str) -> bool:
    """Return True if the resource owner equals ``department``."""
    if isinstance(resource, str):
        resource = parse_resource(resource)
    return resource["owner"] == department


def is_sensitive(resource: str | dict[str, Any], threshold: str = "medium") -> bool:
    """Return True if the resource sensitivity is at least ``threshold``.

    Sensitivity ordering: low < medium < high < critical.
    """
    order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    if threshold not in order:
        raise ValueError(f"Invalid sensitivity threshold: {threshold!r}")
    if isinstance(resource, str):
        resource = parse_resource(resource)
    return order[resource["sensitivity"]] >= order[threshold]


def resource_sensitivity_at_least(resource: str | dict[str, Any], threshold: str) -> bool:
    """Alias for ``is_sensitive`` using an explicit threshold."""
    return is_sensitive(resource, threshold)


def action_priority(action: str) -> int:
    """Return a numeric priority for an action (higher is more privileged)."""
    if action not in _VALID_ACTIONS:
        raise ValueError(f"Invalid action: {action!r}")
    return {"read": 1, "write": 2, "delete": 3, "admin": 4}[action]


def count_matching_policies(
    subject: str | dict[str, Any],
    resource: str | dict[str, Any],
    action: str,
    policies: list[str] | list[dict[str, Any]],
) -> int:
    """Count how many policies match the given subject/resource/action."""
    if isinstance(subject, str):
        subject = parse_subject(subject)
    if isinstance(resource, str):
        resource = parse_resource(resource)
    if action not in _VALID_ACTIONS:
        raise ValueError(f"Invalid action: {action!r}")

    context = {
        "role": subject["role"],
        "department": subject["department"],
        "level": subject["level"],
        "type": resource["type"],
        "sensitivity": resource["sensitivity"],
        "owner": resource["owner"],
        "action": action,
    }
    count = 0
    for policy in policies:
        if isinstance(policy, str):
            policy = parse_policy(policy)
        if evaluate_condition(policy["condition"], context):
            count += 1
    return count


def list_allowed_actions(
    subject: str | dict[str, Any],
    resource: str | dict[str, Any],
    policies: list[str] | list[dict[str, Any]],
    default: bool = False,
) -> list[str]:
    """Return the list of actions that are allowed for subject on resource.

    Actions are returned in ascending priority order: read, write, delete, admin.
    """
    return [
        action
        for action in sorted(_VALID_ACTIONS, key=action_priority)
        if authorize(subject, resource, action, policies, default=default)
    ]
