#!/usr/bin/env python3
"""Python conversion of SAS program EIFMNP03.

Inputs are SAS7BDAT files.  Column names are normalized to upper case.  The
program preserves the original stages: report date, LOAN+WIIS merge, existing
and current NPL calculations, previous-month movement processing, combined
IIS outputs, and summary/detail reports.

PBBLNFMT and PBBELF are provided as Python modules. The supplied NPLNTB include
contains only commented-out mappings, so apply_nplntb() intentionally performs
no transformation, matching the executable SAS behavior.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from pbblnfmt import put as pbbln_put


LOAN_TYPES = {
    128: "HPD AITAB", 130: "HPD AITAB", 983: "HPD AITAB",
    700: "HPD CONVENTIONAL", 705: "HPD CONVENTIONAL",
    380: "HPD CONVENTIONAL", 381: "HPD CONVENTIONAL",
    993: "HPD CONVENTIONAL", 996: "HPD CONVENTIONAL",
    720: "HPD CONVENTIONAL", 725: "HPD CONVENTIONAL",
    **{i: "HOUSING LOANS" for i in range(200, 300)},
}
ACCRUAL_TYPES = {720, 725}
PIBB_PROFILE = False

NUMERIC_ZERO = [
    "IISP", "OIP", "IISPW", "CURBAL", "TERMCHG", "EARNTERM", "NOTETERM",
    "FEETOT2", "FEEAMTA", "FEEAMT5", "FEEAMT", "FEETOT2", "ACCRUAL",
    "WSUSPEND", "WOISUSP", "WRECOVER", "WRECC", "WOIRECV", "WOIRECC",
    "WIISPW", "WOIW", "MARKETVL", "DAYS",
]


def read_sas(path: Path) -> pd.DataFrame:
    df = pd.read_sas(path, format="sas7bdat", encoding="latin1")
    df.columns = [str(c).upper() for c in df.columns]
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].map(
            lambda x: x.decode("latin1").rstrip() if isinstance(x, bytes)
            else (x.rstrip() if isinstance(x, str) else x)
        )
    return df


def sas_sum(*values: Any) -> float:
    a = pd.to_numeric(pd.Series(values), errors="coerce")
    return float(a.sum(skipna=True))


def sas_date(value: Any) -> pd.Timestamp:
    """Convert a SAS date (days since 1960-01-01) or date-like value."""
    if pd.isna(value):
        return pd.NaT
    if isinstance(value, (int, float, np.integer, np.floating)):
        return pd.to_datetime(value, unit="D", origin="1960-01-01")
    return pd.to_datetime(value)


def val(row: pd.Series, name: str, default: Any = 0) -> Any:
    x = row.get(name, default)
    return default if pd.isna(x) else x


def branch_label(ntbrch: Any, branch_map: dict[int, str]) -> str:
    try:
        code = int(ntbrch)
    except (TypeError, ValueError):
        return ""
    description = branch_map.get(code)
    if description is None:
        try:
            description = pbbln_put(code, "BRCHCD.", "")
        except KeyError:
            description = ""
    return f"{description} {code:03d}".strip()


def remaining_months(date: pd.Timestamp, issue: pd.Timestamp, term: float) -> float:
    if pd.isna(date) or pd.isna(issue):
        return np.nan
    return term - ((date.year - issue.year) * 12 + date.month - issue.month + 1)


def initialize_row(row: pd.Series) -> pd.Series:
    for c in NUMERIC_ZERO:
        if c not in row or pd.isna(row[c]):
            row[c] = 0.0
    if val(row, "EARNTERM") == 0:
        row["EARNTERM"] = val(row, "NOTETERM")
    row["WRITEOFF"] = val(row, "WRITEOFF", "N")
    row["WDOWNIND"] = val(row, "WDOWNIND", "N")
    row["RESCHEIND"] = val(row, "RESCHEIND", "N")
    row["USER5"] = val(row, "USER5", "")
    row["BORSTAT"] = val(row, "BORSTAT", "")
    return row


def rule78_sum(rem1: float, rem2: float, charge: float, term: float) -> float:
    if any(pd.isna(x) for x in (rem1, rem2)) or term <= 0 or rem1 < rem2:
        return 0.0
    months = np.arange(int(rem1), int(rem2) - 1, -1)
    return float((2 * (months + 1) * charge / (term * (term + 1))).sum())


def written_off(row: pd.Series) -> pd.Series:
    if row["WRITEOFF"] != "Y":
        return row
    row["SUSPEND"], row["OISUSP"] = val(row, "WSUSPEND"), val(row, "WOISUSP")
    if row["WDOWNIND"] != "Y":
        row["RECOVER"], row["RECC"] = val(row, "WRECOVER"), val(row, "WRECC")
        row["OIRECV"], row["OIRECC"] = val(row, "WOIRECV"), val(row, "WOIRECC")
        row["IIS"] = row["OI"] = 0.0
        row["IISPW"] = sas_sum(row["IISP"], row["SUSPEND"], -row["RECOVER"], -row["RECC"])
        row["OIW"] = sas_sum(row["OIP"], row["OISUSP"], -row["OIRECV"], -row["OIRECC"])
    else:
        row["IISPW"], row["OIW"] = val(row, "WIISPW"), val(row, "WOIW")
        row["IIS"] = sas_sum(row["IISP"], row["SUSPEND"], -val(row, "RECOVER"), -val(row, "RECC"), -row["IISPW"])
        if row["IIS"] < 0:
            row["RECOVER"] = 0.0
            row["IIS"] = sas_sum(row["IISP"], row["SUSPEND"], -val(row, "RECC"), -row["IISPW"])
        row["OI"] = sas_sum(row["OIP"], row["OISUSP"], -val(row, "OIRECV"), -val(row, "OIRECC"), -row["OIW"])
        if row["OI"] < 0:
            row["OIRECV"] = row["OIRECC"] = 0.0
            row["OI"] = sas_sum(row["OIP"], row["OISUSP"], -row["OIW"])
    return row


def rescheduled(row: pd.Series) -> pd.Series:
    if row["RESCHEIND"] == "Y":
        for target, source in [("SUSPEND", "WSUSPEND"), ("OISUSP", "WOISUSP"),
                               ("RECOVER", "WRECOVER"), ("RECC", "WRECC"),
                               ("OIRECV", "WOIRECV"), ("OIRECC", "WOIRECC")]:
            row[target] = val(row, source)
        row["IIS"] = sas_sum(row["IISP"], row["SUSPEND"], -row["RECOVER"], -row["RECC"], -val(row, "IISPW"))
        row["OI"] = sas_sum(row["OIP"], row["OISUSP"], -row["OIRECV"], -row["OIRECC"], -val(row, "OIW"))
    row["TOTIIS"] = sas_sum(row["IIS"], row["OI"])
    return row


def calculate_existing(row: pd.Series, report_date: pd.Timestamp) -> pd.Series:
    row = initialize_row(row.copy())
    for c in ["IIS", "SUSPEND", "UHC", "OI", "OISUSP", "RECOVER", "OIRECV", "OIRECC", "OIW", "RECC"]:
        row[c] = 0.0
    lt, days = int(val(row, "LOANTYPE", 0)), val(row, "DAYS")
    if row["WRITEOFF"] == "Y" and row["WDOWNIND"] != "Y":
        row["BORSTAT"] = "W"
    nonperforming = days > 89 or row["BORSTAT"] in {"F", "R", "I"} or (row["USER5"] == "N" and lt not in {983, 993})
    bl, issue, term, charge = sas_date(row.get("BLDATE")), sas_date(row.get("ISSDTE")), row["EARNTERM"], row["TERMCHG"]
    if pd.notna(bl) and charge > 0 and nonperforming:
        rem1 = remaining_months(bl, issue, term) - (3 if lt in {128, 130} else 1)
        rem2 = max(0, remaining_months(report_date, issue, term))
        rems = remaining_months(pd.Timestamp(report_date.year, 1, 1), issue, term)
        row["IIS"] = rule78_sum(rem1, rem2, charge, term)
        row["SUSPEND"] = rule78_sum(rems, rem2, charge, term)
        row["OI"] = sas_sum(row["FEETOT2"], -row["FEEAMTA"], row["FEEAMT5"])
        if lt not in {128, 130}:
            row["OISUSP"] = sas_sum(row["FEEAMT"], -row["FEEAMTA"], row["FEEAMT5"])
        if rem2 > 0 and term > 0:
            row["UHC"] = rem2 * (rem2 + 1) * charge / (term * (term + 1))
    elif nonperforming:
        row["OI"] = sas_sum(row["FEETOT2"], -row["FEEAMTA"], row["FEEAMT5"])
        row["OISUSP"] = sas_sum(row["FEEAMT"], -row["FEEAMTA"], row["FEEAMT5"])
    row["NETBAL"] = row["CURBAL"] - row["UHC"]
    if row["NETBAL"] <= row["IISP"] and (nonperforming or row["USER5"] == "N"):
        row["IIS"] = row["NETBAL"]
    if row["BORSTAT"] == "W":
        row["IISPW"], row["OIW"] = row["IISP"], row["OIP"]
    else:
        row["RECOVER"] = row["IISP"] + row["SUSPEND"] - row["IIS"]
        if row["RECOVER"] < 0:
            row["SUSPEND"] -= row["RECOVER"]; row["RECOVER"] = 0.0
        if row["RECOVER"] > row["IISP"]:
            row["RECC"] = row["RECOVER"] - row["IISP"]; row["RECOVER"] = row["IISP"]
        if lt not in {128, 130}:
            row["OIRECV"] = row["OIP"] - row["OI"]
            if row["OIRECV"] < 0:
                row["OISUSP"] -= row["OIRECV"]; row["OIRECV"] = 0.0
            if row["OISUSP"] < 0: row["OIRECV"] -= row["OISUSP"]
            if row["OIRECV"] > row["OIP"]:
                row["OIRECC"] = row["OIRECV"] - row["OIP"]; row["OIRECV"] = row["OIP"]
    if charge == 0:
        netexp = row["CURBAL"] - row["IISP"] - (row["MARKETVL"] if row["BORSTAT"] == "R" else 0)
        if (netexp > 0 and days > 89) or row["BORSTAT"] == "R":
            row["IIS"], row["RECOVER"] = row["RECOVER"], 0.0
            row["OI"], row["OIRECV"] = sas_sum(row["FEETOT2"], -row["FEEAMTA"], row["FEEAMT5"]), 0.0
    if lt in ACCRUAL_TYPES: row["IIS"] = row["ACCRUAL"]
    row["OISUSP"] = sas_sum(row["OIRECV"], row["OIRECC"], row["OIW"], -row["OIP"], row["OI"])
    if row["OISUSP"] < 0: row["OIRECV"] -= row["OISUSP"]
    if row["OIRECV"] > row["OIP"]:
        row["OIRECC"] = row["OIRECV"] - row["OIP"]; row["OIRECV"] = row["OIP"]
    row["OISUSP"] = sas_sum(row["OIRECV"], row["OIRECC"], row["OIW"], -row["OIP"], row["OI"])
    return rescheduled(written_off(row))


def calculate_current(row: pd.Series, report_date: pd.Timestamp) -> pd.Series:
    row = initialize_row(row.copy())
    for c in ["IIS", "UHC", "OI", "RECOVER", "RECC", "OIRECV", "OIRECC", "IISPW", "OIW"]:
        row[c] = 0.0
    lt = int(val(row, "LOANTYPE", 0))
    if row["WRITEOFF"] == "Y" and row["WDOWNIND"] != "Y": row["BORSTAT"] = "W"
    issue, bl = sas_date(row.get("ISSDTE")), sas_date(row.get("BLDATE"))
    term, charge = row["EARNTERM"], row["TERMCHG"]
    condition = (pd.notna(bl) and charge > 0) or (row["USER5"] == "N" and lt not in {983, 993})
    rem2 = max(0, remaining_months(report_date, issue, term)) if pd.notna(issue) else 0
    if condition:
        rem1 = remaining_months(bl, issue, term) - (3 if lt in {128, 130} else 1)
        row["IIS"] = rule78_sum(rem1, rem2, charge, term)
    if rem2 > 0 and term > 0: row["UHC"] = rem2 * (rem2 + 1) * charge / (term * (term + 1))
    row["OI"] = sas_sum(row["FEETOT2"], -row["FEEAMTA"], row["FEEAMT5"])
    if lt in ACCRUAL_TYPES: row["IIS"] = row["ACCRUAL"]
    row["SUSPEND"], row["OISUSP"] = row["IIS"], row["OI"]
    row["NETBAL"] = row["CURBAL"] - row["UHC"]
    return rescheduled(written_off(row))


def apply_nplntb(previous: pd.DataFrame) -> pd.DataFrame:
    """Match PGM(NPLNTB), whose supplied transformation rules are commented."""
    return previous


def risk(row: pd.Series) -> str:
    if val(row, "DAYS") > 364 or val(row, "BORSTAT", "") == "W": return "BAD"
    if val(row, "DAYS") > 273: return "DOUBTFUL"
    if val(row, "DAYS") > 182: return "SUBSTANDARD 2"
    return "SUBSTANDARD-1"


def load_branch_map(path: Path | None) -> dict[int, str]:
    if not path: return {}
    m = pd.read_csv(path)
    m.columns = [c.upper() for c in m.columns]
    return dict(zip(m["NTBRCH"].astype(int), m["BRANCH"].astype(str)))


def write_reports(df: pd.DataFrame, output: Path) -> None:
    measures = ["CURBAL", "UHC", "NETBAL", "IISP", "SUSPEND", "RECOVER", "RECC",
                "IISPW", "IIS", "OIP", "OISUSP", "OIRECV", "OIRECC", "OIW", "OI", "TOTIIS"]
    for c in measures:
        if c not in df: df[c] = 0.0
    summary = df.groupby(["LOANTYP", "RISK", "BRANCH"], dropna=False).agg(
        NO_OF_ACCOUNT=("ACCTNO", "size"), **{c: (c, "sum") for c in measures}
    ).reset_index()
    detail_cols = [c for c in ["LOANTYP", "BRANCH", "RISK", "ACCTNO", "NOTENO", "NAME", "DAYS", "BORSTAT", "NETPROC"] + measures if c in df]
    summary.to_csv(output / "eifmnp03_summary.csv", index=False)
    df.sort_values([c for c in ["LOANTYP", "BRANCH", "RISK", "DAYS", "ACCTNO"] if c in df])[detail_cols].to_csv(output / "eifmnp03_detail.csv", index=False)


IIS_REPORT_LABELS = {
    "ACCTNO":"MNI ACCOUNT NO", "DAYS":"NO OF DAYS PAST DUE",
    "BORSTAT":"BORROWER'S STATUS", "NETPROC":"LIMIT", "CURBAL":"CURRENT BAL (A)",
    "UHC":"UNEARNED HIRING CHARGES (B)", "NETBAL":"NET BAL (A-B=C)",
    "IISP":"OPENING BAL FOR FINANCIAL YEAR (D)",
    "SUSPEND":"INTEREST SUSPENDED DURING THE PERIOD (E)",
    "RECOVER":"WRITTEN BACK TO PROFIT & LOSS (F)",
    "RECC":"REVERSAL OF CURRENT YEAR IIS (G)", "IISPW":"WRITTEN OFF (H)",
    "IIS":"IIS CLOSING BAL (D+E-F-G-H=I)",
    "OIP":"OPENING BAL FOR FINANCIAL YEAR (J)",
    "OISUSP":"OI SUSPENDED DURING THE PERIOD (K)",
    "OIRECV":"WRITTEN BACK TO PROFIT & LOSS (L)",
    "OIRECC":"REVERSAL OF CURRENT YEAR OI (M)", "OIW":"WRITTEN OFF (N)",
    "OI":"OI CLOSING BAL (J+K-L-M-N=O)",
    "TOTIIS":"TOTAL CLOSING BAL AS AT RPT DATE (I+O)",
}


def write_original_listing(df: pd.DataFrame, report_date: pd.Timestamp, output: Path) -> str:
    """Render both PROC TABULATE tables and the original PROC PRINT listing."""
    measures=["CURBAL","UHC","NETBAL","IISP","SUSPEND","RECOVER","RECC","IISPW","IIS","OIP","OISUSP","OIRECV","OIRECC","OIW","OI","TOTIIS"]
    for column in measures:
        if column not in df: df[column]=0.0
    title1="PUBLIC BANK - (NPL FROM 3 MONTHS & ABOVE) - NEW"
    title2=f"MOVEMENTS OF INTEREST IN SUSPENSE FOR THE MONTH ENDING {report_date.strftime('%d %B %Y').upper()} (EXISTING AND CURRENT)"
    fmt=lambda value:f"{value:,.2f}"
    risk_branch=df.groupby(["LOANTYP","RISK","BRANCH"],dropna=False).agg(NO_OF_ACCOUNT=("ACCTNO","size"),**{c:(c,"sum") for c in measures}).reset_index()
    branch=df.groupby(["LOANTYP","BRANCH"],dropna=False).agg(NO_OF_ACCOUNT=("ACCTNO","size"),**{c:(c,"sum") for c in measures}).reset_index()
    rename={**IIS_REPORT_LABELS,"NO_OF_ACCOUNT":"NO OF ACCOUNT"}
    lines=[title1,title2,"","SUMMARY BY RISK AND BRANCH",
           risk_branch.rename(columns=rename).to_string(index=False,formatters={rename[c]:fmt for c in measures}),
           "","SUMMARY BY BRANCH",
           branch.rename(columns=rename).to_string(index=False,formatters={rename[c]:fmt for c in measures}),
           "","DETAILED LISTING"]
    ordered=df.sort_values(["LOANTYP","BRANCH","RISK","DAYS","ACCTNO"])
    detail_cols=["ACCTNO","NAME","DAYS","BORSTAT","NETPROC",*measures]
    for (loan_type,branch_name,risk_name),group in ordered.groupby(["LOANTYP","BRANCH","RISK"],dropna=False,sort=False):
        lines.extend(["",f"LOAN TYPE: {loan_type}    BRANCH: {branch_name}    RISK: {risk_name}"])
        display=group[[c for c in detail_cols if c in group]].rename(columns=IIS_REPORT_LABELS)
        lines.append(display.to_string(index=False,formatters={IIS_REPORT_LABELS[c]:fmt for c in measures if c in group}))
        totals=group[measures].sum()
        lines.append("TOTAL: "+" | ".join(f"{IIS_REPORT_LABELS[c]}={totals[c]:,.2f}" for c in measures))
    report="\n".join(lines)+"\n"
    (output/"eifmnp03_report.lst").write_text(report,encoding="utf-8")
    (output/"eifmnp03_report.txt").write_text(report,encoding="utf-8")
    return report


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input-dir", type=Path, required=True)
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--loan-pattern", default="loan{mm}.sas7bdat")
    p.add_argument("--wiis-file", default="wiis.sas7bdat")
    p.add_argument("--previous-pattern", default="iis{mm}.sas7bdat")
    p.add_argument("--ploan-pattern", default="ploan{mm}.sas7bdat")
    p.add_argument("--branch-map", type=Path)
    p.add_argument("--no-console-report", action="store_true")
    args = p.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    # Replacement for NPL.REPTDATE: process as at yesterday's calendar date.
    report_date = pd.Timestamp(date.today() - timedelta(days=1))
    mm, prev = f"{report_date.month:02d}", f"{(report_date.month - 2) % 12 + 1:02d}"
    loan = read_sas(args.input_dir / args.loan_pattern.format(mm=mm))
    wiis = read_sas(args.input_dir / args.wiis_file).drop(columns=["NOTENO", "NTBRCH"], errors="ignore")
    wiis["_WIIS"] = True
    loan = loan.merge(wiis, on="ACCTNO", how="left", suffixes=("", "_WIIS"))
    loan["WRITEOFF"] = np.where(loan["_WIIS"].fillna(False), "Y", "N")
    if "LOANTYPE" in loan:
        loan.loc[loan["LOANTYPE"].isin([380, 381]), "FEEAMT"] = loan.loc[loan["LOANTYPE"].isin([380, 381]), "FEETOT2"]
        loan.loc[loan["LOANTYPE"].isin([983, 993]), "WDOWNIND"] = "N"
    bmap = load_branch_map(args.branch_map)
    existing = loan[loan.get("EXIST", "") == "Y"].apply(calculate_existing, axis=1, report_date=report_date)
    current = loan[loan.get("EXIST", "") != "Y"].apply(calculate_current, axis=1, report_date=report_date)
    for df in (existing, current):
        df["BRANCH"] = df["NTBRCH"].map(lambda x: branch_label(x, bmap))
        df["LOANTYP"] = df["LOANTYPE"].map(LOAN_TYPES).fillna("OTHERS")
    if mm == "01":
        for df in (existing, current): df[["IISPCUM", "OIPCUM", "POI"]] = 0.0
    else:
        previous_path = args.input_dir / args.previous_pattern.format(mm=prev)
        if previous_path.exists():
            previous = apply_nplntb(read_sas(previous_path))
            # Retain prior columns for audit and downstream reconciliation.
            ren = {"DAYS": "PDAYS", "SUSPEND": "PSUSPEND", "OISUSP": "POISUSP", "IISP": "PIISP", "OIP": "POIP", "OI": "POI", "RECC": "PRECC", "OIRECC": "POIRECC", "RECOVER": "PRECOVER", "OIRECV": "POIRECV"}
            previous = previous.rename(columns=ren).drop_duplicates(["ACCTNO", "NOTENO"])
            existing = existing.merge(previous[[c for c in previous if c in set(ren.values()) | {"ACCTNO", "NOTENO"}]], on=["ACCTNO", "NOTENO"], how="outer", suffixes=("", "_PREV"))
            # SAS uses PLOANMM to retain prior current-NPL accounts which are
            # absent from the current LOANMM extract (settled-account path).
            ploan_path = args.input_dir / args.ploan_pattern.format(mm=mm)
            if ploan_path.exists():
                ploan_cols = ["ACCTNO", "NOTENO", "CURBAL", "DAYS", "BORSTAT", "NTBRCH", "COSTCTR"]
                ploan = read_sas(ploan_path)[ploan_cols].drop_duplicates(["ACCTNO", "NOTENO"])
                eligible = previous.copy()
                piisp = pd.to_numeric(eligible.get("PIISP", pd.Series(0, index=eligible.index)), errors="coerce").fillna(0)
                poip = pd.to_numeric(eligible.get("POIP", pd.Series(0, index=eligible.index)), errors="coerce").fillna(0)
                exist = eligible.get("EXIST", pd.Series("", index=eligible.index)).fillna("")
                eligible = eligible[(piisp == 0) & (poip == 0) & (exist != "Y")]
                eligible = eligible.merge(ploan, on=["ACCTNO", "NOTENO"], how="left", suffixes=("", "_PLOAN"))
            else:
                eligible = previous
            current = current.merge(
                eligible[[c for c in eligible if c in set(ren.values()) | {"ACCTNO", "NOTENO"}]],
                on=["ACCTNO", "NOTENO"], how="outer", suffixes=("", "_PREV")
            )
    combined = pd.concat([existing, current], ignore_index=True, sort=False)
    if PIBB_PROFILE:
        # EIIMNP03: Islamic cost centres plus the two explicitly included centres.
        combined = combined[
            ((combined["COSTCTR"] >= 3000) & (combined["COSTCTR"] <= 3999))
            | combined["COSTCTR"].isin([4043, 4048])
        ]
    else:
        # EIFMNP03: PBB excludes Islamic cost centres and 4043/4048.
        combined = combined[
            ((combined["COSTCTR"] < 3000) | (combined["COSTCTR"] > 3999))
            & ~combined["COSTCTR"].isin([4043, 4048])
            & combined["COSTCTR"].notna()
        ]
    combined["RISK"] = combined.apply(risk, axis=1)
    combined = combined.drop_duplicates(["ACCTNO", "NOTENO"])
    combined.to_csv(args.output_dir / f"iis{mm}.csv", index=False)
    write_reports(combined, args.output_dir)
    report = write_original_listing(combined, report_date, args.output_dir)
    print(f"Processed {len(combined):,} rows for {report_date.date()} into {args.output_dir}")
    if not args.no_console_report:
        print(report, end="")


if __name__ == "__main__":
    main()
















#!/usr/bin/env python3
"""PBB EIFMNP06: complete specific-provision job and reports."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from eifmnp03 import branch_label, load_branch_map, read_sas, risk, sas_date, sas_sum, val


