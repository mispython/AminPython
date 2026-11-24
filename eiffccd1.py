"""Main CCD job for PBB (EIFFCCD1) and PIBB (EIIFCCD1)."""

import argparse
import csv
import pickle
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from itertools import groupby
from uuid import uuid4

from ccd_programs import (
    eifmnpp5, lnccd001, lnccd002, lnccd004, lnccdi02, lnccdi04, lnccdi10, lnccdq10,
    disk_sort, key_value, text, write_records,
)


# These calls follow the order of the active %INCLUDE members in each JCL.
JOB_PROGRAMS = {
    "pbb": (lnccd001, lnccd002, lnccd004, lnccdq10, eifmnpp5),
    "pibb": (lnccd001, lnccdi02, lnccdi04, lnccdi10, eifmnpp5),
}


def read_table(folder, stem, required, batch_size):
    names = {f"{stem}.sas7bdat".casefold(), f"{stem}.csv".casefold()}
    matches = sorted(path for path in folder.iterdir() if path.is_file() and path.name.casefold() in names)
    if len(matches) != 1:
        raise ValueError(f"Expected one SAS7BDAT or CSV member {stem} in {folder}, got {len(matches)}")
    path = matches[0]
    def check_columns(columns):
        missing = set(required) - {column.upper() for column in columns}
        if missing:
            raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")

    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            check_columns(reader.fieldnames or [])
            reader.fieldnames = [column.upper() for column in reader.fieldnames]
            yield from reader
        return
    try:
        import pyreadstat
    except ImportError as exc:
        raise ValueError("Install pyreadstat to read SAS7BDAT inputs") from exc
    reader = pyreadstat.read_sas7bdat
    _, meta = reader(str(path), metadataonly=True, output_format="dict")
    columns = meta.column_names
    check_columns(columns)
    keys = [column.upper() for column in columns]
    offset = 0
    while meta.number_rows is None or offset < meta.number_rows:
        raw, _ = reader(str(path), row_offset=offset, row_limit=batch_size, output_format="dict")
        count = len(raw[columns[0]])
        if not count:
            break
        yield from (dict(zip(keys, values)) for values in zip(*(raw[name] for name in columns)))
        offset += count
        del raw
        if count < batch_size:
            break


class LoanWorkTable:
    """Disk-backed equivalent of BNM.LOANTEMP, read afresh for each report."""

    def __init__(self, directory, batch_size):
        self.directory = directory
        self.batch_size = batch_size
        self.path = directory / "loantemp.bin"

    def build(self, prepare, inputs, report_date):
        def tagged_rows():
            for source, rows in enumerate(inputs):
                for row in rows:
                    yield (key_value(row.get("ACCTNO")), source, row)

        ordered = self.sort(tagged_rows(), lambda item: (item[0], item[1]), 2)
        with self.path.open("wb") as handle:
            for _, account in groupby(ordered, key=lambda item: item[0]):
                sources = [[], [], []]
                for _, source, row in account:
                    sources[source].append(row)
                for loan in prepare(*sources, report_date):
                    pickle.dump(loan, handle, protocol=pickle.HIGHEST_PROTOCOL)

    def __iter__(self):
        with self.path.open("rb") as handle:
            while handle.peek(1):
                yield pickle.load(handle)

    def sort(self, rows, key, key_count):
        return disk_sort(rows, key, key_count, self.directory, self.batch_size)



def read_branches(path, encoding):
    branches = {}
    with path.open("rb") as handle:
        for record in handle:
            if record[1:4].strip().isdigit():
                branches[int(record[1:4])] = record[5:8].decode(encoding)
    return branches



