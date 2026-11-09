"""Python port of AminPython/1INPUT (JCL job EIIMNP2A)."""

import argparse
import re
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from itertools import groupby
from pathlib import Path

import pandas as pd
import pyreadstat

EPOCH = date(1960, 1, 1)
HPD_AITAB = {128, 130, 131, 132}
HPD_CONVENTIONAL = {380, 381, 700, 705, 720, 725}
KEEP = """
LOANTYPE NTBRCH ACCTNO NOTENO NAME BORSTAT LOANSTAT NETPROC ORGBAL
CURBAL NOTETERM BLDATE LOANTYP ISSUEDT DAYS NETBAL BRANCH MAKE MODEL
DEALERNO COMPNAME PRIMOFHP CUSTFISS GUAREND OLDNOTEDAYARR CAP SCORE2
""".split()
TOTAL_COLUMNS = KEEP + [
    "TOTNET", "_FREQ_", "_TYPE_", "ISSDTE", "CACNAME", "REGION",
    "SUBTOT", "GRANDTOT", "REPTDATE",
]

def load_formats(include_dir):
    """Load the SAS VALUE definitions used by this job."""
    formats = {}
    includes = {
        "PBBLNFMT": ("LNCUSTCD",),
        "PBBELF": ("BRCHCD", "CACNAME", "REGIOFF"),
    }
    rule = re.compile(r"([\d.,\s-]+|OTHER)\s*=\s*'((?:''|[^'])*)'", re.I)
    for filename, names in includes.items():
        path = include_dir / filename
        source = re.sub(r"/\*[\s\S]*?\*/", "", path.read_text(encoding="utf-8-sig"))
        for name in names:
            definition = re.search(rf"^\s*VALUE\s+{name}\b([\s\S]*?);", source, re.I | re.M)
            if definition is None:
                raise ValueError(f"{path}: missing VALUE {name}")
            body = definition[1]
            rules = [
                (re.sub(r"\s+", "", codes).upper(), label.replace("''", "'"))
                for codes, label in rule.findall(body)
            ]
            if not rules or rule.sub("", body).strip():
                raise ValueError(f"{path}: unsupported VALUE {name} syntax")
            formats[name] = rules
    return formats


def missing(value):
    return pd.isna(value) or isinstance(value, str) and not value.strip()


def read_member(folder, member, columns=None):
    path = folder / (member.lower() + ".sas7bdat")
    if not path.is_file():
        path = folder / (member.upper() + ".sas7bdat")
    frame, _ = pyreadstat.read_sas7bdat(str(path), disable_datetime_conversion=True)
    frame.columns = frame.columns.str.upper()
    if columns is not None:
        frame = frame[columns]
    return frame.to_dict("records")


def by_value(value):
    return (0, "") if missing(value) else (1, value.rstrip() if isinstance(value, str) else value)


def by_key(row, columns):
    return tuple(by_value(row.get(column)) for column in columns)


def match_merge(left, right, columns, require_left=False, require_right=False):
    """SAS BY merge: advance each input once per iteration, retain its values within the group."""
    def groups(rows):
        key = lambda row: by_key(row, columns)
        return {k: list(group) for k, group in groupby(sorted(rows, key=key), key)}

    left_groups, right_groups = groups(left), groups(right)
    for key in sorted(left_groups.keys() | right_groups.keys()):
        a, b = left_groups.get(key, []), right_groups.get(key, [])
        if (require_left and not a) or (require_right and not b):
            continue
        row = {}
        for index in range(max(len(a), len(b))):
            if index < len(a):
                row.update(a[index])
            if index < len(b):
                row.update(b[index])
            yield row.copy()


def number(value, width, decimals=0, comma=False, zero=False):
    if missing(value):
        return " " * width
    rounded = Decimal(str(value)).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    spec = f",.{decimals}f" if comma else f".{decimals}f"
    result = format(rounded, spec)
    if len(result) > width:
        return "*" * width
    return result.zfill(width) if zero else result.rjust(width)


def lookup(formats, name, value):
    default = "." if missing(value) else number(value, 32).strip()
    for codes, label in formats[name]:
        if codes == "OTHER":
            default = label
            continue
        for code in codes.split(","):
            if code == ".":
                if missing(value):
                    return label
            elif not missing(value):
                low, _, high = code.partition("-")
                if int(low) <= value <= int(high or low):
                    return label
    return default


def issue_date(value):
    if missing(value):
        return None
    digits = number(value, 11, zero=True)[:8]
    try:
        return date(int(digits[4:]), int(digits[:2]), int(digits[2:4]))
    except ValueError:
        return None


