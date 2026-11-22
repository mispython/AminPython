#!/usr/bin/env python3
"""EIIWOF02 - Select Islamic write-off accounts; output TXT and SAS7BDAT."""

from decimal import Decimal
from pathlib import Path
import re
import pandas as pd
import saspy

INPUT_FILE = Path("/host_pq/loan/input/WRI2OFF_MIS.txt")
TEXT_FILE = Path("/dwh/ftp/drr/woffhpx.txt")
SAS_FOLDER = Path("/exdwh/host/ln/npl_hp_sasdata/pibb/woff")
SAS_MEMBER = "woffhpx"
SAS_CONFIG = None  # Your configured SASPy profile; None uses the default.


def number(field):
    value = field.strip()
    if not value or value == "." or (
        len(value) == 2 and value[0] == "."
        and (value[1].isalpha() or value[1] == "_")
    ):
        return None
    return Decimal(value.replace(",", ""))


def main():
    accounts = []
    with INPUT_FILE.open(encoding="utf-8") as source:
        for line_no, line in enumerate(source, 1):
            if len(line.rstrip("\r\n")) < 239:
                raise ValueError(f"Line {line_no}: fewer than 239 characters")
            acctno = number(line[141:151])
            costctr = number(line[235:239])
            if costctr is not None and (
                3000 <= costctr <= 3999 or costctr in (4043, 4048)
            ):
                accounts.append(acctno)

    # Missing accounts first; ascending order; duplicates retained.
    accounts.sort(key=lambda value: value if value is not None else Decimal("-Infinity"))
    TEXT_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = TEXT_FILE.with_suffix(".txt.tmp")
    with temporary.open("w", encoding="utf-8", newline="") as target:
        target.writelines(
            (format(value, "f") if value is not None else "") + "\n"
            for value in accounts
        )
    temporary.replace(TEXT_FILE)
    print(f"TXT created: {TEXT_FILE}")

    # Read the TXT output, then convert it to SAS7BDAT through SASPy.
    del accounts
    if TEXT_FILE.stat().st_size == 0:
        frame = pd.DataFrame({"ACCTNO": pd.Series(dtype="float64")})
    else:
        frame = pd.read_csv(
            TEXT_FILE, header=None, names=["ACCTNO"], dtype="float64",
            skip_blank_lines=False, encoding="utf-8",
        )
    SAS_FOLDER.mkdir(parents=True, exist_ok=True)
    sas = saspy.SASsession(cfgname=SAS_CONFIG) if SAS_CONFIG else saspy.SASsession()
    try:
        sas.saslib("outlib", path=str(SAS_FOLDER))
        if re.search(r"^ERROR(?:\s|:)", sas.lastlog(), re.MULTILINE):
            raise RuntimeError(sas.lastlog())
        result = sas.dataframe2sasdata(frame, table=SAS_MEMBER, libref="outlib")
        if result is None or re.search(r"^ERROR(?:\s|:)", sas.lastlog(), re.MULTILINE):
            raise RuntimeError("SAS export failed: " + sas.lastlog())
        if not sas.exist(SAS_MEMBER, libref="outlib"):
            raise RuntimeError("SAS output was not created")
    finally:
        sas.endsas()
    print(f"SAS7BDAT created: {SAS_FOLDER / (SAS_MEMBER + '.sas7bdat')}")
    print(f"EIIWOF02 completed. Records: {len(frame)}")


if __name__ == "__main__":
    main()
