"""Build 90 real-world validation tasks (E9) from python-dateutil, humanize, tabulate.

The script imports the installed packages, uses deterministic, documented, public
functions to generate tasks, writes reference solution files, and validates every
visible/hidden test against the reference solution.

Outputs:
    realworld/tasks/realworld_tasks_final.jsonl
    realworld/tasks/task_validation_report.json
    realworld/solutions/<repo>/<task_id>.py
"""

from __future__ import annotations

import copy
import dateutil.tz
import json
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
REALWORLD_DIR = ROOT / "realworld"
TASKS_DIR = REALWORLD_DIR / "tasks"
SOL_DIR = REALWORLD_DIR / "solutions"
OUT_TASKS = TASKS_DIR / "realworld_tasks_final.jsonl"
OUT_REPORT = TASKS_DIR / "task_validation_report.json"

VISIBLE_COUNT = 2
HIDDEN_COUNT = 3


def repr_args(args: tuple[Any, ...]) -> str:
    return ", ".join(repr(a) for a in args)


def make_assert(function_name: str, args: tuple[Any, ...], expected: Any) -> str:
    return f"assert {function_name}({repr_args(args)}) == {repr(expected)}"


def exec_solution(code: str) -> dict[str, Any]:
    ns: dict[str, Any] = {}
    exec(code, ns)
    return ns


def run_assertions(code: str, assertions: list[str]) -> tuple[bool, str]:
    """Execute reference solution and a list of assert strings."""
    try:
        ns = exec_solution(code)
    except Exception as exc:  # pragma: no cover - validated before this call
        return False, f"solution import failed: {exc}"
    for assertion in assertions:
        try:
            exec(assertion, ns)
        except Exception as exc:
            return False, f"{assertion!r} -> {exc}"
    return True, ""


def build_task(repo: str, level: str, seq: int, template: dict[str, Any]) -> dict[str, Any] | None:
    task_id = f"{repo}_{level.lower()}_{seq:03d}"
    solution_code = template["solution"]
    signature = template["signature"]
    prompt = template["prompt"]

    sol_path = SOL_DIR / repo / f"{task_id}.py"
    sol_path.parent.mkdir(parents=True, exist_ok=True)
    sol_path.write_text(solution_code, encoding="utf-8")

    try:
        ns = exec_solution(solution_code)
        solve = ns["solve"]
    except Exception as exc:
        print(f"  {task_id}: solution import failed: {exc}")
        return None

    cases = template["cases"]
    expected_values: list[Any] = []
    for args in cases:
        try:
            expected_values.append(solve(*args))
        except Exception as exc:
            print(f"  {task_id}: case {args!r} raised {exc}; skipping task")
            return None

    visible_tests = [make_assert("solve", cases[i], expected_values[i]) for i in range(VISIBLE_COUNT)]
    hidden_tests = [
        make_assert("solve", cases[i], expected_values[i])
        for i in range(VISIBLE_COUNT, VISIBLE_COUNT + HIDDEN_COUNT)
    ]

    # Validate before keeping the task.
    ok, err = run_assertions(solution_code, visible_tests + hidden_tests)
    if not ok:
        print(f"  {task_id}: validation failed: {err}")
        return None

    return {
        "task_id": task_id,
        "repo": repo,
        "level": level,
        "prompt": prompt,
        "signature": signature,
        "visible_tests": visible_tests,
        "hidden_tests": hidden_tests,
        "reference_solution_path": str(sol_path.relative_to(ROOT)),
    }


# -----------------------------------------------------------------------------
# Repository-specific task templates
# -----------------------------------------------------------------------------

