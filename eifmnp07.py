#!/usr/bin/env python3
"""PBB EIFMNP07: complete asset-quality/NPL movement job and reports."""
from __future__ import annotations

import argparse
from datetime import date,timedelta
from pathlib import Path
import numpy as np
import pandas as pd
try:
    from eifmnp03 import branch_label,load_branch_map,read_sas,risk,sas_date,sas_sum,val
except ModuleNotFoundError:
    from EIFMNP03 import branch_label,load_branch_map,read_sas,risk,sas_date,sas_sum,val


DEFAULT_BASE = Path("Data_Warehouse/MIS/XMIS/input/prod")
DEFAULT_OUTPUT_DIR = DEFAULT_BASE / "output" / "eifmnp07"

LNTYP = {
    128: "HPD AITAB", 130: "HPD AITAB", 983: "HPD AITAB",
    700: "HPD CONVENTIONAL", 705: "HPD CONVENTIONAL",
    380: "HPD CONVENTIONAL", 381: "HPD CONVENTIONAL",
    720: "HPD CONVENTIONAL", 725: "HPD CONVENTIONAL",
    993: "HPD CONVENTIONAL", 996: "HPD CONVENTIONAL",
    **{i: "HOUSING LOANS" for i in range(200, 300)},
}
PIBB_PROFILE = False
PROGRAM_NAME = "EIFMNP07"
REPORT_ENTITY = "PUBLIC BANK"


REPORT_LABELS = {
    "ACCTNO": "MNI ACCOUNT NO", "DAYS": "NO OF DAYS PAST DUE",
    "CURBALP": "BAL AS AT PREV YEAR (WITH UHC)",
    "CURBAL": "BAL AS AT END OF RPT DATE (WITH UHC)",
    "NETBALP": "NET BAL AS AT PREV YEAR (A)",
    "NEWNPL": "NEW NPL DURING CURRENT YEAR (B)",
    "ACCRINT": "ACCRUED INTEREST (C)", "RECOVER": "RECOVERIES (D)",
    "PL": "NPL CLASSIFIED AS PERFORMING (E)", "NPLW": "NPL WRITTEN-OFF (F)",
    "ADJUST": "ADJUSTMENT", "NPL": "NPL AS AT END OF RPT DATE (A+B+C-D-E-F)",
}


def write_original_report(out: pd.DataFrame, report_date: pd.Timestamp, output_dir: Path) -> str:
    """Render the two PROC TABULATE tables and PROC PRINT detail listing."""
    measures = ["CURBALP","CURBAL","NETBALP","NEWNPL","ACCRINT","RECOVER","PL","NPLW","ADJUST","NPL"]
    detail_cols = ["ACCTNO","NAME","DAYS",*measures]
    title1 = f"{REPORT_ENTITY} - (NPL FROM 3 MONTHS & ABOVE)"
    title2 = f"STATISTICS ON ASSET QUALITY - MOVEMENTS IN NPL {report_date.strftime('%d %B %Y').upper()}"
    number_format = lambda value: f"{value:,.2f}"
    risk_branch = out.groupby(["LOANTYP","RISK","BRANCH"],dropna=False).agg(
        NO_OF_ACCOUNT=("ACCTNO","size"), **{c:(c,"sum") for c in measures}
    ).reset_index()
    branch = out.groupby(["LOANTYP","BRANCH"],dropna=False).agg(
        NO_OF_ACCOUNT=("ACCTNO","size"), **{c:(c,"sum") for c in measures}
    ).reset_index()
    rename = {**REPORT_LABELS, "NO_OF_ACCOUNT":"NO OF ACCOUNT"}
    lines = [title1, title2, "", "SUMMARY BY RISK AND BRANCH"]
    lines.append(risk_branch.rename(columns=rename).to_string(index=False,formatters={rename[c]:number_format for c in measures}))
    lines.extend(["", "SUMMARY BY BRANCH"])
    lines.append(branch.rename(columns=rename).to_string(index=False,formatters={rename[c]:number_format for c in measures}))
    lines.extend(["", "DETAILED LISTING"])
    ordered = out.sort_values(["LOANTYP","BRANCH","RISK","DAYS","ACCTNO"])
    for (loan_type, branch_name, risk_name), group in ordered.groupby(["LOANTYP","BRANCH","RISK"],dropna=False,sort=False):
        lines.extend(["", f"LOAN TYPE: {loan_type}    BRANCH: {branch_name}    RISK: {risk_name}"])
        display = group[[c for c in detail_cols if c in group]].rename(columns=REPORT_LABELS)
        lines.append(display.to_string(index=False,formatters={REPORT_LABELS[c]:number_format for c in measures if c in group}))
        totals = group[measures].sum()
        lines.append("TOTAL: " + " | ".join(f"{REPORT_LABELS[c]}={totals[c]:,.2f}" for c in measures))
    report = "\n".join(lines) + "\n"
    # .lst corresponds to the original SASLIST/PROC PRINT listing output.
    (output_dir/f"{PROGRAM_NAME.lower()}_report.lst").write_text(report,encoding="utf-8")
    (output_dir/f"{PROGRAM_NAME.lower()}_report.txt").write_text(report,encoding="utf-8")
    return report