LNTYP = {
    128: "HPD AITAB", 130: "HPD AITAB", 983: "HPD AITAB",
    700: "HPD CONVENTIONAL", 705: "HPD CONVENTIONAL",
    380: "HPD CONVENTIONAL", 381: "HPD CONVENTIONAL",
    720: "HPD CONVENTIONAL", 725: "HPD CONVENTIONAL",
    993: "HPD CONVENTIONAL", 996: "HPD CONVENTIONAL",
    **{i: "HOUSING LOANS" for i in range(200, 300)},
}
PIBB_PROFILE = False
PROGRAM_NAME = "EIFMNP06"
REPORT_ENTITY = "PUBLIC BANK"

REPORT_LABELS = {
    "ACCTNO":"MNI ACCOUNT NO", "VINNO":"AA NUMBER", "DAYS":"NO OF DAYS PAST DUE",
    "BORSTAT":"BORROWER'S STATUS", "NETPROC":"LIMIT", "CURBAL":"CURRENT BAL (A)",
    "UHC":"UNEARNED HIRING CHARGES (B)", "NETBAL":"NET BAL (A-B=C)", "IIS":"IIS (E)",
    "OSPRIN":"PRINCIPAL OUTSTANDING (C-E=F)", "OTHERFEE":"OTHER FEES",
    "MARKETVL":"REALISABLE VALUE (G)", "NETEXP":"NET EXPOSURE (F-G=H)",
    "SPP2":"OPENING BAL FOR FINANCIAL YEAR (I)",
    "SPPL":"PROVISION MADE AGAINST PROFIT & LOSS (J)",
    "RECOVER":"WRITTEN BACK TO PROFIT & LOSS (K)",
    "SPPW":"WRITTEN OFF AGAINST PROVISION (L)",
    "SP":"CLOSING BAL AS AT RPT DATE (I+J-K-L)",
}


