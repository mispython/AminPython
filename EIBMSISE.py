#!/usr/bin/env python3
"""Generate the EIBMSISD card-acquisition report from fixed-width text files."""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


DEFAULT_INPUT_DIR = Path("/Data_Warehouse/MIS/XMIS/input/prod")
DEFAULT_OUTPUT_DIR = DEFAULT_INPUT_DIR / "output"


def field(line: str, start: int, length: int) -> str:
    """Read a 1-based fixed-width field, matching SAS column input."""
    return line[start - 1 : start - 1 + length].strip()


def number(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


@dataclass
class Totals:
    cmthrc: int = 0
    dmthrc: int = 0
    cyrrc: int = 0
    dyrrc: int = 0
    cmthap: int = 0
    dmthap: int = 0
    cyrap: int = 0
    dyrap: int = 0

    def add(self, other: "Totals") -> None:
        for name in self.__dataclass_fields__:
            setattr(self, name, getattr(self, name) + getattr(other, name))


def read_staff_file(path: Path, branch_kind: str) -> dict[int, int]:
    result: dict[int, int] = {}
    with path.open("r", encoding="latin-1") as source:
        for line in source:
            staff = number(field(line, 5, 5))
            if staff is None:
                continue
            if branch_kind == "branch":
                branch = number(field(line, 69, 3))
                if branch is None or not 2 <= branch <= 300:
                    continue
            elif branch_kind == "regional":
                branch = 888
            else:
                branch = 999
            result[staff] = branch
    return result


def load_staff(input_dir: Path) -> dict[int, int]:
    # Same ordering as SAS SET HRBR HRHO HRRG; later duplicate staff IDs win.
    result: dict[int, int] = {}
    result.update(read_staff_file(input_dir / "BRSTAF.TXT", "branch"))
    result.update(read_staff_file(input_dir / "HOSTAF.TXT", "head_office"))
    result.update(read_staff_file(input_dir / "RGSTAF.TXT", "regional"))
    return result


def load_activity(
    path: Path, staff_branches: dict[int, int], report_end: date
) -> dict[tuple[int, int], Totals]:
    grouped: dict[tuple[int, int], Totals] = defaultdict(Totals)
    report_yy = report_end.year % 100
    report_month = report_end.month

    with path.open("r", encoding="latin-1") as source:
        for line in source:
            apyy = number(field(line, 28, 2))
            if apyy != report_yy:
                continue

            staff = number(field(line, 38, 5))
            cards = number(field(line, 34, 3))
            if staff is None or cards is None or staff not in staff_branches:
                continue

            status = field(line, 10, 1)
            receive_month = number(field(line, 16, 2))
            approval_month = number(field(line, 25, 2))
            card_type = field(line, 44, 2)
            total = grouped[(staff_branches[staff], staff)]

            if card_type == "CR":
                total.cyrrc += cards
                if receive_month == report_month:
                    total.cmthrc += cards
                if status == "A":
                    total.cyrap += cards
                    if approval_month == report_month:
                        total.cmthap += cards
            elif card_type == "DB":
                total.dyrrc += cards
                if receive_month == report_month:
                    total.dmthrc += cards
                if status == "A":
                    total.dyrap += cards
                    if approval_month == report_month:
                        total.dmthap += cards

    return grouped


def sas_worddate(d: date) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def header(branch: int, audience: str, start: date, end: date) -> list[str]:
    month_year = end.strftime("%b%Y").upper()
    line1 = "PUBLIC BANK BERHAD - CARD ACQUISITION"
    line1 += " " * max(1, 42 - len(line1))
    line1 += f"({sas_worddate(start)} TO {sas_worddate(end)})"
    return [
        line1,
        f"REPORT NAME: DCPD/SGC2002/004 ({audience})",
        f"REPORT ID  : EIBMSISD       {end.strftime('%d/%m/%Y')}",
        ".",
        f"BRANCH CODE= {branch:03d}",
        " " * 11 + "------- APPLICATION RECEIVED ---------" + " " * 2
        + "------- APPLICATION APPROVED ---------",
        " " * 12 + f"MONTH OF {month_year:<7}" + " " * 8 + "YEAR-TO-DATE"
        + " " * 6 + f"MONTH OF {month_year:<7}" + " " * 8 + "YEAR-TO-DATE",
        " " * 3 + "STAFF" + " " * 4
        + "CRE CARD  DEB CARD  CRE CARD  DEB CARD" + " " * 2
        + "CRE CARD  DEB CARD  CRE CARD  DEB CARD",
        " " * 3 + "-----" + " " * 4
        + "------------------  ------------------" + " " * 2
        + "------------------  ------------------",
    ]


def detail_line(staff: int, t: Totals) -> str:
    return (
        f"  {staff:5d}" + " " * 7
        + f"{t.cmthrc:5d}" + " " * 5 + f"{t.dmthrc:5d}"
        + " " * 5 + f"{t.cyrrc:5d}" + " " * 5 + f"{t.dyrrc:5d}"
        + " " * 5 + f"{t.cmthap:5d}" + " " * 5 + f"{t.dmthap:5d}"
        + " " * 5 + f"{t.cyrap:5d}" + " " * 5 + f"{t.dyrap:5d}"
    )


def total_line(t: Totals) -> str:
    return (
        "  TOTAL =" + " " * 4
        + f"{t.cmthrc:6d}" + " " * 4 + f"{t.dmthrc:6d}"
        + " " * 4 + f"{t.cyrrc:6d}" + " " * 4 + f"{t.dyrrc:6d}"
        + " " * 4 + f"{t.cmthap:6d}" + " " * 4 + f"{t.dmthap:6d}"
        + " " * 4 + f"{t.cyrap:6d}" + " " * 4 + f"{t.dyrap:6d}"
    )


def render_report(grouped: dict[tuple[int, int], Totals], start: date, end: date) -> str:
    sections = [
        (lambda b: b not in (888, 999), "FOR BRANCHES"),
        (lambda b: b == 888, "FOR SME/PFE"),
        (lambda b: b == 999, "FOR HEAD OFF"),
    ]
    pages: list[str] = []
    branches = sorted({branch for branch, _ in grouped})

    for include, audience in sections:
        for branch in branches:
            if not include(branch):
                continue
            rows = sorted(
                ((staff, totals) for (b, staff), totals in grouped.items() if b == branch),
                key=lambda row: row[0],
            )
            grand = Totals()
            page = header(branch, audience, start, end)
            for staff, totals in rows:
                page.append(detail_line(staff, totals))
                grand.add(totals)
            page.extend(["  " + "-" * 87, total_line(grand), "  " + "-" * 87])
            pages.append("\n".join(page))

    return "\f\n".join(pages) + ("\n" if pages else "")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--run-date",
        type=lambda value: datetime.strptime(value, "%Y-%m-%d").date(),
        default=date.today(),
        help="Override today's date for reruns/testing (YYYY-MM-DD).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    # Always anchor to the first day of the run month, regardless of actual run day.
    month_anchor = args.run_date.replace(day=1)
    report_end = month_anchor - timedelta(days=1)
    report_start = report_end.replace(month=1, day=1)

    staff_branches = load_staff(args.input_dir)
    grouped = load_activity(args.input_dir / "EIBMSISD.txt", staff_branches, report_end)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / "EIBMSISD.txt"
    output_path.write_text(
        render_report(grouped, report_start, report_end), encoding="latin-1", newline="\n"
    )
    print(f"Created {output_path}")


if __name__ == "__main__":
    main()



































//EIBMSISE JOB MIS,EIBMSISD,CLASS=A,NOTIFY=&SYSUID,MSGCLASS=X
//*
//* READ FROM ROSHIDAH'S FILE
//*
//DELETE   EXEC PGM=IEFBR14
//DD1      DD DSN=SAP.PBB.SISCAMP.COLD,

//            DISP=(MOD,DELETE,DELETE),UNIT=SYSDA,
//            SPACE=(CYL,1,RLSE)
//*
//CREATE   EXEC PGM=IEFBR14
//DD1      DD DSN=SAP.PBB.SISCAMP.COLD,
//            DISP=(NEW,CATLG,DELETE),
//            DCB=(RECFM=FBA,LRECL=136,BLKSIZE=0,DSORG=PS),
//            SPACE=(CYL,(10,2),RLSE),UNIT=SYSDA
//*
//EIBMSISD EXEC SAS609
//MNITB     DD DSN=SAP.PBB.MNITB(0),DISP=SHR
//PGM       DD DSN=SAP.BNM.PROGRAM,DISP=SHR
//SGMF      DD DSN=SAP.PBB.EIBMSISD.TEXT(0),DISP=SHR
//HRBR      DD DSN=HRP2.FLAT.STAFF.INCTIVE.BR,DISP=SHR
//HRHO      DD DSN=HRP2.FLAT.STAFF.INCTIVE.HO,DISP=SHR
//HRRG      DD DSN=HRP2.FLAT.STAFF.INCTIVE.REGOFF,DISP=SHR
//SASLIST   DD DSN=SAP.PBB.SISCAMP.COLD,DISP=MOD
//SYSIN     DD *

OPTION NOCENTER NODATE NONUMBER;
*;
DATA REPTDATE;
   REPTDATE=INPUT('01'||PUT(MONTH(TODAY()), Z2.)||
            PUT(YEAR(TODAY()), 4.), DDMMYY8.)-1;
   CYY=YEAR(REPTDATE);
   STRTDATE=MDY(01,01,CYY);
   CALL SYMPUT('SDATE',PUT(STRTDATE,WORDDATX.));
   CALL SYMPUT('RDATE',PUT(REPTDATE,WORDDATX.));
   CALL SYMPUT('RMM',PUT(REPTDATE,MONTH2.));
   CALL SYMPUT('RMON',PUT(REPTDATE,MONYY7.));
   CALL SYMPUT('RYY',PUT(REPTDATE,YEAR2.));
   CALL SYMPUT('RYEAR',PUT(REPTDATE,YEAR4.));
   CALL SYMPUT('XDATE',PUT(REPTDATE,DDMMYY10.));
*;
DATA SGM;
   INFILE SGMF;
   INPUT  @001 REFNO    8.
          @010 STATS    $1.
          @016 RCMM     2. /* RECEIVE MONTH */
          @019 RCYY     2.
          @025 APMM     2. /* APPR MONTH */
          @028 APYY     2.
          @034 NOCARD   3. /* CARDS RECEIVE */
          @038 STAFF    5.
          @044 TYPE    $2.
          ;

     IF APYY=&RYY;

     DMTHRC=0; DYRRC=0; CMTHRC=0; CYRRC=0;
     DMTHAP=0; DYRAP=0; CMTHAP=0; CYRAP=0;

        IF TYPE='CR' THEN DO;
           CYRRC=NOCARD;
           IF RCMM=&RMM THEN CMTHRC=NOCARD;
           IF STATS='A' THEN DO;
              CYRAP=NOCARD;
              IF APMM=&RMM THEN CMTHAP=NOCARD;
           END;
        END;

        IF TYPE='DB' THEN DO;
           DYRRC=NOCARD;
           IF RCMM=&RMM THEN DMTHRC=NOCARD;
           IF STATS='A' THEN DO;
              DYRAP=NOCARD;
              IF APMM=&RMM THEN DMTHAP=NOCARD;
           END;
        END;
*;
PROC SORT; BY STAFF;
*;
DATA HRBR;
   INFILE HRBR;
   INPUT @005 STAFF   5.
         @069 BRANCH  3.;
   IF (002<=BRANCH<=300);
*;
DATA HRHO;
   INFILE HRHO;
   INPUT @005 STAFF   5.;
   BRANCH=999;
*;
DATA HRRG;
   INFILE HRRG;
   INPUT @005 STAFF   5.;
   BRANCH=888;
*;
DATA BRID;
   SET HRBR HRHO HRRG;
*;
PROC SORT; BY STAFF;
*;
DATA SGM;
   MERGE SGM(IN=A) BRID; BY STAFF;
   IF A;
*;
PROC SUMMARY DATA=SGM NWAY;
CLASS BRANCH STAFF;
VAR   DMTHRC DYRRC DMTHAP DYRAP CMTHRC CYRRC CMTHAP CYRAP;
OUTPUT OUT=SGM (DROP=_TYPE_ _FREQ_) SUM=;
*;
DATA SGMB;
   SET SGM;
   IF  BRANCH NOT IN (888,999);
*;
DATA SGM8;
   SET SGM;
   IF  BRANCH=888;
*;
DATA SGM9;
   SET SGM;
   IF  BRANCH=999;
*;
PROC SORT DATA=SGMB; BY BRANCH STAFF;
TITLE;
DATA _NULL_;
  SET SGMB END=LAST; BY BRANCH;
  FILE PRINT HEADER=NEWPAGE;

  IF   FIRST.BRANCH THEN DO;
       PUT _PAGE_;
       BCMTHRC=0;  BDMTHRC=0;
       BCYRRC =0;  BDYRRC =0;
       BCMTHAP=0;  BDMTHAP=0;
       BCYRAP =0;  BDYRAP =0;
  END;
       BCMTHRC+ CMTHRC;    BDMTHRC+ DMTHRC;
       BCYRRC+  CYRRC;     BDYRRC + DYRRC;
       BCMTHAP+ CMTHAP;    BDMTHAP+ DMTHAP;
       BCYRAP+  CYRAP;     BDYRAP + DYRAP;

  PUT @03  STAFF    5.
      @15  CMTHRC   5. @25  DMTHRC  5.
      @35  CYRRC    5. @45  DYRRC   5.
      @55  CMTHAP   5. @65  DMTHAP  5.
      @75  CYRAP    5. @85  DYRAP   5.;

  IF  LAST.BRANCH THEN DO;
      PUT  @03 87*'-';
      PUT  @03 'TOTAL ='
           @14 BCMTHRC  6.  @24 BDMTHRC 6.
           @34 BCYRRC   6.  @44 BDYRRC  6.
           @54 BCMTHAP  6.  @64 BDMTHAP 6.
           @74 BCYRAP   6.  @84 BDYRAP  6.;
      PUT  @03 87*'-';
  END;

  RETURN;

  NEWPAGE:
    PUT @01 'PUBLIC BANK BERHAD - CARD ACQUISITION'
        @43 '(' "&SDATE"  ' TO ' "&RDATE" ')';
    PUT @01 'REPORT NAME: DCPD/SGC2002/004 (FOR BRANCHES)';
    PUT @01 'REPORT ID  : EIBMSISD' @029 "&XDATE";
    PUT @01 '.';
    PUT @01 'BRANCH CODE= ' BRANCH Z3.;
    PUT @12 '------- APPLICATION RECEIVED ---------'
        @52 '------- APPLICATION APPROVED ---------';
    PUT @13 'MONTH OF ' "&RMON"     @35 'YEAR-TO-DATE'
        @53 'MONTH OF ' "&RMON"     @75 'YEAR-TO-DATE';
    PUT @04 'STAFF'
        @12 'CRE CARD  DEB CARD  CRE CARD  DEB CARD'
        @52 'CRE CARD  DEB CARD  CRE CARD  DEB CARD';
    PUT @04 '-----'
        @12 '------------------  ------------------'
        @52 '------------------  ------------------';
  RETURN;
RUN;
*;
PROC SORT DATA=SGM8; BY BRANCH STAFF;
TITLE;
DATA _NULL_;
  SET SGM8 END=LAST; BY BRANCH;
  FILE PRINT HEADER=NEWPAGE;

  IF   FIRST.BRANCH THEN DO;
       PUT _PAGE_;
       BCMTHRC=0;  BDMTHRC=0;
       BCYRRC =0;  BDYRRC =0;
       BCMTHAP=0;  BDMTHAP=0;
       BCYRAP =0;  BDYRAP =0;
  END;
       BCMTHRC+ CMTHRC;    BDMTHRC+ DMTHRC;
       BCYRRC+  CYRRC;     BDYRRC + DYRRC;
       BCMTHAP+ CMTHAP;    BDMTHAP+ DMTHAP;
       BCYRAP+  CYRAP;     BDYRAP + DYRAP;

  PUT @03  STAFF    5.
      @15  CMTHRC   5. @25  DMTHRC  5.
      @35  CYRRC    5. @45  DYRRC   5.
      @55  CMTHAP   5. @65  DMTHAP  5.
      @75  CYRAP    5. @85  DYRAP   5.;

  IF  LAST.BRANCH THEN DO;
      PUT  @03 87*'-';
      PUT  @03 'TOTAL ='
           @14 BCMTHRC  6.  @24 BDMTHRC 6.
           @34 BCYRRC   6.  @44 BDYRRC  6.
           @54 BCMTHAP  6.  @64 BDMTHAP 6.
           @74 BCYRAP   6.  @84 BDYRAP  6.;
      PUT  @03 87*'-';
  END;

  RETURN;

  NEWPAGE:
    PUT @01 'PUBLIC BANK BERHAD - CARD ACQUISITION'
        @43 '(' "&SDATE"  ' TO ' "&RDATE" ')';
    PUT @01 'REPORT NAME: DCPD/SGC2002/004 (FOR SME/PFE)';
    PUT @01 'REPORT ID  : EIBMSISD' @029 "&XDATE";
    PUT @01 '.';
    PUT @01 'BRANCH CODE= ' BRANCH Z3.;
    PUT @12 '------- APPLICATION RECEIVED ---------'
        @52 '------- APPLICATION APPROVED ---------';
    PUT @13 'MONTH OF ' "&RMON"     @35 'YEAR-TO-DATE'
        @53 'MONTH OF ' "&RMON"     @75 'YEAR-TO-DATE';
    PUT @04 'STAFF'
        @12 'CRE CARD  DEB CARD  CRE CARD  DEB CARD'
        @52 'CRE CARD  DEB CARD  CRE CARD  DEB CARD';
    PUT @04 '-----'
        @12 '------------------  ------------------'
        @52 '------------------  ------------------';
  RETURN;
RUN;
*;
PROC SORT DATA=SGM9; BY BRANCH STAFF;
TITLE;
DATA _NULL_;
  SET SGM9 END=LAST; BY BRANCH;
  FILE PRINT HEADER=NEWPAGE;

  IF   FIRST.BRANCH THEN DO;
       PUT _PAGE_;
       BCMTHRC=0;  BDMTHRC=0;
       BCYRRC =0;  BDYRRC =0;
       BCMTHAP=0;  BDMTHAP=0;
       BCYRAP =0;  BDYRAP =0;
  END;
       BCMTHRC+ CMTHRC;    BDMTHRC+ DMTHRC;
       BCYRRC+  CYRRC;     BDYRRC + DYRRC;
       BCMTHAP+ CMTHAP;    BDMTHAP+ DMTHAP;
       BCYRAP+  CYRAP;     BDYRAP + DYRAP;

  PUT @03  STAFF    5.
      @15  CMTHRC   5. @25  DMTHRC  5.
      @35  CYRRC    5. @45  DYRRC   5.
      @55  CMTHAP   5. @65  DMTHAP  5.
      @75  CYRAP    5. @85  DYRAP   5.;

  IF  LAST.BRANCH THEN DO;
      PUT  @03 87*'-';
      PUT  @03 'TOTAL ='
           @14 BCMTHRC  6.  @24 BDMTHRC 6.
           @34 BCYRRC   6.  @44 BDYRRC  6.
           @54 BCMTHAP  6.  @64 BDMTHAP 6.
           @74 BCYRAP   6.  @84 BDYRAP  6.;
      PUT  @03 87*'-';
  END;

  RETURN;

  NEWPAGE:
    PUT @01 'PUBLIC BANK BERHAD - CARD ACQUISITION'
        @43 '(' "&SDATE"  ' TO ' "&RDATE" ')';
    PUT @01 'REPORT NAME: DCPD/SGC2002/004 (FOR HEAD OFF)';
    PUT @01 'REPORT ID  : EIBMSISD' @029 "&XDATE";
    PUT @01 '.';
    PUT @01 'BRANCH CODE= ' BRANCH Z3.;
    PUT @12 '------- APPLICATION RECEIVED ---------'
        @52 '------- APPLICATION APPROVED ---------';
    PUT @13 'MONTH OF ' "&RMON"     @35 'YEAR-TO-DATE'
        @53 'MONTH OF ' "&RMON"     @75 'YEAR-TO-DATE';
    PUT @04 'STAFF'
        @12 'CRE CARD  DEB CARD  CRE CARD  DEB CARD'
        @52 'CRE CARD  DEB CARD  CRE CARD  DEB CARD';
    PUT @04 '-----'
        @12 '------------------  ------------------'
        @52 '------------------  ------------------';
  RETURN;
RUN;
