#!/usr/bin/env python3
"""Python replacement for the EIBWBILE JCL/SAS job.

The source files are fixed-width text files. The program reads directly from
the input directory and writes dated SAS7BDAT datasets directly to the output
directory. Supply --input-root/--output-root to override the project defaults
when needed.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
from typing import Any


# Same default locations as the previous converted jobs.
DEFAULT_INPUT_DIR = Path("Data_Warehouse/MIS/XMIS/input/prod")
DEFAULT_OUTPUT_DIR = DEFAULT_INPUT_DIR / "output"

CUSTOMER_COLUMNS = (
    "ACCTNO",
    "NAME",
    "BRANCH",
    "SECTOR",
    "CUSTCODE",
    "PRODUCT",
    "RESIDENT",
    "MALAYSN",
    "SMALL",
    "STATUS",
    "CUSTTYPE",
    "ORGTYPE",
    "CORPCODE",
    "RACE",
    "BLRCODE",
    "LEGALCD",
    "STATE",
)
FACILITY_COLUMNS = (
    "ACCTNO",
    "AANO",
    "FACILITY",
    "LIMIT",
    "BLRRATE",
    "USANCEPD",
    "LCCRATE",
    "FCCRATE",
    "LCIRATE",
    "FCIRATE",
    "EXIMRATE",
    "ARCODE",
    "EXPIRYDT",
    "COLLCD1",
    "COLLCD2",
    "COLLCD3",
    "COLLCD4",
    "COLLCD5",
    "COLLAMT1",
    "COLLAMT2",
    "COLLAMT3",
    "COLLAMT4",
    "COLLAMT5",
    "BALANCE",
    "PDBBA",
    "PDBBR",
    "BRLCBAL",
    "BRULCBAL",
    "CREATEDT",
    "UPDATEDT",
)
COMBINED_COLUMNS = (
    "ACCTNO",
    "AANO",
    "FACILITY",
    "USANCEPD",
    "LCCRATE",
    "FCCRATE",
    "LCIRATE",
    "FCIRATE",
    "BALANCE",
)
TRANS_COLUMNS = (
    "ACCTNO",
    "AANO",
    "BILLREF",
    "USANCEPD",
    "INTRATE",
    "BILLAMT",
    "INTACCR",
    "IISACCR",
    "MATUREDT",
)
REPTDATE_COLUMNS = ("REPTDATE", "EXTDATE")

CHAR_LENGTHS = {
    "customer": {
        "ACCTNO": 11,
        "NAME": 40,
        "BRANCH": 3,
        "SECTOR": 4,
        "CUSTCODE": 3,
        "PRODUCT": 3,
        "RESIDENT": 1,
        "MALAYSN": 1,
        "SMALL": 1,
        "STATUS": 1,
        "CUSTTYPE": 1,
        "ORGTYPE": 1,
        "CORPCODE": 1,
        "RACE": 1,
        "BLRCODE": 1,
        "LEGALCD": 2,
        "STATE": 2,
    },
    "facility": {
        "ACCTNO": 11,
        "AANO": 13,
        "FACILITY": 2,
        "ARCODE": 1,
        "COLLCD1": 3,
        "COLLCD2": 3,
        "COLLCD3": 3,
        "COLLCD4": 3,
        "COLLCD5": 3,
    },
    "combined": {"ACCTNO": 11, "AANO": 13, "FACILITY": 2},
    "trans": {"ACCTNO": 11, "AANO": 13, "BILLREF": 14},
    "reptdate": {"EXTDATE": 8},
}

NUMERIC_COLUMNS = {
    "facility": {
        "LIMIT",
        "BLRRATE",
        "USANCEPD",
        "LCCRATE",
        "FCCRATE",
        "LCIRATE",
        "FCIRATE",
        "EXIMRATE",
        "EXPIRYDT",
        "COLLAMT1",
        "COLLAMT2",
        "COLLAMT3",
        "COLLAMT4",
        "COLLAMT5",
        "BALANCE",
        "PDBBA",
        "PDBBR",
        "BRLCBAL",
        "BRULCBAL",
        "CREATEDT",
        "UPDATEDT",
    },
    "combined": {
        "USANCEPD",
        "LCCRATE",
        "FCCRATE",
        "LCIRATE",
        "FCIRATE",
        "BALANCE",
    },
    "trans": {"USANCEPD", "INTRATE", "BILLAMT", "INTACCR", "IISACCR", "MATUREDT"},
    "reptdate": {"REPTDATE"},
}

DATE_FORMATS = {
    "facility": {"EXPIRYDT": "DATE9.", "CREATEDT": "DATE9.", "UPDATEDT": "DATE9."},
    "trans": {"MATUREDT": "DATE9."},
    "reptdate": {"REPTDATE": "DATE7."},
}


def text(value: str) -> str:
    """Match SAS character informat behavior for fixed-width text."""
    return value.strip()


def sas_number(value: str, decimals: int = 0) -> float | None:
    """Parse SAS fixed-width numeric informats such as 18.2 or 4."""
    raw = value.strip()
    if not raw:
        return None
    try:
        if "." in raw:
            return float(raw)
        number = int(raw)
        return number / (10**decimals) if decimals else float(number)
    except ValueError:
        return None


def sas_date(value: str) -> int | None:
    """Parse DDMMYY8. into a SAS date number."""
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = datetime.strptime(raw, "%d%m%Y").date()
    except ValueError:
        return None
    return (parsed - date(1960, 1, 1)).days


def output_suffix(run_date: date) -> str:
    """Return YYMMDD suffix for this run's output datasets."""
    return run_date.strftime("%y%m%d")