def write_original_report(out: pd.DataFrame, report_date: pd.Timestamp, output_dir: Path) -> str:
    """Render both PROC TABULATE tables and the original PROC PRINT listing."""
    measures=["CURBAL","UHC","NETBAL","IIS","OSPRIN","MARKETVL","NETEXP","SPP2","SPPL","RECOVER","SPPW","SP","OTHERFEE"]
    title1=f"{REPORT_ENTITY} - (NPL FROM 3 MONTHS & ABOVE) - NEW"
    title2=f"MOVEMENTS OF SPECIFIC PROVISION FOR THE MONTH ENDING {report_date.strftime('%d %B %Y').upper()} (EXISTING AND CURRENT)"
    fmt=lambda value:f"{value:,.2f}"
    risk_branch=out.groupby(["LOANTYP","RISK","BRANCH"],dropna=False).agg(NO_OF_ACCOUNT=("ACCTNO","size"),**{c:(c,"sum") for c in measures}).reset_index()
    branch=out.groupby(["LOANTYP","BRANCH"],dropna=False).agg(NO_OF_ACCOUNT=("ACCTNO","size"),**{c:(c,"sum") for c in measures}).reset_index()
    rename={**REPORT_LABELS,"NO_OF_ACCOUNT":"NO OF ACCOUNT"}
    lines=[title1,title2,"","SUMMARY BY RISK AND BRANCH",
           risk_branch.rename(columns=rename).to_string(index=False,formatters={rename[c]:fmt for c in measures}),
           "","SUMMARY BY BRANCH",
           branch.rename(columns=rename).to_string(index=False,formatters={rename[c]:fmt for c in measures}),
           "","DETAILED LISTING"]
    ordered=out.sort_values(["LOANTYP","BRANCH","RISK","DAYS","ACCTNO"])
    detail_cols=["ACCTNO","NAME","VINNO","DAYS","BORSTAT","NETPROC",*measures]
    for (loan_type,branch_name,risk_name),group in ordered.groupby(["LOANTYP","BRANCH","RISK"],dropna=False,sort=False):
        lines.extend(["",f"LOAN TYPE: {loan_type}    BRANCH: {branch_name}    RISK: {risk_name}"])
        display=group[[c for c in detail_cols if c in group]].rename(columns=REPORT_LABELS)
        lines.append(display.to_string(index=False,formatters={REPORT_LABELS[c]:fmt for c in measures if c in group}))
        totals=group[measures].sum()
        lines.append("TOTAL: "+" | ".join(f"{REPORT_LABELS[c]}={totals[c]:,.2f}" for c in measures))
    report="\n".join(lines)+"\n"
    (output_dir/f"{PROGRAM_NAME.lower()}_report.lst").write_text(report,encoding="utf-8")
    (output_dir/f"{PROGRAM_NAME.lower()}_report.txt").write_text(report,encoding="utf-8")
    return report


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        df.columns = [c.upper() for c in df.columns]
        return df
    return read_sas(path)