def run_entity(args, entity, run_date, report_date, branches, log):
    def checkpoint(percent, message):
        log(f"{entity.upper()} {percent}% {message}")

    checkpoint(0, "Started")
    def matching_entity(row):
        is_pibb = text(row["ENTITY_CD"]) == "PIBB"
        return is_pibb if entity == "pibb" else not is_pibb

    note_fields = ("ENTITY_CD", "ACCTNO", "COMMNO", "NOTENO")
    suffix = report_date.strftime("%d")
    notes = read_table(args.enrichment, f"ENRH_LN_NOTE_D{suffix}", note_fields, args.batch_size)
    commitments = read_table(
        args.enrichment, f"ENRH_LN_COMM_D{suffix}", ("ENTITY_CD", "ACCTNO", "COMMNO"), args.batch_size
    )
    year_month_day = run_date.strftime("%y%m%d")
    ln_folder = args.pbb_ln / f"ln{year_month_day}" if entity == "pbb" else args.pibb_ln / f"iln{year_month_day}"
    snapshots = read_table(ln_folder, f"LOAN{report_date:%m%d}",
                           ("ACCTNO", "NOTENO", "BALANCE", "PRODUCT"), args.batch_size)
    prepare, arrears, npl, rps, cac = JOB_PROGRAMS[entity]
    target = args.output / entity
    target.mkdir(parents=True, exist_ok=True)
    stamp = report_date.strftime("%Y%m%d")
    text_name = f"ccdtxt1_{stamp}.txt"
    rps_name = f"npl_arrears{stamp}.rps"
    cac_name = f"npl_arrears{stamp}.cac"

    names = [text_name]
    with TemporaryDirectory(dir=target) as directory, TemporaryDirectory(dir=args.scratch) as scratch:
        staging = Path(directory)
        loans = LoanWorkTable(Path(scratch), args.batch_size)
        loans.build(prepare, (filter(matching_entity, notes), filter(matching_entity, commitments), snapshots),
                    report_date)
        checkpoint(20, "Inputs merged and LOANTEMP ready")
        report_arguments = (loans, report_date, branches, args.encoding)

        def summary_records():
            yield from arrears(*report_arguments)
            checkpoint(40, "Loan arrears report generated")
            yield from npl(*report_arguments)

        write_records(staging / text_name, summary_records())
        checkpoint(60, "NPL report generated and CCDTXT1 staged")
        if report_date.day == 15:
            write_records(staging / rps_name, rps(*report_arguments))
            write_records(staging / cac_name, cac(staging / rps_name, loans.directory))
            names.extend((rps_name, cac_name))
            checkpoint(80, "RPS and CAC staged")
        else:
            checkpoint(80, "RPS and CAC skipped for this reporting date")
        for name in names:
            destination = target / name
            (staging / name).replace(destination)
            print(destination)
        checkpoint(100, f"Published {len(names)} file(s)")



def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entity", choices=("pbb", "pibb", "both"), default="both")
    parser.add_argument("--run-date", type=date.fromisoformat, default=date.today(), metavar="YYYY-MM-DD")
    parser.add_argument("--enrichment", type=Path, default=Path("/sas/ln/dwh/enrichment"))
    parser.add_argument("--pbb-ln", type=Path, default=Path("/dwh/lnd_ln"))
    parser.add_argument("--pibb-ln", type=Path, default=Path("/dwh/ilnd_ln"))
    parser.add_argument("--branch-file", type=Path, default=Path("/stgsrcsys/host/ftpfiles/DBRANCH.TXT"))
    parser.add_argument("--output", type=Path, default=Path("/exdwh/host/mis/ccd"))
    parser.add_argument("--encoding", default="utf-8", help="ASCII-compatible branch and output text encoding")
    parser.add_argument("--batch-size", type=int, default=100_000, metavar="ROWS",
                        help="Input and disk staging batch size (default: 100000)")
    parser.add_argument("--scratch", type=Path, help="Existing scratch directory for sort and working files")
    parser.add_argument("--log-dir", type=Path, default=Path("/stgsrcsys/host/holding/pas"),
                        help="Directory for a new checkpoint log for each invocation")
    args = parser.parse_args()
    if args.run_date.day not in {11, 16, 21}:
        parser.error("CCD jobs run only on the 11th, 16th and 21st")
    if "BRANCH :".encode(args.encoding) != b"BRANCH :":
        parser.error("--encoding must be ASCII-compatible")
    if args.batch_size < 1:
        parser.error("--batch-size must be at least 1")
    report_date = args.run_date - timedelta(days=1)
    try:
        args.log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        log_path = args.log_dir / f"eiffccd1_{args.run_date:%Y%m%d}_{stamp}_{uuid4().hex[:8]}.log"
        with log_path.open("x", encoding="utf-8", buffering=1) as handle:
            def log(message):
                timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
                handle.write(f"{timestamp} {message}\n")

            print(f"Checkpoint log: {log_path}", flush=True)
            log(f"START entity={args.entity} run_date={args.run_date} data_date={report_date}")
            try:
                branches = read_branches(args.branch_file, args.encoding)
                for entity in ("pbb", "pibb") if args.entity == "both" else (args.entity,):
                    run_entity(args, entity, args.run_date, report_date, branches, log)
            except Exception as error:
                log(f"FAILED {type(error).__name__}: {error}")
                raise
            log("COMPLETE")
    except (ValueError, OSError, sqlite3.Error) as error:
        parser.exit(1, f"ccd_reports: {error}\n")



if __name__ == "__main__":
    main()
