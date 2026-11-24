"""Python subprograms called by the CCD job, matching the SAS member names."""

import re
import pickle
import sqlite3
from collections import defaultdict
from contextlib import ExitStack, closing
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from itertools import chain, groupby, islice
from pathlib import Path
from tempfile import TemporaryDirectory, TemporaryFile

from bisect import bisect_right

from ccd_formats import ARRCLASS, CACBRCH, HPD, LAYOUTS


SAS_EPOCH = date(1960, 1, 1)
HP_CONVENTIONAL = {380, 381, 700, 705, 720, 725}
HP_AITAB = {128, 130, 131, 132}
HP_DIRECT = HPD
ARREARS_BOUNDS = (31, 60, 90, 122, 152, 183, 214, 244, 274, 304, 334, 365, 548, 730, 1095)
SHORT_BOUNDS = ARREARS_BOUNDS[:9] + ARREARS_BOUNDS[11:]
PUT_TOKENS = re.compile(r"""'[^']*'|"[^"]*"|@\d+|[^\s]+""")
SAS_FORMAT = re.compile(r"(COMMA|DDMMYY|Z|\$)?(\d+)\.(\d*)")


def text(value):
    return "" if value is None else str(value).rstrip()



def number(row, field):
    value = row.get(field)
    return Decimal(str(value)) if value not in (None, "", ".") else Decimal(0)



def sas_date(value):
    if value in (None, "", "."):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and "-" in value[1:]:
        return date.fromisoformat(value[:10])
    return SAS_EPOCH + timedelta(days=int(Decimal(str(value))))



def encoded_date(value):
    if value in (None, "", ".", 0, "0"):
        return None
    if isinstance(value, date) or "-" in str(value)[1:]:
        return sas_date(value)
    digits = f"{int(Decimal(str(value))):011d}"
    return datetime.strptime(digits[:8], "%m%d%Y").date()



def key_value(value):
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return format(Decimal(str(value)).normalize(), "f")
    return text(value)



def group_rows(rows, fields):
    groups = defaultdict(list)
    for row in rows:
        groups[tuple(key_value(row.get(field)) for field in fields)].append(row)
    return groups




def categorise(loans, entity, mode, report_date, branches):
    previous_month = (report_date.replace(day=1) - timedelta(days=1)).replace(day=1)
    for row in loans:
        status = text(row.get("BORSTAT"))
        if number(row, "BALANCE") <= 0 or status == "Z":
            continue
        product = int(number(row, "PRODUCT"))
        branch = int(number(row, "BRANCH")) if row.get("BRANCH") not in (None, "", ".") else None
        extras = {15, 20} if entity == "pbb" and mode == "npl" else set()
        categories = (
            ("A", HP_CONVENTIONAL | extras, "(HPD-C)", "HP DIRECT(CONV)"),
            ("B", {380, 381}, "(HP 380/381)", "HP (380,381)"),
            ("C", HP_AITAB, "(AITAB)", "AITAB"),
            ("D", HP_DIRECT | extras, "(-HPD-)", ""),
        )
        copies = 1
        if mode == "npl" and not (
            row["ARREAR"] > 3 or status in {"R", "I", "F"} or text(row.get("USER5")) == "N"
        ):
            continue
        if mode == "rps":
            if product not in HP_DIRECT:
                continue
            issue_date = sas_date(row.get("ISSDTE"))
            copies = int(row["ARREAR2"] >= 3 or status in {"R", "I", "T", "F", "Y"})
            copies += int(bool(issue_date and issue_date >= previous_month and row["DAYDIFF"] >= 8))
        for cat, products, summary_type, detail_type in categories:
            if product not in products or (mode == "rps" and not detail_type):
                continue
            arrear2 = 15 if mode == "rps" and status == "F" else row["ARREAR2"]
            item = {
                **row, "CAT": cat, "BRANCH": branch, "BRHCODE": branches.get(branch, ""),
                "TYPE": detail_type if mode == "rps" else summary_type,
                "ARREAR2": arrear2, "ARREARS": ARRCLASS[str(arrear2)],
            }
            for _ in range(copies):
                yield item