def resolve_input(directory: Path, filename: str) -> Path:
    """Find the input file, accepting either no extension or .TXT/.txt."""
    candidates = [directory / filename]
    if not filename.lower().endswith(".txt"):
        candidates.extend([directory / f"{filename}.TXT", directory / f"{filename}.txt"])
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Missing input file. Tried: " + ", ".join(str(path) for path in candidates)
    )


def read_lines(path: Path, encoding: str, firstobs: int = 1, obs: int | None = None) -> list[str]:
    with path.open("r", encoding=encoding, errors="replace", newline="") as source:
        lines = [line.rstrip("\r\n") for line in source if line.strip()]
    start = max(firstobs - 1, 0)
    sliced = lines[start:]
    return sliced[:obs] if obs is not None else sliced


def parse_customer(line: str) -> dict[str, Any]:
    return {
        "ACCTNO": text(line[0:11]),
        "NAME": text(line[11:51]),
        "BRANCH": text(line[51:54]),
        "SECTOR": text(line[54:58]),
        "CUSTCODE": text(line[58:61]),
        "PRODUCT": text(line[61:64]),
        "RESIDENT": text(line[64:65]),
        "MALAYSN": text(line[65:66]),
        "SMALL": text(line[66:67]),
        "STATUS": text(line[67:68]),
        "CUSTTYPE": text(line[68:69]),
        "ORGTYPE": text(line[69:70]),
        "CORPCODE": text(line[70:71]),
        "RACE": text(line[71:72]),
        "BLRCODE": text(line[72:73]),
        "LEGALCD": text(line[73:75]),
        "STATE": text(line[75:77]),
    }


def parse_facility(line: str) -> dict[str, Any]:
    expiry = text(line[89:97])
    created = text(line[292:300])
    updated = text(line[300:308])
    return {
        "ACCTNO": text(line[0:11]),
        "AANO": text(line[11:24]),
        "FACILITY": text(line[24:26]),
        "LIMIT": sas_number(line[26:44], 2),
        "BLRRATE": sas_number(line[44:50], 2),
        "USANCEPD": sas_number(line[50:54]),
        "LCCRATE": sas_number(line[54:62], 4),
        "FCCRATE": sas_number(line[62:70], 4),
        "LCIRATE": sas_number(line[70:76], 2),
        "FCIRATE": sas_number(line[76:82], 2),
        "EXIMRATE": sas_number(line[82:88], 2),
        "ARCODE": text(line[88:89]),
        "EXPIRYDT": sas_date(expiry),
        "COLLCD1": text(line[97:100]),
        "COLLCD2": text(line[100:103]),
        "COLLCD3": text(line[103:106]),
        "COLLCD4": text(line[106:109]),
        "COLLCD5": text(line[109:112]),
        "COLLAMT1": sas_number(line[112:130], 2),
        "COLLAMT2": sas_number(line[130:148], 2),
        "COLLAMT3": sas_number(line[148:166], 2),
        "COLLAMT4": sas_number(line[166:184], 2),
        "COLLAMT5": sas_number(line[184:202], 2),
        "BALANCE": sas_number(line[202:220], 2),
        "PDBBA": sas_number(line[220:238], 2),
        "PDBBR": sas_number(line[238:256], 2),
        "BRLCBAL": sas_number(line[256:274], 2),
        "BRULCBAL": sas_number(line[274:292], 2),
        "CREATEDT": sas_date(created),
        "UPDATEDT": sas_date(updated),
    }


