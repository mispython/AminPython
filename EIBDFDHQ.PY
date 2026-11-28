//FTPFDHQ1 JOB MSGCLASS=X,MSGLEVEL=(2,1)                                JOB33688
/*JOBPARM S=S1M1
//*
//*%OPC SCAN
//******************************************************************
//* FTP HOST DATASETS TO DATA REPORT REPOSITORY SYSTEM (DRR)
//******************************************************************
//RUNSFTP  EXEC COZBATCH
//CMD.SYSUT1 DD DISP=SHR,DSN=OPER.PBB.PARMLIB(DRR#SFTP)
//           DD *
lzopts servercp=$servercp,notrim,overflow=trunc,mode=text
lzopts linerule=$lr
CD TD/CORPORATE
PUT //SAP.PBB.FD.FDTXT RMFDMAT_%ODD.%OMM.%OYY..CSV
PUT //SAP.PBB.FD.FDTXT1 FCYFDMAT_%ODD.%OMM.%OYY..CSV
EOB
/*



//FTPFDHQ1 JOB MSGCLASS=X,MSGLEVEL=(2,1)                                JOB33688
/*JOBPARM S=S1M1
//*
//*%OPC SCAN
//******************************************************************
//* FTP HOST DATASETS TO DATA REPORT REPOSITORY SYSTEM (DRR)
//******************************************************************
//RUNSFTP  EXEC COZBATCH
//CMD.SYSUT1 DD DISP=SHR,DSN=OPER.PBB.PARMLIB(DRR#SFTP)
//           DD *
lzopts servercp=$servercp,notrim,overflow=trunc,mode=text
lzopts linerule=$lr
CD TD/CORPORATE
PUT //SAP.PBB.FD.FDTXT RMFDMAT_%ODD.%OMM.%OYY..CSV
PUT //SAP.PBB.FD.FDTXT1 FCYFDMAT_%ODD.%OMM.%OYY..CSV
EOB
/*



#!/usr/bin/env python3
"""Convert the EIBDFDHQ SAS job to Python using Polars.

Requires:
    pip install polars

The SAS7BDAT inputs are read from the four source directories below. Reports
continue to be written to Data_Warehouse/MIS/XMIS/input/prod/output by default.
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta
from pathlib import Path

import polars as pl


DEFAULT_OUTPUT_DIR = Path("Data_Warehouse/MIS/XMIS/input/prod/output")
DEPO_SOURCE_DIRS = {
    "fd": Path("/dwh/dpd_fd"),
    "ifd": Path("/dwh/idpd_fd"),
    "ifcy": Path("/dwh/idp_fcy"),
    "fcy": Path("/dwh/dp_fcy"),
}
NAME_SOURCE_DIR = Path("/sas/deposit/dwh/integration")
ENRICHMENT_SOURCE_DIR = Path("/sas/deposit/dwh/enrichment")


OUTPUT_COLUMNS = [
    "BRANCH",
    "SECOND2",
    "NAME",
    "ACCTNO",
    "CURBAL",
    "CDNO",
    "MATDATE",
    "RT",
    "TERM",
]

OUTPUT_HEADERS = [
    "BRANCH",
    "PBB/PIBB",
    "NAME",
    "ACCTNO",
    "PRINCIPAL AM(RM)",
    "CDNO",
    "MATDATE",
    "PREVIOUS RATE(% P.A)",
    "PREVIOUS TERM (MONTH)",
]


def read_sas(path: Path) -> pl.DataFrame:
    """Read a SAS7BDAT file and normalize column names to uppercase."""
    frame = pl.read_sas(path)
    return frame.rename({column: str(column).upper() for column in frame.columns})


def require_file(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"Required SAS7BDAT input not found: {path}")
    return path


def require_columns(frame: pl.DataFrame, columns: list[str], source: str) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{source} is missing columns: {', '.join(missing)}")


def format_sas_value(value: object, column: str) -> str:
    """Produce readable text close to SAS list PUT output."""
    if value is None:
        return ""
    if column == "MATDATE":
        if isinstance(value, (datetime, date)):
            return value.strftime("%d/%m/%Y")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def write_report(frame: pl.DataFrame, path: Path, title: str) -> None:
    """Write the title, header, and data rows used by the original SAS job."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        handle.write(title + "\n")
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(OUTPUT_HEADERS)
        for row in frame.select(OUTPUT_COLUMNS).iter_rows():
            writer.writerow(
                format_sas_value(value, column)
                for column, value in zip(OUTPUT_COLUMNS, row)
            )


def convert(args: argparse.Namespace) -> None:
    run_date = date.fromisoformat(args.run_date) if args.run_date else date.today()
    input_date = run_date - timedelta(days=1)
    suffix = input_date.strftime("%y%m%d")

    # SAS LIBNAME A lists four directories; each dataset contributes its own
    # columns. PURPOSE is intentionally dropped from both FCY inputs.
    depo_sources = [
        ("fd", f"fd{suffix}.sas7bdat", False),
        ("ifd", f"ifd{suffix}.sas7bdat", False),
        ("ifcy", f"ifcy{suffix}.sas7bdat", True),
        ("fcy", f"fcy{suffix}.sas7bdat", True),
    ]
    depo_frames = []
    for source, filename, drop_purpose in depo_sources:
        frame = read_sas(require_file(DEPO_SOURCE_DIRS[source] / filename))
        if drop_purpose and "PURPOSE" in frame.columns:
            frame = frame.drop("PURPOSE")
        depo_frames.append(frame)

    depo = pl.concat(depo_frames, how="diagonal_relaxed").sort(
        ["ACCTNO", "BRANCH"], maintain_order=True
    )
    require_columns(depo, ["ACCTNO", "BRANCH", "SECOND"], "four deposit source files")
    depo = (
        depo.filter(pl.col("SECOND").is_in([99991, 99992]))
        .with_columns(
            pl.when(pl.col("SECOND") == 99991)
            .then(pl.lit("PBB"))
            .otherwise(pl.lit("PIBB"))
            .alias("SECOND2")
        )
        .select("ACCTNO", "BRANCH", "SECOND2")
    )

    fdname_path = require_file(NAME_SOURCE_DIR / "INTG_DP_ACCT_FD_D27.sas7bdat")
    fdname = read_sas(fdname_path)
    require_columns(fdname, ["ACCTNO", "BRANCH", "NAME"], "INTG_DP_ACCT_FD_D27")
    fdname = fdname.sort(["ACCTNO", "BRANCH"], maintain_order=True)
    depo1 = depo.join(
        fdname.select("ACCTNO", "BRANCH", "NAME"),
        on=["ACCTNO", "BRANCH"],
        how="left",
    )

    enrichment_path = require_file(ENRICHMENT_SOURCE_DIR / "ENRH_DP_FD_CERT_D27.sas7bdat")
    enrichment = read_sas(enrichment_path)
    require_columns(
        enrichment,
        ["ACCT_NUM", "BRANCH_CD", "CERT_NUM", "MATURE_DT", "TERM", "RT", "CURR_BAL"],
        "ENRH_DP_FD_CERT_D27",
    )
    mature_dtype = enrichment.schema["MATURE_DT"]
    mature_expr = (
        pl.col("MATURE_DT").dt.date()
        if mature_dtype.is_temporal()
        else pl.from_epoch(pl.col("MATURE_DT").cast(pl.Int64), time_unit="s").dt.date()
    )
    depo2 = enrichment.with_columns(
        pl.col("ACCT_NUM").alias("ACCTNO"),
        pl.col("BRANCH_CD").alias("BRANCH"),
        pl.col("CERT_NUM").alias("CDNO"),
        mature_expr.alias("MATDATE"),
        pl.col("CURR_BAL").alias("CURBAL"),
    ).filter(pl.col("CURBAL") > 0).select(
        "ACCTNO", "BRANCH", "CDNO", "MATDATE", "TERM", "RT", "CURBAL"
    )

    # SAS `MERGE ...; BY ...; IF A AND B;` is an inner match on these keys.
    combined = depo1.join(depo2, on=["ACCTNO", "BRANCH"], how="inner").sort(
        "MATDATE", maintain_order=True
    )

    account_number = pl.col("ACCTNO").cast(pl.Int64, strict=False)
    is_foreign_currency = (
        account_number.is_between(1_590_000_000, 1_599_999_999)
        | account_number.is_between(1_689_999_999, 1_699_999_999)
        | account_number.is_between(1_789_999_999, 1_799_999_999)
    )
    fcyfd = combined.filter(is_foreign_currency)
    fd = combined.filter(~is_foreign_currency.fill_null(False))

    report_text = run_date.strftime("%d/%m/%y")
    write_report(fd, args.fd_output, f"DAILY RM FD MATURITY HQ AS AT {report_text}")
    write_report(fcyfd, args.fcyfd_output, f"DAILY FCYFD MATURITY HQ AS AT {report_text}")

    print(f"Wrote {len(fd):,} RM FD rows to {args.fd_output}")
    print(f"Wrote {len(fcyfd):,} FCYFD rows to {args.fcyfd_output}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-date",
        help="Job date in YYYY-MM-DD format; defaults to today's system date",
    )
    parser.add_argument(
        "--fd-output", type=Path, default=DEFAULT_OUTPUT_DIR / "FDTXT.csv"
    )
    parser.add_argument(
        "--fcyfd-output", type=Path, default=DEFAULT_OUTPUT_DIR / "FDTXT1.csv"
    )
    return parser


if __name__ == "__main__":
    convert(build_parser().parse_args())
