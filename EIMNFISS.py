from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path


@dataclass(frozen=True)
class ReportContext:
    report_date: date
    sdd: int
    week: str
    previous_week: str
    report_month: str
    previous_month: str
    two_months_back: str
    report_year: str
    report_day: str
    rdate: str

    @classmethod
    def build(cls, today: date) -> "ReportContext":
        report_date = date(today.year, today.month, 1) - timedelta(days=1)

        if report_date.day == 8:
            sdd, week, previous_week = 1, "1", "4"
        elif report_date.day == 15:
            sdd, week, previous_week = 9, "2", "1"
        elif report_date.day == 22:
            sdd, week, previous_week = 16, "3", "2"
        else:
            sdd, week, previous_week = 23, "4", "3"

        report_month = report_date.month
        if week == "1":
            previous_month = report_month - 1
            if previous_month == 0:
                previous_month = 12
        else:
            previous_month = report_month

        two_months_back = report_month - 1
        if two_months_back == 0:
            two_months_back = 12

        return cls(
            report_date=report_date,
            sdd=sdd,
            week=week,
            previous_week=previous_week,
            report_month=f"{report_month:02d}",
            previous_month=f"{previous_month:02d}",
            two_months_back=f"{two_months_back:02d}",
            report_year=f"{report_date.year:04d}",
            report_day=f"{report_date.day:02d}",
            rdate=report_date.strftime("%d/%m/%y"),
        )


@dataclass(frozen=True)
class CopyJob:
    temp_name: str
    source_code: str
    member: str


COPY_JOBS = (
    CopyJob("LN_UTIL", "LN", "B80510"),
    CopyJob("LN_UNUTIL", "LN", "B80200"),
    CopyJob("ILN_UTIL", "ILN", "B80510"),
    CopyJob("ILN_UNUTIL", "ILN", "B80200"),
    CopyJob("BT_UTIL", "BT", "B80510"),
    CopyJob("BT_UNUTIL", "BT", "B80200"),
    CopyJob("IBT_UTIL", "IBT", "B80510"),
    CopyJob("IBT_UNUTIL", "IBT", "B80200"),
)


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def source_dirs(args: argparse.Namespace) -> dict[str, Path | None]:
    return {
        "LN": args.ln_dir,
        "ILN": args.iln_dir,
        "BT": args.bt_dir,
        "IBT": args.ibt_dir,
    }


def candidate_paths(
    input_dir: Path,
    source_dir: Path | None,
    source_code: str,
    member: str,
) -> list[Path]:
    candidates: list[Path] = []
    filename = f"{member}.sas7bdat"

    if source_dir is not None:
        candidates.extend([
            source_dir / filename,
            source_dir / source_code / filename,
            source_dir / f"{source_code}_{filename}",
        ])

    candidates.extend([
        input_dir / source_code / filename,
        input_dir / f"{source_code}_{filename}",
        input_dir / filename,
    ])
    return candidates


def resolve_input(
    input_dir: Path,
    source_dir: Path | None,
    source_code: str,
    member: str,
) -> Path:
    for path in candidate_paths(input_dir, source_dir, source_code, member):
        if path.is_file():
            return path

    searched = "\n  ".join(
        str(path) for path in candidate_paths(input_dir, source_dir, source_code, member)
    )
    raise FileNotFoundError(
        f"Required input file not found for {source_code}.{member}. Searched:\n  {searched}"
    )


def copy_inputs_to_temp(
    input_dir: Path,
    output_dir: Path,
    dirs: dict[str, Path | None],
) -> dict[str, str]:
    temp_dir = output_dir / "SAP.NFISS.TEMP"
    temp_dir.mkdir(parents=True, exist_ok=True)

    copied: dict[str, str] = {}
    for job in COPY_JOBS:
        source = resolve_input(input_dir, dirs[job.source_code], job.source_code, job.member)
        target = temp_dir / f"{job.temp_name}.sas7bdat"
        shutil.copy2(source, target)
        copied[job.temp_name] = str(target)
    return copied


