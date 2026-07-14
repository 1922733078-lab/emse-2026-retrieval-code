"""Buggy distractor variants of Quorix functions."""

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


def _parse_kv_string(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for part in text.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key in ("level",):
            try:
                value = int(value)
            except ValueError:
                value = 1
        result[key] = value
    return result


def parse_subject_missing_level(subject: str) -> dict[str, Any]:
    """Parse subject but do not require level (missing field validation)."""
    rec = _parse_kv_string(subject)
    if "role" not in rec:
        rec["role"] = "intern"
    if "department" not in rec:
        rec["department"] = "eng"
    if "level" not in rec:
        rec["level"] = 1
    return rec


def parse_resource_wrong_sensitivity(resource: str) -> dict[str, Any]:
    """Parse resource but accept any sensitivity (missing validation)."""
    rec = _parse_kv_string(resource)
    if "type" not in rec:
        rec["type"] = "file"
    if "sensitivity" not in rec:
        rec["sensitivity"] = "low"
    if "owner" not in rec:
        rec["owner"] = "eng"
    return rec


def parse_policy_inverted_effect(policy: str) -> dict[str, Any]:
    """Parse policy but swap allow/deny (inverted logic)."""
    match = _POLICY_PATTERN.match(policy)
    if not match:
        return {"condition": "True", "effect": "allow"}
    effect = match.group("effect").strip()
    inverted = "deny" if effect == "allow" else "allow"
    return {"condition": match.group("condition").strip(), "effect": inverted}


def evaluate_condition_or_instead_of_and(condition: str, context: dict[str, Any]) -> bool:
    """Evaluate condition but replace 'and' with 'or' (operator bug)."""
    modified = condition.replace(" and ", " or ")
    try:
        tree = ast.parse(modified, mode="eval")
    except SyntaxError:
        return False

    def _eval(node):
        if isinstance(node, ast.BoolOp):
            values = [_eval(v) for v in node.values]
            return any(values)
        if isinstance(node, ast.Compare):
            left = _eval(node.left)
            op_node = node.ops[0]
            right = _eval(node.comparators[0])
            for op_symbol, func in _COMPARISON_OPS.items():
                if isinstance(op_node, _op_class(op_symbol)):
                    return func(left, right)
            return False
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return context.get(node.id, None)
        return False

    return bool(_eval(tree.body))


def _op_class(symbol: str):
    mapping = {
        "==": ast.Eq,
        "!=": ast.NotEq,
        "<": ast.Lt,
        "<=": ast.LtE,
        ">": ast.Gt,
        ">=": ast.GtE,
    }
    return mapping[symbol]


def authorize_allow_all(
    subject: str | dict[str, Any],
    resource: str | dict[str, Any],
    action: str,
    policies: list[str] | list[dict[str, Any]],
    default: bool = False,
) -> bool:
    """Always return True (trivially wrong)."""
    return True


def authorize_deny_all(
    subject: str | dict[str, Any],
    resource: str | dict[str, Any],
    action: str,
    policies: list[str] | list[dict[str, Any]],
    default: bool = False,
) -> bool:
    """Always return False (trivially wrong)."""
    return False


def resolve_policies_allow_first(policies: list[str] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Sort policies so allow policies take precedence (priority reversed)."""
    parsed = []
    for p in policies:
        if isinstance(p, str):
            m = _POLICY_PATTERN.match(p)
            if m:
                parsed.append({"condition": m.group("condition").strip(), "effect": m.group("effect").strip()})
    return sorted(parsed, key=lambda p: 0 if p["effect"] == "allow" else 1)


def audit_access_no_decision(
    subject: str | dict[str, Any],
    resource: str | dict[str, Any],
    action: str,
    decision: bool,
) -> str:
    """Generate audit log but omit the decision (incomplete)."""
    if isinstance(subject, str):
        subject = parse_subject_missing_level(subject)
    if isinstance(resource, str):
        resource = parse_resource_wrong_sensitivity(resource)
    return (
        f"[{subject['role']}/{subject['department']}/L{subject['level']}] "
        f"{action} {resource['type']}:{resource['sensitivity']}:{resource['owner']}"
    )


def suggest_role_inverted_mapping(history: list[dict[str, Any]]) -> str:
    """Suggest a role with inverted action-to-role mapping."""
    if not history:
        return "director"
    counts: dict[str, int] = {}
    for entry in history:
        action = entry.get("action", "read")
        counts[action] = counts.get(action, 0) + 1
    top_action = max(counts, key=counts.get)
    mapping = {
        "read": "intern",
        "write": "director",
        "delete": "engineer",
        "admin": "manager",
    }
    return mapping.get(top_action, "director")


def format_subject_missing_level(role: str, department: str, level: int) -> str:
    """Format a subject string but omit the level field."""
    return f"role={role};department={department}"


def format_resource_wrong_sensitivity(type: str, sensitivity: str, owner: str) -> str:
    """Format a resource string with a hard-coded sensitivity."""
    return f"type={type};sensitivity=low;owner={owner}"


def make_policy_inverted_effect(condition: str, effect: str) -> str:
    """Format a policy with the effect inverted."""
    inverted = "deny" if effect == "allow" else "allow"
    return f"({condition}) -> {inverted}"


def is_admin_inverted(subject: str | dict[str, Any]) -> bool:
    """Return True for every role except admin."""
    if isinstance(subject, str):
        subject = parse_subject_missing_level(subject)
    return subject["role"] != "admin"


def subject_has_role_case_insensitive(subject: str | dict[str, Any], role: str) -> bool:
    """Compare roles case-insensitively (the real API uses exact match)."""
    if isinstance(subject, str):
        subject = parse_subject_missing_level(subject)
    return subject["role"].lower() == role.lower()


def subject_level_at_least_off_by_one(subject: str | dict[str, Any], min_level: int) -> bool:
    """Use a strict greater-than comparison instead of greater-or-equal."""
    if isinstance(subject, str):
        subject = parse_subject_missing_level(subject)
    return subject["level"] > min_level


def resource_owned_by_inverted(resource: str | dict[str, Any], department: str) -> bool:
    """Return True when the owner differs from the department."""
    if isinstance(resource, str):
        resource = parse_resource_wrong_sensitivity(resource)
    return resource["owner"] != department


def is_sensitive_wrong_threshold(resource: str | dict[str, Any], threshold: str = "medium") -> bool:
    """Treat 'low' as sensitive regardless of threshold."""
    if isinstance(resource, str):
        resource = parse_resource_wrong_sensitivity(resource)
    return resource["sensitivity"] != "low"


def resource_sensitivity_at_least_wrong(resource: str | dict[str, Any], threshold: str) -> bool:
    """Compare sensitivity names alphabetically instead of by severity."""
    if isinstance(resource, str):
        resource = parse_resource_wrong_sensitivity(resource)
    return resource["sensitivity"] >= threshold


def action_priority_swapped(action: str) -> int:
    """Return reversed priorities (read highest, admin lowest)."""
    if action not in _VALID_ACTIONS:
        raise ValueError(f"Invalid action: {action!r}")
    return {"read": 4, "write": 3, "delete": 2, "admin": 1}[action]


def count_matching_policies_ignore_effect(
    subject: str | dict[str, Any],
    resource: str | dict[str, Any],
    action: str,
    policies: list[str] | list[dict[str, Any]],
) -> int:
    """Return the total number of policies instead of matching ones."""
    return len(policies)


def list_allowed_actions_all_actions(
    subject: str | dict[str, Any],
    resource: str | dict[str, Any],
    policies: list[str] | list[dict[str, Any]],
    default: bool = False,
) -> list[str]:
    """Claim every action is allowed."""
    return list(_VALID_ACTIONS)
