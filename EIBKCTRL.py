#!/usr/bin/env python3
"""Python replacement for the EIBKCTRL JCL/SAS job.

The source files are fixed-width text files. The program reads directly from
the input directory and writes the BANK CONTROL outputs directly to the output
directory. Supply --input-root/--output-root to override the project defaults
when needed.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path


# Same default locations as the previous converted job.
DEFAULT_INPUT_DIR = Path("Data_Warehouse/MIS/XMIS/input/prod")
DEFAULT_OUTPUT_DIR = DEFAULT_INPUT_DIR / "output"

OUTPUT_FILES = {
    "occup": "occup.txt",
    "misc": "misc.txt",
    "cisfmt": "cisfmt.txt",
}


def text(value: str) -> str:
    """Match SAS character informat behavior for fixed-width text."""
    return value.strip()


def read_lines(path: Path, encoding: str) -> list[str]:
    if not path.is_file():
        raise FileNotFoundError(f"Missing input file: {path}")
    with path.open("r", encoding=encoding, errors="replace", newline="") as source:
        return [line.rstrip("\r\n") for line in source if line.strip()]


def parse_occup(line: str) -> dict[str, str]:
    """Parse OCCUP using the original SAS column positions."""
    return {
        "START": text(line[10:13]),
        "LABEL": text(line[14:39]),
        "TYPE": "C",
        "FMTNAME": "OCCUPFMT",
    }


def parse_misc(line: str) -> dict[str, str]:
    """Parse MISC using the original SAS column positions."""
    demono = text(line[4:6])
    democode = text(line[7:17])
    row = {
        "DEMONO": demono,
        "DEMOCODE": democode,
        "ENTRYDATE": text(line[18:25]),
        "EFFECTDATE": text(line[26:39]),
        "DELIND": text(line[40:41]),
        "LABEL": text(line[42:62]),
        "START": "",
        "TYPE": "",
        "FMTNAME": "",
    }
    if demono == "08":
        row["START"] = democode[1:3]
        row["TYPE"] = "C"
        row["FMTNAME"] = "BGCFMT"
    return row


def sort_nodup(rows: list[dict[str, str]], by: tuple[str, ...]) -> list[dict[str, str]]:
    """Reproduce PROC SORT NODUPKEY for character BY variables."""
    result: list[dict[str, str]] = []
    seen: set[tuple[str, ...]] = set()
    for row in sorted(rows, key=lambda item: tuple(item[field] for field in by)):
        key = tuple(row[field] for field in by)
        if key not in seen:
            result.append(row)
            seen.add(key)
    return result


def build_cisfmt(
    occup_rows: list[dict[str, str]], misc_rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    rows = []
    for source in (*occup_rows, *misc_rows):
        if source.get("FMTNAME", ""):
            rows.append(
                {
                    "START": source.get("START", "")[:10],
                    "TYPE": source.get("TYPE", "")[:1],
                    "LABEL": source.get("LABEL", "")[:100],
                    "FMTNAME": source.get("FMTNAME", "")[:30],
                }
            )
    return sorted(rows, key=lambda item: (item["FMTNAME"], item["START"]))


def dated_input_names(run_date: date) -> tuple[str, str]:
    """Return the OCCUP and MISC filenames fetched for the previous day."""
    file_date = run_date - timedelta(days=1)
    suffix = file_date.strftime("%Y%m%d")
    return f"CIS_OCCUP_MAP_{suffix}", f"CIS_MSCD_MAP_{suffix}"


def write_txt(path: Path, columns: tuple[str, ...], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as target:
        target.write("\t".join(columns) + "\n")
        for row in rows:
            target.write("\t".join(row.get(column, "") for column in columns) + "\n")


def write_outputs(
    occup_rows: list[dict[str, str]],
    misc_rows: list[dict[str, str]],
    cisfmt_rows: list[dict[str, str]],
    output_dir: Path,
) -> dict[str, Path]:
    """Write the converted BANK CONTROL data as text files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir.resolve()

    destinations = {
        name: output_dir / filename for name, filename in OUTPUT_FILES.items()
    }
    write_txt(destinations["occup"], ("START", "LABEL", "TYPE", "FMTNAME"), occup_rows)
    write_txt(
        destinations["misc"],
        (
            "DEMONO",
            "DEMOCODE",
            "ENTRYDATE",
            "EFFECTDATE",
            "DELIND",
            "LABEL",
            "START",
            "TYPE",
            "FMTNAME",
        ),
        misc_rows,
    )
    write_txt(destinations["cisfmt"], ("START", "TYPE", "LABEL", "FMTNAME"), cisfmt_rows)
    return destinations