def provision(row: pd.Series, report_date: pd.Timestamp, existing: bool) -> pd.Series:
    row = row.copy()
    for c in ["CURBAL", "TERMCHG", "EARNTERM", "NOTETERM", "IIS", "FEEAMT", "FEETOT2", "FEEAMT8",
              "FEEAMTA", "FEEAMT5", "APPVALUE", "MARKETVL", "SPP2", "WREALVL", "WSPPL", "WSP",
              "WRECOVER", "WSPPW", "DAYS"]:
        if c not in row or pd.isna(row[c]): row[c] = 0.0
    if row["EARNTERM"] == 0: row["EARNTERM"] = row["NOTETERM"]
    lt, days = int(val(row, "LOANTYPE", 0)), row["DAYS"]
    borstat, user5 = val(row, "BORSTAT", ""), val(row, "USER5", "")
    written = val(row, "WRITEOFF", "N") == "Y"
    wdown = val(row, "WDOWNIND", "N")
    if written and wdown != "Y": borstat = row["BORSTAT"] = "W"
    issue, bill = sas_date(row.get("ISSDTE")), sas_date(row.get("BLDATE"))
    uhc = 0.0
    if pd.notna(issue):
        rem2 = max(0, row["EARNTERM"] - ((report_date.year-issue.year)*12 + report_date.month-issue.month + 1))
        if rem2 > 0 and row["EARNTERM"] > 0:
            uhc = rem2*(rem2+1)*row["TERMCHG"]/(row["EARNTERM"]*(row["EARNTERM"]+1))
    row["UHC"] = uhc
    row["NETBAL"] = row["CURBAL"] - uhc
    row["OSPRIN"] = row["CURBAL"] - uhc - row["IIS"]
    if lt in {380, 381}:
        other = sas_sum(row["FEEAMT"], -row["FEETOT2"])
    else:
        other = sas_sum(row["FEEAMT8"], -row["FEETOT2"], row["FEEAMTA"], -row["FEEAMT5"])
    row["OTHERFEE"] = 0.0 if lt in {983, 993} else max(0.0, other)
    secured = row["APPVALUE"] > 0 and (lt in {705,128,700,130,380,381} or val(row,"CENSUS7","") == "9") \
              and (days > 89 or user5 == "N") and borstat not in {"F","R","I","Y","W"} and lt not in {983,993}
    hardcode = val(row, "HARDCODE", "N") == "Y"
    market = row["MARKETVL"]
    if secured:
        age = int(report_date.year-issue.year + (report_date.month-issue.month)/12) if pd.notna(issue) else 0
        if val(row,"CENSUS7","") != "9": market = row["APPVALUE"] * (1 - age*0.2)
        if hardcode: market = row["WREALVL"]
        market = max(0.0, market)
        netexp = row["OSPRIN"] + row["OTHERFEE"] - (0 if days > 273 else market)
        sp = netexp if days > 364 else netexp/2 if days > 273 else netexp*0.2
    else:
        if borstat != "R": market = 0.0
        if hardcode: market = row["WREALVL"]
        netexp = row["OSPRIN"] + row["OTHERFEE"] - market
        sp = netexp if days > 364 or borstat in {"F","R","I","W"} else netexp/2 if days > 273 else netexp/5 if days > 89 and borstat == "Y" else 0.0
    row["MARKETVL"], row["NETEXP"], row["SP"] = market, netexp, max(0.0, sp)
    row["SPPL"] = max(0.0, row["SP"] - row["SPP2"]) if existing else row["SP"]
    if hardcode:
        if pd.notna(row.get("WSPPL")): row["SPPL"] = row["WSPPL"]
        if pd.notna(row.get("WSP")): row["SP"] = row["WSP"]
    row["RECOVER"], row["SPPW"] = (max(0.0, row["SPP2"]-row["SP"]), 0.0) if existing else (0.0, 0.0)
    if borstat == "W": row["SPPW"], row["SP"], row["MARKETVL"] = row["SPP2"], 0.0, 0.0
    if written:
        row["SPPL"], row["OTHERFEE"] = row["WSPPL"], 0.0
        if wdown != "Y":
            row["RECOVER"], row["SP"] = row["WRECOVER"], 0.0
            row["SPPW"] = sas_sum(row["SPP2"], row["SPPL"], -row["RECOVER"])
        else:
            row["SPPW"] = row["WSPPW"]
            if row["NETEXP"] <= 0: row["RECOVER"] = 0.0
            row["SP"] = sas_sum(row["SPP2"], row["SPPL"], -row["RECOVER"], -row["SPPW"])
            if row["NETEXP"] <= 0 and row["SP"] > 0: row["RECOVER"], row["SP"] = row["SP"], 0.0
    if val(row,"RESCHEIND","") == "Y":
        row["RECOVER"], row["SPPW"] = val(row,"WRECOVER"), val(row,"WSPPW")
        row["SP"] = sas_sum(row["SPP2"], row["SPPL"], -row["RECOVER"], -row["SPPW"])
    return row


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--input-dir",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True)
    p.add_argument("--iis-file",type=Path,help="Optional explicit IIS SAS7BDAT path")
    p.add_argument("--iis-pattern",default="iis{mm}.sas7bdat"); p.add_argument("--loan-pattern",default="loan{mm}.sas7bdat")
    p.add_argument("--wsp2-file",default="wsp2.sas7bdat"); p.add_argument("--previous-pattern",default="sp2{mm}.sas7bdat"); p.add_argument("--branch-map",type=Path); p.add_argument("--no-console-report",action="store_true")
    a=p.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True); rd=pd.Timestamp(date.today()-timedelta(days=1)); mm=f"{rd.month:02d}"; prev=f"{(rd.month-2)%12+1:02d}"
    loan=read_sas(a.input_dir/a.loan_pattern.format(mm=mm)); wsp=read_sas(a.input_dir/a.wsp2_file).drop(columns=["NOTENO","NTBRCH"],errors="ignore"); wsp["_WSP"]=True
    data=loan.merge(wsp,on="ACCTNO",how="left",suffixes=("","_WSP")); data["WRITEOFF"]=np.where(data["_WSP"].fillna(False),"Y","N")
    iis_path = a.iis_file if a.iis_file else a.input_dir/a.iis_pattern.format(mm=mm)
    iis=read_table(iis_path)[["ACCTNO","IIS"]].drop_duplicates("ACCTNO"); data=data.merge(iis,on="ACCTNO",how="left",suffixes=("","_IIS")); data["IIS"]=data.get("IIS_IIS",data.get("IIS",0)).fillna(0)
    existing=data[data.get("EXIST","")=="Y"].apply(provision,axis=1,report_date=rd,existing=True); current=data[data.get("EXIST","")!="Y"].apply(provision,axis=1,report_date=rd,existing=False)
    out=pd.concat([existing,current],ignore_index=True,sort=False)
    if PIBB_PROFILE:
        out=out[((out["COSTCTR"]>=3000)&(out["COSTCTR"]<=3999))|out["COSTCTR"].isin([4043,4048])]
    else:
        out=out[((out["COSTCTR"]<3000)|(out["COSTCTR"]>3999))&~out["COSTCTR"].isin([4043,4048])&out["COSTCTR"].notna()]
    bm=load_branch_map(a.branch_map); out["BRANCH"]=out["NTBRCH"].map(lambda x:branch_label(x,bm)); out["LOANTYP"]=out["LOANTYPE"].map(LNTYP).fillna("OTHERS"); out["RISK"]=out.apply(risk,axis=1); out=out.drop_duplicates(["ACCTNO","NOTENO"])
    out.to_csv(a.output_dir/f"sp2{mm}.csv",index=False); measures=["CURBAL","UHC","NETBAL","IIS","OSPRIN","MARKETVL","NETEXP","SPP2","SPPL","RECOVER","SPPW","SP","OTHERFEE"]
    out.groupby(["LOANTYP","RISK","BRANCH"],dropna=False)[measures].sum().reset_index().to_csv(a.output_dir/f"{PROGRAM_NAME.lower()}_summary.csv",index=False)
    out.to_csv(a.output_dir/f"{PROGRAM_NAME.lower()}_detail.csv",index=False); report=write_original_report(out,rd,a.output_dir); print(f"{PROGRAM_NAME} processed {len(out):,} rows for {rd.date()}")
    if not a.no_console_report: print(report,end="")