def formatted(value, spec):
    if spec is None:
        return text(value)
    kind, width, precision = SAS_FORMAT.fullmatch(spec).groups()
    width = int(width)
    if kind == "$":
        return text(value)[:width].ljust(width)
    if kind == "DDMMYY":
        value = sas_date(value)
        return value.strftime("%d/%m/%y") if value else ".".rjust(width)
    if value in (None, "", "."):
        return ".".rjust(width)
    value = Decimal(str(value))
    precision = int(precision or 0)
    value = value.quantize(Decimal(1).scaleb(-precision), rounding=ROUND_HALF_UP)
    if kind == "Z":
        result = f"{int(value):0{width}d}"
    elif kind == "COMMA":
        result = f"{value:,.{precision}f}"
        if len(result) > width:
            result = result.replace(",", "")
    else:
        result = f"{value:.{precision}f}"
    return result.rjust(width) if len(result) <= width else "*" * width



def put(statement, values, width, encoding):
    tokens = PUT_TOKENS.findall(statement)
    record = bytearray(b" " * width)
    offset = 0
    index = 0
    while index < len(tokens):
        token = tokens[index]
        index += 1
        if token.startswith("@"):
            offset = int(token[1:]) - 1
            continue
        if token.startswith(("'", '"')):
            value = token[1:-1].replace("&RDATE", values["RDATE"]) if token[0] == '"' else token[1:-1]
        else:
            spec = tokens[index] if index < len(tokens) and SAS_FORMAT.fullmatch(tokens[index]) else None
            if spec:
                index += 1
            value = formatted(values[token], spec)
            if not spec:
                value += " "
        encoded = value.encode(encoding, errors="replace")[:max(0, width - offset)]
        record[offset:offset + len(encoded)] = encoded
        offset += len(encoded)
    return bytes(record)



def totals(counts, amounts, total):
    prefixes = ("TOTACC", "TOTAMT") if total else ("NOACC", "BRHAMT")
    fields = {
        f"{prefix}{index}": value
        for prefix, array in zip(prefixes, (counts, amounts))
        for index, value in enumerate(array, 1)
    }
    keys = ("SGTOTACC", "SGTOTBRH", "SGTOTAC2", "SGTOTBR2", "GTOTACC", "GTOTBRH") if total else (
        "SUBACC", "SUBBRH", "SUBAC2", "SUBBR2", "SOTACC", "TOTBRH"
    )
    fields.update(zip(keys, (sum(counts[3:]), sum(amounts[3:]), sum(counts[6:]), sum(amounts[6:]),
                             sum(counts), sum(amounts))))
    return fields



def sort_branch(row):
    return -1 if row["BRANCH"] is None else row["BRANCH"]



def disk_sort(rows, key, key_count, scratch, batch_size):
    """Stable external sort with an on-disk index and bounded insert batches."""
    columns = ", ".join(f"k{index}" for index in range(key_count))
    placeholders = ", ".join("?" for _ in range(key_count + 1))
    with TemporaryDirectory(dir=scratch) as directory:
        with closing(sqlite3.connect(Path(directory) / "sort.sqlite")) as db:
            db.execute("PRAGMA journal_mode=OFF")
            db.execute("PRAGMA synchronous=OFF")
            db.execute("PRAGMA cache_size=-8192")
            db.execute(f"CREATE TABLE rows (seq INTEGER PRIMARY KEY, {columns}, payload BLOB)")
            db.execute(f"CREATE INDEX sort_order ON rows ({columns}, seq)")
            records = iter(rows)
            with db:
                while True:
                    batch = islice(records, batch_size)
                    first = next(batch, None)
                    if first is None:
                        break
                    db.executemany(
                        f"INSERT INTO rows ({columns}, payload) VALUES ({placeholders})",
                        ((*key(row), pickle.dumps(row, protocol=pickle.HIGHEST_PROTOCOL))
                         for row in chain((first,), batch)),
                    )
            for (payload,) in db.execute(f"SELECT payload FROM rows ORDER BY {columns}, seq"):
                yield pickle.loads(payload)