def write_manifest(output_dir: Path, context: ReportContext, copied: dict[str, str]) -> Path:
    manifest_path = output_dir / "SAP.NFISS.TEMP" / "manifest.json"
    manifest = {
        "job": "EIMNFISS",
        "report_context": {
            "REPTDATE": context.report_date.isoformat(),
            "SDD": context.sdd,
            "NOWK": context.week,
            "NOWK1": "1",
            "NOWK2": "2",
            "NOWK3": "3",
            "WK1": context.previous_week,
            "REPTMON": context.report_month,
            "REPTMON1": context.previous_month,
            "REPTMON2": context.two_months_back,
            "REPTYEAR": context.report_year,
            "REPTDAY": context.report_day,
            "RDATE": context.rdate,
        },
        "datasets": copied,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def create_transfer_zip(output_dir: Path, copied: dict[str, str], manifest_path: Path) -> Path:
    transfer_file = output_dir / "SAP.NFISS.TEMP.FTP.zip"
    transfer_file.unlink(missing_ok=True)

    with zipfile.ZipFile(transfer_file, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path_text in copied.values():
            path = Path(path_text)
            archive.write(path, arcname=path.name)
        archive.write(manifest_path, arcname=manifest_path.name)
    return transfer_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Python conversion of EIMNFISS")
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("Data_Warehouse/MIS/XMIS/input/prod"),
        help="Base folder for SAS7BDAT inputs",
    )
    parser.add_argument("--ln-dir", type=Path, help="Folder containing LN B80510/B80200 sas7bdat")
    parser.add_argument("--iln-dir", type=Path, help="Folder containing ILN B80510/B80200 sas7bdat")
    parser.add_argument("--bt-dir", type=Path, help="Folder containing BT B80510/B80200 sas7bdat")
    parser.add_argument("--ibt-dir", type=Path, help="Folder containing IBT B80510/B80200 sas7bdat")
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--today-date",
        type=parse_date,
        help="YYYY-MM-DD; overrides TODAY() for testing only",
    )
    args = parser.parse_args()

    input_dir = args.input_dir
    output_dir = args.output_dir or input_dir / "output"
    output_dir.mkdir(parents=True, exist_ok=True)

    context = ReportContext.build(args.today_date or date.today())
    copied = copy_inputs_to_temp(input_dir, output_dir, source_dirs(args))
    manifest_path = write_manifest(output_dir, context, copied)
    transfer_file = create_transfer_zip(output_dir, copied, manifest_path)

    print(f"REPTDATE={context.report_date.isoformat()}")
    print(f"Created {transfer_file}")


if __name__ == "__main__":
    main()



















































//EIMNFISS JOB MISEIS,EIBMTH1A,MSGCLASS=A,CLASS=A,NOTIFY=&SYSUID,
//         USER=OPCC
//*
//DELETE   EXEC PGM=IEFBR14
//DD1      DD DISP=(MOD,DELETE,DELETE),
//            SPACE=(TRK,(1,10)),
//            DSN=SAP.NFISS.TEMP
//DD2      DD DISP=(MOD,DELETE,DELETE),
//            SPACE=(TRK,(1,10)),
//            DSN=SAP.NFISS.TEMP.FTP
//CREATE   EXEC PGM=IEFBR14
//CRT01    DD DSN=SAP.NFISS.TEMP.FTP,
//            DISP=(NEW,CATLG,DELETE),
//            DCB=(RECFM=FB,LRECL=80,BLKSIZE=24000),
//            SPACE=(CYL,(200,200),RLSE),UNIT=(SYSDA,5)
//EIMNFISS  EXEC SAS609,REGION=8M,WORK='250000,200000'
//BT        DD DSN=SAP.BT.FISS,DISP=SHR
//IBT       DD DSN=SAP.IBT.FISS,DISP=SHR
//TEMP      DD DSN=SAP.NFISS.TEMP,DISP=(NEW,DELETE,DELETE),
//             DCB=(RECFM=FS,LRECL=27648,BLKSIZE=27648),
//             SPACE=(CYL,(100,50)),UNIT=(SYSDA,5)
//PGM       DD DSN=SAP.BNM.PROGRAM,DISP=SHR
//SASLIST   DD SYSOUT=X
//SYSIN     DD *

