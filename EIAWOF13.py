#!/usr/bin/env python3
"""Controller for PBB EIAWOF13; keeps EIFMNP03/06/07 separate."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_BASE = Path("Data_Warehouse/MIS/XMIS/input/prod")
DEFAULT_OUTPUT_DIR = DEFAULT_BASE / "output"
SCHEDULED_DAY = 27


def run(
    program: str,
    environment: dict[str, str] | None = None,
) -> None:
    candidates = [
        SCRIPT_DIR / (program + ".py"),
        SCRIPT_DIR / (program.lower() + ".py"),
    ]

    script = next(
        (candidate for candidate in candidates if candidate.is_file()),
        None,
    )

    if script is None:
        searched = ", ".join(str(candidate) for candidate in candidates)
        raise SystemExit(
            f"EIAWOF13: program file not found; searched: {searched}"
        )

    print(f"EIAWOF13: starting {program}")

    child_environment = os.environ.copy()
    if environment:
        child_environment.update(environment)

    # Input/output paths are passed through environment variables.
    # This prevents sitecustomize from using paths containing "/" in
    # its generated log filename.
    result = subprocess.run(
        [sys.executable, str(script)],
        env=child_environment,
        check=False,
    )

    if result.returncode:
        raise SystemExit(
            f"EIAWOF13: {program} failed "
            f"with return code {result.returncode}"
        )

    print(f"EIAWOF13: {program} completed")


def main() -> None:
    today = date.today()

    if today.day != SCHEDULED_DAY:
        print(
            f"EIAWOF13 skipped: job only runs on day {SCHEDULED_DAY} "
            f"of each month. Today is {today:%Y-%m-%d}."
        )
        return

    parser = argparse.ArgumentParser(
        description="Run separate PBB EIFMNP03/06/07 steps"
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_BASE,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
    )
    parser.add_argument(
        "--branch-map",
        type=Path,
    )
    args = parser.parse_args()

    args.input_dir = args.input_dir.resolve()
    args.output_dir = args.output_dir.resolve()

    if not args.input_dir.is_dir():
        raise SystemExit(
            f"EIAWOF13: input directory not found: {args.input_dir}"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"EIAWOF13: run date         = {today:%Y-%m-%d}")
    print(f"EIAWOF13: process date     = {today - timedelta(days=1):%Y-%m-%d}")
    print(f"EIAWOF13: input directory  = {args.input_dir}")
    print(f"EIAWOF13: output directory = {args.output_dir}")

    step03 = args.output_dir / "eifmnp03"
    step06 = args.output_dir / "eifmnp06"
    step07 = args.output_dir / "eifmnp07"

    base_environment = {
        "XMIS_INPUT_DIR": str(args.input_dir),
    }

    if args.branch_map:
        base_environment["XMIS_BRANCH_MAP"] = str(
            args.branch_map.resolve()
        )

    run(
        "EIFMNP03",
        {
            **base_environment,
            "XMIS_OUTPUT_DIR": str(step03),
        },
    )

    month = f"{(today - timedelta(days=1)).month:02d}"

    # IIS current month is produced by EIFMNP03,
    # then passed to EIFMNP06.
    run(
        "EIFMNP06",
        {
            **base_environment,
            "XMIS_OUTPUT_DIR": str(step06),
            "XMIS_IIS_FILE": str(step03 / f"iis{month}.csv"),
        },
    )

    run(
        "EIFMNP07",
        {
            **base_environment,
            "XMIS_OUTPUT_DIR": str(step07),
        },
    )

    print("EIAWOF13: all three separate PBB steps completed")


if __name__ == "__main__":
    main()