def parse_combined(line: str) -> dict[str, Any]:
    return {
        "ACCTNO": text(line[0:11]),
        "AANO": text(line[11:24]),
        "FACILITY": text(line[24:26]),
        "USANCEPD": sas_number(line[26:30]),
        "LCCRATE": sas_number(line[30:38], 4),
        "FCCRATE": sas_number(line[38:46], 4),
        "LCIRATE": sas_number(line[46:52], 2),
        "FCIRATE": sas_number(line[52:58], 2),
        "BALANCE": sas_number(line[58:76], 2),
    }


def parse_trans(line: str) -> dict[str, Any]:
    maturity = text(line[102:110])
    return {
        "ACCTNO": text(line[0:11]),
        "AANO": text(line[11:24]),
        "BILLREF": text(line[24:38]),
        "USANCEPD": sas_number(line[38:42]),
        "INTRATE": sas_number(line[42:48], 2),
        "BILLAMT": sas_number(line[48:66], 2),
        "INTACCR": sas_number(line[66:84], 2),
        "IISACCR": sas_number(line[84:102], 2),
        "MATUREDT": sas_date(maturity),
    }


def parse_reptdate(line: str) -> dict[str, Any]:
    extdate = text(line[0:8])
    return {"REPTDATE": sas_date(extdate), "EXTDATE": extdate}


def load_rows(input_dir: Path, encoding: str, filenames: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    paths = {name: resolve_input(input_dir, filename) for name, filename in filenames.items()}
    return {
        "customer": [parse_customer(line) for line in read_lines(paths["customer"], encoding, firstobs=2)],
        "facility": [parse_facility(line) for line in read_lines(paths["facility"], encoding, firstobs=2)],
        "combined": [parse_combined(line) for line in read_lines(paths["combined"], encoding, firstobs=2)],
        "trans": [parse_trans(line) for line in read_lines(paths["trans"], encoding, firstobs=2)],
        "reptdate": [parse_reptdate(line) for line in read_lines(paths["customer"], encoding, obs=1)],
    }


def write_sas7bdat(rows: dict[str, list[dict[str, Any]]], output_dir: Path, suffix: str) -> dict[str, Path]:
    """Write the converted BILLS datasets as SAS7BDAT files."""
    try:
        import pandas as pd
        import saspy
    except ImportError as error:
        raise RuntimeError(
            "Writing SAS7BDAT requires pandas, saspy, and a configured SAS runtime"
        ) from error

    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir.resolve()
    column_order = {
        "customer": CUSTOMER_COLUMNS,
        "facility": FACILITY_COLUMNS,
        "combined": COMBINED_COLUMNS,
        "trans": TRANS_COLUMNS,
        "reptdate": REPTDATE_COLUMNS,
    }

    output_names = {
        "customer": f"CUSTOMER_{suffix}",
        "facility": f"FACILITY_{suffix}",
        "combined": f"COMBINE_{suffix}",
        "trans": f"TRANS_{suffix}",
        "reptdate": f"REPTDATE_{suffix}",
    }

    frames = {}
    for name, columns in column_order.items():
        frame = pd.DataFrame(rows[name], columns=columns)
        for column, length in CHAR_LENGTHS.get(name, {}).items():
            frame[column] = frame[column].fillna("").astype(str).str.slice(0, length)
        for column in NUMERIC_COLUMNS.get(name, set()):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frames[output_names[name]] = (name, frame)

    sas = saspy.SASsession()
    try:
        sas_path = str(output_dir).replace("'", "''")
        result = sas.submit(f"libname BILLS '{sas_path}';")
        if "ERROR:" in result.get("LOG", ""):
            raise RuntimeError(result["LOG"])

        for table, (schema, frame) in frames.items():
            sas.df2sd(
                frame,
                table=table,
                libref="BILLS",
                char_lengths=CHAR_LENGTHS.get(schema, {}),
                outfmts=DATE_FORMATS.get(schema, {}),
            )
    finally:
        sas.endsas()

    destinations = {
        name: output_dir / f"{table}.sas7bdat"
        for name, table in output_names.items()
    }
    missing = [path for path in destinations.values() if not path.is_file()]
    if missing:
        raise RuntimeError(
            "SAS did not create the expected file(s): "
            + ", ".join(str(path) for path in missing)
        )
    return destinations


def convert(
    input_dir: Path,
    output_dir: Path,
    encoding: str,
    filenames: dict[str, str],
    suffix: str,
) -> dict[str, Path]:
    rows = load_rows(input_dir, encoding, filenames)
    return write_sas7bdat(rows, output_dir, suffix)


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
    parser.add_argument("--customer-file", default="BIILS_CUSTOMER.txt")
    parser.add_argument("--facility-file", default="BIILS_FACILITY.txt")
    parser.add_argument("--combined-file", default="BIILS_COMBINED.txt")
    parser.add_argument("--trans-file", default="BIILS_TRANS.txt")
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="input encoding; use cp037 for EBCDIC",
    )
    args = parser.parse_args()

    suffix = output_suffix(args.today)
    filenames = {
        "customer": args.customer_file,
        "facility": args.facility_file,
        "combined": args.combined_file,
        "trans": args.trans_file,
    }

    print(f"Run date: {args.today:%Y-%m-%d}")
    print(f"Output suffix: {suffix}")
    print(f"Input: {args.input_root}")
    for name, filename in filenames.items():
        print(f"{name.upper()} input: {filename}")

    destinations = convert(args.input_root, args.output_root, args.encoding, filenames, suffix)
    for name, path in destinations.items():
        print(f"{name.upper()}: {path}")

    # Original SAS has PROC PRINT DATA=...(OBS=100) for checking only.
    # Keep that preview commented off while testing the file creation.
    #
    # rows = load_rows(args.input_root, args.encoding, filenames)
    # for dataset_name, dataset_rows in rows.items():
    #     print(f"\n{dataset_name.upper()} first 100 observations")
    #     for row in dataset_rows[:100]:
    #         print(row)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())























































