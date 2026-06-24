
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



















#!/usr/bin/env python3
"""Python replacement for the EIBWBILE JCL/SAS job.

The source files are fixed-width text files. The program reads directly from
the input directory and writes dated SAS7BDAT datasets directly to the output
directory. Supply --input-root/--output-root to override the project defaults
when needed.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
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
    """Return YYMMDD suffix for the previous day's output datasets."""
    return (run_date - timedelta(days=1)).strftime("%y%m%d")


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


def sas_quote(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def write_sas7bdat(input_paths: dict[str, Path], output_dir: Path, suffix: str) -> dict[str, Path]:
    """Write the converted BILLS datasets as SAS7BDAT files.

    Let SAS read the fixed-width text directly so numeric informats match the
    original job exactly under PROC COMPARE METHOD=EXACT.
    """
    try:
        import saspy
    except ImportError as error:
        raise RuntimeError(
            "Writing SAS7BDAT requires saspy and a configured SAS runtime"
        ) from error

    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir.resolve()
    output_names = {
        "customer": f"customer_{suffix}",
        "facility": f"facility_{suffix}",
        "combined": f"combine_{suffix}",
        "trans": f"trans_{suffix}",
        "reptdate": f"reptdate_{suffix}",
    }

    sas = saspy.SASsession()
    try:
        result = sas.submit(
            f"""
options yearcutoff=1950 nocenter;
libname BILLS '{sas_quote(output_dir)}';
filename CUSTOMER '{sas_quote(input_paths["customer"])}';
filename FACILITY '{sas_quote(input_paths["facility"])}';
filename COMBINED '{sas_quote(input_paths["combined"])}';
filename TRANS    '{sas_quote(input_paths["trans"])}';

data BILLS.{output_names["reptdate"]};
  keep reptdate extdate;
  infile CUSTOMER missover obs=1;
  input @1 extdate $8.;
  reptdate=input(extdate,ddmmyy8.);
run;

data BILLS.{output_names["customer"]};
  infile CUSTOMER firstobs=2;
  input @1   acctno   $11.
        @12  name     $40.
        @52  branch   $3.
        @55  sector   $4.
        @59  custcode $3.
        @62  product  $3.
        @65  resident $1.
        @66  malaysn  $1.
        @67  small    $1.
        @68  status   $1.
        @69  custtype $1.
        @70  orgtype  $1.
        @71  corpcode $1.
        @72  race     $1.
        @73  blrcode  $1.
        @74  legalcd  $2.
        @76  state    $2.;
run;

data BILLS.{output_names["facility"]};
  infile FACILITY firstobs=2;
  input @1   acctno   $11.
        @12  aano     $13.
        @25  facility $2.
        @27  limit    18.2
        @45  blrrate  6.2
        @51  usancepd 4.
        @55  lccrate  8.4
        @63  fccrate  8.4
        @71  lcirate  6.2
        @77  fcirate  6.2
        @83  eximrate 6.2
        @89  arcode   $1.
        @90  expiry   $8.
        @98  collcd1  $3.
        @101 collcd2  $3.
        @104 collcd3  $3.
        @107 collcd4  $3.
        @110 collcd5  $3.
        @113 collamt1 18.2
        @131 collamt2 18.2
        @149 collamt3 18.2
        @167 collamt4 18.2
        @185 collamt5 18.2
        @203 balance  18.2
        @221 pdbba    18.2
        @239 pdbbr    18.2
        @257 brlcbal  18.2
        @275 brulcbal 18.2
        @293 create   $8.
        @301 update   $8.;
        expirydt=input(expiry,ddmmyy8.);
        createdt=input(create,ddmmyy8.);
        updatedt=input(update,ddmmyy8.);
        keep acctno aano facility limit blrrate usancepd lccrate fccrate
             lcirate fcirate eximrate arcode expirydt collcd1 collcd2
             collcd3 collcd4 collcd5 collamt1 collamt2 collamt3 collamt4
             collamt5 balance pdbba pdbbr brlcbal brulcbal createdt updatedt;
run;

data BILLS.{output_names["combined"]};
  infile COMBINED firstobs=2;
  input @1   acctno   $11.
        @12  aano     $13.
        @25  facility $2.
        @27  usancepd 4.
        @31  lccrate  8.4
        @39  fccrate  8.4
        @47  lcirate  6.2
        @53  fcirate  6.2
        @59  balance  18.2;
run;

data BILLS.{output_names["trans"]};
  infile TRANS firstobs=2;
  input @1   acctno   $11.
        @12  aano     $13.
        @25  billref  $14.
        @39  usancepd 4.
        @43  intrate  6.2
        @49  billamt  18.2
        @67  intaccr  18.2
        @85  iisaccr  18.2
        @103 maturity $8.;
        maturedt=input(maturity,ddmmyy8.);
        keep acctno aano billref usancepd intrate billamt intaccr iisaccr maturedt;
run;
"""
        )
        if "ERROR:" in result.get("LOG", ""):
            raise RuntimeError(result["LOG"])
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
    input_paths = {
        name: resolve_input(input_dir, filename)
        for name, filename in filenames.items()
    }
    return write_sas7bdat(input_paths, output_dir, suffix)


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
    parser.add_argument("--customer-file", default="BILLS_CUSTOMER.txt")
    parser.add_argument("--facility-file", default="BILLS_FACILITY.txt")
    parser.add_argument("--combined-file", default="BILLS_COMBINED.txt")
    parser.add_argument("--trans-file", default="BILLS_TRANS.txt")
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



Section G 

COMPLIANCE/FINANCIAL CRIME COMPLIANCE FUNCTION 2026 

                                                       The COMPARE Procedure                                                        
                                             Comparison of A.TRANS with A.TRANS_260623                                              
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                                         Data Set Summary                                                           
                                                                                                                                    
                                  Dataset                  Created          Modified  NVar    NObs                                  
                                                                                                                                    
                                  A.TRANS         24JUN26:10:18:51  24JUN26:10:18:51     9     127                                  
                                  A.TRANS_260623  24JUN26:14:42:39  24JUN26:14:42:39     9     127                                  
                                                                                                                                    
                                                                                                                                    
                                                         Variables Summary                                                          
                                                                                                                                    
                                               Number of Variables in Common: 9.                                                    


                                                                                                                                    
                                                                                                                                    
                                                        Observation Summary                                                         
                                                                                                                                    
                                                   Observation      Base  Compare                                                   
                                                                                                                                    
                                                   First Obs           1        1                                                   
                                                   First Unequal       2        2                                                   
                                                   Last  Unequal     124      124                                                   
                                                   Last  Obs         127      127                                                   
                                                                                                                                    
                                  Number of Observations in Common: 127.                                                            
                                  Total Number of Observations Read from A.TRANS: 127.                                              
                                  Total Number of Observations Read from A.TRANS_260623: 127.                                       
                                                                                                                                    
                                  Number of Observations with Some Compared Variables Unequal: 50.                                  
                                  Number of Observations with All Compared Variables Equal: 77.                                     
                                                                                                                                    
                                                                                                                                    
                                                     Values Comparison Summary                                                      
                                                                                                                                    
                                  Number of Variables Compared with All Observations Equal: 5.                                      
                                  Number of Variables Compared with Some Observations Unequal: 4.                                   
                                  Total Number of Values which Compare Unequal: 65.                                                 
                                  Maximum Difference: 9.3132E-10.                                                                   
                                                                                                                                    
                                                                                                                                    
                                                   Variables with Unequal Values                                                    
                                                                                                                                    
                                                Variable  Type  Len  Ndif   MaxDif                                                  
                                                                                                                                    
                                                INTRATE   NUM     8    13  444E-18                                                  
                                                BILLAMT   NUM     8    23  931E-12                                                  
                                                INTACCR   NUM     8    16  146E-13                                                  
                                                IISACCR   NUM     8    13  582E-13                                                  
                                                                                                                                    




Section G 

COMPLIANCE/FINANCIAL CRIME COMPLIANCE FUNCTION 2026 

                                                       The COMPARE Procedure                                                        
                                             Comparison of A.TRANS with A.TRANS_260623                                              
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                               Value Comparison Results for Variables                                               
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    INTRATE    intrate      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            28  ||     3.7000     3.7000  4.441E-16    1.2E-14                                      
                                            29  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            30  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            31  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            32  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            33  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            34  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            35  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            36  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            37  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            38  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            39  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            40  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                     __________________________________________________________                                     
                                                                                                                                    
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    BILLAMT    billamt      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                             2  ||    1253045    1253045  2.328E-10  1.858E-14                                      
                                             4  ||      35534      35534  7.276E-12  2.048E-14                                      
                                             8  ||    2293121    2293121  4.657E-10  2.031E-14                                      
                                            22  ||    2094712    2094712  2.328E-10  1.112E-14                                      
                                            23  ||      42502      42502  7.276E-12  1.712E-14                                      
                                            25  ||      42502      42502  7.276E-12  1.712E-14                                      
                                            27  ||      21248      21248  3.638E-12  1.712E-14                                      
                                            49  ||     250333     250333   2.91E-11  1.163E-14                                      
                                            70  ||      55556      55556  7.276E-12   1.31E-14                                      
                                            71  ||       7222       7222  9.095E-13  1.259E-14                                      
                                            73  ||       3556       3556  4.547E-13  1.279E-14                                      
                                            75  ||    1169313    1169313  2.328E-10  1.991E-14                                      
                                            76  ||     122550     122550  1.455E-11  1.187E-14                                      
                                            79  ||    1484524    1484524  2.328E-10  1.568E-14                                      
                                            84  ||    7940883    7940883  9.313E-10  1.173E-14                                      
                                            86  ||    3350689    3350689  4.657E-10   1.39E-14                                      
                                            95  ||     333956     333956  5.821E-11  1.743E-14                                      
                                            98  ||    1105561    1105561  2.328E-10  2.106E-14                                      
                                           108  ||      21136      21136  3.638E-12  1.721E-14                                      
                                           113  ||      21248      21248  3.638E-12  1.712E-14                                      
                                           116  ||     0.5500     0.5500   1.11E-16  2.019E-14                                      
                                           119  ||      19975      19975  3.638E-12  1.821E-14                                      
                                           124  ||      57235      57235  7.276E-12  1.271E-14                                      
                                     __________________________________________________________                                     




Section G 

COMPLIANCE/FINANCIAL CRIME COMPLIANCE FUNCTION 2026 
                                                       The COMPARE Procedure                                                        
                                             Comparison of A.TRANS with A.TRANS_260623                                              
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                               Value Comparison Results for Variables                                               
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    INTACCR    intaccr      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            61  ||       2887       2887  4.547E-13  1.575E-14                                      
                                            63  ||    88.3700    88.3700  1.421E-14  1.608E-14                                      
                                            66  ||    88.4200    88.4200  1.421E-14  1.607E-14                                      
                                            68  ||       2972       2972  4.547E-13   1.53E-14                                      
                                            69  ||   402.6800   402.6800  5.684E-14  1.412E-14                                      
                                            70  ||   892.5800   892.5800  1.137E-13  1.274E-14                                      
                                            71  ||   199.9300   199.9300  2.842E-14  1.422E-14                                      
                                            76  ||       3242       3242  4.547E-13  1.403E-14                                      
                                            77  ||      18768      18768  3.638E-12  1.938E-14                                      
                                            79  ||      35181      35181  7.276E-12  2.068E-14                                      
                                            80  ||      57500      57500  7.276E-12  1.265E-14                                      
                                            86  ||      80784      80784  1.455E-11  1.801E-14                                      
                                            99  ||       1130       1130  2.274E-13  2.012E-14                                      
                                           101  ||       6616       6616  9.095E-13  1.375E-14                                      
                                           104  ||       3312       3312  4.547E-13  1.373E-14                                      
                                           105  ||   767.6000   767.6000  1.137E-13  1.481E-14                                      
                                     __________________________________________________________                                     
                                                                                                                                    
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    IISACCR    iisaccr      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            61  ||       5084       5084  9.095E-13  1.789E-14                                      
                                            66  ||   147.0300   147.0300  2.842E-14  1.933E-14                                      
                                            67  ||   130.8300   130.8300  2.842E-14  2.172E-14                                      
                                            68  ||       4697       4697  9.095E-13  1.936E-14                                      
                                            70  ||       1399       1399  2.274E-13  1.626E-14                                      
                                            71  ||   384.8700   384.8700  5.684E-14  1.477E-14                                      
                                            75  ||      34455      34455  7.276E-12  2.112E-14                                      
                                            76  ||       3628       3628  4.547E-13  1.254E-14                                      
                                            78  ||     109976     109976  1.455E-11  1.323E-14                                      
                                            79  ||      78720      78720  1.455E-11  1.849E-14                                      
                                            80  ||     129326     129326  1.455E-11  1.125E-14                                      
                                            81  ||     303430     303430  5.821E-11  1.918E-14                                      
                                            86  ||     171711     171711   2.91E-11  1.695E-14                                      
                                     __________________________________________________________                                     





Section G 

COMPLIANCE/FINANCIAL CRIME COMPLIANCE FUNCTION 2026 

                                                       The COMPARE Procedure                                                        
                                          Comparison of A.FACILITY with A.FACILITY_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                                         Data Set Summary                                                           
                                                                                                                                    
                                Dataset                     Created          Modified  NVar    NObs                                 
                                                                                                                                    
                                A.FACILITY         24JUN26:10:18:51  24JUN26:10:18:51    30      63                                 
                                A.FACILITY_260623  24JUN26:14:42:39  24JUN26:14:42:39    30      63                                 
                                                                                                                                    
                                                                                                                                    
                                                         Variables Summary                                                          
                                                                                                                                    
                                               Number of Variables in Common: 30.                                                   


                                                                                                                                    
                                                                                                                                    
                                                        Observation Summary                                                         
                                                                                                                                    
                                                   Observation      Base  Compare                                                   
                                                                                                                                    
                                                   First Obs           1        1                                                   
                                                   First Unequal       7        7                                                   
                                                   Last  Unequal      61       61                                                   
                                                   Last  Obs          63       63                                                   
                                                                                                                                    
                                  Number of Observations in Common: 63.                                                             
                                  Total Number of Observations Read from A.FACILITY: 63.                                            
                                  Total Number of Observations Read from A.FACILITY_260623: 63.                                     
                                                                                                                                    
                                  Number of Observations with Some Compared Variables Unequal: 7.                                   
                                  Number of Observations with All Compared Variables Equal: 56.                                     
                                                                                                                                    
                                                                                                                                    
                                                     Values Comparison Summary                                                      
                                                                                                                                    
                                  Number of Variables Compared with All Observations Equal: 27.                                     
                                  Number of Variables Compared with Some Observations Unequal: 3.                                   
                                  Total Number of Values which Compare Unequal: 8.                                                  
                                  Maximum Difference: 1.8626E-09.                                                                   
                                                                                                                                    
                                                                                                                                    
                                                   Variables with Unequal Values                                                    
                                                                                                                                    
                                                Variable  Type  Len  Ndif   MaxDif                                                  
                                                                                                                                    
                                                BALANCE   NUM     8     6  1.86E-9                                                  
                                                BRLCBAL   NUM     8     1  1.86E-9                                                  
                                                BRULCBAL  NUM     8     1  233E-12                                                  
                                                                                                                                    




Section G 

COMPLIANCE/FINANCIAL CRIME COMPLIANCE FUNCTION 2026 

                                                       The COMPARE Procedure                                                        
                                          Comparison of A.FACILITY with A.FACILITY_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                               Value Comparison Results for Variables                                               
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    BALANCE    balance      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                             7  ||   10798494   10798494  1.8626E-9  1.725E-14                                      
                                             8  ||    7167282    7167282  9.313E-10  1.299E-14                                      
                                            12  ||      50534      50534  7.276E-12   1.44E-14                                      
                                            30  ||    1086262    1086262  2.328E-10  2.143E-14                                      
                                            54  ||      42502      42502  7.276E-12  1.712E-14                                      
                                            61  ||      42502      42502  7.276E-12  1.712E-14                                      
                                     __________________________________________________________                                     
                                                                                                                                    
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    BRLCBAL    brlcbal      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            45  ||   10736782   10736782  1.8626E-9  1.735E-14                                      
                                     __________________________________________________________                                     
                                                                                                                                    
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||   BRULCBAL   brulcbal      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            45  ||    1283641    1283641  2.328E-10  1.814E-14                                      
                                     __________________________________________________________                                     





Section G 

COMPLIANCE/FINANCIAL CRIME COMPLIANCE FUNCTION 2026 

                                                       The COMPARE Procedure                                                        
                                          Comparison of A.CUSTOMER with A.CUSTOMER_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                                         Data Set Summary                                                           
                                                                                                                                    
                                Dataset                     Created          Modified  NVar    NObs                                 
                                                                                                                                    
                                A.CUSTOMER         24JUN26:10:18:51  24JUN26:10:18:51    17      20                                 
                                A.CUSTOMER_260623  24JUN26:14:42:39  24JUN26:14:42:39    17      20                                 
                                                                                                                                    
                                                                                                                                    
                                                         Variables Summary                                                          
                                                                                                                                    
                                               Number of Variables in Common: 17.                                                   


                                                                                                                                    
                                                                                                                                    
                                                        Observation Summary                                                         
                                                                                                                                    
                                                   Observation      Base  Compare                                                   
                                                                                                                                    
                                                   First Obs           1        1                                                   
                                                   Last  Obs          20       20                                                   
                                                                                                                                    
                                  Number of Observations in Common: 20.                                                             
                                  Total Number of Observations Read from A.CUSTOMER: 20.                                            
                                  Total Number of Observations Read from A.CUSTOMER_260623: 20.                                     
                                                                                                                                    
                                  Number of Observations with Some Compared Variables Unequal: 0.                                   
                                  Number of Observations with All Compared Variables Equal: 20.                                     
                                                                                                                                    
                                  NOTE: No unequal values were found. All values compared are exactly equal.                        
                                                                                                                                    





Section G 

COMPLIANCE/FINANCIAL CRIME COMPLIANCE FUNCTION 2026 

                                                       The COMPARE Procedure                                                        
                                           Comparison of A.COMBINED with A.COMBINE_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                                         Data Set Summary                                                           
                                                                                                                                    
                                 Dataset                    Created          Modified  NVar    NObs                                 
                                                                                                                                    
                                 A.COMBINED        24JUN26:10:18:51  24JUN26:10:18:51     9      53                                 
                                 A.COMBINE_260623  24JUN26:14:42:39  24JUN26:14:42:39     9      53                                 
                                                                                                                                    
                                                                                                                                    
                                                         Variables Summary                                                          
                                                                                                                                    
                                               Number of Variables in Common: 9.                                                    


                                                                                                                                    
                                                                                                                                    
                                                        Observation Summary                                                         
                                                                                                                                    
                                                   Observation      Base  Compare                                                   
                                                                                                                                    
                                                   First Obs           1        1                                                   
                                                   First Unequal      17       17                                                   
                                                   Last  Unequal      51       51                                                   
                                                   Last  Obs          53       53                                                   
                                                                                                                                    
                                  Number of Observations in Common: 53.                                                             
                                  Total Number of Observations Read from A.COMBINED: 53.                                            
                                  Total Number of Observations Read from A.COMBINE_260623: 53.                                      
                                                                                                                                    
                                  Number of Observations with Some Compared Variables Unequal: 5.                                   
                                  Number of Observations with All Compared Variables Equal: 48.                                     
                                                                                                                                    
                                                                                                                                    
                                                     Values Comparison Summary                                                      
                                                                                                                                    
                                  Number of Variables Compared with All Observations Equal: 8.                                      
                                  Number of Variables Compared with Some Observations Unequal: 1.                                   
                                  Total Number of Values which Compare Unequal: 5.                                                  
                                  Maximum Difference: 1.8626E-09.                                                                   
                                                                                                                                    
                                                                                                                                    
                                                   Variables with Unequal Values                                                    
                                                                                                                                    
                                                Variable  Type  Len  Ndif   MaxDif                                                  
                                                                                                                                    
                                                BALANCE   NUM     8     5  1.86E-9                                                  
                                                                                                                                    




Section G 

COMPLIANCE/FINANCIAL CRIME COMPLIANCE FUNCTION 2026 

                                                       The COMPARE Procedure                                                        
                                           Comparison of A.COMBINED with A.COMBINE_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                               Value Comparison Results for Variables                                               
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    BALANCE    balance      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            17  ||    1253045    1253045  2.328E-10  1.858E-14                                      
                                            23  ||   15547147   15547147  1.8626E-9  1.198E-14                                      
                                            27  ||     0.0100     0.0100  1.735E-18  1.735E-14                                      
                                            33  ||    2094712    2094712  2.328E-10  1.112E-14                                      
                                            51  ||      58556      58556  7.276E-12  1.243E-14                                      
                                     __________________________________________________________         













#!/usr/bin/env python3
"""Python replacement for the EIBWBILE JCL/SAS job.

The source files are fixed-width text files. The program reads directly from
the input directory and writes dated SAS7BDAT datasets directly to the output
directory. Supply --input-root/--output-root to override the project defaults
when needed.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
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
    """Return YYMMDD suffix for the previous day's output datasets."""
    return (run_date - timedelta(days=1)).strftime("%y%m%d")


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


def sas_quote(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def write_sas7bdat(input_paths: dict[str, Path], output_dir: Path, suffix: str) -> dict[str, Path]:
    """Write the converted BILLS datasets as SAS7BDAT files.

    Let SAS read the fixed-width text directly so numeric informats match the
    original job exactly under PROC COMPARE METHOD=EXACT.
    """
    try:
        import saspy
    except ImportError as error:
        raise RuntimeError(
            "Writing SAS7BDAT requires saspy and a configured SAS runtime"
        ) from error

    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir.resolve()
    output_names = {
        "customer": f"customer_{suffix}",
        "facility": f"facility_{suffix}",
        "combined": f"combine_{suffix}",
        "trans": f"trans_{suffix}",
        "reptdate": f"reptdate_{suffix}",
    }

    sas = saspy.SASsession()
    try:
        result = sas.submit(
            f"""
options yearcutoff=1950 nocenter;
libname BILLS '{sas_quote(output_dir)}';
filename CUSTOMER '{sas_quote(input_paths["customer"])}';
filename FACILITY '{sas_quote(input_paths["facility"])}';
filename COMBINED '{sas_quote(input_paths["combined"])}';
filename TRANS    '{sas_quote(input_paths["trans"])}';

data BILLS.{output_names["reptdate"]};
  keep reptdate extdate;
  infile CUSTOMER missover obs=1;
  input @1 extdate $8.;
  reptdate=input(extdate,ddmmyy8.);
run;

data BILLS.{output_names["customer"]};
  infile CUSTOMER firstobs=2;
  input @1   acctno   $11.
        @12  name     $40.
        @52  branch   $3.
        @55  sector   $4.
        @59  custcode $3.
        @62  product  $3.
        @65  resident $1.
        @66  malaysn  $1.
        @67  small    $1.
        @68  status   $1.
        @69  custtype $1.
        @70  orgtype  $1.
        @71  corpcode $1.
        @72  race     $1.
        @73  blrcode  $1.
        @74  legalcd  $2.
        @76  state    $2.;
run;

data BILLS.{output_names["facility"]};
  infile FACILITY firstobs=2;
  input @1   acctno   $11.
        @12  aano     $13.
        @25  facility $2.
        @27  limit    18.2
        @45  blrrate  6.2
        @51  usancepd 4.
        @55  lccrate  8.4
        @63  fccrate  8.4
        @71  lcirate  6.2
        @77  fcirate  6.2
        @83  eximrate 6.2
        @89  arcode   $1.
        @90  expiry   $8.
        @98  collcd1  $3.
        @101 collcd2  $3.
        @104 collcd3  $3.
        @107 collcd4  $3.
        @110 collcd5  $3.
        @113 collamt1 18.2
        @131 collamt2 18.2
        @149 collamt3 18.2
        @167 collamt4 18.2
        @185 collamt5 18.2
        @203 balance  18.2
        @221 pdbba    18.2
        @239 pdbbr    18.2
        @257 brlcbal  18.2
        @275 brulcbal 18.2
        @293 create   $8.
        @301 update   $8.;
        expirydt=input(expiry,ddmmyy8.);
        createdt=input(create,ddmmyy8.);
        updatedt=input(update,ddmmyy8.);
        limit=round(limit,.01);
        blrrate=round(blrrate,.01);
        lccrate=round(lccrate,.0001);
        fccrate=round(fccrate,.0001);
        lcirate=round(lcirate,.01);
        fcirate=round(fcirate,.01);
        eximrate=round(eximrate,.01);
        collamt1=round(collamt1,.01);
        collamt2=round(collamt2,.01);
        collamt3=round(collamt3,.01);
        collamt4=round(collamt4,.01);
        collamt5=round(collamt5,.01);
        balance=round(balance,.01);
        pdbba=round(pdbba,.01);
        pdbbr=round(pdbbr,.01);
        brlcbal=round(brlcbal,.01);
        brulcbal=round(brulcbal,.01);
        keep acctno aano facility limit blrrate usancepd lccrate fccrate
             lcirate fcirate eximrate arcode expirydt collcd1 collcd2
             collcd3 collcd4 collcd5 collamt1 collamt2 collamt3 collamt4
             collamt5 balance pdbba pdbbr brlcbal brulcbal createdt updatedt;
run;

data BILLS.{output_names["combined"]};
  infile COMBINED firstobs=2;
  input @1   acctno   $11.
        @12  aano     $13.
        @25  facility $2.
        @27  usancepd 4.
        @31  lccrate  8.4
        @39  fccrate  8.4
        @47  lcirate  6.2
        @53  fcirate  6.2
        @59  balance  18.2;
        lccrate=round(lccrate,.0001);
        fccrate=round(fccrate,.0001);
        lcirate=round(lcirate,.01);
        fcirate=round(fcirate,.01);
        balance=round(balance,.01);
run;

data BILLS.{output_names["trans"]};
  infile TRANS firstobs=2;
  input @1   acctno   $11.
        @12  aano     $13.
        @25  billref  $14.
        @39  usancepd 4.
        @43  intrate  6.2
        @49  billamt  18.2
        @67  intaccr  18.2
        @85  iisaccr  18.2
        @103 maturity $8.;
        maturedt=input(maturity,ddmmyy8.);
        intrate=round(intrate,.01);
        billamt=round(billamt,.01);
        intaccr=round(intaccr,.01);
        iisaccr=round(iisaccr,.01);
        keep acctno aano billref usancepd intrate billamt intaccr iisaccr maturedt;
run;
"""
        )
        if "ERROR:" in result.get("LOG", ""):
            raise RuntimeError(result["LOG"])
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
    input_paths = {
        name: resolve_input(input_dir, filename)
        for name, filename in filenames.items()
    }
    return write_sas7bdat(input_paths, output_dir, suffix)


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
    parser.add_argument("--customer-file", default="BILLS_CUSTOMER.txt")
    parser.add_argument("--facility-file", default="BILLS_FACILITY.txt")
    parser.add_argument("--combined-file", default="BILLS_COMBINED.txt")
    parser.add_argument("--trans-file", default="BILLS_TRANS.txt")
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







  
                                                       The COMPARE Procedure                                                        
                                             Comparison of A.TRANS with A.TRANS_260623                                              
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                                         Data Set Summary                                                           
                                                                                                                                    
                                  Dataset                  Created          Modified  NVar    NObs                                  
                                                                                                                                    
                                  A.TRANS         24JUN26:10:18:51  24JUN26:10:18:51     9     127                                  
                                  A.TRANS_260623  24JUN26:14:08:11  24JUN26:14:08:11     9     127                                  
                                                                                                                                    
                                                                                                                                    
                                                         Variables Summary                                                          
                                                                                                                                    
                                               Number of Variables in Common: 9.                                                    


                                                                                                                                    
                                                                                                                                    
                                                        Observation Summary                                                         
                                                                                                                                    
                                                   Observation      Base  Compare                                                   
                                                                                                                                    
                                                   First Obs           1        1                                                   
                                                   First Unequal       2        2                                                   
                                                   Last  Unequal     124      124                                                   
                                                   Last  Obs         127      127                                                   
                                                                                                                                    
                                  Number of Observations in Common: 127.                                                            
                                  Total Number of Observations Read from A.TRANS: 127.                                              
                                  Total Number of Observations Read from A.TRANS_260623: 127.                                       
                                                                                                                                    
                                  Number of Observations with Some Compared Variables Unequal: 50.                                  
                                  Number of Observations with All Compared Variables Equal: 77.                                     
                                                                                                                                    
                                                                                                                                    
                                                     Values Comparison Summary                                                      
                                                                                                                                    
                                  Number of Variables Compared with All Observations Equal: 5.                                      
                                  Number of Variables Compared with Some Observations Unequal: 4.                                   
                                  Total Number of Values which Compare Unequal: 65.                                                 
                                  Maximum Difference: 9.3132E-10.                                                                   
                                                                                                                                    
                                                                                                                                    
                                                   Variables with Unequal Values                                                    
                                                                                                                                    
                                                Variable  Type  Len  Ndif   MaxDif                                                  
                                                                                                                                    
                                                INTRATE   NUM     8    13  444E-18                                                  
                                                BILLAMT   NUM     8    23  931E-12                                                  
                                                INTACCR   NUM     8    16  146E-13                                                  
                                                IISACCR   NUM     8    13  582E-13                                                  
                                                                                                                                    



                                                       The COMPARE Procedure                                                        
                                             Comparison of A.TRANS with A.TRANS_260623                                              
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                               Value Comparison Results for Variables                                               
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    INTRATE    intrate      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            28  ||     3.7000     3.7000  4.441E-16    1.2E-14                                      
                                            29  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            30  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            31  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            32  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            33  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            34  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            35  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            36  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            37  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            38  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            39  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            40  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                     __________________________________________________________                                     
                                                                                                                                    
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    BILLAMT    billamt      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                             2  ||    1253045    1253045  2.328E-10  1.858E-14                                      
                                             4  ||      35534      35534  7.276E-12  2.048E-14                                      
                                             8  ||    2293121    2293121  4.657E-10  2.031E-14                                      
                                            22  ||    2094712    2094712  2.328E-10  1.112E-14                                      
                                            23  ||      42502      42502  7.276E-12  1.712E-14                                      
                                            25  ||      42502      42502  7.276E-12  1.712E-14                                      
                                            27  ||      21248      21248  3.638E-12  1.712E-14                                      
                                            49  ||     250333     250333   2.91E-11  1.163E-14                                      
                                            70  ||      55556      55556  7.276E-12   1.31E-14                                      
                                            71  ||       7222       7222  9.095E-13  1.259E-14                                      
                                            73  ||       3556       3556  4.547E-13  1.279E-14                                      
                                            75  ||    1169313    1169313  2.328E-10  1.991E-14                                      
                                            76  ||     122550     122550  1.455E-11  1.187E-14                                      
                                            79  ||    1484524    1484524  2.328E-10  1.568E-14                                      
                                            84  ||    7940883    7940883  9.313E-10  1.173E-14                                      
                                            86  ||    3350689    3350689  4.657E-10   1.39E-14                                      
                                            95  ||     333956     333956  5.821E-11  1.743E-14                                      
                                            98  ||    1105561    1105561  2.328E-10  2.106E-14                                      
                                           108  ||      21136      21136  3.638E-12  1.721E-14                                      
                                           113  ||      21248      21248  3.638E-12  1.712E-14                                      
                                           116  ||     0.5500     0.5500   1.11E-16  2.019E-14                                      
                                           119  ||      19975      19975  3.638E-12  1.821E-14                                      
                                           124  ||      57235      57235  7.276E-12  1.271E-14                                      
                                     __________________________________________________________                                     


                                                       The COMPARE Procedure                                                        
                                             Comparison of A.TRANS with A.TRANS_260623                                              
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                               Value Comparison Results for Variables                                               
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    INTACCR    intaccr      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            61  ||       2887       2887  4.547E-13  1.575E-14                                      
                                            63  ||    88.3700    88.3700  1.421E-14  1.608E-14                                      
                                            66  ||    88.4200    88.4200  1.421E-14  1.607E-14                                      
                                            68  ||       2972       2972  4.547E-13   1.53E-14                                      
                                            69  ||   402.6800   402.6800  5.684E-14  1.412E-14                                      
                                            70  ||   892.5800   892.5800  1.137E-13  1.274E-14                                      
                                            71  ||   199.9300   199.9300  2.842E-14  1.422E-14                                      
                                            76  ||       3242       3242  4.547E-13  1.403E-14                                      
                                            77  ||      18768      18768  3.638E-12  1.938E-14                                      
                                            79  ||      35181      35181  7.276E-12  2.068E-14                                      
                                            80  ||      57500      57500  7.276E-12  1.265E-14                                      
                                            86  ||      80784      80784  1.455E-11  1.801E-14                                      
                                            99  ||       1130       1130  2.274E-13  2.012E-14                                      
                                           101  ||       6616       6616  9.095E-13  1.375E-14                                      
                                           104  ||       3312       3312  4.547E-13  1.373E-14                                      
                                           105  ||   767.6000   767.6000  1.137E-13  1.481E-14                                      
                                     __________________________________________________________                                     
                                                                                                                                    
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    IISACCR    iisaccr      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            61  ||       5084       5084  9.095E-13  1.789E-14                                      
                                            66  ||   147.0300   147.0300  2.842E-14  1.933E-14                                      
                                            67  ||   130.8300   130.8300  2.842E-14  2.172E-14                                      
                                            68  ||       4697       4697  9.095E-13  1.936E-14                                      
                                            70  ||       1399       1399  2.274E-13  1.626E-14                                      
                                            71  ||   384.8700   384.8700  5.684E-14  1.477E-14                                      
                                            75  ||      34455      34455  7.276E-12  2.112E-14                                      
                                            76  ||       3628       3628  4.547E-13  1.254E-14                                      
                                            78  ||     109976     109976  1.455E-11  1.323E-14                                      
                                            79  ||      78720      78720  1.455E-11  1.849E-14                                      
                                            80  ||     129326     129326  1.455E-11  1.125E-14                                      
                                            81  ||     303430     303430  5.821E-11  1.918E-14                                      
                                            86  ||     171711     171711   2.91E-11  1.695E-14                                      
                                     __________________________________________________________                                     




                                                       The COMPARE Procedure                                                        
                                          Comparison of A.FACILITY with A.FACILITY_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                                         Data Set Summary                                                           
                                                                                                                                    
                                Dataset                     Created          Modified  NVar    NObs                                 
                                                                                                                                    
                                A.FACILITY         24JUN26:10:18:51  24JUN26:10:18:51    30      63                                 
                                A.FACILITY_260623  24JUN26:14:08:11  24JUN26:14:08:11    30      63                                 
                                                                                                                                    
                                                                                                                                    
                                                         Variables Summary                                                          
                                                                                                                                    
                                               Number of Variables in Common: 30.                                                   


                                                                                                                                    
                                                                                                                                    
                                                        Observation Summary                                                         
                                                                                                                                    
                                                   Observation      Base  Compare                                                   
                                                                                                                                    
                                                   First Obs           1        1                                                   
                                                   First Unequal       7        7                                                   
                                                   Last  Unequal      61       61                                                   
                                                   Last  Obs          63       63                                                   
                                                                                                                                    
                                  Number of Observations in Common: 63.                                                             
                                  Total Number of Observations Read from A.FACILITY: 63.                                            
                                  Total Number of Observations Read from A.FACILITY_260623: 63.                                     
                                                                                                                                    
                                  Number of Observations with Some Compared Variables Unequal: 7.                                   
                                  Number of Observations with All Compared Variables Equal: 56.                                     
                                                                                                                                    
                                                                                                                                    
                                                     Values Comparison Summary                                                      
                                                                                                                                    
                                  Number of Variables Compared with All Observations Equal: 27.                                     
                                  Number of Variables Compared with Some Observations Unequal: 3.                                   
                                  Total Number of Values which Compare Unequal: 8.                                                  
                                  Maximum Difference: 1.8626E-09.                                                                   
                                                                                                                                    
                                                                                                                                    
                                                   Variables with Unequal Values                                                    
                                                                                                                                    
                                                Variable  Type  Len  Ndif   MaxDif                                                  
                                                                                                                                    
                                                BALANCE   NUM     8     6  1.86E-9                                                  
                                                BRLCBAL   NUM     8     1  1.86E-9                                                  
                                                BRULCBAL  NUM     8     1  233E-12                                                  
                                                                                                                                    



                                                       The COMPARE Procedure                                                        
                                          Comparison of A.FACILITY with A.FACILITY_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                               Value Comparison Results for Variables                                               
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    BALANCE    balance      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                             7  ||   10798494   10798494  1.8626E-9  1.725E-14                                      
                                             8  ||    7167282    7167282  9.313E-10  1.299E-14                                      
                                            12  ||      50534      50534  7.276E-12   1.44E-14                                      
                                            30  ||    1086262    1086262  2.328E-10  2.143E-14                                      
                                            54  ||      42502      42502  7.276E-12  1.712E-14                                      
                                            61  ||      42502      42502  7.276E-12  1.712E-14                                      
                                     __________________________________________________________                                     
                                                                                                                                    
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    BRLCBAL    brlcbal      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            45  ||   10736782   10736782  1.8626E-9  1.735E-14                                      
                                     __________________________________________________________                                     
                                                                                                                                    
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||   BRULCBAL   brulcbal      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            45  ||    1283641    1283641  2.328E-10  1.814E-14                                      
                                     __________________________________________________________                                     




                                                       The COMPARE Procedure                                                        
                                          Comparison of A.CUSTOMER with A.CUSTOMER_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                                         Data Set Summary                                                           
                                                                                                                                    
                                Dataset                     Created          Modified  NVar    NObs                                 
                                                                                                                                    
                                A.CUSTOMER         24JUN26:10:18:51  24JUN26:10:18:51    17      20                                 
                                A.CUSTOMER_260623  24JUN26:14:08:11  24JUN26:14:08:11    17      20                                 
                                                                                                                                    
                                                                                                                                    
                                                         Variables Summary                                                          
                                                                                                                                    
                                               Number of Variables in Common: 17.                                                   


                                                                                                                                    
                                                                                                                                    
                                                        Observation Summary                                                         
                                                                                                                                    
                                                   Observation      Base  Compare                                                   
                                                                                                                                    
                                                   First Obs           1        1                                                   
                                                   Last  Obs          20       20                                                   
                                                                                                                                    
                                  Number of Observations in Common: 20.                                                             
                                  Total Number of Observations Read from A.CUSTOMER: 20.                                            
                                  Total Number of Observations Read from A.CUSTOMER_260623: 20.                                     
                                                                                                                                    
                                  Number of Observations with Some Compared Variables Unequal: 0.                                   
                                  Number of Observations with All Compared Variables Equal: 20.                                     
                                                                                                                                    
                                  NOTE: No unequal values were found. All values compared are exactly equal.                        
                                                                                                                                    




                                                       The COMPARE Procedure                                                        
                                           Comparison of A.COMBINED with A.COMBINE_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                                         Data Set Summary                                                           
                                                                                                                                    
                                 Dataset                    Created          Modified  NVar    NObs                                 
                                                                                                                                    
                                 A.COMBINED        24JUN26:10:18:51  24JUN26:10:18:51     9      53                                 
                                 A.COMBINE_260623  24JUN26:14:08:11  24JUN26:14:08:11     9      53                                 
                                                                                                                                    
                                                                                                                                    
                                                         Variables Summary                                                          
                                                                                                                                    
                                               Number of Variables in Common: 9.                                                    


                                                                                                                                    
                                                                                                                                    
                                                        Observation Summary                                                         
                                                                                                                                    
                                                   Observation      Base  Compare                                                   
                                                                                                                                    
                                                   First Obs           1        1                                                   
                                                   First Unequal      17       17                                                   
                                                   Last  Unequal      51       51                                                   
                                                   Last  Obs          53       53                                                   
                                                                                                                                    
                                  Number of Observations in Common: 53.                                                             
                                  Total Number of Observations Read from A.COMBINED: 53.                                            
                                  Total Number of Observations Read from A.COMBINE_260623: 53.                                      
                                                                                                                                    
                                  Number of Observations with Some Compared Variables Unequal: 5.                                   
                                  Number of Observations with All Compared Variables Equal: 48.                                     
                                                                                                                                    
                                                                                                                                    
                                                     Values Comparison Summary                                                      
                                                                                                                                    
                                  Number of Variables Compared with All Observations Equal: 8.                                      
                                  Number of Variables Compared with Some Observations Unequal: 1.                                   
                                  Total Number of Values which Compare Unequal: 5.                                                  
                                  Maximum Difference: 1.8626E-09.                                                                   
                                                                                                                                    
                                                                                                                                    
                                                   Variables with Unequal Values                                                    
                                                                                                                                    
                                                Variable  Type  Len  Ndif   MaxDif                                                  
                                                                                                                                    
                                                BALANCE   NUM     8     5  1.86E-9                                                  
                                                                                                                                    



                                                       The COMPARE Procedure                                                        
                                           Comparison of A.COMBINED with A.COMBINE_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                               Value Comparison Results for Variables                                               
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    BALANCE    balance      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            17  ||    1253045    1253045  2.328E-10  1.858E-14                                      
                                            23  ||   15547147   15547147  1.8626E-9  1.198E-14                                      
                                            27  ||     0.0100     0.0100  1.735E-18  1.735E-14                                      
                                            33  ||    2094712    2094712  2.328E-10  1.112E-14                                      
                                            51  ||      58556      58556  7.276E-12  1.243E-14                                      
                                     __________________________________________________________                   



















#!/usr/bin/env python3
"""Python replacement for the EIBWBILE JCL/SAS job.

The source files are fixed-width text files. The program reads directly from
the input directory and writes dated SAS7BDAT datasets directly to the output
directory. Supply --input-root/--output-root to override the project defaults
when needed.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
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
    """Return YYMMDD suffix for the previous day's output datasets."""
    return (run_date - timedelta(days=1)).strftime("%y%m%d")


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


def sas_quote(path: Path) -> str:
    return str(path.resolve()).replace("'", "''")


def write_sas7bdat(input_paths: dict[str, Path], output_dir: Path, suffix: str) -> dict[str, Path]:
    """Write the converted BILLS datasets as SAS7BDAT files.

    Let SAS read the fixed-width text directly so numeric informats match the
    original job exactly under PROC COMPARE METHOD=EXACT.
    """
    try:
        import saspy
    except ImportError as error:
        raise RuntimeError(
            "Writing SAS7BDAT requires saspy and a configured SAS runtime"
        ) from error

    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir.resolve()
    output_names = {
        "customer": f"customer_{suffix}",
        "facility": f"facility_{suffix}",
        "combined": f"combine_{suffix}",
        "trans": f"trans_{suffix}",
        "reptdate": f"reptdate_{suffix}",
    }

    sas = saspy.SASsession()
    try:
        result = sas.submit(
            f"""
options yearcutoff=1950 nocenter;
libname BILLS '{sas_quote(output_dir)}';
filename CUSTOMER '{sas_quote(input_paths["customer"])}';
filename FACILITY '{sas_quote(input_paths["facility"])}';
filename COMBINED '{sas_quote(input_paths["combined"])}';
filename TRANS    '{sas_quote(input_paths["trans"])}';

data BILLS.{output_names["reptdate"]};
  keep reptdate extdate;
  infile CUSTOMER missover obs=1;
  input @1 extdate $8.;
  reptdate=input(extdate,ddmmyy8.);
run;

data BILLS.{output_names["customer"]};
  infile CUSTOMER firstobs=2;
  input @1   acctno   $11.
        @12  name     $40.
        @52  branch   $3.
        @55  sector   $4.
        @59  custcode $3.
        @62  product  $3.
        @65  resident $1.
        @66  malaysn  $1.
        @67  small    $1.
        @68  status   $1.
        @69  custtype $1.
        @70  orgtype  $1.
        @71  corpcode $1.
        @72  race     $1.
        @73  blrcode  $1.
        @74  legalcd  $2.
        @76  state    $2.;
run;

data BILLS.{output_names["facility"]};
  infile FACILITY firstobs=2;
  input @1   acctno   $11.
        @12  aano     $13.
        @25  facility $2.
        @27  limit    18.2
        @45  blrrate  6.2
        @51  usancepd 4.
        @55  lccrate  8.4
        @63  fccrate  8.4
        @71  lcirate  6.2
        @77  fcirate  6.2
        @83  eximrate 6.2
        @89  arcode   $1.
        @90  expiry   $8.
        @98  collcd1  $3.
        @101 collcd2  $3.
        @104 collcd3  $3.
        @107 collcd4  $3.
        @110 collcd5  $3.
        @113 collamt1 18.2
        @131 collamt2 18.2
        @149 collamt3 18.2
        @167 collamt4 18.2
        @185 collamt5 18.2
        @203 balance  18.2
        @221 pdbba    18.2
        @239 pdbbr    18.2
        @257 brlcbal  18.2
        @275 brulcbal 18.2
        @293 create   $8.
        @301 update   $8.;
        expirydt=input(expiry,ddmmyy8.);
        createdt=input(create,ddmmyy8.);
        updatedt=input(update,ddmmyy8.);
        keep acctno aano facility limit blrrate usancepd lccrate fccrate
             lcirate fcirate eximrate arcode expirydt collcd1 collcd2
             collcd3 collcd4 collcd5 collamt1 collamt2 collamt3 collamt4
             collamt5 balance pdbba pdbbr brlcbal brulcbal createdt updatedt;
run;

data BILLS.{output_names["combined"]};
  infile COMBINED firstobs=2;
  input @1   acctno   $11.
        @12  aano     $13.
        @25  facility $2.
        @27  usancepd 4.
        @31  lccrate  8.4
        @39  fccrate  8.4
        @47  lcirate  6.2
        @53  fcirate  6.2
        @59  balance  18.2;
run;

data BILLS.{output_names["trans"]};
  infile TRANS firstobs=2;
  input @1   acctno   $11.
        @12  aano     $13.
        @25  billref  $14.
        @39  usancepd 4.
        @43  intrate  6.2
        @49  billamt  18.2
        @67  intaccr  18.2
        @85  iisaccr  18.2
        @103 maturity $8.;
        maturedt=input(maturity,ddmmyy8.);
        keep acctno aano billref usancepd intrate billamt intaccr iisaccr maturedt;
run;
"""
        )
        if "ERROR:" in result.get("LOG", ""):
            raise RuntimeError(result["LOG"])
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
    input_paths = {
        name: resolve_input(input_dir, filename)
        for name, filename in filenames.items()
    }
    return write_sas7bdat(input_paths, output_dir, suffix)


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
    parser.add_argument("--customer-file", default="BILLS_CUSTOMER.txt")
    parser.add_argument("--facility-file", default="BILLS_FACILITY.txt")
    parser.add_argument("--combined-file", default="BILLS_COMBINED.txt")
    parser.add_argument("--trans-file", default="BILLS_TRANS.txt")
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





























                                                       The COMPARE Procedure                                                        
                                             Comparison of A.TRANS with A.TRANS_260623                                              
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                                         Data Set Summary                                                           
                                                                                                                                    
                                  Dataset                  Created          Modified  NVar    NObs                                  
                                                                                                                                    
                                  A.TRANS         24JUN26:10:18:51  24JUN26:10:18:51     9     127                                  
                                  A.TRANS_260623  24JUN26:10:59:50  24JUN26:10:59:50     9     127                                  
                                                                                                                                    
                                                                                                                                    
                                                         Variables Summary                                                          
                                                                                                                                    
                                         Number of Variables in Common: 9.                                                          
                                         Number of Variables with Differing Attributes: 1.                                          


                                                                                                                                    
                                                                                                                                    
                                       Listing of Common Variables with Differing Attributes                                        
                                                                                                                                    
                                           Variable  Dataset         Type  Length  Format                                           
                                                                                                                                    
                                           MATUREDT  A.TRANS         Num        8                                                   
                                                     A.TRANS_260623  Num        8  DATE9.                                           


                                                                                                                                    
                                                                                                                                    
                                                        Observation Summary                                                         
                                                                                                                                    
                                                   Observation      Base  Compare                                                   
                                                                                                                                    
                                                   First Obs           1        1                                                   
                                                   First Unequal       2        2                                                   
                                                   Last  Unequal     124      124                                                   
                                                   Last  Obs         127      127                                                   
                                                                                                                                    
                                  Number of Observations in Common: 127.                                                            
                                  Total Number of Observations Read from A.TRANS: 127.                                              
                                  Total Number of Observations Read from A.TRANS_260623: 127.                                       
                                                                                                                                    
                                  Number of Observations with Some Compared Variables Unequal: 50.                                  
                                  Number of Observations with All Compared Variables Equal: 77.                                     
                                                                                                                                    
                                                                                                                                    
                                                     Values Comparison Summary                                                      
                                                                                                                                    
                                  Number of Variables Compared with All Observations Equal: 5.                                      
                                  Number of Variables Compared with Some Observations Unequal: 4.                                   
                                  Total Number of Values which Compare Unequal: 65.                                                 
                                  Maximum Difference: 9.3132E-10.                                                                   
                                                                                                                                    


                                                       The COMPARE Procedure                                                        
                                             Comparison of A.TRANS with A.TRANS_260623                                              
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                                   Variables with Unequal Values                                                    
                                                                                                                                    
                                                Variable  Type  Len  Ndif   MaxDif                                                  
                                                                                                                                    
                                                INTRATE   NUM     8    13  444E-18                                                  
                                                BILLAMT   NUM     8    23  931E-12                                                  
                                                INTACCR   NUM     8    16  146E-13                                                  
                                                IISACCR   NUM     8    13  582E-13                                                  
                                                                                                                                    


                                                                                                                                    
                                                                                                                                    
                                               Value Comparison Results for Variables                                               
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    INTRATE    INTRATE      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            28  ||     3.7000     3.7000  4.441E-16    1.2E-14                                      
                                            29  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            30  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            31  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            32  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            33  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            34  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            35  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            36  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            37  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            38  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            39  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                            40  ||     3.6000     3.6000  4.441E-16  1.234E-14                                      
                                     __________________________________________________________                                     
                                                                                                                                    
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    BILLAMT    BILLAMT      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                             2  ||    1253045    1253045  2.328E-10  1.858E-14                                      
                                             4  ||      35534      35534  7.276E-12  2.048E-14                                      
                                             8  ||    2293121    2293121  4.657E-10  2.031E-14                                      
                                            22  ||    2094712    2094712  2.328E-10  1.112E-14                                      
                                            23  ||      42502      42502  7.276E-12  1.712E-14                                      
                                            25  ||      42502      42502  7.276E-12  1.712E-14                                      
                                            27  ||      21248      21248  3.638E-12  1.712E-14                                      
                                            49  ||     250333     250333   2.91E-11  1.163E-14                                      
                                            70  ||      55556      55556  7.276E-12   1.31E-14                                      
                                            71  ||       7222       7222  9.095E-13  1.259E-14                                      
                                            73  ||       3556       3556  4.547E-13  1.279E-14                                      
                                            75  ||    1169313    1169313  2.328E-10  1.991E-14                                      
                                            76  ||     122550     122550  1.455E-11  1.187E-14                                      


                                                       The COMPARE Procedure                                                        
                                             Comparison of A.TRANS with A.TRANS_260623                                              
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                               Value Comparison Results for Variables                                               
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    BILLAMT    BILLAMT      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            79  ||    1484524    1484524  2.328E-10  1.568E-14                                      
                                            84  ||    7940883    7940883  9.313E-10  1.173E-14                                      
                                            86  ||    3350689    3350689  4.657E-10   1.39E-14                                      
                                            95  ||     333956     333956  5.821E-11  1.743E-14                                      
                                            98  ||    1105561    1105561  2.328E-10  2.106E-14                                      
                                           108  ||      21136      21136  3.638E-12  1.721E-14                                      
                                           113  ||      21248      21248  3.638E-12  1.712E-14                                      
                                           116  ||     0.5500     0.5500   1.11E-16  2.019E-14                                      
                                           119  ||      19975      19975  3.638E-12  1.821E-14                                      
                                           124  ||      57235      57235  7.276E-12  1.271E-14                                      
                                     __________________________________________________________                                     
                                                                                                                                    
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    INTACCR    INTACCR      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            61  ||       2887       2887  4.547E-13  1.575E-14                                      
                                            63  ||    88.3700    88.3700  1.421E-14  1.608E-14                                      
                                            66  ||    88.4200    88.4200  1.421E-14  1.607E-14                                      
                                            68  ||       2972       2972  4.547E-13   1.53E-14                                      
                                            69  ||   402.6800   402.6800  5.684E-14  1.412E-14                                      
                                            70  ||   892.5800   892.5800  1.137E-13  1.274E-14                                      
                                            71  ||   199.9300   199.9300  2.842E-14  1.422E-14                                      
                                            76  ||       3242       3242  4.547E-13  1.403E-14                                      
                                            77  ||      18768      18768  3.638E-12  1.938E-14                                      
                                            79  ||      35181      35181  7.276E-12  2.068E-14                                      
                                            80  ||      57500      57500  7.276E-12  1.265E-14                                      
                                            86  ||      80784      80784  1.455E-11  1.801E-14                                      
                                            99  ||       1130       1130  2.274E-13  2.012E-14                                      
                                           101  ||       6616       6616  9.095E-13  1.375E-14                                      
                                           104  ||       3312       3312  4.547E-13  1.373E-14                                      
                                           105  ||   767.6000   767.6000  1.137E-13  1.481E-14                                      
                                     __________________________________________________________                                     


                                                       The COMPARE Procedure                                                        
                                             Comparison of A.TRANS with A.TRANS_260623                                              
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                               Value Comparison Results for Variables                                               
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    IISACCR    IISACCR      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            61  ||       5084       5084  9.095E-13  1.789E-14                                      
                                            66  ||   147.0300   147.0300  2.842E-14  1.933E-14                                      
                                            67  ||   130.8300   130.8300  2.842E-14  2.172E-14                                      
                                            68  ||       4697       4697  9.095E-13  1.936E-14                                      
                                            70  ||       1399       1399  2.274E-13  1.626E-14                                      
                                            71  ||   384.8700   384.8700  5.684E-14  1.477E-14                                      
                                            75  ||      34455      34455  7.276E-12  2.112E-14                                      
                                            76  ||       3628       3628  4.547E-13  1.254E-14                                      
                                            78  ||     109976     109976  1.455E-11  1.323E-14                                      
                                            79  ||      78720      78720  1.455E-11  1.849E-14                                      
                                            80  ||     129326     129326  1.455E-11  1.125E-14                                      
                                            81  ||     303430     303430  5.821E-11  1.918E-14                                      
                                            86  ||     171711     171711   2.91E-11  1.695E-14                                      
                                     __________________________________________________________                                     




                                                       The COMPARE Procedure                                                        
                                          Comparison of A.FACILITY with A.FACILITY_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                                         Data Set Summary                                                           
                                                                                                                                    
                                Dataset                     Created          Modified  NVar    NObs                                 
                                                                                                                                    
                                A.FACILITY         24JUN26:10:18:51  24JUN26:10:18:51    30      63                                 
                                A.FACILITY_260623  24JUN26:10:59:50  24JUN26:10:59:50    30      63                                 
                                                                                                                                    
                                                                                                                                    
                                                         Variables Summary                                                          
                                                                                                                                    
                                         Number of Variables in Common: 30.                                                         
                                         Number of Variables with Differing Attributes: 3.                                          


                                                                                                                                    
                                                                                                                                    
                                       Listing of Common Variables with Differing Attributes                                        
                                                                                                                                    
                                         Variable  Dataset            Type  Length  Format                                          
                                                                                                                                    
                                         EXPIRYDT  A.FACILITY         Num        8                                                  
                                                   A.FACILITY_260623  Num        8  DATE9.                                          
                                         CREATEDT  A.FACILITY         Num        8                                                  
                                                   A.FACILITY_260623  Num        8  DATE9.                                          
                                         UPDATEDT  A.FACILITY         Num        8                                                  
                                                   A.FACILITY_260623  Num        8  DATE9.                                          


                                                                                                                                    
                                                                                                                                    
                                                        Observation Summary                                                         
                                                                                                                                    
                                                   Observation      Base  Compare                                                   
                                                                                                                                    
                                                   First Obs           1        1                                                   
                                                   First Unequal       7        7                                                   
                                                   Last  Unequal      61       61                                                   
                                                   Last  Obs          63       63                                                   
                                                                                                                                    
                                  Number of Observations in Common: 63.                                                             
                                  Total Number of Observations Read from A.FACILITY: 63.                                            
                                  Total Number of Observations Read from A.FACILITY_260623: 63.                                     
                                                                                                                                    
                                  Number of Observations with Some Compared Variables Unequal: 7.                                   
                                  Number of Observations with All Compared Variables Equal: 56.                                     
                                                                                                                                    
                                                                                                                                    
                                                     Values Comparison Summary                                                      
                                                                                                                                    
                                  Number of Variables Compared with All Observations Equal: 27.                                     
                                  Number of Variables Compared with Some Observations Unequal: 3.                                   
                                  Total Number of Values which Compare Unequal: 8.                                                  
                                  Maximum Difference: 1.8626E-09.                                                                   
                                                                                                                                    


                                                       The COMPARE Procedure                                                        
                                          Comparison of A.FACILITY with A.FACILITY_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                                   Variables with Unequal Values                                                    
                                                                                                                                    
                                                Variable  Type  Len  Ndif   MaxDif                                                  
                                                                                                                                    
                                                BALANCE   NUM     8     6  1.86E-9                                                  
                                                BRLCBAL   NUM     8     1  1.86E-9                                                  
                                                BRULCBAL  NUM     8     1  233E-12                                                  
                                                                                                                                    


                                                                                                                                    
                                                                                                                                    
                                               Value Comparison Results for Variables                                               
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    BALANCE    BALANCE      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                             7  ||   10798494   10798494  1.8626E-9  1.725E-14                                      
                                             8  ||    7167282    7167282  9.313E-10  1.299E-14                                      
                                            12  ||      50534      50534  7.276E-12   1.44E-14                                      
                                            30  ||    1086262    1086262  2.328E-10  2.143E-14                                      
                                            54  ||      42502      42502  7.276E-12  1.712E-14                                      
                                            61  ||      42502      42502  7.276E-12  1.712E-14                                      
                                     __________________________________________________________                                     
                                                                                                                                    
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    BRLCBAL    BRLCBAL      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            45  ||   10736782   10736782  1.8626E-9  1.735E-14                                      
                                     __________________________________________________________                                     
                                                                                                                                    
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||   BRULCBAL   BRULCBAL      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            45  ||    1283641    1283641  2.328E-10  1.814E-14                                      
                                     __________________________________________________________                                     




                                                       The COMPARE Procedure                                                        
                                          Comparison of A.CUSTOMER with A.CUSTOMER_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                                         Data Set Summary                                                           
                                                                                                                                    
                                Dataset                     Created          Modified  NVar    NObs                                 
                                                                                                                                    
                                A.CUSTOMER         24JUN26:10:18:51  24JUN26:10:18:51    17      20                                 
                                A.CUSTOMER_260623  24JUN26:10:59:50  24JUN26:10:59:50    17      20                                 
                                                                                                                                    
                                                                                                                                    
                                                         Variables Summary                                                          
                                                                                                                                    
                                               Number of Variables in Common: 17.                                                   


                                                                                                                                    
                                                                                                                                    
                                                        Observation Summary                                                         
                                                                                                                                    
                                                   Observation      Base  Compare                                                   
                                                                                                                                    
                                                   First Obs           1        1                                                   
                                                   Last  Obs          20       20                                                   
                                                                                                                                    
                                  Number of Observations in Common: 20.                                                             
                                  Total Number of Observations Read from A.CUSTOMER: 20.                                            
                                  Total Number of Observations Read from A.CUSTOMER_260623: 20.                                     
                                                                                                                                    
                                  Number of Observations with Some Compared Variables Unequal: 0.                                   
                                  Number of Observations with All Compared Variables Equal: 20.                                     
                                                                                                                                    
                                  NOTE: No unequal values were found. All values compared are exactly equal.                        
                                                                                                                                    




                                                       The COMPARE Procedure                                                        
                                           Comparison of A.COMBINED with A.COMBINE_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                                         Data Set Summary                                                           
                                                                                                                                    
                                 Dataset                    Created          Modified  NVar    NObs                                 
                                                                                                                                    
                                 A.COMBINED        24JUN26:10:18:51  24JUN26:10:18:51     9      53                                 
                                 A.COMBINE_260623  24JUN26:10:59:50  24JUN26:10:59:50     9      53                                 
                                                                                                                                    
                                                                                                                                    
                                                         Variables Summary                                                          
                                                                                                                                    
                                               Number of Variables in Common: 9.                                                    


                                                                                                                                    
                                                                                                                                    
                                                        Observation Summary                                                         
                                                                                                                                    
                                                   Observation      Base  Compare                                                   
                                                                                                                                    
                                                   First Obs           1        1                                                   
                                                   First Unequal      17       17                                                   
                                                   Last  Unequal      51       51                                                   
                                                   Last  Obs          53       53                                                   
                                                                                                                                    
                                  Number of Observations in Common: 53.                                                             
                                  Total Number of Observations Read from A.COMBINED: 53.                                            
                                  Total Number of Observations Read from A.COMBINE_260623: 53.                                      
                                                                                                                                    
                                  Number of Observations with Some Compared Variables Unequal: 5.                                   
                                  Number of Observations with All Compared Variables Equal: 48.                                     
                                                                                                                                    
                                                                                                                                    
                                                     Values Comparison Summary                                                      
                                                                                                                                    
                                  Number of Variables Compared with All Observations Equal: 8.                                      
                                  Number of Variables Compared with Some Observations Unequal: 1.                                   
                                  Total Number of Values which Compare Unequal: 5.                                                  
                                  Maximum Difference: 1.8626E-09.                                                                   
                                                                                                                                    
                                                                                                                                    
                                                   Variables with Unequal Values                                                    
                                                                                                                                    
                                                Variable  Type  Len  Ndif   MaxDif                                                  
                                                                                                                                    
                                                BALANCE   NUM     8     5  1.86E-9                                                  
                                                                                                                                    



                                                       The COMPARE Procedure                                                        
                                           Comparison of A.COMBINED with A.COMBINE_260623                                           
                                                           (Method=EXACT)                                                           
                                                                                                                                    
                                               Value Comparison Results for Variables                                               
                                                                                                                                    
                                     __________________________________________________________                                     
                                                ||       Base    Compare                                                            
                                            Obs ||    BALANCE    BALANCE      Diff.     % Diff                                      
                                      ________  ||  _________  _________  _________  _________                                      
                                                ||                                                                                  
                                            17  ||    1253045    1253045  2.328E-10  1.858E-14                                      
                                            23  ||   15547147   15547147  1.8626E-9  1.198E-14                                      
                                            27  ||     0.0100     0.0100  1.735E-18  1.735E-14                                      
                                            33  ||    2094712    2094712  2.328E-10  1.112E-14                                      
                                            51  ||      58556      58556  7.276E-12  1.243E-14                                      
                                     __________________________________________________________                                     









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
        "customer": f"customer_{suffix}",
        "facility": f"facility_{suffix}",
        "combined": f"combine_{suffix}",
        "trans": f"trans_{suffix}",
        "reptdate": f"reptdate_{suffix}",
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
    parser.add_argument("--customer-file", default="BILLS_CUSTOMER.txt")
    parser.add_argument("--facility-file", default="BILLS_FACILITY.txt")
    parser.add_argument("--combined-file", default="BILLS_COMBINED.txt")
    parser.add_argument("--trans-file", default="BILLS_TRANS.txt")
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














Traceback (most recent call last):
  File "/sas/python/virt_edw/Data_Warehouse/MIS/XMIS/EIBWBILE_PAS.py", line 470, in <module>
    raise SystemExit(main())
  File "/sas/python/virt_edw/Data_Warehouse/MIS/XMIS/EIBWBILE_PAS.py", line 454, in main
    destinations = convert(args.input_root, args.output_root, args.encoding, filenames, suffix)
  File "/sas/python/virt_edw/Data_Warehouse/MIS/XMIS/EIBWBILE_PAS.py", line 414, in convert
    return write_sas7bdat(rows, output_dir, suffix)
  File "/sas/python/virt_edw/Data_Warehouse/MIS/XMIS/EIBWBILE_PAS.py", line 399, in write_sas7bdat
    raise RuntimeError(
RuntimeError: SAS did not create the expected file(s): /sas/python/virt_edw/Data_Warehouse/MIS/XMIS/input/prod/output/CUSTOMER_260624.sas7bdat, /sas/python/virt_edw/Data_Warehouse/MIS/XMIS/input/prod/output/FACILITY_260624.sas7bdat, /sas/python/virt_edw/Data_Warehouse/MIS/XMIS/input/prod/output/COMBINE_260624.sas7bdat, /sas/python/virt_edw/Data_Warehouse/MIS/XMIS/input/prod/output/TRANS_260624.sas7bdat, /sas/python/virt_edw/Data_Warehouse/MIS/XMIS/input/prod/output/REPTDATE_260624.sas7bdat




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