if __name__=="__main__": main()















#!/usr/bin/env python3
"""PBB EIFMNP07: complete asset-quality/NPL movement job and reports."""
from __future__ import annotations

import argparse
from datetime import date,timedelta
from pathlib import Path
import numpy as np
import pandas as pd
from eifmnp03 import branch_label,load_branch_map,read_sas,risk,sas_date,sas_sum,val

LNTYP = {
    128: "HPD AITAB", 130: "HPD AITAB", 983: "HPD AITAB",
    700: "HPD CONVENTIONAL", 705: "HPD CONVENTIONAL",
    380: "HPD CONVENTIONAL", 381: "HPD CONVENTIONAL",
    720: "HPD CONVENTIONAL", 725: "HPD CONVENTIONAL",
    993: "HPD CONVENTIONAL", 996: "HPD CONVENTIONAL",
    **{i: "HOUSING LOANS" for i in range(200, 300)},
}
PIBB_PROFILE = False
PROGRAM_NAME = "EIFMNP07"
REPORT_ENTITY = "PUBLIC BANK"


REPORT_LABELS = {
    "ACCTNO": "MNI ACCOUNT NO", "DAYS": "NO OF DAYS PAST DUE",
    "CURBALP": "BAL AS AT PREV YEAR (WITH UHC)",
    "CURBAL": "BAL AS AT END OF RPT DATE (WITH UHC)",
    "NETBALP": "NET BAL AS AT PREV YEAR (A)",
    "NEWNPL": "NEW NPL DURING CURRENT YEAR (B)",
    "ACCRINT": "ACCRUED INTEREST (C)", "RECOVER": "RECOVERIES (D)",
    "PL": "NPL CLASSIFIED AS PERFORMING (E)", "NPLW": "NPL WRITTEN-OFF (F)",
    "ADJUST": "ADJUSTMENT", "NPL": "NPL AS AT END OF RPT DATE (A+B+C-D-E-F)",
}


