#!/usr/bin/env python
"""Python replacement for the EIIMPORT JCL/SAS job.

All inputs are SAS7BDAT files.  By default REPTDATE is yesterday, relative to
the machine running this program.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd


SA_PRODUCTS = {204, 207, 214, 215}
CA_CONCEPTS = {
    "WADIAH": {60, 61, 62, 63, 64, 66, 67, 93, 96, 97, 160, 161, 162, 163, 164, 165, 182},
    "BAI BITHAMAN AJIL": {32, 70, 73, 94, 95, 166, 183, 184, 185, 187, 188},
    "MURABAHAH": {169},
    "BAI AL INAH": {33, 71, 167, 168},
    "QARD": {440, 441, 442, 443, 444},
    "MUSYARAKAH": {186},
}
# This is the source SAS input filter. Products 187 and 188 are deliberately
# absent because they were absent from that filter, despite appearing above.
CA_PRODUCTS = {
    32, 33, 60, 61, 62, 63, 64, 66, 67, 70, 71, 73, 93, 94, 95, 96, 97,
    160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 182, 183, 184, 185,
    186, 440, 441, 442, 443, 444,
}
MGIA_CONCEPTS = {"MUDARABAH": {302, 396}, "ISTISMAR": {315, 394}}
EQT_CONCEPTS = {
    "BCS": "ISTISMAR",
    "BCI": "MUDARABAH",
    "BCT": "COMMODITY MURABAHAH TAWARRUQ",
    "BCW": "WADIAH",
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the Islamic portfolio exposure report.")
    parser.add_argument("--input-dir", type=Path, required=True, help="Root containing the SAS7BDAT inputs.")
    parser.add_argument("--output", type=Path, default=Path("PORTF.txt"), help="Output text file.")
    parser.add_argument(
        "--report-date",
        type=lambda value: datetime.strptime(value, "%Y-%m-%d").date(),
        default=date.today() - timedelta(days=1),
        help="Override REPTDATE (YYYY-MM-DD); default: yesterday.",
    )
    parser.add_argument("--saving", type=Path, help="Override SAVING.sas7bdat.")
    parser.add_argument("--current", type=Path, help="Override CURRENT.sas7bdat.")
    parser.add_argument("--fd", type=Path, help="Override FD.sas7bdat.")
    parser.add_argument("--equt", type=Path, help="Override IUTFXyymmdd.sas7bdat.")
    parser.add_argument("--ini", type=Path, help="Override W1ALmmw.sas7bdat.")
    return parser.parse_args()


def locate(root: Path, filename: str, override: Path | None) -> Path:
    if override:
        path = override
    else:
        matches = [p for p in root.rglob("*") if p.is_file() and p.name.casefold() == filename.casefold()]
        if not matches:
            raise FileNotFoundError(f"Could not find {filename!r} below {root}")
        if len(matches) > 1:
            raise RuntimeError(f"Multiple files named {filename!r}; pass an explicit override: {matches}")
        path = matches[0]
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def load(path: Path, required: Iterable[str]) -> pd.DataFrame:
    frame = pd.read_sas(path, format="sas7bdat", encoding="utf-8")
    frame.columns = [str(column).upper() for column in frame.columns]
    missing = set(required) - set(frame.columns)
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")
    return frame


def clean_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def eligible_deposits(frame: pd.DataFrame, products: set[int]) -> pd.DataFrame:
    product = pd.to_numeric(frame["PRODUCT"], errors="coerce")
    balance = pd.to_numeric(frame["CURBAL"], errors="coerce")
    open_indicator = clean_text(frame["OPENIND"]).str.upper()
    return frame.loc[product.isin(products) & ~open_indicator.isin({"B", "C", "P"}) & balance.ge(0)].copy()


def concept_amounts(
    frame: pd.DataFrame,
    mapping: dict[str, set[int]],
    amount_column: str,
    defaults: Iterable[str],
) -> dict[str, float]:
    result = {concept: 0.0 for concept in defaults}
    products = pd.to_numeric(frame["PRODUCT"], errors="coerce")
    amounts = pd.to_numeric(frame[amount_column], errors="coerce").fillna(0)
    for concept, product_codes in mapping.items():
        result[concept] = float(amounts.loc[products.isin(product_codes)].sum())
    return result


def week_number(report_date: date) -> int:
    if report_date.day <= 8:
        return 1
    if report_date.day <= 15:
        return 2
    if report_date.day <= 22:
        return 3
    return 4


def report_rows(args: argparse.Namespace) -> list[tuple[float, str, float]]:
    root = args.input_dir.resolve()
    stamp = args.report_date.strftime("%y%m%d")
    ini_name = f"W1AL{args.report_date:%m}{week_number(args.report_date)}.sas7bdat"

    saving = load(locate(root, "SAVING.sas7bdat", args.saving), {"PRODUCT", "OPENIND", "CURBAL"})
    current = load(locate(root, "CURRENT.sas7bdat", args.current), {"PRODUCT", "OPENIND", "CURBAL"})
    fd = load(locate(root, "FD.sas7bdat", args.fd), {"PRODUCT", "OPENIND", "CURBAL"})
    equt = load(locate(root, f"IUTFX{stamp}.sas7bdat", args.equt), {"DEALTYPE", "AMTPAY"})
    ini = load(locate(root, ini_name, args.ini), {"SET_ID", "AMOUNT"})

    sa = eligible_deposits(saving, SA_PRODUCTS)
    sa_amounts = {"WADIAH": float(pd.to_numeric(sa["CURBAL"], errors="coerce").fillna(0).sum())}

    ca = eligible_deposits(current, CA_PRODUCTS)
    ca_amounts = concept_amounts(ca, CA_CONCEPTS, "CURBAL", CA_CONCEPTS)

    mgia = eligible_deposits(fd, set().union(*MGIA_CONCEPTS.values()))
    mgia_amounts = concept_amounts(mgia, MGIA_CONCEPTS, "CURBAL", MGIA_CONCEPTS)

    comm = eligible_deposits(fd, {316, 393})
    comm_amounts = {
        "COMMODITY MURABAHAH TAWARRUQ":
            float(pd.to_numeric(comm["CURBAL"], errors="coerce").fillna(0).sum())
    }

    deal_types = clean_text(equt["DEALTYPE"]).str.upper()
    pay = pd.to_numeric(equt["AMTPAY"], errors="coerce").fillna(0)
    equt_amounts = {
        concept: float(pay.loc[deal_types.eq(code)].sum())
        for code, concept in EQT_CONCEPTS.items()
    }

    set_ids = clean_text(ini["SET_ID"]).str.upper()
    ini_amounts = {
        "BAI AL INAH":
            float(pd.to_numeric(ini.loc[set_ids.eq("F142150NIDI"), "AMOUNT"], errors="coerce").fillna(0).sum())
    }

    sections = [
        (1.0, "1.SAVINGS", 1.1, sa_amounts),
        (2.0, "2.CURRENT", 2.1, ca_amounts),
    ]
    term_parts = [
        (3.1, "A.MGIA", 3.11, mgia_amounts),
        (3.2, "B.COMMODITY MURABAHAH", 3.21, comm_amounts),
        (3.3, "C.SHORT TERM DEPOSIT", 3.31, equt_amounts),
        (3.4, "D.INI", 3.41, ini_amounts),
    ]

    rows: list[tuple[float, str, float]] = []
    for total_id, title, detail_id, amounts in sections:
        rows.append((total_id, title, sum(amounts.values())))
        rows.extend((detail_id, concept, amount) for concept, amount in amounts.items())
    rows.append((3.0, "3.TERM", sum(sum(values.values()) for _, _, _, values in term_parts)))
    for total_id, title, detail_id, amounts in term_parts:
        rows.append((total_id, title, sum(amounts.values())))
        rows.extend((detail_id, concept, amount) for concept, amount in amounts.items())
    return sorted(rows, key=lambda row: row[0])


def write_report(path: Path, report_date: date, rows: list[tuple[float, str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        " ",
        "TITLE: REPORTING REQUIREMENTS FOR ISLAMIC BANKING PORTFOLIO EXPOSURE ",
        "       (INVESTMENT,DEPOSIT,DERIVATIVES AND SUKUK HOLDING) ACCORDING TO PRODUCT AND SHARIAH APPROVED",
        f"       AS AT :{report_date:%d/%m/%Y}",
        "ITEM/CONCEPT",
        "DEPOSIT/INVESTMENT;RM(AMOUNT);",
    ]
    lines.extend(f"{concept};{amount:.2f};" for _, concept, amount in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = arguments()
    rows = report_rows(args)
    write_report(args.output, args.report_date, rows)
    print(f"Created {args.output.resolve()} for REPTDATE {args.report_date:%Y-%m-%d}")


if __name__ == "__main__":
    main()
