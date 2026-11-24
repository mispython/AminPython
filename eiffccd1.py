"""Main CCD job for PBB (EIFFCCD1) and PIBB (EIIFCCD1)."""

import argparse
import csv
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from ccd_programs import (
    eifmnpp5, lnccd001, lnccd002, lnccd004, lnccdi02, lnccdi04, lnccdi10, lnccdq10,
    text, write_records,
)


# These calls follow the order of the active %INCLUDE members in each JCL.
JOB_PROGRAMS = {
    "pbb": (lnccd001, lnccd002, lnccd004, lnccdq10, eifmnpp5),
    "pibb": (lnccd001, lnccdi02, lnccdi04, lnccdi10, eifmnpp5),
}


def read_table(folder, stem, required):
    names = {f"{stem}.sas7bdat".casefold(), f"{stem}.csv".casefold()}
    matches = sorted(path for path in folder.iterdir() if path.is_file() and path.name.casefold() in names)
    if len(matches) != 1:
        raise ValueError(f"Expected one SAS7BDAT or CSV member {stem} in {folder}, got {len(matches)}")
    path = matches[0]
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            columns = reader.fieldnames or []
            rows = list(reader)
    else:
        try:
            import pyreadstat
        except ImportError as exc:
            raise ValueError("Install pyreadstat to read SAS7BDAT inputs") from exc
        raw, meta = pyreadstat.read_sas7bdat(str(path), output_format="dict")
        columns = meta.column_names
        rows = [dict(zip(columns, values)) for values in zip(*(raw[name] for name in columns))]
    missing = set(required) - {column.upper() for column in columns}
    if missing:
        raise ValueError(f"{path} is missing columns: {', '.join(sorted(missing))}")
    return [{key.upper(): value for key, value in row.items()} for row in rows]



def read_branches(path, encoding):
    branches = {}
    with path.open("rb") as handle:
        for record in handle:
            if record[1:4].strip().isdigit():
                branches[int(record[1:4])] = record[5:8].decode(encoding)
    return branches



def run_entity(args, entity, run_date, report_date, branches):
    def matching_entity(row):
        is_pibb = text(row["ENTITY_CD"]) == "PIBB"
        return is_pibb if entity == "pibb" else not is_pibb

    note_fields = ("ENTITY_CD", "ACCTNO", "COMMNO", "NOTENO")
    suffix = report_date.strftime("%d")
    notes = read_table(args.enrichment, f"ENRH_LN_NOTE_D{suffix}", note_fields)
    commitments = read_table(
        args.enrichment, f"ENRH_LN_COMM_D{suffix}", ("ENTITY_CD", "ACCTNO", "COMMNO")
    )
    year_month_day = run_date.strftime("%y%m%d")
    ln_folder = args.pbb_ln / f"ln{year_month_day}" if entity == "pbb" else args.pibb_ln / f"iln{year_month_day}"
    snapshots = read_table(ln_folder, f"LOAN{report_date:%m%d}", ("ACCTNO", "NOTENO", "BALANCE", "PRODUCT"))
    prepare, arrears, npl, rps, cac = JOB_PROGRAMS[entity]
    # BNM.LOANTEMP is the working table passed to the report subprograms.
    loans = list(prepare(filter(matching_entity, notes), filter(matching_entity, commitments),
                         snapshots, report_date))
    report_arguments = (loans, report_date, branches, args.encoding)
    target = args.output / entity
    target.mkdir(parents=True, exist_ok=True)
    stamp = report_date.strftime("%Y%m%d")
    text_name = f"ccdtxt1_{stamp}.txt"
    rps_name = f"npl_arrears{stamp}.rps"
    cac_name = f"npl_arrears{stamp}.cac"

    def summary_records():
        yield from arrears(*report_arguments)
        yield from npl(*report_arguments)

    names = [text_name]
    with TemporaryDirectory(dir=target) as directory:
        staging = Path(directory)
        write_records(staging / text_name, summary_records())
        if report_date.day == 15:
            write_records(staging / rps_name, rps(*report_arguments))
            write_records(staging / cac_name, cac(staging / rps_name))
            names.extend((rps_name, cac_name))
        for name in names:
            destination = target / name
            (staging / name).replace(destination)
            print(destination)



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
    args = parser.parse_args()
    if args.run_date.day not in {11, 16, 21}:
        parser.error("CCD jobs run only on the 11th, 16th and 21st")
    if "BRANCH :".encode(args.encoding) != b"BRANCH :":
        parser.error("--encoding must be ASCII-compatible")
    report_date = args.run_date - timedelta(days=1)
    try:
        branches = read_branches(args.branch_file, args.encoding)
        for entity in ("pbb", "pibb") if args.entity == "both" else (args.entity,):
            run_entity(args, entity, args.run_date, report_date, branches)
    except (ValueError, OSError) as error:
        parser.exit(1, f"ccd_reports: {error}\n")



if __name__ == "__main__":
    main()