def write_original_report(out: pd.DataFrame, report_date: pd.Timestamp, output_dir: Path) -> str:
    """Render the two PROC TABULATE tables and PROC PRINT detail listing."""
    measures = ["CURBALP","CURBAL","NETBALP","NEWNPL","ACCRINT","RECOVER","PL","NPLW","ADJUST","NPL"]
    detail_cols = ["ACCTNO","NAME","DAYS",*measures]
    title1 = f"{REPORT_ENTITY} - (NPL FROM 3 MONTHS & ABOVE)"
    title2 = f"STATISTICS ON ASSET QUALITY - MOVEMENTS IN NPL {report_date.strftime('%d %B %Y').upper()}"
    number_format = lambda value: f"{value:,.2f}"
    risk_branch = out.groupby(["LOANTYP","RISK","BRANCH"],dropna=False).agg(
        NO_OF_ACCOUNT=("ACCTNO","size"), **{c:(c,"sum") for c in measures}
    ).reset_index()
    branch = out.groupby(["LOANTYP","BRANCH"],dropna=False).agg(
        NO_OF_ACCOUNT=("ACCTNO","size"), **{c:(c,"sum") for c in measures}
    ).reset_index()
    rename = {**REPORT_LABELS, "NO_OF_ACCOUNT":"NO OF ACCOUNT"}
    lines = [title1, title2, "", "SUMMARY BY RISK AND BRANCH"]
    lines.append(risk_branch.rename(columns=rename).to_string(index=False,formatters={rename[c]:number_format for c in measures}))
    lines.extend(["", "SUMMARY BY BRANCH"])
    lines.append(branch.rename(columns=rename).to_string(index=False,formatters={rename[c]:number_format for c in measures}))
    lines.extend(["", "DETAILED LISTING"])
    ordered = out.sort_values(["LOANTYP","BRANCH","RISK","DAYS","ACCTNO"])
    for (loan_type, branch_name, risk_name), group in ordered.groupby(["LOANTYP","BRANCH","RISK"],dropna=False,sort=False):
        lines.extend(["", f"LOAN TYPE: {loan_type}    BRANCH: {branch_name}    RISK: {risk_name}"])
        display = group[[c for c in detail_cols if c in group]].rename(columns=REPORT_LABELS)
        lines.append(display.to_string(index=False,formatters={REPORT_LABELS[c]:number_format for c in measures if c in group}))
        totals = group[measures].sum()
        lines.append("TOTAL: " + " | ".join(f"{REPORT_LABELS[c]}={totals[c]:,.2f}" for c in measures))
    report = "\n".join(lines) + "\n"
    # .lst corresponds to the original SASLIST/PROC PRINT listing output.
    (output_dir/f"{PROGRAM_NAME.lower()}_report.lst").write_text(report,encoding="utf-8")
    (output_dir/f"{PROGRAM_NAME.lower()}_report.txt").write_text(report,encoding="utf-8")
    return report


