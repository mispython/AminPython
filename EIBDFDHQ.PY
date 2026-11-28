#!/usr/bin/env python3
"""Upload EIBDFDHQ reports to DRR using the site's psftp control dataset."""

from __future__ import annotations

import argparse
import subprocess
from datetime import date
from pathlib import Path

import polars as pl


DEFAULT_OUTPUT_DIR = Path("Data_Warehouse/MIS/XMIS/input/prod/output")
CONTROL = Path("/sasdata/dwh/control/ctl_dwh_sftp_info.sas7bdat")
BATCH = Path("/sasdata/dwh/logs/FTPFDHQ1.txt")
FTP_LOG = Path("/sasdata/dwh/logs/FTPFDHQ1_LOG.txt")
REMOTE_DIR = "/TD/CORPORATE"


def clean(value: object) -> str:
    if value is None:
        return ""
    return "".join(str(value).split())


def upload_to_drr(files: list[tuple[Path, str]]) -> None:
    for local_file, _ in files:
        if not local_file.is_file():
            raise FileNotFoundError(f"Report file not found: {local_file}")
    if not CONTROL.is_file():
        raise FileNotFoundError(f"DRR SFTP control dataset not found: {CONTROL}")

    BATCH.parent.mkdir(parents=True, exist_ok=True)
    batch_lines = [f'cd "{REMOTE_DIR}"']
    batch_lines.extend(
        f'put "{local_file.resolve()}" "{remote_name}"'
        for local_file, remote_name in files
    )
    BATCH.write_bytes(("\r\n".join(batch_lines) + "\r\n").encode())

    control = pl.read_sas(CONTROL)
    control = control.rename({column: str(column).upper() for column in control.columns})
    if "HOST_DESC" not in control.columns:
        raise RuntimeError("DRR control dataset is missing HOST_DESC")
    rows = control.filter(
        pl.col("HOST_DESC").cast(pl.String).fill_null("").str.contains(
            "Data Report Repository (DRR)", literal=True
        )
    )
    if rows.height != 1:
        raise RuntimeError(f"Expected one DRR row in SFTP control dataset; found {rows.height}")
    row = rows.row(0, named=True)
    required = ["SFTP_PW", "SFTP_ID", "HOST_IP"]
    missing = [column for column in required if column not in row]
    if missing:
        raise RuntimeError("DRR control row missing: " + ", ".join(missing))

    command = [
        "psftp",
        "-pw", clean(row["SFTP_PW"]),
        f"{clean(row['SFTP_ID'])}@{clean(row['HOST_IP'])}",
        "-b", str(BATCH), "-be",
    ]
    with FTP_LOG.open("w", encoding="utf-8") as log:
        subprocess.run(
            command, input="y\n", text=True, stdout=log,
            stderr=subprocess.STDOUT, check=True,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-date", help="Run date YYYY-MM-DD; defaults to today")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    run_date = date.fromisoformat(args.run_date) if args.run_date else date.today()
    date_suffix = run_date.strftime("%d.%m.%y")
    reports = [
        (args.output_dir / "FDTXT.csv", f"RMFDMAT_{date_suffix}.CSV"),
        (args.output_dir / "FDTXT1.csv", f"FCYFDMAT_{date_suffix}.CSV"),
    ]
    upload_to_drr(reports)
    print(f"Uploaded {len(reports)} reports to DRR {REMOTE_DIR}")


if __name__ == "__main__":
    main()
