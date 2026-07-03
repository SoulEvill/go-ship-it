#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class CommandResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class CheckResult:
    command: list[str]
    status: str
    message: str


@dataclass(frozen=True)
class ReleaseReport:
    results: list[CheckResult]

    @property
    def failed_count(self) -> int:
        return sum(1 for result in self.results if result.status == "failed")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run GoShipit release readiness checks.")
    parser.add_argument("--keep-going", action="store_true", help="Run all checks even after a failure.")
    args = parser.parse_args(argv)

    report = run_release_check(keep_going=args.keep_going)
    for result in report.results:
        print(f"{result.status.upper()} {' '.join(result.command)}")
        if result.message:
            print(result.message)
    return 1 if report.failed_count else 0


def run_release_check(*, keep_going: bool = False) -> ReleaseReport:
    checks = [
        ["uv", "run", "pytest", "-q"],
        ["uv", "run", "go-ship-it", "doctor"],
        ["uv", "build"],
        ["scripts/validate-packaged-install.py", "--wheel", "dist/go_ship_it-0.1.0-py3-none-any.whl"],
        ["scripts/validate-agent-cli-integration.py"],
    ]
    results: list[CheckResult] = []
    for command in checks:
        result = _run_command(command)
        if result.returncode == 0:
            results.append(CheckResult(command=command, status="passed", message=_tail(result.stdout)))
            continue
        results.append(CheckResult(command=command, status="failed", message=_tail(result.stderr or result.stdout)))
        if not keep_going:
            break
    return ReleaseReport(results=results)


def _run_command(command: list[str]) -> CommandResult:
    result = subprocess.run(command, capture_output=True, check=False, text=True)
    return CommandResult(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)


def _tail(text: str) -> str:
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return "\n".join(lines[-8:])


if __name__ == "__main__":
    sys.exit(main())