HUMANIZE_TEMPLATES: list[dict[str, Any]] = [
    # ------------------------- L1 ------------------------------------------------
    {
        "level": "L1",
        "signature": "def solve(n: int) -> str:",
        "prompt": "Implement `solve(n)` that returns the comma-separated decimal representation of `n` using `humanize.intcomma`.",
        "solution": "import humanize\n\ndef solve(n: int) -> str:\n    return humanize.intcomma(n)\n",
        "cases": [(1000,), (1234567,), (0,), (-1000,), (999,)],
    },
    {
        "level": "L1",
        "signature": "def solve(n) -> str:",
        "prompt": "Implement `solve(n)` that returns a human-readable word representation of a large number using `humanize.intword`.",
        "solution": "import humanize\n\ndef solve(n) -> str:\n    return humanize.intword(n)\n",
        "cases": [(1234567890,), (1000000,), (1500,), (1000000000000,), (0,)],
    },
    {
        "level": "L1",
        "signature": "def solve(n: int) -> str:",
        "prompt": "Implement `solve(n)` that returns the English word for small numbers and digits for larger ones using `humanize.apnumber`.",
        "solution": "import humanize\n\ndef solve(n: int) -> str:\n    return humanize.apnumber(n)\n",
        "cases": [(4,), (13,), (0,), (100,), (1,)],
    },
    {
        "level": "L1",
        "signature": "def solve(n: int) -> str:",
        "prompt": "Implement `solve(n)` that returns the ordinal string for an integer using `humanize.ordinal`.",
        "solution": "import humanize\n\ndef solve(n: int) -> str:\n    return humanize.ordinal(n)\n",
        "cases": [(5,), (22,), (1,), (3,), (100,)],
    },
    {
        "level": "L1",
        "signature": "def solve(x) -> str:",
        "prompt": "Implement `solve(x)` that returns a simple fractional representation of `x` using `humanize.fractional`.",
        "solution": "import humanize\n\ndef solve(x) -> str:\n    return humanize.fractional(x)\n",
        "cases": [(0.5,), (0.25,), (2.5,), (1.75,), (0.0,)],
    },
    {
        "level": "L1",
        "signature": "def solve(n: float) -> str:",
        "prompt": "Implement `solve(n)` that returns a human-readable file size using `humanize.naturalsize`.",
        "solution": "import humanize\n\ndef solve(n: float) -> str:\n    return humanize.naturalsize(n)\n",
        "cases": [(1024,), (2048,), (500,), (0,), (1048576,)],
    },
    {
        "level": "L1",
        "signature": "def solve(n: float) -> str:",
        "prompt": "Implement `solve(n)` that returns a binary (IEC) human-readable file size using `humanize.naturalsize`.",
        "solution": "import humanize\n\ndef solve(n: float) -> str:\n    return humanize.naturalsize(n, binary=True)\n",
        "cases": [(1024,), (2048,), (1536,), (1048576,), (0,)],
    },
    {
        "level": "L1",
        "signature": "def solve(x) -> str:",
        "prompt": "Implement `solve(x)` that returns a scientific notation string using `humanize.scientific`.",
        "solution": "import humanize\n\ndef solve(x) -> str:\n    return humanize.scientific(x)\n",
        "cases": [(0.00123,), (1230000,), (1,), (0.0,), (-500,)],
    },
    {
        "level": "L1",
        "signature": "def solve(x: float) -> str:",
        "prompt": "Implement `solve(x)` that returns a metric-prefixed string using `humanize.metric`.",
        "solution": "import humanize\n\ndef solve(x: float) -> str:\n    return humanize.metric(x)\n",
        "cases": [(0.001,), (1000,), (1000000,), (-0.002,), (0.000001,)],
    },
    {
        "level": "L1",
        "signature": "def solve(x: float) -> str:",
        "prompt": "Implement `solve(x)` that clamps `x` between 0 and 10 and returns the formatted string using `humanize.clamp`.",
        "solution": "import humanize\n\ndef solve(x: float) -> str:\n    return humanize.clamp(x, floor=0, ceil=10)\n",
        "cases": [(5.5,), (-3.0,), (12.0,), (0.0,), (10.0,)],
    },
    # ------------------------- L2 ------------------------------------------------
    {
        "level": "L2",
        "signature": "def solve(n: float) -> str:",
        "prompt": "Implement `solve(n)` that returns a binary file size with two decimal places using `humanize.naturalsize`.",
        "solution": "import humanize\n\ndef solve(n: float) -> str:\n    return humanize.naturalsize(n, binary=True, format='%.2f')\n",
        "cases": [(1536.0,), (1048576.0,), (1024.0,), (5368709120.0,), (0.0,)],
    },
    {
        "level": "L2",
        "signature": "def solve(n: float) -> str:",
        "prompt": "Implement `solve(n)` that returns a GNU-style file size using `humanize.naturalsize`.",
        "solution": "import humanize\n\ndef solve(n: float) -> str:\n    return humanize.naturalsize(n, gnu=True)\n",
        "cases": [(1024.0,), (1536.0,), (2048.0,), (0.0,), (5000000.0,)],
    },
    {
        "level": "L2",
        "signature": "def solve(n) -> str:",
        "prompt": "Implement `solve(n)` that returns a large number as words with two decimal places using `humanize.intword`.",
        "solution": "import humanize\n\ndef solve(n) -> str:\n    return humanize.intword(n, format='%.2f')\n",
        "cases": [(1234567890,), (1000000,), (1500000,), (1000,), (0,)],
    },
    {
        "level": "L2",
        "signature": "def solve(n: int, gender: str) -> str:",
        "prompt": "Implement `solve(n, gender)` that returns the ordinal string for `n`, selecting gender via `humanize.ordinal`.",
        "solution": "import humanize\n\ndef solve(n: int, gender: str) -> str:\n    return humanize.ordinal(n, gender=gender)\n",
        "cases": [(1, "male"), (2, "female"), (3, "male"), (21, "female"), (0, "male")],
    },
    {
        "level": "L2",
        "signature": "def solve(value: float, unit: str) -> str:",
        "prompt": "Implement `solve(value, unit)` that returns a metric-prefixed quantity with the given unit using `humanize.metric`.",
        "solution": "import humanize\n\ndef solve(value: float, unit: str) -> str:\n    return humanize.metric(value, unit=unit, precision=2)\n",
        "cases": [(0.001, "m"), (1000.0, "m"), (1e-06, "s"), (1000000.0, "Hz"), (10.0, "m")],
    },
    {
        "level": "L2",
        "signature": "def solve(value: float) -> str:",
        "prompt": "Implement `solve(value)` that clamps `value` between 0 and 100 using custom floor/ceil tokens via `humanize.clamp`.",
        "solution": "import humanize\n\ndef solve(value: float) -> str:\n    return humanize.clamp(value, format='{:.0f}', floor=0, ceil=100, floor_token='\u2264', ceil_token='\u2265')\n",
        "cases": [(-5.0,), (50.0,), (150.0,), (0.0,), (100.0,)],
    },
    {
        "level": "L2",
        "signature": "def solve(seconds: float) -> str:",
        "prompt": "Implement `solve(seconds)` that returns a natural-language duration with millisecond precision using `humanize.naturaldelta`.",
        "solution": "import datetime\nimport humanize\n\ndef solve(seconds: float) -> str:\n    return humanize.naturaldelta(datetime.timedelta(seconds=seconds), minimum_unit='milliseconds')\n",
        "cases": [(0.0015,), (0.5,), (0.0005,), (0.002,), (1.0,)],
    },
    {
        "level": "L2",
        "signature": "def solve(dt_str: str, when_str: str) -> str:",
        "prompt": "Implement `solve(dt_str, when_str)` that returns a natural-language relative time using `humanize.naturaltime`. Both inputs are ISO 8601 strings without timezone.",
        "solution": "import datetime\nimport humanize\n\ndef solve(dt_str: str, when_str: str) -> str:\n    dt = datetime.datetime.strptime(dt_str, '%Y-%m-%dT%H:%M:%S')\n    when = datetime.datetime.strptime(when_str, '%Y-%m-%dT%H:%M:%S')\n    return humanize.naturaltime(dt, when=when)\n",
        "cases": [
            ("2024-01-01T12:00:00", "2024-01-01T13:00:00"),
            ("2024-01-01T12:00:00", "2024-01-01T11:00:00"),
            ("2024-01-01T12:00:00", "2024-01-01T12:30:00"),
            ("2024-01-01T12:00:00", "2024-01-01T11:30:00"),
            ("2024-01-01T12:00:00", "2024-01-02T12:00:00"),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(value, ndigits: int) -> str:",
        "prompt": "Implement `solve(value, ndigits)` that formats a number with commas and rounds it to `ndigits` decimal places using `humanize.intcomma`.",
        "solution": "import humanize\n\ndef solve(value, ndigits: int) -> str:\n    return humanize.intcomma(value, ndigits=ndigits)\n",
        "cases": [(1234.567, 2), (1234567, 0), (1234.5, 1), (0.12345, 3), (-9999.99, 1)],
    },
    {
        "level": "L2",
        "signature": "def solve(total_seconds: int) -> str:",
        "prompt": "Implement `solve(total_seconds)` that returns a precise duration while suppressing seconds and milliseconds using `humanize.precisedelta`.",
        "solution": "import datetime\nimport humanize\n\ndef solve(total_seconds: int) -> str:\n    return humanize.precisedelta(datetime.timedelta(seconds=total_seconds), suppress=['seconds', 'milliseconds'])\n",
        "cases": [(7385,), (9000,), (3600,), (86400,), (0,)],
    },
    # ------------------------- L3 ------------------------------------------------
    {
        "level": "L3",
        "signature": "def solve(sizes: list) -> str:",
        "prompt": "Implement `solve(sizes)` that returns a comma-separated list of binary file sizes with two decimal places using `humanize.naturalsize`.",
        "solution": "import humanize\n\ndef solve(sizes: list) -> str:\n    return ', '.join(humanize.naturalsize(s, binary=True, format='%.2f') for s in sizes)\n",
        "cases": [([1024, 2048],), ([0, 1048576],), ([1536, 3072],), ([1024],), ([5368709120, 2048],)],
    },
    {
        "level": "L3",
        "signature": "def solve(n: int) -> str:",
        "prompt": "Implement `solve(n)` that returns a count formatted with commas and as a human-readable word using `humanize.intcomma` and `humanize.intword`.",
        "solution": "import humanize\n\ndef solve(n: int) -> str:\n    return f\"{humanize.intcomma(n)} ({humanize.intword(n)})\"\n",
        "cases": [(1000000,), (1234567890,), (1500,), (0,), (999999,)],
    },
    {
        "level": "L3",
        "signature": "def solve(ratio: float) -> str:",
        "prompt": "Implement `solve(ratio)` that converts a ratio to a percentage string clamped between 0% and 100% using `humanize.clamp`.",
        "solution": "import humanize\n\ndef solve(ratio: float) -> str:\n    return humanize.clamp(ratio * 100, format='{:.1f}%', floor=0, ceil=100)\n",
        "cases": [(0.5,), (1.2,), (-0.1,), (0.0,), (1.0,)],
    },
    {
        "level": "L3",
        "signature": "def solve(side_m: float) -> str:",
        "prompt": "Implement `solve(side_m)` that computes the area of a square in square meters and returns a metric-prefixed string using `humanize.metric`.",
        "solution": "import humanize\n\ndef solve(side_m: float) -> str:\n    return humanize.metric(side_m ** 2, unit='m\u00b2', precision=2)\n",
        "cases": [(0.001,), (1000.0,), (2.0,), (100.0,), (0.0001,)],
    },
    {
        "level": "L3",
        "signature": "def solve(items: list) -> str:",
        "prompt": "Implement `solve(items)` that formats each (label, count) pair on its own line, turning the count into a human word using `humanize.intword`.",
        "solution": "import humanize\n\ndef solve(items: list) -> str:\n    return '\\n'.join(f\"{k}: {humanize.intword(v)}\" for k, v in items)\n",
        "cases": [
            ([("a", 1000), ("b", 1000000)],),
            ([("x", 1234567890)],),
            ([("views", 1500), ("downloads", 5000000)],),
            ([],),
            ([("count", 0)],),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(n: int) -> str:",
        "prompt": "Implement `solve(n)` that returns both the spelled-out number and its ordinal using `humanize.apnumber` and `humanize.ordinal`.",
        "solution": "import humanize\n\ndef solve(n: int) -> str:\n    return f\"{humanize.apnumber(n)} {humanize.ordinal(n)}\"\n",
        "cases": [(1,), (4,), (21,), (100,), (0,)],
    },
    {
        "level": "L3",
        "signature": "def solve(lo: float, hi: float) -> str:",
        "prompt": "Implement `solve(lo, hi)` that returns a clamped range string, formatting each endpoint with `humanize.clamp`.",
        "solution": "import humanize\n\ndef solve(lo: float, hi: float) -> str:\n    return f\"{humanize.clamp(lo, format='{:.0f}', floor=0)}-{humanize.clamp(hi, format='{:.0f}', ceil=100)}\"\n",
        "cases": [(-5.0, 150.0), (0.0, 50.0), (10.0, 90.0), (-10.0, 200.0), (0.0, 0.0)],
    },
    {
        "level": "L3",
        "signature": "def solve(x: float) -> str:",
        "prompt": "Implement `solve(x)` that returns a metric-prefixed gram string for values with magnitude at least 1, and scientific notation for smaller values using `humanize.metric` and `humanize.scientific`.",
        "solution": "import humanize\n\ndef solve(x: float) -> str:\n    if abs(x) >= 1:\n        return humanize.metric(x, unit='g', precision=2)\n    return humanize.scientific(x, precision=2)\n",
        "cases": [(1000.0,), (0.00123,), (0.5,), (5000000.0,), (0.000001,)],
    },
    {
        "level": "L3",
        "signature": "def solve(sizes: list) -> str:",
        "prompt": "Implement `solve(sizes)` that returns a GNU-style size string joined by pipes using `humanize.naturalsize`.",
        "solution": "import humanize\n\ndef solve(sizes: list) -> str:\n    return '|'.join(humanize.naturalsize(s, gnu=True) for s in sizes)\n",
        "cases": [([1024, 1536],), ([0, 1048576],), ([2048, 3072],), ([1024],), ([],)],
    },
    {
        "level": "L3",
        "signature": "def solve(values: list) -> str:",
        "prompt": "Implement `solve(values)` that returns a comma-separated list of fractional representations using `humanize.fractional`.",
        "solution": "import humanize\n\ndef solve(values: list) -> str:\n    return ', '.join(humanize.fractional(v) for v in values)\n",
        "cases": [([0.5, 0.25],), ([2.5, 1.75],), ([0.0, 0.125],), ([1.0],), ([],)],
    },
]


DATEUTIL_TEMPLATES: list[dict[str, Any]] = [
    # ------------------------- L1 ------------------------------------------------
    {
        "level": "L1",
        "signature": "def solve(s: str) -> str:",
        "prompt": "Implement `solve(s)` that parses an ISO 8601 timestamp using `dateutil.parser.isoparse` and returns it as an ISO string.",
        "solution": "import dateutil.parser\n\ndef solve(s: str) -> str:\n    return dateutil.parser.isoparse(s).isoformat()\n",
        "cases": [
            ("2024-03-15",),
            ("2024-12-31T23:59:59",),
            ("2020-02-29",),
            ("2023-01-01T00:00:00+00:00",),
            ("2024-06-01T12:30:00",),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(s: str) -> str:",
        "prompt": "Implement `solve(s)` that parses a date/time string using `dateutil.parser.parse` and returns the result as an ISO string.",
        "solution": "import dateutil.parser\n\ndef solve(s: str) -> str:\n    return dateutil.parser.parse(s).isoformat()\n",
        "cases": [
            ("2024-03-15 14:30",),
            ("2023-12-25",),
            ("2024-01-01 00:00:00",),
            ("2025-07-04 09:00:00",),
            ("2022-11-11 11:11:11",),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(s: str) -> str:",
        "prompt": "Implement `solve(s)` that parses a day-first date string using `dateutil.parser.parse(dayfirst=True)` and returns the result as an ISO string.",
        "solution": "import dateutil.parser\n\ndef solve(s: str) -> str:\n    return dateutil.parser.parse(s, dayfirst=True).isoformat()\n",
        "cases": [
            ("15/03/2024 14:30",),
            ("31/12/2023",),
            ("01/02/2024",),
            ("29/02/2024 00:00:00",),
            ("11/11/2022 11:11:11",),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(year: int) -> str:",
        "prompt": "Implement `solve(year)` that returns the date of Easter Sunday for the given year using `dateutil.easter.easter`.",
        "solution": "import dateutil.easter\n\ndef solve(year: int) -> str:\n    return dateutil.easter.easter(year).isoformat()\n",
        "cases": [(2024,), (2025,), (2023,), (2022,), (2020,)],
    },
    {
        "level": "L1",
        "signature": "def solve(d: date) -> str:",
        "prompt": "Implement `solve(d)` that adds three months to a date using `dateutil.relativedelta.relativedelta` and returns the ISO date string.",
        "solution": "import datetime\nimport dateutil.relativedelta\n\ndef solve(d: datetime.date) -> str:\n    return (d + dateutil.relativedelta.relativedelta(months=+3)).isoformat()\n",
        "cases": [
            (date(2024, 1, 15),),
            (date(2023, 5, 31),),
            (date(2020, 2, 29),),
            (date(2022, 11, 30),),
            (date(2024, 12, 1),),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(d: date) -> str:",
        "prompt": "Implement `solve(d)` that returns the last day of the month for the month containing `d` using `dateutil.relativedelta.relativedelta`.",
        "solution": "import datetime\nimport dateutil.relativedelta\n\ndef solve(d: datetime.date) -> str:\n    return (d + dateutil.relativedelta.relativedelta(day=31)).isoformat()\n",
        "cases": [
            (date(2024, 2, 15),),
            (date(2023, 2, 15),),
            (date(2024, 4, 15),),
            (date(2024, 1, 15),),
            (date(2023, 11, 15),),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(name: str, hours: float) -> float:",
        "prompt": "Implement `solve(name, hours)` that creates a fixed-offset timezone with `dateutil.tz.tzoffset` and returns the UTC offset in seconds.",
        "solution": "import dateutil.tz\n\ndef solve(name: str, hours: float) -> float:\n    return dateutil.tz.tzoffset(name, hours * 3600).utcoffset(None).total_seconds()\n",
        "cases": [("EST", -5.0), ("CET", 1.0), ("UTC", 0.0), ("IST", 5.5), ("PST", -8.0)],
    },
    {
        "level": "L1",
        "signature": "def solve(dt: datetime) -> str:",
        "prompt": "Implement `solve(dt)` that attaches the UTC timezone to a naive datetime using `dateutil.utils.default_tzinfo` and returns the ISO string.",
        "solution": "import datetime\nimport dateutil.tz\nimport dateutil.utils\n\ndef solve(dt: datetime.datetime) -> str:\n    return dateutil.utils.default_tzinfo(dt, dateutil.tz.UTC).isoformat()\n",
        "cases": [
            (datetime(2024, 1, 1),),
            (datetime(2020, 2, 29, 12, 0),),
            (datetime(2023, 6, 15, 23, 59, 59),),
            (datetime(2024, 1, 1, 0, 0),),
            (datetime(2022, 12, 31, 23, 0),),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(dt1: datetime, dt2: datetime) -> bool:",
        "prompt": "Implement `solve(dt1, dt2)` that returns whether two datetimes are within one hour of each other using `dateutil.utils.within_delta`.",
        "solution": "import datetime\nimport dateutil.utils\n\ndef solve(dt1: datetime.datetime, dt2: datetime.datetime) -> bool:\n    return dateutil.utils.within_delta(dt1, dt2, datetime.timedelta(hours=1))\n",
        "cases": [
            (datetime(2024, 1, 1, 12, 0), datetime(2024, 1, 1, 12, 30)),
            (datetime(2024, 1, 1, 12, 0), datetime(2024, 1, 1, 13, 0)),
            (datetime(2024, 1, 1, 12, 0), datetime(2024, 1, 1, 14, 0)),
            (datetime(2024, 1, 1, 12, 0), datetime(2024, 1, 1, 12, 59)),
            (datetime(2024, 1, 1, 12, 0), datetime(2024, 1, 1, 12, 0)),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(s: str) -> bool:",
        "prompt": "Implement `solve(s)` that parses an ISO timestamp, attaches the UTC timezone, and checks whether the datetime exists using `dateutil.tz.datetime_exists`.",
        "solution": "import dateutil.parser\nimport dateutil.tz\n\ndef solve(s: str) -> bool:\n    dt = dateutil.parser.isoparse(s).replace(tzinfo=dateutil.tz.UTC)\n    return dateutil.tz.datetime_exists(dt, dateutil.tz.UTC)\n",
        "cases": [
            ("2024-03-10T02:30:00",),
            ("2024-01-01T00:00:00",),
            ("2020-02-29T12:00:00",),
            ("2023-06-15T23:59:59",),
            ("2022-12-31T23:00:00",),
        ],
    },
    # ------------------------- L2 ------------------------------------------------
    {
        "level": "L2",
        "signature": "def solve(s: str, fmt: str) -> str:",
        "prompt": "Implement `solve(s, fmt)` that parses an ISO timestamp with `dateutil.parser.isoparse` and formats it with `strftime`.",
        "solution": "import dateutil.parser\n\ndef solve(s: str, fmt: str) -> str:\n    return dateutil.parser.isoparse(s).strftime(fmt)\n",
        "cases": [
            ("2024-03-15", "%Y/%m/%d"),
            ("2024-12-31T23:59:59", "%H:%M:%S"),
            ("2020-02-29", "%j"),
            ("2024-06-01T12:30:00", "%A, %B %d"),
            ("2023-01-01T00:00:00+00:00", "%Y-%m-%d"),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(s: str) -> str:",
        "prompt": "Implement `solve(s)` that extracts a date from free-form text using `dateutil.parser.parse(fuzzy=True)` and returns the ISO string.",
        "solution": "import dateutil.parser\n\ndef solve(s: str) -> str:\n    return dateutil.parser.parse(s, fuzzy=True).isoformat()\n",
        "cases": [
            ("Today is 2024-03-15",),
            ("Meeting: 2023-12-25 at 10:00",),
            ("Deadline 2022-11-11",),
            ("Event on 2025-07-04",),
            ("Start 2020-02-29 end",),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(s: str) -> str:",
        "prompt": "Implement `solve(s)` that parses a date/time string and returns only the date part as an ISO string.",
        "solution": "import dateutil.parser\n\ndef solve(s: str) -> str:\n    return dateutil.parser.parse(s).date().isoformat()\n",
        "cases": [
            ("2024-03-15 14:30",),
            ("2023-12-25 00:00:00",),
            ("2025-07-04 09:00:00",),
            ("2022-11-11 11:11:11",),
            ("2020-02-29 23:59:59",),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(year: int, method: int) -> str:",
        "prompt": "Implement `solve(year, method)` that computes the Easter date for a given method using `dateutil.easter.easter` and returns it as an ISO string.",
        "solution": "import dateutil.easter\n\ndef solve(year: int, method: int) -> str:\n    return dateutil.easter.easter(year, method).isoformat()\n",
        "cases": [(2024, 3), (2025, 3), (2023, 3), (2022, 3), (2020, 3)],
    },
    {
        "level": "L2",
        "signature": "def solve(d: date) -> str:",
        "prompt": "Implement `solve(d)` that returns the next Friday on or after `d` using `dateutil.relativedelta.relativedelta`.",
        "solution": "import datetime\nimport dateutil.relativedelta\n\ndef solve(d: datetime.date) -> str:\n    return (d + dateutil.relativedelta.relativedelta(weekday=dateutil.relativedelta.FR)).isoformat()\n",
        "cases": [
            (date(2024, 3, 11),),
            (date(2024, 3, 13),),
            (date(2024, 3, 14),),
            (date(2024, 3, 16),),
            (date(2024, 3, 17),),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(d: date) -> str:",
        "prompt": "Implement `solve(d)` that returns the last day of the month after `d` using `dateutil.relativedelta.relativedelta`.",
        "solution": "import datetime\nimport dateutil.relativedelta\n\ndef solve(d: datetime.date) -> str:\n    return (d + dateutil.relativedelta.relativedelta(months=+1, day=31)).isoformat()\n",
        "cases": [
            (date(2024, 1, 15),),
            (date(2023, 1, 15),),
            (date(2024, 3, 15),),
            (date(2023, 11, 15),),
            (date(2024, 5, 31),),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(s: str, hours: int) -> str:",
        "prompt": "Implement `solve(s, hours)` that parses an ISO timestamp and replaces its timezone with a fixed offset of `hours` using `dateutil.tz.tzoffset`.",
        "solution": "import dateutil.parser\nimport dateutil.tz\n\ndef solve(s: str, hours: int) -> str:\n    dt = dateutil.parser.isoparse(s)\n    return dt.replace(tzinfo=dateutil.tz.tzoffset(None, hours * 3600)).isoformat()\n",
        "cases": [
            ("2024-01-01T12:00:00", -5),
            ("2024-06-01T00:00:00", 0),
            ("2024-03-15T08:30:00", 3),
            ("2023-12-31T23:00:00", -8),
            ("2025-07-04T12:00:00", 1),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(s: str) -> str:",
        "prompt": "Implement `solve(s)` that resolves an imaginary datetime in the UTC timezone using `dateutil.tz.resolve_imaginary` and returns the ISO string.",
        "solution": "import dateutil.parser\nimport dateutil.tz\n\ndef solve(s: str) -> str:\n    dt = dateutil.parser.isoparse(s).replace(tzinfo=dateutil.tz.UTC)\n    return dateutil.tz.resolve_imaginary(dt).isoformat()\n",
        "cases": [
            ("2024-01-01T12:00:00",),
            ("2020-02-29T23:59:59",),
            ("2023-06-15T00:00:00",),
            ("2022-12-31T23:00:00",),
            ("2025-07-04T12:00:00",),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(d: date) -> str:",
        "prompt": "Implement `solve(d)` that adds two years and subtracts one month from `d` using `dateutil.relativedelta.relativedelta`.",
        "solution": "import datetime\nimport dateutil.relativedelta\n\ndef solve(d: datetime.date) -> str:\n    return (d + dateutil.relativedelta.relativedelta(years=+2, months=-1)).isoformat()\n",
        "cases": [
            (date(2022, 5, 20),),
            (date(2020, 1, 31),),
            (date(2024, 3, 31),),
            (date(2023, 8, 15),),
            (date(2021, 6, 30),),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(s: str) -> int:",
        "prompt": "Implement `solve(s)` that parses an ISO timestamp and returns its proleptic Gregorian ordinal using `dateutil.parser.isoparse`.",
        "solution": "import dateutil.parser\n\ndef solve(s: str) -> int:\n    return dateutil.parser.isoparse(s).toordinal()\n",
        "cases": [
            ("2024-01-01",),
            ("2020-02-29",),
            ("2023-12-31",),
            ("2025-07-04",),
            ("2022-11-11",),
        ],
    },
    # ------------------------- L3 ------------------------------------------------
    {
        "level": "L3",
        "signature": "def solve(year: int) -> str:",
        "prompt": "Implement `solve(year)` that returns the date of Good Friday (Easter Sunday minus two days) using `dateutil.easter.easter` and `dateutil.relativedelta.relativedelta`.",
        "solution": "import dateutil.easter\nimport dateutil.relativedelta\n\ndef solve(year: int) -> str:\n    e = dateutil.easter.easter(year)\n    return (e + dateutil.relativedelta.relativedelta(days=-2)).isoformat()\n",
        "cases": [(2024,), (2025,), (2023,), (2022,), (2020,)],
    },
    {
        "level": "L3",
        "signature": "def solve(year: int) -> int:",
        "prompt": "Implement `solve(year)` that returns the number of days from January 1st of `year` to Easter Sunday using `dateutil.easter.easter`.",
        "solution": "import datetime\nimport dateutil.easter\n\ndef solve(year: int) -> int:\n    return (dateutil.easter.easter(year) - datetime.date(year, 1, 1)).days\n",
        "cases": [(2024,), (2025,), (2023,), (2022,), (2020,)],
    },
    {
        "level": "L3",
        "signature": "def solve(s: str) -> str:",
        "prompt": "Implement `solve(s)` that parses an RFC 3339 timestamp and converts it to UTC using `dateutil.parser.isoparse`; return the ISO string.",
        "solution": "import dateutil.parser\nimport dateutil.tz\n\ndef solve(s: str) -> str:\n    dt = dateutil.parser.isoparse(s)\n    if dt.tzinfo is not None:\n        dt = dt.astimezone(dateutil.tz.UTC)\n    return dt.isoformat()\n",
        "cases": [
            ("2024-06-01T12:00:00+02:00",),
            ("2024-01-01T08:30:00-05:00",),
            ("2024-03-15T00:00:00Z",),
            ("2025-07-04T20:00:00+00:00",),
            ("2023-12-31T23:00:00-03:00",),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(year: int, month: int) -> str:",
        "prompt": "Implement `solve(year, month)` that returns the last day of the given month using `dateutil.relativedelta.relativedelta`.",
        "solution": "import datetime\nimport dateutil.relativedelta\n\ndef solve(year: int, month: int) -> str:\n    d = datetime.date(year, month, 1)\n    return (d + dateutil.relativedelta.relativedelta(months=+1, days=-1)).isoformat()\n",
        "cases": [(2024, 2), (2023, 2), (2024, 1), (2024, 4), (2023, 11)],
    },
    {
        "level": "L3",
        "signature": "def solve(d: date, n: int) -> str:",
        "prompt": "Implement `solve(d, n)` that adds `n` weekdays (skipping weekends) to `d` using `dateutil.relativedelta.relativedelta`.",
        "solution": "import datetime\nimport dateutil.relativedelta\n\ndef solve(d: datetime.date, n: int) -> str:\n    cur = d\n    added = 0\n    while added < n:\n        cur += dateutil.relativedelta.relativedelta(days=+1)\n        if cur.weekday() < 5:\n            added += 1\n    return cur.isoformat()\n",
        "cases": [
            (date(2024, 3, 14), 2),
            (date(2024, 3, 15), 1),
            (date(2024, 3, 16), 1),
            (date(2024, 3, 1), 5),
            (date(2024, 3, 11), 10),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(year: int, month: int) -> int:",
        "prompt": "Implement `solve(year, month)` that counts how many Sundays occur in the given month using `dateutil.relativedelta.relativedelta`.",
        "solution": "import datetime\nimport dateutil.relativedelta\n\ndef solve(year: int, month: int) -> int:\n    d = datetime.date(year, month, 1)\n    count = 0\n    while d.month == month:\n        if d.weekday() == 6:\n            count += 1\n        d += dateutil.relativedelta.relativedelta(days=+1)\n    return count\n",
        "cases": [(2024, 3), (2024, 2), (2023, 5), (2024, 9), (2024, 12)],
    },
    {
        "level": "L3",
        "signature": "def solve(s: str) -> tuple:",
        "prompt": "Implement `solve(s)` that parses an ISO timestamp and returns the ISO date strings of the Monday and Sunday of that week using `dateutil.relativedelta.relativedelta`.",
        "solution": "import dateutil.parser\nimport dateutil.relativedelta\n\ndef solve(s: str) -> tuple:\n    dt = dateutil.parser.isoparse(s)\n    start = dt - dateutil.relativedelta.relativedelta(days=dt.weekday())\n    end = start + dateutil.relativedelta.relativedelta(days=6)\n    return (start.date().isoformat(), end.date().isoformat())\n",
        "cases": [
            ("2024-03-15",),
            ("2024-01-01",),
            ("2023-12-31",),
            ("2020-02-29",),
            ("2025-07-04",),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(s: str, offset_h: int) -> str:",
        "prompt": "Implement `solve(s, offset_h)` that parses an ISO timestamp and converts it to a fixed-offset timezone using `dateutil.tz.tzoffset`; return the ISO string.",
        "solution": "import dateutil.parser\nimport dateutil.tz\n\ndef solve(s: str, offset_h: int) -> str:\n    dt = dateutil.parser.isoparse(s)\n    tz = dateutil.tz.tzoffset('X', offset_h * 3600)\n    return dt.astimezone(tz).isoformat()\n",
        "cases": [
            ("2024-01-01T12:00:00+00:00", -5),
            ("2024-06-01T00:00:00Z", 3),
            ("2024-03-15T08:30:00+02:00", 0),
            ("2023-12-31T23:00:00-08:00", 1),
            ("2025-07-04T12:00:00+05:00", -3),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(s1: str, s2: str) -> str:",
        "prompt": "Implement `solve(s1, s2)` that parses two ISO date strings and returns the difference as a 'Y#M#D#' string using `dateutil.relativedelta.relativedelta`.",
        "solution": "import dateutil.parser\nimport dateutil.relativedelta\n\ndef solve(s1: str, s2: str) -> str:\n    d1 = dateutil.parser.isoparse(s1).date()\n    d2 = dateutil.parser.isoparse(s2).date()\n    rd = dateutil.relativedelta.relativedelta(d2, d1)\n    return f\"{rd.years}y{rd.months}m{rd.days}d\"\n",
        "cases": [
            ("2022-02-15", "2024-05-10"),
            ("2020-01-01", "2020-03-15"),
            ("2023-08-01", "2024-08-01"),
            ("2019-12-31", "2020-01-01"),
            ("2021-05-20", "2022-05-20"),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(year: int, month: int, weekday: int, n: int) -> str:",
        "prompt": "Implement `solve(year, month, weekday, n)` that returns the ISO date of the `n`-th occurrence of `weekday` (0=Monday) in the given month using `dateutil.relativedelta.relativedelta`.",
        "solution": "import datetime\nimport dateutil.relativedelta\n\ndef solve(year: int, month: int, weekday: int, n: int) -> str:\n    d = datetime.date(year, month, 1)\n    count = 0\n    while d.month == month:\n        if d.weekday() == weekday:\n            count += 1\n            if count == n:\n                return d.isoformat()\n        d += dateutil.relativedelta.relativedelta(days=+1)\n    raise ValueError('not found')\n",
        "cases": [
            (2024, 3, 0, 1),
            (2024, 3, 4, 1),
            (2024, 3, 6, 2),
            (2024, 2, 4, 4),
            (2024, 12, 2, 2),
        ],
    },
]


TABULATE_TEMPLATES: list[dict[str, Any]] = [
    # ------------------------- L1 ------------------------------------------------
    {
        "level": "L1",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table with headers 'Name' and 'Score' using `tabulate.tabulate` with the 'plain' format.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers=['Name', 'Score'], tablefmt='plain')\n",
        "cases": [
            ([["Alice", 90]],),
            ([["Bob", 85]],),
            ([["Carol", 78]],),
            ([["Dave", 92]],),
            ([["Eve", 88]],),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table with headers 'Name' and 'Score' using `tabulate.tabulate` with the 'grid' format.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers=['Name', 'Score'], tablefmt='grid')\n",
        "cases": [
            ([["Alice", 90]],),
            ([["Bob", 85]],),
            ([["Carol", 78]],),
            ([["Dave", 92]],),
            ([["Eve", 88]],),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a list of dictionaries as a table using `tabulate.tabulate` with `headers='keys'` and the 'simple' format.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers='keys', tablefmt='simple')\n",
        "cases": [
            ([{"a": 1, "b": 2}],),
            ([{"a": 10, "b": 20}],),
            ([{"a": 5, "b": 7}],),
            ([{"a": 0, "b": 0}],),
            ([{"a": 100, "b": 200}],),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table separated by pipes using `tabulate.tabulate` with `tabulate.simple_separated_format`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers=['Name', 'Score'], tablefmt=tabulate.simple_separated_format('|'))\n",
        "cases": [
            ([["Alice", 90]],),
            ([["Bob", 85]],),
            ([["Carol", 78]],),
            ([["Dave", 92]],),
            ([["Eve", 88]],),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table of floats with two decimal places using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, floatfmt='.2f', tablefmt='plain')\n",
        "cases": [
            ([[1, 3.14159]],),
            ([[2, 2.71828]],),
            ([[0, 0.5]],),
            ([[10, 1.0]],),
            ([[3, 1.41421]],),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table including an automatic row index using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, showindex=True, tablefmt='plain')\n",
        "cases": [
            ([["Alice", 90]],),
            ([["Bob", 85]],),
            ([["Carol", 78]],),
            ([["Dave", 92]],),
            ([["Eve", 88]],),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table, replacing missing values with 'N/A' using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, missingval='N/A', tablefmt='plain')\n",
        "cases": [
            ([["Alice", None]],),
            ([["Bob", 85]],),
            ([["Carol", None]],),
            ([["Dave", 92]],),
            ([["Eve", None]],),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table with numeric columns right-aligned using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers=['A', 'B'], numalign='right', tablefmt='plain')\n",
        "cases": [
            ([[1, 2]],),
            ([[10, 20]],),
            ([[5, 7]],),
            ([[0, 0]],),
            ([[100, 200]],),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table with string columns center-aligned using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers=['Name'], stralign='center', tablefmt='plain')\n",
        "cases": [
            ([["Alice"]],),
            ([["Bob"]],),
            ([["Carol"]],),
            ([["Dave"]],),
            ([["Eve"]],),
        ],
    },
    {
        "level": "L1",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table using the first row as headers with `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers='firstrow', tablefmt='plain')\n",
        "cases": [
            ([["Name", "Score"], ["Alice", 90]],),
            ([["Name", "Score"], ["Bob", 85]],),
            ([["Name", "Score"], ["Carol", 78]],),
            ([["Name", "Score"], ["Dave", 92]],),
            ([["Name", "Score"], ["Eve", 88]],),
        ],
    },
    # ------------------------- L2 ------------------------------------------------
    {
        "level": "L2",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table with a maximum column width of 5 characters using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers=['Long'], maxcolwidths=[5], tablefmt='plain')\n",
        "cases": [
            ([["Hello world"]],),
            ([["Goodbye"]],),
            ([["1234567890"]],),
            ([["short"]],),
            ([["A longer phrase"]],),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table with per-column alignment using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers=['X', 'Y'], colalign=('left', 'right'), tablefmt='plain')\n",
        "cases": [
            ([["A", 1]],),
            ([["B", 20]],),
            ([["C", 300]],),
            ([["D", 0]],),
            ([["E", 42]],),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table with a comma separator format and two decimal places using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers=['A', 'B'], tablefmt=tabulate.simple_separated_format(','), floatfmt='.2f')\n",
        "cases": [
            ([[1, 3.14159]],),
            ([[2, 2.71828]],),
            ([[0, 0.5]],),
            ([[10, 1.0]],),
            ([[3, 1.41421]],),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table with zero-padded four-digit integers using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, intfmt='04d', tablefmt='plain')\n",
        "cases": [
            ([[5, 12]],),
            ([[1, 100]],),
            ([[9999, 7]],),
            ([[0, 0]],),
            ([[42, 123]],),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table while disabling numeric parsing so strings are preserved using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, disable_numparse=True, tablefmt='plain')\n",
        "cases": [
            ([["00123"]],),
            ([["0456"]],),
            ([["1.00"]],),
            ([["000"]],),
            ([["999"]],),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a Markdown-compatible pipe table using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers=['Name', 'Score'], tablefmt='pipe')\n",
        "cases": [
            ([["Alice", 90]],),
            ([["Bob", 85]],),
            ([["Carol", 78]],),
            ([["Dave", 92]],),
            ([["Eve", 88]],),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a simple table from dictionaries using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers='keys', tablefmt='simple')\n",
        "cases": [
            ([{"x": 1, "y": 2}],),
            ([{"x": 10, "y": 20}],),
            ([{"x": 5, "y": 7}],),
            ([{"x": 0, "y": 0}],),
            ([{"x": 100, "y": 200}],),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table with right-aligned numbers and three decimal places using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers=['I', 'F'], numalign='right', floatfmt='.3f', tablefmt='plain')\n",
        "cases": [
            ([[1, 3.14159]],),
            ([[2, 2.71828]],),
            ([[0, 0.5]],),
            ([[10, 1.0]],),
            ([[3, 1.41421]],),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table with custom index labels using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers=['X', 'Y'], showindex=['a', 'b'], tablefmt='plain')\n",
        "cases": [
            ([[1, 2], [3, 4]],),
            ([[10, 20], [30, 40]],),
            ([[5, 6], [7, 8]],),
            ([[0, 0], [1, 1]],),
            ([[9, 8], [7, 6]],),
        ],
    },
    {
        "level": "L2",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that formats a table with a limited header column width using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    return tabulate.tabulate(data, headers=['VeryLongHeader'], maxheadercolwidths=[4], tablefmt='plain')\n",
        "cases": [
            ([[12345]],),
            ([[67890]],),
            ([[0]],),
            ([[42]],),
            ([[99999]],),
        ],
    },
    # ------------------------- L3 ------------------------------------------------
    {
        "level": "L3",
        "signature": "def solve(rows: list) -> str:",
        "prompt": "Implement `solve(rows)` that returns a grid-formatted summary table of items and values using `tabulate.tabulate`, formatting floats to one decimal place.",
        "solution": "import tabulate\n\ndef solve(rows: list) -> str:\n    return tabulate.tabulate(rows, headers=['Item', 'Value'], floatfmt='.1f', tablefmt='grid')\n",
        "cases": [
            ([["A", 3.14159]],),
            ([["B", 2.71828]],),
            ([["C", 1.41421]],),
            ([["D", 0.0]],),
            ([["E", 100.5]],),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(rows: list) -> str:",
        "prompt": "Implement `solve(rows)` that formats a table with row indices and '?' for missing values using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(rows: list) -> str:\n    return tabulate.tabulate(rows, headers=['A', 'B'], showindex=True, missingval='?', tablefmt='plain')\n",
        "cases": [
            ([[1, None]],),
            ([[None, 2]],),
            ([[3, 4]],),
            ([[None, None]],),
            ([[5, 6]],),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(data: list) -> str:",
        "prompt": "Implement `solve(data)` that transposes a rectangular matrix and formats it using `tabulate.tabulate` with the first row as headers.",
        "solution": "import tabulate\n\ndef solve(data: list) -> str:\n    transposed = list(zip(*data))\n    return tabulate.tabulate(transposed, headers='firstrow', tablefmt='plain')\n",
        "cases": [
            ([["Name", "Score"], ["Alice", 90], ["Bob", 85]],),
            ([["Name", "Score"], ["Carol", 78], ["Dave", 92]],),
            ([["X", "Y"], [1, 2], [3, 4]],),
            ([["X", "Y"], [10, 20], [30, 40]],),
            ([["A", "B"], [5, 6], [7, 8]],),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(rows: list, threshold: int) -> str:",
        "prompt": "Implement `solve(rows, threshold)` that filters rows by the second column and formats the result using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(rows: list, threshold: int) -> str:\n    filtered = [r for r in rows if r[1] >= threshold]\n    return tabulate.tabulate(filtered, headers=['Name', 'Score'], tablefmt='plain')\n",
        "cases": [
            ([["Alice", 80], ["Bob", 55], ["Carol", 90]], 60),
            ([["Alice", 80], ["Bob", 55], ["Carol", 90]], 80),
            ([["Alice", 40], ["Bob", 70], ["Carol", 60]], 50),
            ([["Alice", 100], ["Bob", 0]], 1),
            ([["Alice", 50], ["Bob", 50]], 50),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(rows: list) -> str:",
        "prompt": "Implement `solve(rows)` that normalizes scores to percentages and formats them using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(rows: list) -> str:\n    total = sum(v for _, v in rows)\n    normalized = [[name, round(v / total * 100, 1)] for name, v in rows]\n    return tabulate.tabulate(normalized, headers=['Name', 'Pct'], floatfmt='.1f', tablefmt='plain')\n",
        "cases": [
            ([["Alice", 80], ["Bob", 120], ["Carol", 200]],),
            ([["A", 50], ["B", 50]],),
            ([["X", 10], ["Y", 30], ["Z", 60]],),
            ([["Only", 100]],),
            ([["A", 25], ["B", 25], ["C", 50]],),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(dicts: list) -> str:",
        "prompt": "Implement `solve(dicts)` that merges dictionaries into a grid table using `tabulate.tabulate` with `headers='keys'`.",
        "solution": "import tabulate\n\ndef solve(dicts: list) -> str:\n    return tabulate.tabulate(dicts, headers='keys', tablefmt='grid')\n",
        "cases": [
            ([{"k": 1, "v": "a"}],),
            ([{"k": 2, "v": "b"}],),
            ([{"k": 3, "v": "c"}],),
            ([{"k": 0, "v": "z"}],),
            ([{"k": 10, "v": "x"}],),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(rows: list) -> str:",
        "prompt": "Implement `solve(rows)` that formats a table with a double-colon separator using `tabulate.tabulate` and `tabulate.simple_separated_format`.",
        "solution": "import tabulate\n\ndef solve(rows: list) -> str:\n    return tabulate.tabulate(rows, headers=['A', 'B'], tablefmt=tabulate.simple_separated_format('::'))\n",
        "cases": [
            ([[1, 2]],),
            ([[10, 20]],),
            ([[5, 7]],),
            ([[0, 0]],),
            ([[100, 200]],),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(rows: list) -> str:",
        "prompt": "Implement `solve(rows)` that formats a Markdown pipe table with headers 'Name' and 'Score' using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(rows: list) -> str:\n    return tabulate.tabulate(rows, headers=['Name', 'Score'], tablefmt='pipe')\n",
        "cases": [
            ([["Alice", 90], ["Bob", 85]],),
            ([["Carol", 78], ["Dave", 92]],),
            ([["Eve", 88], ["Frank", 70]],),
            ([["Grace", 95]],),
            ([],),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(rows: list) -> str:",
        "prompt": "Implement `solve(rows)` that formats a table with left-aligned first column, right-aligned second column, and two decimal places using `tabulate.tabulate`.",
        "solution": "import tabulate\n\ndef solve(rows: list) -> str:\n    return tabulate.tabulate(rows, headers=['X', 'Y'], colalign=('left', 'right'), floatfmt='.2f', tablefmt='plain')\n",
        "cases": [
            ([["A", 3.14159]],),
            ([["B", 2.71828]],),
            ([["C", 1.41421]],),
            ([["D", 0.0]],),
            ([["E", 100.5]],),
        ],
    },
    {
        "level": "L3",
        "signature": "def solve(rows: list, fmt: str) -> str:",
        "prompt": "Implement `solve(rows, fmt)` that formats a table using the requested `tabulate` tablefmt.",
        "solution": "import tabulate\n\ndef solve(rows: list, fmt: str) -> str:\n    return tabulate.tabulate(rows, headers=['A', 'B'], tablefmt=fmt)\n",
        "cases": [
            ([[1, 2]], "plain"),
            ([[1, 2]], "grid"),
            ([[10, 20]], "plain"),
            ([[10, 20]], "grid"),
            ([[5, 7]], "plain"),
        ],
    },
]


REPO_TEMPLATES = {
    "python-dateutil": DATEUTIL_TEMPLATES,
    "humanize": HUMANIZE_TEMPLATES,
    "tabulate": TABULATE_TEMPLATES,
}


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def main() -> None:
    all_tasks: list[dict[str, Any]] = []
    report = {
        "generated_at": None,  # will be set below
        "total_requested": 90,
        "total_generated": 0,
        "total_passed": 0,
        "total_failed": 0,
        "per_repo": {},
        "per_task": [],
    }

    for repo, templates in REPO_TEMPLATES.items():
        print(f"Building tasks for {repo}...")
        repo_pass = 0
        repo_fail = 0
        level_seq: dict[str, int] = {"L1": 0, "L2": 0, "L3": 0}
        for template in templates:
            level = template["level"]
            level_seq[level] += 1
            task = build_task(repo, level, level_seq[level], template)
            if task is None:
                repo_fail += 1
                report["per_task"].append(
                    {
                        "task_id": f"{repo}_{level.lower()}_{level_seq[level]:03d}",
                        "repo": repo,
                        "level": level,
                        "status": "failed",
                        "error": "validation or import error (see script output)",
                    }
                )
                continue
            all_tasks.append(task)
            repo_pass += 1
            report["per_task"].append(
                {
                    "task_id": task["task_id"],
                    "repo": repo,
                    "level": level,
                    "status": "passed",
                    "error": "",
                }
            )
        report["per_repo"][repo] = {"passed": repo_pass, "failed": repo_fail}
        report["total_passed"] += repo_pass
        report["total_failed"] += repo_fail
        print(f"  {repo}: {repo_pass} passed, {repo_fail} failed")

    report["total_generated"] = len(all_tasks)
    report["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    TASKS_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_TASKS.open("w", encoding="utf-8") as f:
        for task in all_tasks:
            f.write(json.dumps(task, ensure_ascii=False) + "\n")

    with OUT_REPORT.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(all_tasks)} tasks to {OUT_TASKS}")
    print(f"Wrote validation report to {OUT_REPORT}")
    print(f"Passed: {report['total_passed']}, Failed: {report['total_failed']}")


if __name__ == "__main__":
    main()