#!/usr/bin/env python3
"""Python replacement for the EIBWBILE JCL/SAS job.

The source files are fixed-width text files. The program reads directly from
the input directory and writes dated SAS7BDAT datasets directly to the output
directory. Supply --input-root/--output-root to override the project defaults
when needed.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
from typing import Any


# Same default locations as the previous converted jobs.
DEFAULT_INPUT_DIR = Path("Data_Warehouse/MIS/XMIS/input/prod")
DEFAULT_OUTPUT_DIR = DEFAULT_INPUT_DIR / "output"

CUSTOMER_COLUMNS = (
    "ACCTNO",
    "NAME",
    "BRANCH",
    "SECTOR",
    "CUSTCODE",
    "PRODUCT",
    "RESIDENT",
    "MALAYSN",
    "SMALL",
    "STATUS",
    "CUSTTYPE",
    "ORGTYPE",
    "CORPCODE",
    "RACE",
    "BLRCODE",
    "LEGALCD",
    "STATE",
)
FACILITY_COLUMNS = (
    "ACCTNO",
    "AANO",
    "FACILITY",
    "LIMIT",
    "BLRRATE",
    "USANCEPD",
    "LCCRATE",
    "FCCRATE",
    "LCIRATE",
    "FCIRATE",
    "EXIMRATE",
    "ARCODE",
    "EXPIRYDT",
    "COLLCD1",
    "COLLCD2",
    "COLLCD3",
    "COLLCD4",
    "COLLCD5",
    "COLLAMT1",
    "COLLAMT2",
    "COLLAMT3",
    "COLLAMT4",
    "COLLAMT5",
    "BALANCE",
    "PDBBA",
    "PDBBR",
    "BRLCBAL",
    "BRULCBAL",
    "CREATEDT",
    "UPDATEDT",
)
COMBINED_COLUMNS = (
    "ACCTNO",
    "AANO",
    "FACILITY",
    "USANCEPD",
    "LCCRATE",
    "FCCRATE",
    "LCIRATE",
    "FCIRATE",
    "BALANCE",
)
TRANS_COLUMNS = (
    "ACCTNO",
    "AANO",
    "BILLREF",
    "USANCEPD",
    "INTRATE",
    "BILLAMT",
    "INTACCR",
    "IISACCR",
    "MATUREDT",
)
REPTDATE_COLUMNS = ("REPTDATE", "EXTDATE")

CHAR_LENGTHS = {
    "customer": {
        "ACCTNO": 11,
        "NAME": 40,
        "BRANCH": 3,
        "SECTOR": 4,
        "CUSTCODE": 3,
        "PRODUCT": 3,
        "RESIDENT": 1,
        "MALAYSN": 1,
        "SMALL": 1,
        "STATUS": 1,
        "CUSTTYPE": 1,
        "ORGTYPE": 1,
        "CORPCODE": 1,
        "RACE": 1,
        "BLRCODE": 1,
        "LEGALCD": 2,
        "STATE": 2,
    },
    "facility": {
        "ACCTNO": 11,
        "AANO": 13,
        "FACILITY": 2,
        "ARCODE": 1,
        "COLLCD1": 3,
        "COLLCD2": 3,
        "COLLCD3": 3,
        "COLLCD4": 3,
        "COLLCD5": 3,
    },
    "combined": {"ACCTNO": 11, "AANO": 13, "FACILITY": 2},
    "trans": {"ACCTNO": 11, "AANO": 13, "BILLREF": 14},
    "reptdate": {"EXTDATE": 8},
}

NUMERIC_COLUMNS = {
    "facility": {
        "LIMIT",
        "BLRRATE",
        "USANCEPD",
        "LCCRATE",
        "FCCRATE",
        "LCIRATE",
        "FCIRATE",
        "EXIMRATE",
        "EXPIRYDT",
        "COLLAMT1",
        "COLLAMT2",
        "COLLAMT3",
        "COLLAMT4",
        "COLLAMT5",
        "BALANCE",
        "PDBBA",
        "PDBBR",
        "BRLCBAL",
        "BRULCBAL",
        "CREATEDT",
        "UPDATEDT",
    },
    "combined": {
        "USANCEPD",
        "LCCRATE",
        "FCCRATE",
        "LCIRATE",
        "FCIRATE",
        "BALANCE",
    },
    "trans": {"USANCEPD", "INTRATE", "BILLAMT", "INTACCR", "IISACCR", "MATUREDT"},
    "reptdate": {"REPTDATE"},
}

DATE_FORMATS = {
    "facility": {"EXPIRYDT": "DATE9.", "CREATEDT": "DATE9.", "UPDATEDT": "DATE9."},
    "trans": {"MATUREDT": "DATE9."},
    "reptdate": {"REPTDATE": "DATE7."},
}


def text(value: str) -> str:
    """Match SAS character informat behavior for fixed-width text."""
    return value.strip()


def sas_number(value: str, decimals: int = 0) -> float | None:
    """Parse SAS fixed-width numeric informats such as 18.2 or 4."""
    raw = value.strip()
    if not raw:
        return None
    try:
        if "." in raw:
            return float(raw)
        number = int(raw)
        return number / (10**decimals) if decimals else float(number)
    except ValueError:
        return None


def sas_date(value: str) -> int | None:
    """Parse DDMMYY8. into a SAS date number."""
    raw = value.strip()
    if not raw:
        return None
    try:
        parsed = datetime.strptime(raw, "%d%m%Y").date()
    except ValueError:
        return None
    return (parsed - date(1960, 1, 1)).days


def output_suffix(run_date: date) -> str:
    """Return YYMMDD suffix for this run's output datasets."""
    return run_date.strftime("%y%m%d")


