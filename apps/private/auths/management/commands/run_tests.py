from __future__ import annotations

import fnmatch
import logging
import os
import subprocess
import sys
import time
import unittest
from typing import Any

from django.core.management.base import BaseCommand
from django.test.runner import DiscoverRunner

# ── Coverage config ─────────────────────────────────────────

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


# ── ANSI helpers ─────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
CYAN = "\033[36m"


def c(text: str, *codes: str) -> str:
    return "".join(codes) + str(text) + RESET


# ── SilentTestResult ─────────────────────────────────────────


class SilentTestResult(unittest.TestResult):
    """Captures every outcome without printing anything."""

    def __init__(self):
        super().__init__()
        self.successes: list[unittest.TestCase] = []

    def addSuccess(self, test: unittest.TestCase) -> None:  # noqa: N802
        super().addSuccess(test)
        self.successes.append(test)


# ── Management Command ───────────────────────────────────────


class Command(BaseCommand):
    help = "Run tests with a one-line summary and optional coverage"

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "test_labels",
            nargs="*",
            help="Specific test labels to run (e.g. tests.test_models). All tests if omitted.",
        )
        parser.add_argument(
            "--no-coverage",
            action="store_true",
            help="Skip coverage measurement for faster runs",
        )
        parser.add_argument(
            "--fail-under",
            type=float,
            default=0,
            help="Exit with error if total coverage is below this percentage",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        test_labels = options["test_labels"] or None
        no_coverage = options["no_coverage"]
        fail_under = options["fail_under"]

        # When coverage is requested, re-launch as a subprocess so that
        # coverage.start() runs BEFORE Django imports any app modules.
        # This ensures module-level code (class/function definitions) is
        # counted in the coverage report.
        if not no_coverage and "_RUN_TESTS_SUBPROCESS" not in os.environ:
            cmd = [sys.executable, "-m", "run_tests_with_coverage"]
            if test_labels:
                cmd.extend(test_labels)
            if fail_under:
                cmd.extend(["--fail-under", str(fail_under)])
            proc = subprocess.run(cmd, cwd=os.getcwd())
            raise SystemExit(proc.returncode)

        # ── Run tests (full Django lifecycle) ──
        runner = DiscoverRunner(verbosity=0)
        runner.setup_test_environment()
        suite = runner.build_suite(test_labels)
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

        # ── One-line summary ──
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

        mark = c("✓", GREEN, BOLD) if ok else c("✗", RED, BOLD)
        self.stdout.write(f"\n {mark} {summary}\n")

        # ── Failure details (always shown) ──
        for test, tb in result.failures + result.errors:
            self.stdout.write(c(f"\n   ✗ {test}", RED, BOLD))
            for line in tb.strip().splitlines():
                self.stdout.write(c(f"     {line}", DIM))
            self.stdout.write("")

        if not ok:
            raise SystemExit(1)

    @staticmethod
    def _is_app_file(filepath: str) -> bool:
        """Check if a file belongs to our app source directories and isn't omitted."""
        rel = filepath
        for prefix in ("/app/", os.getcwd() + "/"):
            if rel.startswith(prefix):
                rel = rel[len(prefix) :]
                break

        if not any(rel.startswith(d) for d in COVERAGE_SOURCE_DIRS):
            return False

        return not any(fnmatch.fnmatch(rel, pat) for pat in COVERAGE_OMIT_PATTERNS)

    @staticmethod
    def _total_coverage(cov) -> float:
        """Compute total coverage percentage over app source files only."""
        total_stmts = 0
        total_miss = 0
        for filename in cov.get_data().measured_files():
            if not Command._is_app_file(filename):
                continue
            try:
                _, statements, _, missing, _ = cov.analysis2(filename)
            except Exception:
                continue
            total_stmts += len(statements)
            total_miss += len(missing)
        return ((total_stmts - total_miss) / total_stmts * 100) if total_stmts else 0