def movement(row:pd.Series,rd:pd.Timestamp,existing:bool)->pd.Series:
    row=row.copy()
    for c in ["CURBALP","CURBAL","NETBALP","FEEAMT","FEETOT2","FEEYTD","FEEPDYTD","TERMCHG","EARNTERM","NOTETERM","UHCP","WACCRINT","WNEWNPL","WRECOVER","WNPLW","DAYS"]:
        if c not in row or pd.isna(row[c]): row[c]=0.0
    if row["EARNTERM"]==0: row["EARNTERM"]=row["NOTETERM"]
    lt=int(val(row,"LOANTYPE",0)); bor=val(row,"BORSTAT",""); user5=val(row,"USER5",""); written=val(row,"WRITEOFF","N")=="Y"; wdown=val(row,"WDOWNIND","N")
    if written and wdown!="Y": bor=row["BORSTAT"]="W"
    row["ADJUST"]=row["FEEAMT"]-row["FEETOT2"] if existing else 0.0
    row["NEWNPL"]=row["ACCRINT"]=row["RECOVER"]=row["PL"]=row["NPLW"]=row["NPL"]=0.0; uhc=0.0
    issue=sas_date(row.get("ISSDTE")); bill=sas_date(row.get("BLDATE"))
    if pd.notna(issue):
        rem2=max(0,row["EARNTERM"]-((rd.year-issue.year)*12+rd.month-issue.month+1))
        if rem2>0 and row["EARNTERM"]>0: uhc=rem2*(rem2+1)*row["TERMCHG"]/(row["EARNTERM"]*(row["EARNTERM"]+1))
    if existing:
        performing=(row["DAYS"]<90 and bor in {"","A","C","S","T","Y"} and row["CURBAL"]>=0 and user5!="N") or lt in {983,993}
        if performing:
            row["PL"]=row["NETBALP"]
            if row["DAYS"]==0 and row["CURBAL"]==0: row["RECOVER"],row["PL"]=row["NETBALP"],0.0
        else:
            row["ACCRINT"]=row["FEEYTD"]; row["OI"]=row["FEEAMT"]
            if bor=="F": row["CURBALP"]-=row["UHCP"]
            row["RECOVER"]=0.0 if bor=="W" else row["CURBALP"]-row["CURBAL"]+row["FEEPDYTD"]
            if row["RECOVER"]<0: row["CURBALP"]-=row["RECOVER"]; row["RECOVER"]=0.0
            row["NPLW"]=row["NETBALP"] if bor=="W" else 0.0; row["NPL"]=0.0 if bor=="W" else row["CURBAL"]-uhc+row["OI"]
    else:
        row["OI"]=row["FEEAMT"]; row["NEWNPL"]=row["CURBAL"]-uhc+row["OI"]; row["NPL"]=row["NEWNPL"]
    if written or lt in {983,993}:
        row["ACCRINT"],row["NEWNPL"],row["ADJUST"]=row["WACCRINT"],row["WNEWNPL"],0.0
        if wdown!="Y": row["RECOVER"],row["PL"],row["NPL"]=row["WRECOVER"],0.0,0.0; row["NPLW"]=sas_sum(row["NETBALP"],row["NEWNPL"],row["ACCRINT"],-row["RECOVER"])
        else: row["NPLW"]=row["WNPLW"]; row["NPL"]=sas_sum(row["NETBALP"],row["NEWNPL"],row["ACCRINT"],-row["RECOVER"],-row["NPLW"],-row["PL"])
    row["CHKNPL"]=sas_sum(row["NETBALP"],row["NEWNPL"],row["ACCRINT"],-row["RECOVER"],-row["PL"],-row["NPLW"]); return row