def resolve_input(directory: Path, filename: str) -> Path:
    """Find the input file, accepting either no extension or .TXT/.txt."""
    candidates = [directory / filename]
    if not filename.lower().endswith(".txt"):
        candidates.extend([directory / f"{filename}.TXT", directory / f"{filename}.txt"])
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(
        "Missing input file. Tried: " + ", ".join(str(path) for path in candidates)
    )


def read_lines(path: Path, encoding: str, firstobs: int = 1, obs: int | None = None) -> list[str]:
    with path.open("r", encoding=encoding, errors="replace", newline="") as source:
        lines = [line.rstrip("\r\n") for line in source if line.strip()]
    start = max(firstobs - 1, 0)
    sliced = lines[start:]
    return sliced[:obs] if obs is not None else sliced


def parse_customer(line: str) -> dict[str, Any]:
    return {
        "ACCTNO": text(line[0:11]),
        "NAME": text(line[11:51]),
        "BRANCH": text(line[51:54]),
        "SECTOR": text(line[54:58]),
        "CUSTCODE": text(line[58:61]),
        "PRODUCT": text(line[61:64]),
        "RESIDENT": text(line[64:65]),
        "MALAYSN": text(line[65:66]),
        "SMALL": text(line[66:67]),
        "STATUS": text(line[67:68]),
        "CUSTTYPE": text(line[68:69]),
        "ORGTYPE": text(line[69:70]),
        "CORPCODE": text(line[70:71]),
        "RACE": text(line[71:72]),
        "BLRCODE": text(line[72:73]),
        "LEGALCD": text(line[73:75]),
        "STATE": text(line[75:77]),
    }