def summary_report(loans, rows, layout, report_date, short, encoding):
    bins = 15 if short else 17
    field = "ARREAR2" if short else "ARREAR"
    ordered = loans.sort(rows, lambda row: (row["CAT"], sort_branch(row), row[field]), 3)
    for _, category in groupby(ordered, key=lambda row: row["CAT"]):
        first = next(category)
        context = {**first, "RDATE": report_date.strftime("%d/%m/%y"), "PAGECNT": 1}
        for index, line in enumerate(layout["header"]):
            yield (b"1" if index == 0 else b" ") + put(line, context, 132, encoding)
        all_counts, all_amounts = [0] * bins, [Decimal(0)] * bins
        for _, group in groupby(chain((first,), category), key=lambda row: row["BRANCH"]):
            counts, amounts = [0] * bins, [Decimal(0)] * bins
            for row in group:
                index = row[field] - 1
                counts[index] += 1
                amounts[index] += number(row, "BALANCE")
            all_counts = [left + right for left, right in zip(all_counts, counts)]
            all_amounts = [left + right for left, right in zip(all_amounts, amounts)]
            context.update(row)
            context.update(totals(counts, amounts, False))
            yield from (b" " + put(line, context, 132, encoding) for line in layout["branch"])
        context.update(totals(all_counts, all_amounts, True))
        yield from (b" " + put(line, context, 132, encoding) for line in layout["total"])



def detail_report(loans, rows, layout, report_date, encoding):
    ordered = loans.sort(
        rows, lambda row: (row["CAT"], sort_branch(row), row["ARREAR2"], float(row["DAYDIFF"])), 4
    )
    body = layout["body"]
    total_cap = Decimal(0)
    for _, category in groupby(ordered, key=lambda row: row["CAT"]):
        total_balance = Decimal(0)
        for _, branch in groupby(category, key=lambda row: row["BRANCH"]):
            page, line_count = 0, 6
            branch_balance = branch_cap = Decimal(0)
            for _, band in groupby(branch, key=lambda row: row["ARREAR2"]):
                band_balance = band_cap = Decimal(0)
                for row in band:
                    context = defaultdict(str, row, RDATE=report_date.strftime("%d/%m/%y"))
                    if page == 0:
                        page, line_count = 1, 6
                        context["PAGECNT"] = page
                        yield from (put(line, context, 134, encoding) for line in layout["header"][1:])
                    yield from (put(line, context, 134, encoding) for line in body[:4])
                    line_count += 4
                    balance, cap = number(row, "BALANCE"), number(row, "CAP")
                    band_balance += balance
                    branch_balance += balance
                    total_balance += balance
                    band_cap += cap
                    branch_cap += cap
                    total_cap += cap
                    if line_count > 56:
                        page, line_count = page + 1, 6
                        context["PAGECNT"] = page
                        yield from (put(line, context, 134, encoding) for line in layout["header"][1:])
                context.update(BRHARR=band_balance, BRHCAP=band_cap)
                yield from (put(line, context, 134, encoding) for line in body[4:8])
                line_count += 4
                if line_count > 56:
                    page, line_count = page + 1, 6
                    context["PAGECNT"] = page
                    yield from (put(line, context, 134, encoding) for line in layout["header"][1:])
            context.update(BRHAMT=branch_balance, BRHCAPB=branch_cap)
            yield from (put(line, context, 134, encoding) for line in body[8:12])
        context.update(TOTAL=total_balance, TOTALCAP=total_cap)
        yield from (put(line, context, 134, encoding) for line in body[12:16])




def write_records(path, records):
    with path.open("wb") as handle:
        for record in records:
            handle.write(record + b"\n")


def arrears_report(loans, entity, report_date, branches, encoding):
    layout = LAYOUTS[entity]["summary"]
    rows = categorise(loans, entity, "arrears", report_date, branches)
    yield from summary_report(loans, rows, layout[0], report_date, False, encoding)
    if report_date.day == 15:
        rows = categorise(loans, entity, "arrears", report_date, branches)
        yield from summary_report(loans, rows, layout[1], report_date, True, encoding)


def npl_report(loans, entity, report_date, branches, encoding):
    rows = categorise(loans, entity, "npl", report_date, branches)
    yield from summary_report(loans, rows, LAYOUTS[entity]["summary"][2], report_date, False, encoding)


def rps_report(loans, entity, report_date, branches, encoding):
    rows = categorise(loans, entity, "rps", report_date, branches)
    yield from detail_report(loans, rows, LAYOUTS[entity]["detail"], report_date, encoding)