def convert(
    input_dir: Path,
    output_dir: Path,
    encoding: str,
    occup_input: str,
    misc_input: str,
) -> dict[str, Path]:
    occup_rows = sort_nodup(
        [parse_occup(line) for line in read_lines(input_dir / occup_input, encoding)],
        ("START",),
    )
    misc_rows = sort_nodup(
        [parse_misc(line) for line in read_lines(input_dir / misc_input, encoding)],
        ("DEMONO", "DEMOCODE", "START"),
    )
    cisfmt_rows = build_cisfmt(occup_rows, misc_rows)
    return write_outputs(occup_rows, misc_rows, cisfmt_rows, output_dir)


def parse_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as error:
        raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--today", type=parse_date, default=date.today(), help="run date (YYYY-MM-DD)")
    parser.add_argument("--input-root", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--occup-file", help="override OCCUP input filename")
    parser.add_argument("--misc-file", help="override MISC input filename")
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="input encoding; use cp037 for EBCDIC",
    )
    args = parser.parse_args()

    default_occup, default_misc = dated_input_names(args.today)
    occup_input = args.occup_file or default_occup
    misc_input = args.misc_file or default_misc

    print(f"Run date: {args.today:%Y-%m-%d}")
    print(f"Input file date: {args.today - timedelta(days=1):%Y%m%d}")
    print(f"Input: {args.input_root}")
    print(f"OCCUP input: {occup_input}")
    print(f"MISC input: {misc_input}")
    destinations = convert(
        args.input_root,
        args.output_root,
        args.encoding,
        occup_input,
        misc_input,
    )
    for name, path in destinations.items():
        print(f"{name.upper()}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())














lzopts servercp=$servercp,notrim,overflow=trunc,mode=text         
lzopts linerule=$lr                                               
cd /dwh/input/CIS                                                  
put //RBP2.B033.UNLOAD.CUSTMSCD.DESC(0) CIS_MSCD_MAP_20260622     
put //RBP2.B033.BANKCTRL.OCCUP          CIS_OCCUP_MAP_20260622    








//EIBKCTRL JOB MSGCLASS=X,MSGLEVEL=(1,1),REGION=64M,NOTIFY=&SYSUID      JOB29240
//*---------------------------------------------------------------------
//* BANK CONTROL
//*---------------------------------------------------------------------
//EIBKCTRL EXEC SAS609
//OCCUP    DD DISP=SHR,DSN=RBP2.B033.BANKCTRL.OCCUP
//MISC     DD DISP=SHR,DSN=RBP2.B033.UNLOAD.CUSTMSCD.DESC(0)
//BKCTRL   DD DISP=OLD,DSN=SAP.PBB.BANK.CONTROL
//SYSIN    DD *

OPTIONS YEARCUTOFF=1960 NODATE NONUMBER NOCENTER;

DATA BKCTRL.OCCUP;
   INFILE OCCUP;
   INPUT @011 START        $3.  /* OCCUPAT     */
         @015 LABEL       $25.  /* DESCRIPTION */
         ;
   TYPE    = 'C';
   FMTNAME = 'OCCUPFMT';
RUN;
PROC SORT DATA=BKCTRL.OCCUP NODUPKEY; BY START; RUN;

DATA BKCTRL.MISC;
   INFILE MISC;
   INPUT @005 DEMONO       $2.
         @008 DEMOCODE    $10.  /* DEMOCODE    */
         @019 ENTRYDATE    $7.
         @027 EFFECTDATE  $13.
         @041 DELIND       $1.
         @043 LABEL       $20.  /* DESCRIPTION */
         ;
   IF DEMONO = '08' THEN DO;
      START   = SUBSTR(DEMOCODE,2,2);
      TYPE    = 'C';
      FMTNAME = 'BGCFMT';
   END;
RUN;
PROC SORT DATA=BKCTRL.MISC NODUPKEY; BY DEMONO DEMOCODE START; RUN;

DATA BKCTRL.CISFMT;
   FORMAT START $10. LABEL $100. FMTNAME $30.;
   SET BKCTRL.OCCUP BKCTRL.MISC;
   WHERE FMTNAME NE '';
   KEEP START TYPE LABEL FMTNAME;
RUN;
PROC SORT; BY FMTNAME START; RUN;
PROC FORMAT LIBRARY=WORK CNTLIN=BKCTRL.CISFMT; RUN;