def main():
    p=argparse.ArgumentParser();p.add_argument("--input-dir",type=Path,default=DEFAULT_BASE);p.add_argument("--output-dir",type=Path,default=DEFAULT_OUTPUT_DIR);p.add_argument("--loan-pattern",default="loan{mm}.sas7bdat");p.add_argument("--waq-file",default="waq.sas7bdat");p.add_argument("--branch-map",type=Path);p.add_argument("--no-console-report",action="store_true",help="Save the PROC PRINT listing without echoing it to stdout");a=p.parse_args()
    a.output_dir.mkdir(parents=True,exist_ok=True);rd=pd.Timestamp(date.today()-timedelta(days=1));mm=f"{rd.month:02d}";loan=read_sas(a.input_dir/a.loan_pattern.format(mm=mm));waq=read_sas(a.input_dir/a.waq_file).drop(columns=["NOTENO","NTBRCH"],errors="ignore");waq["_WAQ"]=True
    data=loan.merge(waq,on="ACCTNO",how="left",suffixes=("","_WAQ"));data["WRITEOFF"]=np.where(data["_WAQ"].fillna(False),"Y","N");ex=data[data.get("EXIST","")=="Y"].apply(movement,axis=1,rd=rd,existing=True);cu=data[data.get("EXIST","")!="Y"].apply(movement,axis=1,rd=rd,existing=False);out=pd.concat([ex,cu],ignore_index=True,sort=False)
    if PIBB_PROFILE: out=out[((out["COSTCTR"]>=3000)&(out["COSTCTR"]<=3999))|out["COSTCTR"].isin([4043,4048])]
    else: out=out[((out["COSTCTR"]<3000)|(out["COSTCTR"]>3999))&~out["COSTCTR"].isin([4043,4048])&out["COSTCTR"].notna()]
    bm=load_branch_map(a.branch_map);out["BRANCH"]=out["NTBRCH"].map(lambda x:branch_label(x,bm));out["LOANTYP"]=out["LOANTYPE"].map(LNTYP).fillna("OTHERS");out["RISK"]=out.apply(risk,axis=1);out.to_csv(a.output_dir/"aq.csv",index=False)
    measures=["CURBALP","CURBAL","NETBALP","NEWNPL","ACCRINT","RECOVER","PL","NPLW","ADJUST","NPL"];out.groupby(["LOANTYP","RISK","BRANCH"],dropna=False)[measures].sum().reset_index().to_csv(a.output_dir/f"{PROGRAM_NAME.lower()}_summary.csv",index=False);out.to_csv(a.output_dir/f"{PROGRAM_NAME.lower()}_detail.csv",index=False);report=write_original_report(out,rd,a.output_dir);print(f"{PROGRAM_NAME} processed {len(out):,} rows for {rd.date()}");
    if not a.no_console_report: print(report,end="")


if __name__=="__main__":main()