def movement(row:pd.Series,rd:pd.Timestamp,existing:bool)->pd.Series:
    row=row.copy()
    for c in ["CURBALP","CURBAL","NETBALP","FEEAMT","FEETOT2","FEEYTD","FEEPDYTD","TERMCHG","EARNTERM","NOTETERM","UHCP","WACCRINT","WNEWNPL","WRECOVER","WNPLW","DAYS"]:
        if c not in row or pd.isna(row[c]): row[c]=0.0
    if row["EARNTERM"]==0: row["EARNTERM"]=row["NOTETERM"]
    lt=int(val(row,"LOANTYPE",0)); bor=val(row,"BORSTAT",""); user5=val(row,"USER5",""); written=val(row,"WRITEOFF","N")=="Y"; wdown=val(row,"WDOWNIND","N")
    if written and wdown!="Y": bor=row["BORSTAT"]="W"
    row["ADJUST"]=row["FEEAMT"]-row["FEETOT2"] if existing else 0.0
    row["NEWNPL"]=row["ACCRINT"]=row["RECOVER"]=row["PL"]=row["NPLW"]=row["NPL"]=0.0; uhc=0.0
    issue=sas_date(row.get("ISSDTE")); bill=sas_date(row.get("BLDATE"))
    if pd.notna(issue):
        rem2=max(0,row["EARNTERM"]-((rd.year-issue.year)*12+rd.month-issue.month+1))
        if rem2>0 and row["EARNTERM"]>0: uhc=rem2*(rem2+1)*row["TERMCHG"]/(row["EARNTERM"]*(row["EARNTERM"]+1))
    if existing:
        performing=(row["DAYS"]<90 and bor in {"","A","C","S","T","Y"} and row["CURBAL"]>=0 and user5!="N") or lt in {983,993}
        if performing:
            row["PL"]=row["NETBALP"]
            if row["DAYS"]==0 and row["CURBAL"]==0: row["RECOVER"],row["PL"]=row["NETBALP"],0.0
        else:
            row["ACCRINT"]=row["FEEYTD"]; row["OI"]=row["FEEAMT"]
            if bor=="F": row["CURBALP"]-=row["UHCP"]
            row["RECOVER"]=0.0 if bor=="W" else row["CURBALP"]-row["CURBAL"]+row["FEEPDYTD"]
            if row["RECOVER"]<0: row["CURBALP"]-=row["RECOVER"]; row["RECOVER"]=0.0
            row["NPLW"]=row["NETBALP"] if bor=="W" else 0.0; row["NPL"]=0.0 if bor=="W" else row["CURBAL"]-uhc+row["OI"]
    else:
        row["OI"]=row["FEEAMT"]; row["NEWNPL"]=row["CURBAL"]-uhc+row["OI"]; row["NPL"]=row["NEWNPL"]
    if written or lt in {983,993}:
        row["ACCRINT"],row["NEWNPL"],row["ADJUST"]=row["WACCRINT"],row["WNEWNPL"],0.0
        if wdown!="Y": row["RECOVER"],row["PL"],row["NPL"]=row["WRECOVER"],0.0,0.0; row["NPLW"]=sas_sum(row["NETBALP"],row["NEWNPL"],row["ACCRINT"],-row["RECOVER"])
        else: row["NPLW"]=row["WNPLW"]; row["NPL"]=sas_sum(row["NETBALP"],row["NEWNPL"],row["ACCRINT"],-row["RECOVER"],-row["NPLW"],-row["PL"])
    row["CHKNPL"]=sas_sum(row["NETBALP"],row["NEWNPL"],row["ACCRINT"],-row["RECOVER"],-row["PL"],-row["NPLW"]); return row