OPTIONS SORTDEV=3390 YEARCUTOFF=1950 LS=132 PS=60 NOCENTER;

DATA REPTDATE (KEEP=REPTDATE);
  REPTDATE=INPUT('01'||PUT(MONTH(TODAY()), Z2.)||
                 PUT(YEAR(TODAY()), 4.), DDMMYY8.)-1;
  SELECT(DAY(REPTDATE));
    WHEN (8)  DO; SDD = 1;  WK = '1'; WK1 = '4'; END;
    WHEN(15)  DO; SDD = 9;  WK = '2'; WK1 = '1'; END;
    WHEN(22)  DO; SDD = 16; WK = '3'; WK1 = '2'; END;
    OTHERWISE DO; SDD = 23; WK = '4'; WK1 = '3';
                            WK2= '2'; WK3 = '1'; END;
  END;
  MM = MONTH(REPTDATE);
  IF WK = '1' THEN DO;
     MM1 = MM - 1;
     IF MM1 = 0 THEN MM1 = 12;
  END;
  ELSE MM1 = MM;
  MM2 = MM - 1;
  IF MM2 = 0 THEN MM2 = 12;
  CALL SYMPUT('NOWK',PUT(WK,$1.));
  CALL SYMPUT('NOWK1',PUT('1',$1.));
  CALL SYMPUT('NOWK2',PUT('2',$1.));
  CALL SYMPUT('NOWK3',PUT('3',$1.));
  CALL SYMPUT('REPTMON',PUT(MM,Z2.));
  CALL SYMPUT('REPTMON1',PUT(MM1,Z2.));
  CALL SYMPUT('REPTMON2',PUT(MM2,Z2.));
  CALL SYMPUT('REPTYEAR',PUT(REPTDATE,YEAR4.));
  CALL SYMPUT('REPTDAY',PUT(DAY(REPTDATE),Z2.));
  CALL SYMPUT('RDATE',PUT(REPTDATE,DDMMYY8.));
  CALL SYMPUT('TDATE',REPTDATE);
RUN;

LIBNAME LN  "SAP.PBB.D&REPTYEAR" DISP=SHR;
LIBNAME ILN "SAP.PIBB.D&REPTYEAR" DISP=SHR;

DATA TEMP.LN_UTIL; SET LN.B80510; RUN;
DATA TEMP.LN_UNUTIL; SET LN.B80200; RUN;
DATA TEMP.ILN_UTIL; SET ILN.B80510; RUN;
DATA TEMP.ILN_UNUTIL; SET ILN.B80200; RUN;
DATA TEMP.BT_UTIL; SET BT.B80510; RUN;
DATA TEMP.BT_UNUTIL; SET BT.B80200; RUN;
DATA TEMP.IBT_UTIL; SET IBT.B80510; RUN;
DATA TEMP.IBT_UNUTIL; SET IBT.B80200; RUN;

FILENAME TRANFILE 'SAP.NFISS.TEMP.FTP' DISP=OLD;
PROC CPORT LIBRARY=TEMP FILE=TRANFILE;

//******************************************************************
//* FTP HOST DATASETS TO EDW
//******************************************************************
//RUNSFTP  EXEC COZBATCH
//CMD.SYSUT1 DD DISP=SHR,DSN=OPER.PBB.PARMLIB(EDW#SFTP)
//           DD *
lzopts servercp=$servercp,notrim,overflow=trunc,mode=binary
lzopts linerule=$lr
cd /stgsrcsys/host/ftpfiles
PUT //SAP.NFISS.TEMP.FTP  UTNFFTP
lzopts servercp=$servercp,notrim,overflow=trunc,mode=text
lzopts linerule=$lr
cd /stgsrcsys/host/control
PUT //SAP.CRMS.DAY.CONTROL UTNFISS.TXT
EOB
/*