def parse_facility(line: str) -> dict[str, Any]:
    expiry = text(line[89:97])
    created = text(line[292:300])
    updated = text(line[300:308])
    return {
        "ACCTNO": text(line[0:11]),
        "AANO": text(line[11:24]),
        "FACILITY": text(line[24:26]),
        "LIMIT": sas_number(line[26:44], 2),
        "BLRRATE": sas_number(line[44:50], 2),
        "USANCEPD": sas_number(line[50:54]),
        "LCCRATE": sas_number(line[54:62], 4),
        "FCCRATE": sas_number(line[62:70], 4),
        "LCIRATE": sas_number(line[70:76], 2),
        "FCIRATE": sas_number(line[76:82], 2),
        "EXIMRATE": sas_number(line[82:88], 2),
        "ARCODE": text(line[88:89]),
        "EXPIRYDT": sas_date(expiry),
        "COLLCD1": text(line[97:100]),
        "COLLCD2": text(line[100:103]),
        "COLLCD3": text(line[103:106]),
        "COLLCD4": text(line[106:109]),
        "COLLCD5": text(line[109:112]),
        "COLLAMT1": sas_number(line[112:130], 2),
        "COLLAMT2": sas_number(line[130:148], 2),
        "COLLAMT3": sas_number(line[148:166], 2),
        "COLLAMT4": sas_number(line[166:184], 2),
        "COLLAMT5": sas_number(line[184:202], 2),
        "BALANCE": sas_number(line[202:220], 2),
        "PDBBA": sas_number(line[220:238], 2),
        "PDBBR": sas_number(line[238:256], 2),
        "BRLCBAL": sas_number(line[256:274], 2),
        "BRULCBAL": sas_number(line[274:292], 2),
        "CREATEDT": sas_date(created),
        "UPDATEDT": sas_date(updated),
    }


def parse_combined(line: str) -> dict[str, Any]:
    return {
        "ACCTNO": text(line[0:11]),
        "AANO": text(line[11:24]),
        "FACILITY": text(line[24:26]),
        "USANCEPD": sas_number(line[26:30]),
        "LCCRATE": sas_number(line[30:38], 4),
        "FCCRATE": sas_number(line[38:46], 4),
        "LCIRATE": sas_number(line[46:52], 2),
        "FCIRATE": sas_number(line[52:58], 2),
        "BALANCE": sas_number(line[58:76], 2),
    }


def parse_trans(line: str) -> dict[str, Any]:
    maturity = text(line[102:110])
    return {
        "ACCTNO": text(line[0:11]),
        "AANO": text(line[11:24]),
        "BILLREF": text(line[24:38]),
        "USANCEPD": sas_number(line[38:42]),
        "INTRATE": sas_number(line[42:48], 2),
        "BILLAMT": sas_number(line[48:66], 2),
        "INTACCR": sas_number(line[66:84], 2),
        "IISACCR": sas_number(line[84:102], 2),
        "MATUREDT": sas_date(maturity),
    }


def parse_reptdate(line: str) -> dict[str, Any]:
    extdate = text(line[0:8])
    return {"REPTDATE": sas_date(extdate), "EXTDATE": extdate}


def load_rows(input_dir: Path, encoding: str, filenames: dict[str, str]) -> dict[str, list[dict[str, Any]]]:
    paths = {name: resolve_input(input_dir, filename) for name, filename in filenames.items()}
    return {
        "customer": [parse_customer(line) for line in read_lines(paths["customer"], encoding, firstobs=2)],
        "facility": [parse_facility(line) for line in read_lines(paths["facility"], encoding, firstobs=2)],
        "combined": [parse_combined(line) for line in read_lines(paths["combined"], encoding, firstobs=2)],
        "trans": [parse_trans(line) for line in read_lines(paths["trans"], encoding, firstobs=2)],
        "reptdate": [parse_reptdate(line) for line in read_lines(paths["customer"], encoding, obs=1)],
    }


