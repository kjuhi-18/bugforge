import ast
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from models.schemas import TestExecutionOutput, TestOutcome


def execute_tests(source, test_code, enabled=False, timeout=20):
    """Run generated pytest tests with the same Python interpreter as the app.

    This is a temporary subprocess, not a secure sandbox. Only execute trusted code.
    """
    if not enabled:
        return TestExecutionOutput(
            False,
            [],
            note="Execution disabled. Acknowledge the local execution risk in the UI.",
        )

    try:
        ast.parse(source)
    except SyntaxError as exc:
        return TestExecutionOutput(
            True, [], note=f"Source syntax validation failed: {exc}"
        )

    try:
        ast.parse(test_code)
    except SyntaxError as exc:
        return TestExecutionOutput(
            True, [], note=f"Generated test syntax validation failed: {exc}"
        )

    # Reject empty/non-test code rather than reporting a false successful run.
    if not re.search(r"^\s*def\s+test_\w+\s*\(", test_code, re.MULTILINE):
        return TestExecutionOutput(
            True,
            [],
            note="No executable pytest test functions were generated.",
        )

    start = time.monotonic()

    with tempfile.TemporaryDirectory(prefix="bug-analyzer-") as temp_dir:
        workdir = Path(temp_dir)
        (workdir / "submitted_module.py").write_text(source, encoding="utf-8")
        (workdir / "test_generated.py").write_text(test_code, encoding="utf-8")

        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTHONNOUSERSITE"] = "0"

        # Do not use Python's -I flag here: it can hide user-site packages,
        # which may be where pytest/Pygments were installed.
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-v",
            "-p",
            "no:cacheprovider",
            "test_generated.py",
        ]

        try:
            process = subprocess.run(
                command,
                cwd=str(workdir),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            stdout = (process.stdout or "")[-12000:]
            stderr = (process.stderr or "")[-6000:]
            outcomes = []

            for line in (stdout + "\n" + stderr).splitlines():
                match = re.search(
                    r"^test_generated\.py::\S+\s+(PASSED|FAILED|ERROR)\b",
                    line.strip(),
                )
                if match:
                    outcome = {
                        "PASSED": "passed",
                        "FAILED": "failed",
                        "ERROR": "error",
                    }[match.group(1)]
                    outcomes.append(TestOutcome(line.strip(), outcome))

            passed = sum(item.outcome == "passed" for item in outcomes)
            failed = sum(item.outcome == "failed" for item in outcomes)
            errors = sum(item.outcome == "error" for item in outcomes)

            note = (
                "Temporary subprocess with timeout; NOT a secure sandbox. "
                "Run only trusted code."
            )
            if not outcomes:
                note += (
                    f" Pytest exited with code {process.returncode} but no test "
                    "outcomes were parsed. Check stderr/stdout for collection or "
                    "dependency errors."
                )

            return TestExecutionOutput(
                True,
                outcomes,
                passed,
                failed,
                errors,
                time.monotonic() - start,
                stdout,
                stderr,
                note,
            )

        except subprocess.TimeoutExpired:
            return TestExecutionOutput(
                True,
                [],
                duration_seconds=time.monotonic() - start,
                note=f"Pytest timed out after {timeout}s. This is not a secure sandbox.",
            )
        except OSError as exc:
            return TestExecutionOutput(
                True,
                [],
                duration_seconds=time.monotonic() - start,
                note=(
                    f"Could not start pytest using {sys.executable}: {exc}. "
                    "Install pytest in the same Python environment that runs Streamlit."
                ),
            )
