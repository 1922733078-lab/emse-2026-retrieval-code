"""Unit tests for the Quorix Access Control Engine."""

import pytest

import quorix


def test_parse_subject():
    rec = quorix.parse_subject("role=manager;department=eng;level=3")
    assert rec == {"role": "manager", "department": "eng", "level": 3}


def test_parse_subject_invalid_role():
    with pytest.raises(ValueError):
        quorix.parse_subject("role=ceo;department=eng;level=3")


def test_parse_resource():
    rec = quorix.parse_resource("type=report;sensitivity=high;owner=hr")
    assert rec["sensitivity"] == "high"


def test_parse_policy():
    policy = quorix.parse_policy('(role == "manager") -> allow')
    assert policy["condition"] == 'role == "manager"'
    assert policy["effect"] == "allow"


def test_evaluate_condition_simple():
    ctx = {"role": "manager", "level": 3, "sensitivity": "high"}
    assert quorix.evaluate_condition('role == "manager"', ctx) is True
    assert quorix.evaluate_condition("level >= 3", ctx) is True
    assert quorix.evaluate_condition('sensitivity == "low"', ctx) is False


def test_evaluate_condition_compound():
    ctx = {"role": "manager", "level": 3, "sensitivity": "high"}
    assert quorix.evaluate_condition('role == "manager" and level >= 3', ctx) is True
    assert quorix.evaluate_condition('role == "engineer" or level >= 3', ctx) is True


def test_authorize_allow():
    subject = "role=manager;department=eng;level=3"
    resource = "type=report;sensitivity=high;owner=eng"
    policies = ['(role == "manager" and level >= 3) -> allow']
    assert quorix.authorize(subject, resource, "read", policies) is True


def test_authorize_deny_overrides():
    subject = "role=manager;department=eng;level=3"
    resource = "type=report;sensitivity=critical;owner=hr"
    policies = [
        '(role == "manager" and level >= 3) -> allow',
        '(sensitivity == "critical") -> deny',
    ]
    assert quorix.authorize(subject, resource, "read", policies) is False


def test_authorize_default_deny():
    subject = "role=intern;department=eng;level=1"
    resource = "type=report;sensitivity=high;owner=hr"
    policies = ['(role == "manager") -> allow']
    assert quorix.authorize(subject, resource, "read", policies, default=False) is False


def test_resolve_policies():
    policies = [
        '(role == "manager") -> allow',
        '(sensitivity == "critical") -> deny',
    ]
    ordered = quorix.resolve_policies(policies)
    assert ordered[0]["effect"] == "deny"
    assert ordered[1]["effect"] == "allow"


def test_audit_access():
    log = quorix.audit_access(
        "role=manager;department=eng;level=3",
        "type=report;sensitivity=high;owner=hr",
        "read",
        True,
    )
    assert "ALLOW" in log
    assert "manager" in log


def test_suggest_role():
    history = [{"action": "write"}, {"action": "write"}, {"action": "read"}]
    assert quorix.suggest_role(history) == "manager"
    assert quorix.suggest_role([]) == "intern"


def test_format_subject():
    assert quorix.format_subject("engineer", "eng", 2) == "role=engineer;department=eng;level=2"


def test_format_resource():
    assert quorix.format_resource("doc", "high", "hr") == "type=doc;sensitivity=high;owner=hr"


def test_make_policy():
    assert quorix.make_policy('role == "manager"', "allow") == '(role == "manager") -> allow'


def test_is_admin():
    assert quorix.is_admin("role=admin;department=ops;level=5") is True
    assert quorix.is_admin("role=engineer;department=eng;level=2") is False


def test_subject_level_at_least():
    assert quorix.subject_level_at_least("role=manager;department=eng;level=3", 3) is True
    assert quorix.subject_level_at_least("role=intern;department=eng;level=1", 2) is False


def test_resource_owned_by():
    assert quorix.resource_owned_by("type=report;sensitivity=high;owner=eng", "eng") is True
    assert quorix.resource_owned_by("type=report;sensitivity=high;owner=hr", "eng") is False


def test_is_sensitive():
    assert quorix.is_sensitive("type=report;sensitivity=high;owner=eng") is True
    assert quorix.is_sensitive("type=report;sensitivity=low;owner=eng", "high") is False


def test_action_priority():
    assert quorix.action_priority("admin") > quorix.action_priority("read")


def test_count_matching_policies():
    subject = "role=manager;department=eng;level=3"
    resource = "type=report;sensitivity=high;owner=eng"
    policies = ['(role == "manager") -> allow', '(sensitivity == "critical") -> deny']
    assert quorix.count_matching_policies(subject, resource, "read", policies) == 1


def test_list_allowed_actions():
    subject = "role=admin;department=ops;level=5"
    resource = "type=report;sensitivity=low;owner=ops"
    policies = ['(role == "admin") -> allow']
    assert "read" in quorix.list_allowed_actions(subject, resource, policies)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
