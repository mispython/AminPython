#!/usr/bin/env python3
"""
Python conversion of mainframe SAS job EIBMSCRA.

This job keeps SAS include files separate. Put converted include modules under
./includes, for example includes/pbmisfmt.py and includes/pbbdpfmt.py.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


DEFAULT_BASE = Path("Data_Warehouse/MIS/XMIS/input/prod")
DEFAULT_OUTPUT_DIR = DEFAULT_BASE / "output"


# SAS: %INC PGM(PBMISFMT,PBBDPFMT);
# Prefer include modules in the same folder as this job. Keep includes/ as a
# fallback for shared converted include modules.
try:
    import pbbdpfmt  # noqa: F401
    import pbmisfmt  # noqa: F401
except ImportError:
    try:
        from includes import pbbdpfmt, pbmisfmt  # noqa: F401
    except ImportError:
        pbbdpfmt = pbmisfmt = None


@dataclass(frozen=True)
class Branch:
    branch: int
    brchcd: str


@dataclass(frozen=True)
class HrBranch:
    staff: int
    branch: int
    brchcd: str


@dataclass(frozen=True)
class HrHo:
    staff: int
    hoe: str


@dataclass
class SrsRecord:
    staff: int
    product: str
    ncore: str
    branch: int = 0
    brchcd: str = ""
    hoe: str = ""
    tag: str = ""
    acctno: int | None = None
    aanum: str = ""
    c1cnt: int = 0
    c2cnt: int = 0
    c3cnt: int = 0
    c1bal: float = 0.0
    c2bal: float = 0.0
    c3bal: float = 0.0


@dataclass
class Summary:
    values: dict[str, object]
    sums: dict[str, float] = field(default_factory=lambda: defaultdict(float))


def parse_sas_number(raw: str, implied_decimals: int = 0) -> float:
    value = raw.strip()
    if not value:
        return 0.0
    if "." in value:
        return float(value)
    return int(value) / (10**implied_decimals)


def parse_int(raw: str) -> int:
    return int(parse_sas_number(raw))


def resolve_input_path(path: Path) -> Path:
    path_variants = [path]
    if path.suffix.lower() != ".txt":
        path_variants.append(path.with_name(f"{path.name}.txt"))

    if path.is_absolute():
        for variant in path_variants:
            if variant.exists():
                return variant
        return path

    candidates = [
        base / variant
        for base in (Path.cwd(), *Path.cwd().parents)
        for variant in path_variants
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    return Path.cwd() / path


def format_report_date(value: str, output_format: str = "%d/%m/%Y") -> str:
    value = value.strip()
    for fmt in ("%d/%m/%Y", "%d/%m/%y", "%Y-%m-%d", "%Y%m%d", "%d%m%Y", "%d%m%y"):
        try:
            return datetime.strptime(value, fmt).strftime(output_format)
        except ValueError:
            pass
    raise ValueError(f"Cannot parse report date: {value!r}")


def read_report_date(path: Path | None, override: str | None) -> str:
    if override:
        return format_report_date(override)
    if path is None or not path.exists():
        return date.today().strftime("%d/%m/%Y")

    text = path.read_text(encoding="utf-8").strip()
    if not text:
        return date.today().strftime("%d/%m/%Y")

    first_line = text.splitlines()[0]
    if "," in first_line:
        rows = list(csv.DictReader(text.splitlines()))
        if rows:
            raw = rows[0].get("REPTDATE") or rows[0].get("reptdate")
            if raw:
                return format_report_date(raw)

    return format_report_date(text.replace(",", " ").split()[0])


def read_branch_file(path: Path) -> tuple[dict[int, Branch], dict[str, Branch]]:
    by_branch: dict[int, Branch] = {}
    by_brchcd: dict[str, Branch] = {}

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            branch = parse_int(line[1:4])
            brchcd = line[5:8].strip()
            item = Branch(branch=branch, brchcd=brchcd)
            by_branch[branch] = item
            by_brchcd[brchcd] = item

    return by_branch, by_brchcd


def read_hr_branch(path: Path) -> dict[int, HrBranch]:
    rows: dict[int, HrBranch] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            staff = parse_int(line[4:9])
            branch = parse_int(line[68:71])
            brchcd = line[71:74].strip()
            if 2 <= branch <= 267:
                rows[staff] = HrBranch(staff=staff, branch=branch, brchcd=brchcd)
    return rows


def read_hr_ho(path: Path) -> dict[int, HrHo]:
    rows: dict[int, HrHo] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            staff = parse_int(line[4:9])
            hoe = line[71:86].strip()
            rows[staff] = HrHo(staff=staff, hoe=hoe)
    return rows


def read_card_files(paths: Iterable[Path]) -> list[SrsRecord]:
    rows: list[SrsRecord] = []

    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue

                acctno = parse_int(line[0:11])
                typec = int(str(acctno)[:5])
                if typec not in {3301, 3302, 3305, 3306, 3308, 3309, 5503, 5504}:
                    continue

                opnmm = parse_int(line[13:15])
                opnyr = parse_int(line[15:17])
                seco = line[560:572].strip()
                if not ((opnyr == 6 and opnmm > 8) or opnyr >= 7):
                    continue
                if not (1 < len(seco) < 6):
                    continue

                staff = parse_int(seco)
                if not (1 < staff < 99999):
                    continue

                if typec == 3309:
                    rows.append(
                        SrsRecord(
                            staff=staff,
                            product="CARD",
                            ncore="X",
                            acctno=acctno,
                            c1cnt=1,
                        )
                    )
                else:
                    rows.append(
                        SrsRecord(
                            staff=staff,
                            product="CARD",
                            ncore="C",
                            acctno=acctno,
                            c2cnt=1,
                        )
                    )

    return rows


def read_dep_files(paths: Iterable[Path], branch_by_number: dict[int, Branch]) -> list[SrsRecord]:
    rows: list[SrsRecord] = []

    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue

                acctno = parse_int(line[1:11])
                primoff = parse_int(line[49:54])
                secnoff = parse_int(line[55:60])
                xcore = line[60:61]
                ytdbals = parse_sas_number(line[75:89], implied_decimals=2)
                nummth = parse_int(line[89:91])
                branch_no = parse_int(line[96:99])
                branch = branch_by_number.get(branch_no)
                if branch is None:
                    continue

                product = ""
                if 1000000000 <= acctno <= 1999999999 or 7000000000 <= acctno <= 7999999999:
                    product = "FIXED DEPOSITS"
                elif 3000000000 <= acctno <= 3999999999:
                    product = "CURRENT ACCOUNT"
                elif 4000000000 <= acctno <= 4999999999 or 6000000000 <= acctno <= 6999999999:
                    product = "SAVING ACCOUNT"

                if not product or nummth == 0:
                    continue

                ytdbal = round(ytdbals / nummth)

                if primoff and xcore == " ":
                    rows.append(
                        SrsRecord(
                            staff=primoff,
                            product=product,
                            ncore="X",
                            branch=branch.branch,
                            brchcd=branch.brchcd,
                            tag="DEPO",
                            acctno=acctno,
                            c1cnt=1,
                            c1bal=ytdbal,
                        )
                    )

                staff = secnoff or primoff
                if staff and xcore in {"C", "N"}:
                    if xcore == "C":
                        rows.append(
                            SrsRecord(
                                staff=staff,
                                product=product,
                                ncore="C",
                                branch=branch.branch,
                                brchcd=branch.brchcd,
                                tag="DEPO",
                                acctno=acctno,
                                c2cnt=1,
                                c2bal=ytdbal,
                            )
                        )
                    else:
                        rows.append(
                            SrsRecord(
                                staff=staff,
                                product=product,
                                ncore="N",
                                branch=branch.branch,
                                brchcd=branch.brchcd,
                                tag="DEPO",
                                acctno=acctno,
                                c3cnt=1,
                                c3bal=ytdbal,
                            )
                        )

    return rows


def read_elds(path: Path, branch_by_code: dict[str, Branch]) -> list[SrsRecord]:
    rows: list[SrsRecord] = []
    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue

            aanum = line[0:13].strip()
            stafx1 = line[16:21].strip()
            stafx2 = line[25:30].strip()
            stafx3 = line[34:39].strip()
            product = line[50:68].strip()
            ytdbal = parse_sas_number(line[68:80])
            brchcd = aanum[:3]
            branch = branch_by_code.get(brchcd)
            if stafx1 == "*****" or branch is None:
                continue

            if "00001" <= stafx1 <= "99999":
                rows.append(
                    SrsRecord(
                        staff=parse_int(stafx1),
                        product=product,
                        ncore="X",
                        branch=branch.branch,
                        brchcd=branch.brchcd,
                        tag="ELDS",
                        aanum=aanum,
                        c1cnt=1,
                        c1bal=ytdbal,
                    )
                )

            if "00001" <= stafx2 <= "99999":
                rows.append(
                    SrsRecord(
                        staff=parse_int(stafx2),
                        product=product,
                        ncore="C",
                        branch=branch.branch,
                        brchcd=branch.brchcd,
                        tag="ELDS",
                        aanum=aanum,
                        c2cnt=1,
                        c2bal=ytdbal,
                    )
                )

            if "00001" <= stafx3 <= "99999":
                rows.append(
                    SrsRecord(
                        staff=parse_int(stafx3),
                        product=product,
                        ncore="N",
                        branch=branch.branch,
                        brchcd=branch.brchcd,
                        tag="ELDS",
                        aanum=aanum,
                        c3cnt=1,
                        c3bal=ytdbal,
                    )
                )

    return rows


def attach_card_locations(
    cards: list[SrsRecord],
    hr_branch_by_staff: dict[int, HrBranch],
    hr_ho_by_staff: dict[int, HrHo],
) -> tuple[list[SrsRecord], list[SrsRecord], list[SrsRecord]]:
    branch_rows: list[SrsRecord] = []
    ho_rows: list[SrsRecord] = []
    unmatched: list[SrsRecord] = []

    for row in cards:
        hr_branch = hr_branch_by_staff.get(row.staff)
        if hr_branch:
            row.branch = hr_branch.branch
            row.brchcd = hr_branch.brchcd
            branch_rows.append(row)
            continue

        hr_ho = hr_ho_by_staff.get(row.staff)
        if hr_ho:
            row.hoe = hr_ho.hoe
            ho_rows.append(row)
            continue

        unmatched.append(row)

    return branch_rows, ho_rows, unmatched


def split_srs_locations(
    rows: list[SrsRecord], hr_ho_by_staff: dict[int, HrHo]
) -> tuple[list[SrsRecord], list[SrsRecord], list[SrsRecord]]:
    branch_rows: list[SrsRecord] = []
    ho_rows: list[SrsRecord] = []
    unmatched: list[SrsRecord] = []

    for row in rows:
        hr_ho = hr_ho_by_staff.get(row.staff)
        if hr_ho:
            row.hoe = hr_ho.hoe
            ho_rows.append(row)
        elif row.branch > 0:
            branch_rows.append(row)
        else:
            unmatched.append(row)

    return branch_rows, ho_rows, unmatched


def summarize(rows: Iterable[SrsRecord], class_fields: tuple[str, ...]) -> list[Summary]:
    sums = ("c1cnt", "c2cnt", "c3cnt", "c1bal", "c2bal", "c3bal")
    grouped: dict[tuple[object, ...], Summary] = {}

    for row in rows:
        key = tuple(getattr(row, field_name) for field_name in class_fields)
        if key not in grouped:
            grouped[key] = Summary(values=dict(zip(class_fields, key, strict=True)))
        for name in sums:
            grouped[key].sums[name] += getattr(row, name)

    return sorted(grouped.values(), key=lambda item: tuple(item.values.values()))


def srss_product_summary(rows: Iterable[SrsRecord]) -> list[Summary]:
    by_staff_product_ncore = summarize(rows, ("staff", "product", "ncore"))
    product_rows: list[SrsRecord] = []

    for item in by_staff_product_ncore:
        ncore = str(item.values["ncore"])
        product_rows.append(
            SrsRecord(
                staff=int(item.values["staff"]),
                product=str(item.values["product"]),
                ncore=ncore,
                c1cnt=int(item.sums["c1cnt"]),
                c2cnt=int(item.sums["c2cnt"]),
                c3cnt=int(item.sums["c3cnt"]),
                c1bal=item.sums["c1bal"],
                c2bal=item.sums["c2bal"],
                c3bal=item.sums["c3bal"],
            )
        )

    grouped: dict[str, Summary] = {}
    for row in product_rows:
        if row.product not in grouped:
            grouped[row.product] = Summary(values={"product": row.product})
        item = grouped[row.product]
        item.sums["s1cnt"] += 1 if row.ncore == "X" else 0
        item.sums["s2cnt"] += 1 if row.ncore == "C" else 0
        item.sums["s3cnt"] += 1 if row.ncore == "N" else 0
        item.sums["c1cnt"] += row.c1cnt
        item.sums["c2cnt"] += row.c2cnt
        item.sums["c3cnt"] += row.c3cnt
        item.sums["c1bal"] += row.c1bal
        item.sums["c2bal"] += row.c2bal
        item.sums["c3bal"] += row.c3bal

    return sorted(grouped.values(), key=lambda item: str(item.values["product"]))


def write_summary_csv(rows: list[Summary], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].values.keys()) + sorted(rows[0].sums.keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            values = dict(row.values)
            values.update(row.sums)
            writer.writerow(values)


def write_exception_report(rows: list[SrsRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["EXCEPTION REPORT : UMMATCHED STAFF ID AGAINST HR FILE", ""]

    elds_rows = [row for row in rows if row.tag == "ELDS"]
    depo_rows = [row for row in rows if row.tag == "DEPO"]

    lines.append("ELDS")
    lines.append(f"{'AANUM':<14}{'STAFF':>8}  {'PRODUCT':<18}{'YTDBAL':>14}")
    for row in elds_rows:
        lines.append(f"{row.aanum:<14}{row.staff:>8}  {row.product:<18}{row.c1bal + row.c2bal + row.c3bal:>14,.2f}")

    lines.append("")
    lines.append("DEPO")
    lines.append(f"{'ACCTNO':<14}{'STAFF':>8}  {'PRODUCT':<18}{'YTDBAL':>14}")
    for row in depo_rows:
        lines.append(f"{row.acctno or '':<14}{row.staff:>8}  {row.product:<18}{row.c1bal + row.c2bal + row.c3bal:>14,.2f}")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_print_report(rows: list[Summary], report_date: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "SUMMARY REPORT ON STAFF PARTICIPATION UNDER SCR BY PRODUCT",
        f"REPORT DATE: {report_date}",
        "",
        (
            f"{'PRODUCT':<20}{'CAT.1 #STAFF':>14}{'CAT.1 #ACCTS':>14}{'CAT.1 YTD BALANCE':>22}"
            f"{'CAT.2 #STAFF CORE':>20}{'CAT.2 #ACCTS CORE':>20}{'CAT.2 YTDBAL CORE':>22}"
            f"{'CAT.2 #STAFF NON-CORE':>24}{'CAT.2 #ACCTS NON-CORE':>24}{'CAT.2 YTDBAL NON-CORE':>26}"
        ),
    ]

    totals = defaultdict(float)
    for row in rows:
        sums = row.sums
        for key, value in sums.items():
            totals[key] += value
        lines.append(
            f"{str(row.values['product']):<20}"
            f"{sums['s1cnt']:>14.0f}{sums['c1cnt']:>14.0f}{sums['c1bal']:>22,.2f}"
            f"{sums['s2cnt']:>20.0f}{sums['c2cnt']:>20.0f}{sums['c2bal']:>22,.2f}"
            f"{sums['s3cnt']:>24.0f}{sums['c3cnt']:>24.0f}{sums['c3bal']:>26,.2f}"
        )

    lines.append(
        f"{'TOTAL':<20}"
        f"{totals['s1cnt']:>14.0f}{totals['c1cnt']:>14.0f}{totals['c1bal']:>22,.2f}"
        f"{totals['s2cnt']:>20.0f}{totals['c2cnt']:>20.0f}{totals['c2bal']:>22,.2f}"
        f"{totals['s3cnt']:>24.0f}{totals['c3cnt']:>24.0f}{totals['c3bal']:>26,.2f}"
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def existing_paths(paths: list[Path]) -> list[Path]:
    resolved_paths = []
    for path in paths:
        resolved = resolve_input_path(path)
        if resolved.exists():
            resolved_paths.append(resolved)
    return resolved_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert SAS EIBMSCRA SCR summary job to Python.")
    parser.add_argument("--mnitb-reptdate", type=Path, help="Optional report-date text/CSV file.")
    parser.add_argument("--brhfi", type=Path, default=DEFAULT_BASE / "BRANCH.txt")
    parser.add_argument("--elds", type=Path, default=DEFAULT_BASE / "ELDS.txt")
    parser.add_argument("--dep", action="append", type=Path, default=None, help="DEP fixed-width file. Repeatable.")
    parser.add_argument("--cardfile", action="append", type=Path, default=None, help="Card fixed-width file. Repeatable.")
    parser.add_argument("--hrbr", type=Path, default=DEFAULT_BASE / "BRSTAF.TXT")
    parser.add_argument("--hrho", type=Path, default=DEFAULT_BASE / "HOSTAF.TXT")
    parser.add_argument("--hrrg", type=Path, default=DEFAULT_BASE / "RGSTAF.TXT", help="Regional staff file; kept for DD mapping, not used by this SAS flow.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-date", help="Optional report date override, e.g. 31/12/2025 or 2025-12-31.")
    args = parser.parse_args()

    dep_paths = args.dep or [DEFAULT_BASE / "DP_SRR.txt", DEFAULT_BASE / "DP_SCRFFD.txt"]
    card_paths = args.cardfile or [DEFAULT_BASE / "ACCT33.txt", DEFAULT_BASE / "ACCT55.txt"]

    report_date_path = resolve_input_path(args.mnitb_reptdate) if args.mnitb_reptdate else None
    report_date = read_report_date(report_date_path, args.report_date)
    branch_by_number, branch_by_code = read_branch_file(resolve_input_path(args.brhfi))
    hr_branch_by_staff = read_hr_branch(resolve_input_path(args.hrbr))
    hr_ho_by_staff = read_hr_ho(resolve_input_path(args.hrho))

    cards = read_card_files(existing_paths(card_paths))
    card_branch_rows, card_ho_rows, card_unmatched = attach_card_locations(
        cards, hr_branch_by_staff, hr_ho_by_staff
    )

    dep_rows = read_dep_files(existing_paths(dep_paths), branch_by_number)
    elds_rows = read_elds(resolve_input_path(args.elds), branch_by_code)
    srs_rows = elds_rows + dep_rows

    srs_branch_rows, srs_ho_rows, srs_unmatched = split_srs_locations(srs_rows, hr_ho_by_staff)
    final_branch_rows = srs_branch_rows + card_branch_rows
    final_ho_rows = srs_ho_rows + card_ho_rows
    all_rows = final_ho_rows + final_branch_rows

    output_dir = args.output_dir
    write_exception_report(srs_unmatched + card_unmatched, output_dir / "exception_report.txt")
    write_summary_csv(summarize(final_branch_rows, ("brchcd", "staff", "product", "ncore")), output_dir / "SRSBR.csv")
    write_summary_csv(summarize(final_ho_rows, ("hoe", "staff", "product", "ncore")), output_dir / "SRSHO.csv")

    product_summary = srss_product_summary(all_rows)
    write_summary_csv(product_summary, output_dir / "SRSP.csv")
    write_print_report(product_summary, report_date, output_dir / "SASLIST.txt")


if __name__ == "__main__":
    main()


















==========================================================================





source /sas/python/virt_edw/bin/activate
[sas_edw_dev@svdwh004 virt_edw]$ source /sas/python/virt_edw/bin/activate
(virt_edw) [sas_edw_dev@svdwh004 virt_edw]$ /sas/python/virt_edw/bin/python /sas/python/virt_edw/Data_Warehouse/MIS/XMIS/EIBMSCRA.py
**********************************************************
* Job:      EIBMSCRA                                     *
* Location: /sas/python/virt_edw/Data_Warehouse/MIS/XMIS *
*                                                        *
* Modified: Monday, May 18, 2026, 03:35:48 PM            *
**********************************************************
Program start : 2026/05/18 15:42:02

1       """
2       from __future__ import annotations
3       import argparse
4       import csv
5       from collections import defaultdict
6       from dataclasses import dataclass, field
7       from datetime import date, datetime
8       from pathlib import Path
9       from typing import Iterable
10      DEFAULT_BASE = Path("Data_Warehouse/MIS/XMIS/input/prod")
11      DEFAULT_OUTPUT_DIR = DEFAULT_BASE / "output"
12      try:
13          import pbbdpfmt  # noqa: F401
14      except ImportError:
15          try:
16              from includes import pbbdpfmt, pbmisfmt  # noqa: F401
17          except ImportError:
18              pbbdpfmt = pbmisfmt = None
19      @dataclass(frozen=True)
20      class Branch:
21          branch: int
22          brchcd: str
23      @dataclass(frozen=True)
24      class HrBranch:
25          staff: int
26          branch: int
27          brchcd: str
28      @dataclass(frozen=True)
29      class HrHo:
30          staff: int
31          hoe: str
32      @dataclass
33      class SrsRecord:
34          staff: int
35          product: str
36          ncore: str
37          branch: int = 0
38          brchcd: str = ""
39          hoe: str = ""
40          tag: str = ""
41          acctno: int | None = None
42          aanum: str = ""
43          c1cnt: int = 0
44          c2cnt: int = 0
45          c3cnt: int = 0
46          c1bal: float = 0.0
47          c2bal: float = 0.0
48          c3bal: float = 0.0
49      @dataclass
50      class Summary:
51          values: dict[str, object]
52          sums: dict[str, float] = field(default_factory=lambda: defaultdict(float))
53      def parse_sas_number(raw: str, implied_decimals: int = 0) -> float:
54      def parse_int(raw: str) -> int:
55      def resolve_input_path(path: Path) -> Path:
56      def format_report_date(value: str, output_format: str = "%d/%m/%Y") -> str:
57      def read_report_date(path: Path | None, override: str | None) -> str:
58      def read_branch_file(path: Path) -> tuple[dict[int, Branch], dict[str, Branch]]:
59      def read_hr_branch(path: Path) -> dict[int, HrBranch]:
60      def read_hr_ho(path: Path) -> dict[int, HrHo]:
61      def read_card_files(paths: Iterable[Path]) -> list[SrsRecord]:
62      def read_dep_files(paths: Iterable[Path], branch_by_number: dict[int, Branch]) -> list[SrsRecord]:
63      def read_elds(path: Path, branch_by_code: dict[str, Branch]) -> list[SrsRecord]:
64      def attach_card_locations(
65      def split_srs_locations(
66      def summarize(rows: Iterable[SrsRecord], class_fields: tuple[str, ...]) -> list[Summary]:
67      def srss_product_summary(rows: Iterable[SrsRecord]) -> list[Summary]:
68      def write_summary_csv(rows: list[Summary], path: Path) -> None:
69      def write_exception_report(rows: list[SrsRecord], path: Path) -> None:
70      def write_print_report(rows: list[Summary], report_date: str, path: Path) -> None:
71      def existing_paths(paths: list[Path]) -> list[Path]:
72      def main() -> None:
73      if __name__ == "__main__":
74          main()
75          parser = argparse.ArgumentParser(description="Convert SAS EIBMSCRA SCR summary job to Python.")
76          parser.add_argument("--mnitb-reptdate", type=Path, help="Optional report-date text/CSV file.")
77          parser.add_argument("--brhfi", type=Path, default=DEFAULT_BASE / "BRANCH.txt")
78          parser.add_argument("--elds", type=Path, default=DEFAULT_BASE / "ELDS.txt")
79          parser.add_argument("--dep", action="append", type=Path, default=None, help="DEP fixed-width file. Repeatable.")
80          parser.add_argument("--cardfile", action="append", type=Path, default=None, help="Card fixed-width file. Repeatable.")
81          parser.add_argument("--hrbr", type=Path, default=DEFAULT_BASE / "BRSTAF.TXT")
82          parser.add_argument("--hrho", type=Path, default=DEFAULT_BASE / "HOSTAF.TXT")
83          parser.add_argument("--hrrg", type=Path, default=DEFAULT_BASE / "RGSTAF.TXT", help="Regional staff file; kept for DD mapping, not used by this SAS flow.")
84          parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
85          parser.add_argument("--report-date", help="Optional report date override, e.g. 31/12/2025 or 2025-12-31.")
86          args = parser.parse_args()
87          dep_paths = args.dep or [DEFAULT_BASE / "DP_SRR.txt", DEFAULT_BASE / "DP_SCRFFD.txt"]
88          card_paths = args.cardfile or [DEFAULT_BASE / "ACCT33.txt", DEFAULT_BASE / "ACCT55.txt"]
89          report_date_path = resolve_input_path(args.mnitb_reptdate) if args.mnitb_reptdate else None
90          report_date = read_report_date(report_date_path, args.report_date)
91          if override:
92          if path is None or not path.exists():
93              return date.today().strftime("%d/%m/%Y")
94          branch_by_number, branch_by_code = read_branch_file(resolve_input_path(args.brhfi))
95          path_variants = [path]
96          if path.suffix.lower() != ".txt":
97          if path.is_absolute():
98          candidates = [
99              for base in (Path.cwd(), *Path.cwd().parents)
100             for variant in path_variants
101             base / variant
102         for candidate in candidates:
103             if candidate.exists():
104                 return candidate
105         by_branch: dict[int, Branch] = {}
106         by_brchcd: dict[str, Branch] = {}
107         with path.open("r", encoding="utf-8") as handle:
108             for line in handle:
109                 if not line.strip():
110                 branch = parse_int(line[1:4])
111         return int(parse_sas_number(raw))
112         value = raw.strip()
113         if not value:
114         if "." in value:
115         return int(value) / (10**implied_decimals)
116                 brchcd = line[5:8].strip()
117                 item = Branch(branch=branch, brchcd=brchcd)
118                 by_branch[branch] = item
119                 by_brchcd[brchcd] = item
120         return by_branch, by_brchcd
121         hr_branch_by_staff = read_hr_branch(resolve_input_path(args.hrbr))
122         rows: dict[int, HrBranch] = {}
123         with path.open("r", encoding="utf-8") as handle:
124             for line in handle:
125                 if not line.strip():
126                 staff = parse_int(line[4:9])
127                 branch = parse_int(line[68:71])
128                 brchcd = line[71:74].strip()
129                 if 2 <= branch <= 267:
130                     rows[staff] = HrBranch(staff=staff, branch=branch, brchcd=brchcd)
131         return rows
132         hr_ho_by_staff = read_hr_ho(resolve_input_path(args.hrho))
133         rows: dict[int, HrHo] = {}
134         with path.open("r", encoding="utf-8") as handle:
135             for line in handle:
136                 if not line.strip():
137                 staff = parse_int(line[4:9])
138                 hoe = line[71:86].strip()
139                 rows[staff] = HrHo(staff=staff, hoe=hoe)
140         return rows
141         cards = read_card_files(existing_paths(card_paths))
142         resolved_paths = []
143         for path in paths:
144             resolved = resolve_input_path(path)
145             if resolved.exists():
146                 resolved_paths.append(resolved)
147         return resolved_paths
148         rows: list[SrsRecord] = []
149         for path in paths:
150             with path.open("r", encoding="utf-8") as handle:
151                 for line in handle:
152                     if not line.strip():
153                     acctno = parse_int(line[0:11])
154                     typec = int(str(acctno)[:5])
155                     if typec not in {3301, 3302, 3305, 3306, 3308, 3309, 5503, 5504}:
156                         continue
157         return rows
158         card_branch_rows, card_ho_rows, card_unmatched = attach_card_locations(
159             cards, hr_branch_by_staff, hr_ho_by_staff
160         branch_rows: list[SrsRecord] = []
161         ho_rows: list[SrsRecord] = []
162         unmatched: list[SrsRecord] = []
163         for row in cards:
164         return branch_rows, ho_rows, unmatched
165         dep_rows = read_dep_files(existing_paths(dep_paths), branch_by_number)
166         rows: list[SrsRecord] = []
167         for path in paths:
168             with path.open("r", encoding="utf-8") as handle:
169                 for line in handle:
170                     if not line.strip():
171                     acctno = parse_int(line[1:11])
172                     primoff = parse_int(line[49:54])
173                     secnoff = parse_int(line[55:60])
174                     xcore = line[60:61]
175                     ytdbals = parse_sas_number(line[75:89], implied_decimals=2)
176             return float(value)
177                     nummth = parse_int(line[89:91])
178                     branch_no = parse_int(line[96:99])
179                     branch = branch_by_number.get(branch_no)
180                     if branch is None:
181                     product = ""
182                     if 1000000000 <= acctno <= 1999999999 or 7000000000 <= acctno <= 7999999999:
183                     elif 3000000000 <= acctno <= 3999999999:
184                         product = "CURRENT ACCOUNT"
185                     if not product or nummth == 0:
186                         continue
187                     elif 4000000000 <= acctno <= 4999999999 or 6000000000 <= acctno <= 6999999999:
188                         product = "SAVING ACCOUNT"
189                             rows.append(
Traceback (most recent call last):
  File "/sas/python/virt_edw/Data_Warehouse/MIS/XMIS/EIBMSCRA.py", line 621, in <module>
    main()
  File "/sas/python/virt_edw/Data_Warehouse/MIS/XMIS/EIBMSCRA.py", line 601, in main
    dep_rows = read_dep_files(existing_paths(dep_paths), branch_by_number)
  File "/sas/python/virt_edw/Data_Warehouse/MIS/XMIS/EIBMSCRA.py", line 255, in read_dep_files
    nummth = parse_int(line[89:91])
  File "/sas/python/virt_edw/Data_Warehouse/MIS/XMIS/EIBMSCRA.py", line 91, in parse_int
    return int(parse_sas_number(raw))
  File "/sas/python/virt_edw/Data_Warehouse/MIS/XMIS/EIBMSCRA.py", line 86, in parse_sas_number
    return float(value)
ValueError: could not convert string to float: '.'

Total time elapsed : 00:21:02
Memory used: 7.39 MB
Program end : 2026/05/18 16:03:04
(virt_edw) [sas_edw_dev@svdwh004 virt_edw]$ 