def write_sas7bdat(rows: dict[str, list[dict[str, Any]]], output_dir: Path, suffix: str) -> dict[str, Path]:
    """Write the converted BILLS datasets as SAS7BDAT files."""
    try:
        import pandas as pd
        import saspy
    except ImportError as error:
        raise RuntimeError(
            "Writing SAS7BDAT requires pandas, saspy, and a configured SAS runtime"
        ) from error

    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir.resolve()
    column_order = {
        "customer": CUSTOMER_COLUMNS,
        "facility": FACILITY_COLUMNS,
        "combined": COMBINED_COLUMNS,
        "trans": TRANS_COLUMNS,
        "reptdate": REPTDATE_COLUMNS,
    }

    frames = {}
    for name, columns in column_order.items():
        frame = pd.DataFrame(rows[name], columns=columns)
        for column, length in CHAR_LENGTHS.get(name, {}).items():
            frame[column] = frame[column].fillna("").astype(str).str.slice(0, length)
        for column in NUMERIC_COLUMNS.get(name, set()):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frames[f"{name}_{suffix}"] = (name, frame)

    sas = saspy.SASsession()
    try:
        sas_path = str(output_dir).replace("'", "''")
        result = sas.submit(f"libname BILLS '{sas_path}';")
        if "ERROR:" in result.get("LOG", ""):
            raise RuntimeError(result["LOG"])

        for table, (schema, frame) in frames.items():
            sas.df2sd(
                frame,
                table=table,
                libref="BILLS",
                char_lengths=CHAR_LENGTHS.get(schema, {}),
                outfmts=DATE_FORMATS.get(schema, {}),
            )
    finally:
        sas.endsas()

    destinations = {
        name: output_dir / f"{name}_{suffix}.sas7bdat"
        for name in ("customer", "facility", "combined", "trans", "reptdate")
    }
    missing = [path for path in destinations.values() if not path.is_file()]
    if missing:
        raise RuntimeError(
            "SAS did not create the expected file(s): "
            + ", ".join(str(path) for path in missing)
        )
    return destinations


