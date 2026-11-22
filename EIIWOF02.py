#!/usr/bin/env python3
"""EIIWOF02 - Extract write-off accounts to TXT and SAS7BDAT."""

import argparse
import re
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path

import saspy


# Input and output paths.
WOFF_FILE = Path("/host_pq/loan/input/WRI2OFF_MIS.txt")
OUTPUT_FOLDER = Path("/exdwh/host/ln/npl_hp_sasdata/pibb/woff")
TEXT_FILE = Path("/dwh/ftp/drr/woffhpx.txt")
SAS_MEMBER = "woffhpx"
ENCODING = "utf-8"

# None uses your default configured SASPy connection.
SAS_CONFIG = None


def number(field):
    value = field.strip()

    if (
        not value
        or value == "."
        or (
            len(value) == 2
            and value[0] == "."
            and (value[1].isalpha() or value[1] == "_")
        )
    ):
        return None

    return Decimal(value.replace(",", ""))


def write_sas7bdat(text_file, output_folder, member, expected_rows):
    """Use the configured SAS server to create a SAS7BDAT file."""

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,31}", member):
        raise ValueError("Invalid SAS dataset name")

    def quote(value):
        return "'" + str(value).replace("'", "''") + "'"

    sas = (
        saspy.SASsession(cfgname=SAS_CONFIG)
        if SAS_CONFIG
        else saspy.SASsession()
    )

    try:
        # Validate in SAS WORK before writing the final dataset.
        result = sas.submit(
            f"""
data work.woffhp_export;
    infile {quote(text_file)}
        truncover lrecl=32767;
    input ACCTNO :best32.;
run;

%macro publish;
    %local dsid rowcount rc;

    %if &syserr > 4 %then %return;

    %let dsid=%sysfunc(open(work.woffhp_export));
    %if &dsid = 0 %then %return;

    %let rowcount=%sysfunc(attrn(&dsid,nlobs));
    %let rc=%sysfunc(close(&dsid));

    %if &rowcount ne {expected_rows} %then %do;
        %put ERROR: WOFFHP row count does not match Python.;
        %return;
    %end;

    libname outlib {quote(output_folder)};
    %if &syslibrc ne 0 %then %return;

    data outlib.{member};
        set work.woffhp_export;
    run;

    %if &syserr > 4 %then %return;

    %put WOFFHP_EXPORT_COMPLETE;
%mend;

%publish;
""",
            results="TEXT",
        )

        log = result["LOG"]
        print(log)

        if (
            re.search(r"^ERROR(?:\\s|:)", log, re.MULTILINE)
            or not re.search(
                r"^WOFFHP_EXPORT_COMPLETE\\s*$",
                log,
                re.MULTILINE,
            )
        ):
            raise RuntimeError("SAS output failed. Check the SAS log.")

        print(f"Created: {output_folder / (member + '.sas7bdat')}")
    finally:
        sas.endsas()


def run(run_date=None):
    scheduled = (
        date.fromisoformat(run_date)
        if run_date
        else datetime.now(timezone(timedelta(hours=8))).date()
    )

    if (scheduled.month, scheduled.day) != (12, 27):
        raise ValueError(
            "Run date must be 27 December; "
            "use --run-date YYYY-12-27 for testing or reruns."
        )

    accounts = []

    with WOFF_FILE.open(encoding=ENCODING) as handle:
        for line_number, line in enumerate(handle, 1):
            if len(line.rstrip("\r\n")) < 239:
                raise ValueError(
                    f"WOFF line {line_number}: "
                    "record shorter than required fields."
                )

            # SAS positions: ACCTNO @142 length 10, COSTCTR @236 length 4.
            acctno = number(line[141:151])
            costctr = number(line[235:239])

            if costctr is not None and (
                3000 <= costctr <= 3999
                or costctr in (4043, 4048)
            ):
                accounts.append(acctno)

    # Ascending order; missing values first. Keep duplicates.
    accounts.sort(
        key=lambda value: (value is not None, value or Decimal(0))
    )

    OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
    TEXT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # One ACCTNO per line, no header. Missing values use a blank line.
    temporary_text = TEXT_FILE.with_suffix(".txt.tmp")

    with temporary_text.open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        for acctno in accounts:
            handle.write(
                ("" if acctno is None else format(acctno, "f")) + "\n"
            )

    temporary_text.replace(TEXT_FILE)
    print(f"Created: {TEXT_FILE}")

    write_sas7bdat(
        TEXT_FILE,
        OUTPUT_FOLDER,
        SAS_MEMBER,
        len(accounts),
    )

    print(f"EIIWOF02 completed. Records: {len(accounts)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="EIIWOF02 - WOFF text to TXT and SAS7BDAT"
    )
    parser.add_argument("--run-date", help="Scheduled date YYYY-12-27")
    args = parser.parse_args()
    run(run_date=args.run_date)
