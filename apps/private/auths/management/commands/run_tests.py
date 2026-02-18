from __future__ import annotations

import logging
import time
import unittest
from typing import Any

from django.core.management.base import BaseCommand
from django.test.runner import DiscoverRunner


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

    def addSuccess(self, test: unittest.TestCase) -> None:
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

        # ── Start coverage ──
        cov = None
        if not no_coverage:
            try:
                import coverage

                cov = coverage.Coverage()
                cov.start()
            except ImportError:
                pass

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

        # ── Stop coverage & compute total ──
        cover_pct = None
        if cov:
            cov.stop()
            cov.save()
            cover_pct = self._total_coverage(cov)

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

        if cover_pct is not None:
            cov_color = GREEN if cover_pct >= 80 else YELLOW if cover_pct >= 60 else RED
            summary += "  " + c(f"({cover_pct:.0f}% coverage)", cov_color, BOLD)

        mark = c("✓", GREEN, BOLD) if ok else c("✗", RED, BOLD)
        self.stdout.write(f"\n {mark} {summary}\n")

        # ── Failure details (always shown) ──
        for test, tb in result.failures + result.errors:
            self.stdout.write(c(f"\n   ✗ {test}", RED, BOLD))
            for line in tb.strip().splitlines():
                self.stdout.write(c(f"     {line}", DIM))
            self.stdout.write("")

        # ── Exit code ──
        coverage_too_low = fail_under and cover_pct is not None and cover_pct < fail_under
        if coverage_too_low:
            self.stderr.write(c(f"\n   Coverage {cover_pct:.1f}% is below --fail-under {fail_under}%\n", RED, BOLD))

        if not ok or coverage_too_low:
            raise SystemExit(1)

    @staticmethod
    def _total_coverage(cov) -> float:
        """Compute total coverage percentage."""
        total_stmts = 0
        total_miss = 0
        for filename in cov.get_data().measured_files():
            try:
                _, statements, _, missing, _ = cov.analysis2(filename)
            except Exception:
                continue
            total_stmts += len(statements)
            total_miss += len(missing)
        return ((total_stmts - total_miss) / total_stmts * 100) if total_stmts else 0
