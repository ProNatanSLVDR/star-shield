"""
Subprocess entry point for run_tests with coverage.

Starts coverage BEFORE Django loads so that module-level code
(class definitions, imports) is included in the measurement.
"""

from __future__ import annotations

import fnmatch
import logging
import os
import sys
import time
import unittest

# ── Start coverage before any Django imports ──
import coverage

COVERAGE_SOURCE_DIRS = ("apps/", "starshield/")
COVERAGE_OMIT_PATTERNS = (
    "*/migrations/*",
    "*/tests/*",
    "tests/*",
    "*/management/commands/*",
    "*/wsgi.py",
    "*/asgi.py",
    "*/settings.py",
)

cov = coverage.Coverage()
cov.start()

# ── Now set up Django ──

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "starshield.settings")
os.environ.setdefault("DJANGO_CONFIGURATION", "Dev")
os.environ["_RUN_TESTS_SUBPROCESS"] = "1"

import configurations  # noqa: E402

configurations.setup()

from django.test.runner import DiscoverRunner  # noqa: E402

# ── ANSI helpers ──

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"


def c(text: str, *codes: str) -> str:
    return "".join(codes) + str(text) + RESET


class SilentTestResult(unittest.TestResult):
    def __init__(self):
        super().__init__()
        self.successes: list[unittest.TestCase] = []

    def addSuccess(self, test):  # noqa: N802
        super().addSuccess(test)
        self.successes.append(test)


def _is_app_file(filepath: str) -> bool:
    rel = filepath
    for prefix in ("/app/", os.getcwd() + "/"):
        if rel.startswith(prefix):
            rel = rel[len(prefix) :]
            break
    if not any(rel.startswith(d) for d in COVERAGE_SOURCE_DIRS):
        return False
    return not any(fnmatch.fnmatch(rel, pat) for pat in COVERAGE_OMIT_PATTERNS)


def main():
    # Parse simple args: test labels and --fail-under
    test_labels = []
    fail_under = 0.0
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--fail-under" and i + 1 < len(args):
            fail_under = float(args[i + 1])
            i += 2
        else:
            test_labels.append(args[i])
            i += 1

    # Run tests
    runner = DiscoverRunner(verbosity=0)
    runner.setup_test_environment()
    suite = runner.build_suite(test_labels or None)
    databases = runner.get_databases(suite)
    old_config = runner.setup_databases(aliases=databases)

    result = SilentTestResult()
    start = time.monotonic()

    logging.disable(logging.CRITICAL)
    try:
        suite(result)
    finally:
        logging.disable(logging.NOTSET)
        duration = time.monotonic() - start
        runner.teardown_databases(old_config)
        runner.teardown_test_environment()

    # Stop coverage
    cov.stop()
    cov.save()

    # Compute coverage over app files only
    total_stmts = 0
    total_miss = 0
    for filename in cov.get_data().measured_files():
        if not _is_app_file(filename):
            continue
        try:
            _, statements, _, missing, _ = cov.analysis2(filename)
        except Exception:
            continue
        total_stmts += len(statements)
        total_miss += len(missing)
    cover_pct = ((total_stmts - total_miss) / total_stmts * 100) if total_stmts else 0

    # Summary
    passed = len(result.successes)
    failed = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    ok = not failed and not errors

    parts = []
    parts.append(c(f"{passed} passed", GREEN, BOLD) if passed else f"{passed} passed")
    if failed:
        parts.append(c(f"{failed} failed", RED, BOLD))
    if errors:
        parts.append(c(f"{errors} errors", RED, BOLD))
    if skipped:
        parts.append(c(f"{skipped} skipped", YELLOW))

    summary = ", ".join(parts) + c(f" in {duration:.2f}s", DIM)

    cov_color = GREEN if cover_pct >= 80 else YELLOW if cover_pct >= 60 else RED
    summary += "  " + c(f"({cover_pct:.0f}% coverage)", cov_color, BOLD)

    mark = c("✓", GREEN, BOLD) if ok else c("✗", RED, BOLD)
    print(f"\n {mark} {summary}\n")  # noqa: T201

    # Failure details
    for test, tb in result.failures + result.errors:
        print(c(f"\n   ✗ {test}", RED, BOLD))  # noqa: T201
        for line in tb.strip().splitlines():
            print(c(f"     {line}", DIM))  # noqa: T201
        print()  # noqa: T201

    # Exit code
    coverage_too_low = fail_under and cover_pct < fail_under
    if coverage_too_low:
        print(  # noqa: T201
            c(f"\n   Coverage {cover_pct:.1f}% is below --fail-under {fail_under}%\n", RED, BOLD),
            file=sys.stderr,
        )

    sys.exit(1 if (not ok or coverage_too_low) else 0)


if __name__ == "__main__":
    main()