def lnccd001(notes, commitments, snapshots, report_date):
    comm_by_key = group_rows(commitments, ("ACCTNO", "COMMNO"))
    notes = [
        {**note, **comm_by_key.get(key, [{}])[0]}
        for key, group in group_rows(notes, ("ACCTNO", "COMMNO")).items()
        for note in group
    ]
    joined_notes = group_rows(
        (row for row in notes if text(row.get("PAIDIND")) != "P"), ("ACCTNO", "NOTENO")
    )
    joined_snapshots = group_rows(snapshots, ("ACCTNO", "NOTENO"))
    for key in sorted(joined_notes.keys() & joined_snapshots.keys()):
        left, right = joined_notes[key], joined_snapshots[key]
        # SAS BY merge retains the last row from the shorter input within a BY group.
        for index in range(max(len(left), len(right))):
            row = {**left[min(index, len(left) - 1)], **right[min(index, len(right) - 1)]}
            if text(row.get("PAIDIND")) == "P" or text(row.get("REVERSED")) == "Y":
                continue
            if row.get("BRANCH") not in (None, "", ".") and number(row, "BRANCH") == 0:
                row["BRANCH"] = row.get("NTBRCH")
            original, current, payment = (number(row, field) for field in ("ORGBAL", "CURBAL", "PAYAMT"))
            installments = Decimal(0)
            if original > 0 and current > 0 and payment > 0:
                installments = ((original - current) / payment).quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
            row["NOISTLPD"] = None if text(row.get("BORSTAT")) == "F" else installments
            row["LASTRAN"] = encoded_date(row.get("LASTTRAN"))
            row["MATURDT"] = encoded_date(row.get("MATUREDT"))
            bill_date = sas_date(row.get("BLDATE"))
            days = (report_date - bill_date).days if bill_date and bill_date > SAS_EPOCH else 0
            old_days = number(row, "OLDNOTEDAYARR")
            if old_days > 0 and 98000 <= number(row, "NOTENO") <= 98999:
                days = max(0, days) + old_days
            row["DAYDIFF"] = days
            row["ARREAR"] = bisect_right(ARREARS_BOUNDS, days) + 1
            row["ARREAR2"] = bisect_right(SHORT_BOUNDS, days) + 1
            # CAP is absent from the KEEP list in LNCCD001.
            row.pop("CAP", None)
            yield row


def lnccd002(loans, report_date, branches, encoding):
    return arrears_report(loans, "pbb", report_date, branches, encoding)


def lnccd004(loans, report_date, branches, encoding):
    return npl_report(loans, "pbb", report_date, branches, encoding)


def lnccdq10(loans, report_date, branches, encoding):
    return rps_report(loans, "pbb", report_date, branches, encoding)


def lnccdi02(loans, report_date, branches, encoding):
    return arrears_report(loans, "pibb", report_date, branches, encoding)


def lnccdi04(loans, report_date, branches, encoding):
    return npl_report(loans, "pibb", report_date, branches, encoding)


def lnccdi10(loans, report_date, branches, encoding):
    return rps_report(loans, "pibb", report_date, branches, encoding)


def eifmnpp5(rps, scratch):
    codes = ("911", "912", "916", "915", "914", "913")
    title = b"P000REPORT NO :  SANPLRPS REPORTS"
    code = "000"
    with ExitStack() as stack, rps.open("rb") as handle:
        groups = {code: stack.enter_context(TemporaryFile(dir=scratch)) for code in codes}
        for record in handle:
            record = record.rstrip(b"\r\n")
            if len(record) != 134:
                raise ValueError(f"Expected a 134-byte RPS record in {rps}, got {len(record)}")
            if record[24:32] == b"BRANCH :":
                branch = record[33:36].strip()
                code = CACBRCH.get(str(int(branch)), "000") if branch.isdigit() else "000"
                if code in groups:
                    groups[code].write(b"E255\n" + title + b"\n")
            if code in groups:
                groups[code].write(b"P001" + record + b"\n")
        for code, records in groups.items():
            if not records.tell():
                continue
            yield b"E255".ljust(138)
            yield b"P000PBBEDPPBBEDP".ljust(132) + ("B" + code).encode("ascii").ljust(6)
            yield title.ljust(138)
            records.seek(0)
            records.readline()
            records.readline()
            yield from (record.rstrip(b"\n").ljust(138) for record in records)