def main():
    p=argparse.ArgumentParser();p.add_argument("--input-dir",type=Path,required=True);p.add_argument("--output-dir",type=Path,required=True);p.add_argument("--loan-pattern",default="loan{mm}.sas7bdat");p.add_argument("--waq-file",default="waq.sas7bdat");p.add_argument("--branch-map",type=Path);p.add_argument("--no-console-report",action="store_true",help="Save the PROC PRINT listing without echoing it to stdout");a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=True);rd=pd.Timestamp(date.today()-timedelta(days=1));mm=f"{rd.month:02d}";loan=read_sas(a.input_dir/a.loan_pattern.format(mm=mm));waq=read_sas(a.input_dir/a.waq_file).drop(columns=["NOTENO","NTBRCH"],errors="ignore");waq["_WAQ"]=True
    data=loan.merge(waq,on="ACCTNO",how="left",suffixes=("","_WAQ"));data["WRITEOFF"]=np.where(data["_WAQ"].fillna(False),"Y","N");ex=data[data.get("EXIST","")=="Y"].apply(movement,axis=1,rd=rd,existing=True);cu=data[data.get("EXIST","")!="Y"].apply(movement,axis=1,rd=rd,existing=False);out=pd.concat([ex,cu],ignore_index=True,sort=False)
    if PIBB_PROFILE: out=out[((out["COSTCTR"]>=3000)&(out["COSTCTR"]<=3999))|out["COSTCTR"].isin([4043,4048])]
    else: out=out[((out["COSTCTR"]<3000)|(out["COSTCTR"]>3999))&~out["COSTCTR"].isin([4043,4048])&out["COSTCTR"].notna()]
    bm=load_branch_map(a.branch_map);out["BRANCH"]=out["NTBRCH"].map(lambda x:branch_label(x,bm));out["LOANTYP"]=out["LOANTYPE"].map(LNTYP).fillna("OTHERS");out["RISK"]=out.apply(risk,axis=1);out.to_csv(a.output_dir/"aq.csv",index=False)
    measures=["CURBALP","CURBAL","NETBALP","NEWNPL","ACCRINT","RECOVER","PL","NPLW","ADJUST","NPL"];out.groupby(["LOANTYP","RISK","BRANCH"],dropna=False)[measures].sum().reset_index().to_csv(a.output_dir/f"{PROGRAM_NAME.lower()}_summary.csv",index=False);out.to_csv(a.output_dir/f"{PROGRAM_NAME.lower()}_detail.csv",index=False);report=write_original_report(out,rd,a.output_dir);print(f"{PROGRAM_NAME} processed {len(out):,} rows for {rd.date()}");
    if not a.no_console_report: print(report,end="")


if __name__=="__main__":main()