def convert(
    input_dir: Path,
    output_dir: Path,
    encoding: str,
    filenames: dict[str, str],
    suffix: str,
) -> dict[str, Path]:
    rows = load_rows(input_dir, encoding, filenames)
    return write_sas7bdat(rows, output_dir, suffix)


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
    parser.add_argument("--customer-file", default="CUSTOMER")
    parser.add_argument("--facility-file", default="FACILITY")
    parser.add_argument("--combined-file", default="COMBINED")
    parser.add_argument("--trans-file", default="TRANS")
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="input encoding; use cp037 for EBCDIC",
    )
    args = parser.parse_args()

    suffix = output_suffix(args.today)
    filenames = {
        "customer": args.customer_file,
        "facility": args.facility_file,
        "combined": args.combined_file,
        "trans": args.trans_file,
    }

    print(f"Run date: {args.today:%Y-%m-%d}")
    print(f"Output suffix: {suffix}")
    print(f"Input: {args.input_root}")
    for name, filename in filenames.items():
        print(f"{name.upper()} input: {filename}")

    destinations = convert(args.input_root, args.output_root, args.encoding, filenames, suffix)
    for name, path in destinations.items():
        print(f"{name.upper()}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())





//EIBWBILE JOB MISEIS,EIBWBILE,MSGCLASS=A,MSGLEVEL=(1,1),CLASS=A,       JOB04843
//         REGION=8M,NOTIFY=&SYSUID,USER=OPCC
/*JOBPARM S=S1M1
//*
//SAS609  EXEC SAS609
//CUSTOMER DD DSN=SAP.PBB.BILLS.CUSTOMER(0),DISP=SHR
//FACILITY DD DSN=SAP.PBB.BILLS.FACILITY(0),DISP=SHR
//COMBINED DD DSN=SAP.PBB.BILLS.COMBINED(0),DISP=SHR
//TRANS    DD DSN=SAP.PBB.BILLS.TRANS(0),DISP=SHR
//BILLS    DD DSN=SAP.PBB.BILLS(+1),DISP=(NEW,CATLG,DELETE),
//            DCB=(RECFM=FS,LRECL=27648,BLKSIZE=27648),
//            SPACE=(CYL,(20,10),RLSE),UNIT=SYSDA
//SYSIN     DD *
OPTIONS NOCENTER YEARCUTOFF=1950 LS=132;

DATA BILLS.REPTDATE;
  KEEP REPTDATE EXTDATE;
  INFILE CUSTOMER MISSOVER OBS=1;
  INPUT @1 EXTDATE $8.;
  REPTDATE=INPUT(PUT(EXTDATE,8.),DDMMYY8.);
RUN;

%LET CUSVAR=(KEEP=ACCTNO NAME BRANCH SECTOR CUSTCODE PRODUCT RESIDENT
                  MALAYSN SMALL STATUS CUSTTYPE ORGTYPE CORPCODE
                  RACE BLRCODE LEGALCD STATE );
%LET FACVAR=(KEEP=ACCTNO AANO FACILITY LIMIT BLRRATE USANCEPD LCCRATE
                  FCCRATE LCIRATE FCIRATE EXIMRATE ARCODE EXPIRYDT
                  COLLCD1 COLLCD2 COLLCD3 COLLCD4 COLLCD5 COLLAMT1
                  COLLAMT2 COLLAMT3 COLLAMT4 COLLAMT5 BALANCE PDBBA
                  PDBBR BRLCBAL BRULCBAL CREATEDT UPDATEDT);
%LET COMVAR=(KEEP=ACCTNO AANO FACILITY USANCEPD LCCRATE FCCRATE
                  LCIRATE FCIRATE BALANCE);
%LET TRNVAR=(KEEP=ACCTNO AANO BILLREF USANCEPD INTRATE BILLAMT INTACCR
                  IISACCR MATUREDT);
*;
DATA BILLS.CUSTOMER &CUSVAR;
  INFILE CUSTOMER FIRSTOBS=2;
  INPUT @1   ACCTNO   $11.
        @12  NAME     $40.
        @52  BRANCH   $3.
        @55  SECTOR   $4.
        @59  CUSTCODE $3.
        @62  PRODUCT  $3.
        @65  RESIDENT $1.
        @66  MALAYSN  $1.
        @67  SMALL    $1.
        @68  STATUS   $1.
        @69  CUSTTYPE $1.
        @70  ORGTYPE  $1.
        @71  CORPCODE $1.
        @72  RACE     $1.
        @73  BLRCODE  $1.
        @74  LEGALCD  $2.
        @76  STATE    $2.;
RUN;
*;
DATA BILLS.FACILITY &FACVAR;
  INFILE FACILITY FIRSTOBS=2;
  INPUT @1   ACCTNO   $11.
        @12  AANO     $13.
        @25  FACILITY $2.
        @27  LIMIT    18.2
        @45  BLRRATE  6.2
        @51  USANCEPD 4.
        @55  LCCRATE  8.4
        @63  FCCRATE  8.4
        @71  LCIRATE  6.2
        @77  FCIRATE  6.2
        @83  EXIMRATE 6.2
        @89  ARCODE   $1.
        @90  EXPIRY   $8.
        @98  COLLCD1  $3.
        @101 COLLCD2  $3.
        @104 COLLCD3  $3.
        @107 COLLCD4  $3.
        @110 COLLCD5  $3.
        @113 COLLAMT1 18.2
        @131 COLLAMT2 18.2
        @149 COLLAMT3 18.2
        @167 COLLAMT4 18.2
        @185 COLLAMT5 18.2
        @203 BALANCE  18.2
        @221 PDBBA    18.2
        @239 PDBBR    18.2
        @257 BRLCBAL  18.2
        @275 BRULCBAL 18.2
        @293 CREATE   $8.
        @301 UPDATE   $8.;
        EXPIRYDT=INPUT(PUT(EXPIRY,8.),DDMMYY8.);
        CREATEDT=INPUT(PUT(CREATE,8.),DDMMYY8.);
        UPDATEDT=INPUT(PUT(UPDATE,8.),DDMMYY8.);
RUN;
*;
DATA BILLS.COMBINED &COMVAR;
  INFILE COMBINED FIRSTOBS=2;
  INPUT @1   ACCTNO   $11.
        @12  AANO     $13.
        @25  FACILITY $2.
        @27  USANCEPD 4.
        @31  LCCRATE  8.4
        @39  FCCRATE  8.4
        @47  LCIRATE  6.2
        @53  FCIRATE  6.2
        @59  BALANCE  18.2;
RUN;
*;
DATA BILLS.TRANS &TRNVAR;
  INFILE TRANS FIRSTOBS=2;
  INPUT @1   ACCTNO   $11.
        @12  AANO     $13.
        @25  BILLREF  $14.
        @39  USANCEPD 4.
        @43  INTRATE  6.2
        @49  BILLAMT  18.2
        @67  INTACCR  18.2
        @85  IISACCR  18.2
        @103 MATURITY $8.;
        MATUREDT=INPUT(PUT(MATURITY,8.),DDMMYY8.);
RUN;
*;
PROC PRINT DATA=BILLS.CUSTOMER(OBS=100); RUN;
PROC PRINT DATA=BILLS.FACILITY(OBS=100); RUN;
PROC PRINT DATA=BILLS.COMBINED(OBS=100); RUN;
PROC PRINT DATA=BILLS.TRANS(OBS=100); RUN;
PROC PRINT DATA=BILLS.REPTDATE;
   FORMAT REPTDATE DATE7.; RUN;