def adjusted_bill_date(bill, issued):
    if issued is None:
        return None
    year = bill.year + (bill.month == 12)
    month = bill.month % 12 + 1
    limits = (31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    try:
        return date(year, month, min(issued.day, limits[month - 1]))
    except ValueError:
        return None


def select_loans(notes, dealers, caps, commissions, report_date, formats):
    notes = match_merge(dealers, notes, ["DEALERNO"], require_right=True)
    notes = match_merge(caps, notes, ["ACCTNO", "NOTENO"], require_right=True)
    eligible = (
        row for row in notes
        if str(row["REVERSED"]).rstrip() != "Y"
        and not missing(row["NOTENO"])
        and not missing(row["NTBRCH"])
        and str(row["PAIDIND"]).rstrip() != "P"
        and str(row["BORSTAT"]).rstrip() not in {"F", "R", "I", "Z"}
        and row["LOANTYPE"] in HPD_AITAB | HPD_CONVENTIONAL
    )
    key = lambda row: by_key(row, ["ACCTNO", "COMMNO"])
    unique = (next(group) for _, group in groupby(sorted(eligible, key=key), key))
    result = []
    for row in match_merge(unique, commissions, ["ACCTNO", "COMMNO"], require_left=True):
        if missing(row["BLDATE"]):
            continue
        bill = EPOCH + timedelta(days=int(row["BLDATE"]))
        total = 0 if missing(row["BILTOT"]) else row["BILTOT"]
        if not missing(row["BILPAY"]) and row["BILPAY"] > 0 and total / row["BILPAY"] <= 0.01:
            bill = adjusted_bill_date(bill, issue_date(row["ISSUEDT"]))
        days = (report_date - bill).days if bill else None
        old_days = row["OLDNOTEDAYARR"]
        if not missing(old_days) and old_days > 0 and 98000 <= row["NOTENO"] <= 98999:
            days = max(days or 0, 0) + old_days
        if days is None or not 60 <= days <= 89:
            continue
        collateral = "" if missing(row["COLLDESC"]) else row["COLLDESC"]
        branch = row["NTBRCH"]
        row.update(
            BLDATE=(bill - EPOCH).days if bill else None,
            DAYS=days, NETBAL=row["BALANCE"],
            LOANTYP="HPD AITAB" if row["LOANTYPE"] in HPD_AITAB else "HPD CONVENTIONAL",
            BRANCH=lookup(formats, "BRCHCD", branch).ljust(3) + " " + number(branch, 3, zero=True),
            MAKE=collateral[:14], MODEL=collateral[13:34],
            CUSTFISS=lookup(formats, "LNCUSTCD", row["CUSTCODE"]),
            PRIMOFHP=number(row["PRMOFFHP"], 5)[2:5],
        )
        result.append({column: row.get(column) for column in KEEP})
    return sorted(result, key=lambda row: (by_value(row["GUAREND"]), descending(row["NETBAL"])))


def descending(value):
    return (1, 0) if missing(value) else (0, -value)


def report_rows(loans, report_date, formats):
    rows = []
    totals = []
    for _, group in groupby(loans, lambda row: by_value(row["GUAREND"])):
        group = list(group)
        guarantor = group[0]["GUAREND"]
        total = None if missing(guarantor) else sum(
            row["NETBAL"] for row in group if not missing(row["NETBAL"])
        )
        if total is not None:
            totals.append(total)
        for row in group:
            issued = issue_date(row["ISSUEDT"])
            rows.append(dict(row, TOTNET=total, _FREQ_=len(group) if total is not None else None,
                             _TYPE_=1 if total is not None else None,
                             ISSDTE=issued.strftime("%d/%m/%Y") if issued else "",
                             CACNAME=lookup(formats, "CACNAME", row["NTBRCH"]),
                             REGION=lookup(formats, "REGIOFF", row["NTBRCH"])))
        if total is not None and len(group) > 1:
            rows.append(dict(GUAREND=guarantor, TOTNET=total, NETBAL=total,
                             _TYPE_=1, _FREQ_=len(group), SUBTOT="SUB-TOTAL"))
    rows.sort(key=lambda row: (descending(row["TOTNET"]), by_value(row["GUAREND"]), row.get("SUBTOT", "")))
    grand = sum(totals)
    rows.append(dict(SUBTOT="GRAND TOTAL", GRANDTOT=grand, NETBAL=grand, _TYPE_=0, _FREQ_=len(totals)))
    for row in rows:
        row["REPTDATE"] = report_date.strftime("%d/%m/%y")
    return rows


TXT_HEAD = {
    1: "A/C NO.", 19: "NOTE NO.", 29: "NAME", 65: " - ", 75: "BRANCH",
    84: "DAYS", 90: "BORSTAT", 101: "ISSUE DATE", 115: "NETPROC", 135: "NETBAL",
    155: "CAC NAME", 180: "REGION OFF", 200: "MAKE", 215: "MODEL", 255: "DEALER NO",
    265: "DEALER NAME", 305: "ORI BRANCH", 316: "CUSTFISS", 326: "CAPCLOSE", 343: "SCORE2",
}


def fixed_record(width, fields, encoding):
    record = bytearray(b" " * width)
    for column, value in fields.items():
        if missing(value) or column > width:
            continue
        offset = column - 1
        data = str(value).encode(encoding)
        if len(data) > width - offset:
            data = data[:width - offset].decode(encoding, errors="ignore").encode(encoding)
        record[offset:offset + len(data)] = data
    return bytes(record) + b"\n"


def text_fields(row):
    return {
        1: number(row.get("ACCTNO"), 12), 19: number(row.get("NOTENO"), 8),
        29: row.get("NAME"), 65: row.get("SUBTOT"), 75: row.get("BRANCH"),
        84: number(row.get("DAYS"), 4), 90: row.get("BORSTAT"), 101: row.get("ISSDTE"),
        115: number(row.get("NETPROC"), 13, 2, comma=True),
        135: number(row.get("NETBAL"), 13, 2, comma=True),
        155: row.get("CACNAME"), 180: row.get("REGION"), 200: row.get("MAKE"),
        215: row.get("MODEL"), 255: number(row.get("DEALERNO"), 8).lstrip(), 265: row.get("COMPNAME"),
        305: row.get("PRIMOFHP"), 316: row.get("CUSTFISS"),
        326: number(row.get("CAP"), 16, 2, comma=True), 343: row.get("SCORE2"),
    }


def rps_headers(branch, page, report_date):
    return [
        {1: "BRANCH    :  ", 14: branch, 44: "P U B L I C   I S L A M I C  B A N K   B E R H A D",
         122: f"PAGE NO : {page}"},
        {1: "REPORT NO :  2MTHNPL", 42: "CLOSE ATTENTION IN 2 MONTHS", 72: report_date.strftime("%d/%m/%y")},
        {}, {},
        {10: "A/C NO.", 19: "NOTE NO.", 29: "NAME", 65: "BRANCH", 74: "DAYS",
         80: "BORSTAT", 91: "ISSUE DATE", 115: "NETBAL"},
        {5: "-" * 130}, {}, {},
    ]


def write_reports(folder, loans, totals, report_date, encoding):
    with (folder / "NPLHP2M.TXT").open("wb") as stream:
        stream.write(fixed_record(350, {1: "PIBB - (CA IN 2 MONTHS) AS AT ", 38: totals[0]["REPTDATE"]}, encoding))
        stream.write(fixed_record(350, TXT_HEAD, encoding))
        for row in totals:
            stream.write(fixed_record(350, text_fields(row), encoding))
    with (folder / "NPLHP2M.RPS").open("wb") as stream:
        ordered = sorted(loans, key=lambda row: (row["BRANCH"], descending(row["NETBAL"])))
        for branch, group in groupby(ordered, lambda row: row["BRANCH"]):
            page = 1
            line = 7
            for header in rps_headers(branch, page, report_date):
                stream.write(fixed_record(138, header, encoding))
            for row in group:
                issued = issue_date(row["ISSUEDT"])
                fields = {
                    5: number(row["ACCTNO"], 12), 19: number(row["NOTENO"], 8), 29: row["NAME"],
                    65: branch, 74: number(row["DAYS"], 4), 83: row["BORSTAT"],
                    91: issued.strftime("%d/%m/%Y") if issued else "",
                    110: number(row["NETBAL"], 13, 2, comma=True),
                }
                stream.write(fixed_record(138, fields, encoding))
                line += 1
                if line > 55:
                    page += 1
                    for header in rps_headers(branch, page, report_date):
                        stream.write(fixed_record(138, header, encoding))
                    line = 7


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loan-dir", required=True, type=Path)
    parser.add_argument("--inc-dir", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--icap-dir", required=True, type=Path)
    parser.add_argument("--icap-member", help="Override the default ICAP<MMYY> member name")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--report-encoding", default="utf-8")
    args = parser.parse_args()
    formats = load_formats(args.inc_dir)
    dates = read_member(args.loan_dir, "REPTDATE", ["REPTDATE"])
    if len(dates) != 1 or missing(dates[0]["REPTDATE"]):
        raise ValueError("REPTDATE must contain one nonmissing SAS date")
    report_date = EPOCH + timedelta(days=int(dates[0]["REPTDATE"]))
    previous = report_date.replace(day=1) - timedelta(days=1)
    loans = select_loans(
        read_member(args.loan_dir, "LNNOTE"),
        read_member(args.loan_dir, "HPCOMP", ["DEALERNO", "COMPNAME"]),
        read_member(args.icap_dir, args.icap_member or f"ICAP{previous:%m%y}", ["ACCTNO", "NOTENO", "CAP"]),
        read_member(args.loan_dir, "LNCOMM", ["ACCTNO", "COMMNO", "CORGAMT"]),
        report_date,
        formats,
    )
    totals = report_rows(loans, report_date, formats)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(loans, columns=KEEP).to_parquet(args.output_dir / f"loan2m{report_date:%m}.parquet", index=False)
    pd.DataFrame(totals, columns=TOTAL_COLUMNS).to_parquet(args.output_dir / "totname.parquet", index=False)
    write_reports(args.output_dir, loans, totals, report_date, args.report_encoding)


if __name__ == "__main__":
    main()
