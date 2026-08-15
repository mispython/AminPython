#!/usr/bin/env python3
"""PBB EIFMNP06: complete specific-provision job and reports."""
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from eifmnp03 import branch_label, load_branch_map, read_sas, risk, sas_date, sas_sum, val
except ModuleNotFoundError:
    from EIFMNP03 import branch_label, load_branch_map, read_sas, risk, sas_date, sas_sum, val


DEFAULT_BASE = Path("Data_Warehouse/MIS/XMIS/input/prod")
DEFAULT_OUTPUT_DIR = DEFAULT_BASE / "output" / "eifmnp06"


LNTYP = {
    128: "HPD AITAB", 130: "HPD AITAB", 983: "HPD AITAB",
    700: "HPD CONVENTIONAL", 705: "HPD CONVENTIONAL",
    380: "HPD CONVENTIONAL", 381: "HPD CONVENTIONAL",
    720: "HPD CONVENTIONAL", 725: "HPD CONVENTIONAL",
    993: "HPD CONVENTIONAL", 996: "HPD CONVENTIONAL",
    **{i: "HOUSING LOANS" for i in range(200, 300)},
}
PIBB_PROFILE = False
PROGRAM_NAME = "EIFMNP06"
REPORT_ENTITY = "PUBLIC BANK"

REPORT_LABELS = {
    "ACCTNO":"MNI ACCOUNT NO", "VINNO":"AA NUMBER", "DAYS":"NO OF DAYS PAST DUE",
    "BORSTAT":"BORROWER'S STATUS", "NETPROC":"LIMIT", "CURBAL":"CURRENT BAL (A)",
    "UHC":"UNEARNED HIRING CHARGES (B)", "NETBAL":"NET BAL (A-B=C)", "IIS":"IIS (E)",
    "OSPRIN":"PRINCIPAL OUTSTANDING (C-E=F)", "OTHERFEE":"OTHER FEES",
    "MARKETVL":"REALISABLE VALUE (G)", "NETEXP":"NET EXPOSURE (F-G=H)",
    "SPP2":"OPENING BAL FOR FINANCIAL YEAR (I)",
    "SPPL":"PROVISION MADE AGAINST PROFIT & LOSS (J)",
    "RECOVER":"WRITTEN BACK TO PROFIT & LOSS (K)",
    "SPPW":"WRITTEN OFF AGAINST PROVISION (L)",
    "SP":"CLOSING BAL AS AT RPT DATE (I+J-K-L)",
}


def write_original_report(out: pd.DataFrame, report_date: pd.Timestamp, output_dir: Path) -> str:
    """Render both PROC TABULATE tables and the original PROC PRINT listing."""
    measures=["CURBAL","UHC","NETBAL","IIS","OSPRIN","MARKETVL","NETEXP","SPP2","SPPL","RECOVER","SPPW","SP","OTHERFEE"]
    title1=f"{REPORT_ENTITY} - (NPL FROM 3 MONTHS & ABOVE) - NEW"
    title2=f"MOVEMENTS OF SPECIFIC PROVISION FOR THE MONTH ENDING {report_date.strftime('%d %B %Y').upper()} (EXISTING AND CURRENT)"
    fmt=lambda value:f"{value:,.2f}"
    risk_branch=out.groupby(["LOANTYP","RISK","BRANCH"],dropna=False).agg(NO_OF_ACCOUNT=("ACCTNO","size"),**{c:(c,"sum") for c in measures}).reset_index()
    branch=out.groupby(["LOANTYP","BRANCH"],dropna=False).agg(NO_OF_ACCOUNT=("ACCTNO","size"),**{c:(c,"sum") for c in measures}).reset_index()
    rename={**REPORT_LABELS,"NO_OF_ACCOUNT":"NO OF ACCOUNT"}
    lines=[title1,title2,"","SUMMARY BY RISK AND BRANCH",
           risk_branch.rename(columns=rename).to_string(index=False,formatters={rename[c]:fmt for c in measures}),
           "","SUMMARY BY BRANCH",
           branch.rename(columns=rename).to_string(index=False,formatters={rename[c]:fmt for c in measures}),
           "","DETAILED LISTING"]
    ordered=out.sort_values(["LOANTYP","BRANCH","RISK","DAYS","ACCTNO"])
    detail_cols=["ACCTNO","NAME","VINNO","DAYS","BORSTAT","NETPROC",*measures]
    for (loan_type,branch_name,risk_name),group in ordered.groupby(["LOANTYP","BRANCH","RISK"],dropna=False,sort=False):
        lines.extend(["",f"LOAN TYPE: {loan_type}    BRANCH: {branch_name}    RISK: {risk_name}"])
        display=group[[c for c in detail_cols if c in group]].rename(columns=REPORT_LABELS)
        lines.append(display.to_string(index=False,formatters={REPORT_LABELS[c]:fmt for c in measures if c in group}))
        totals=group[measures].sum()
        lines.append("TOTAL: "+" | ".join(f"{REPORT_LABELS[c]}={totals[c]:,.2f}" for c in measures))
    report="\n".join(lines)+"\n"
    (output_dir/f"{PROGRAM_NAME.lower()}_report.lst").write_text(report,encoding="utf-8")
    (output_dir/f"{PROGRAM_NAME.lower()}_report.txt").write_text(report,encoding="utf-8")
    return report


def read_table(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        df.columns = [c.upper() for c in df.columns]
        return df
    return read_sas(path)


def provision(row: pd.Series, report_date: pd.Timestamp, existing: bool) -> pd.Series:
    row = row.copy()
    for c in ["CURBAL", "TERMCHG", "EARNTERM", "NOTETERM", "IIS", "FEEAMT", "FEETOT2", "FEEAMT8",
              "FEEAMTA", "FEEAMT5", "APPVALUE", "MARKETVL", "SPP2", "WREALVL", "WSPPL", "WSP",
              "WRECOVER", "WSPPW", "DAYS"]:
        if c not in row or pd.isna(row[c]): row[c] = 0.0
    if row["EARNTERM"] == 0: row["EARNTERM"] = row["NOTETERM"]
    lt, days = int(val(row, "LOANTYPE", 0)), row["DAYS"]
    borstat, user5 = val(row, "BORSTAT", ""), val(row, "USER5", "")
    written = val(row, "WRITEOFF", "N") == "Y"
    wdown = val(row, "WDOWNIND", "N")
    if written and wdown != "Y": borstat = row["BORSTAT"] = "W"
    issue, bill = sas_date(row.get("ISSDTE")), sas_date(row.get("BLDATE"))
    uhc = 0.0
    if pd.notna(issue):
        rem2 = max(0, row["EARNTERM"] - ((report_date.year-issue.year)*12 + report_date.month-issue.month + 1))
        if rem2 > 0 and row["EARNTERM"] > 0:
            uhc = rem2*(rem2+1)*row["TERMCHG"]/(row["EARNTERM"]*(row["EARNTERM"]+1))
    row["UHC"] = uhc
    row["NETBAL"] = row["CURBAL"] - uhc
    row["OSPRIN"] = row["CURBAL"] - uhc - row["IIS"]
    if lt in {380, 381}:
        other = sas_sum(row["FEEAMT"], -row["FEETOT2"])
    else:
        other = sas_sum(row["FEEAMT8"], -row["FEETOT2"], row["FEEAMTA"], -row["FEEAMT5"])
    row["OTHERFEE"] = 0.0 if lt in {983, 993} else max(0.0, other)
    secured = row["APPVALUE"] > 0 and (lt in {705,128,700,130,380,381} or val(row,"CENSUS7","") == "9") \
              and (days > 89 or user5 == "N") and borstat not in {"F","R","I","Y","W"} and lt not in {983,993}
    hardcode = val(row, "HARDCODE", "N") == "Y"
    market = row["MARKETVL"]
    if secured:
        age = int(report_date.year-issue.year + (report_date.month-issue.month)/12) if pd.notna(issue) else 0
        if val(row,"CENSUS7","") != "9": market = row["APPVALUE"] * (1 - age*0.2)
        if hardcode: market = row["WREALVL"]
        market = max(0.0, market)
        netexp = row["OSPRIN"] + row["OTHERFEE"] - (0 if days > 273 else market)
        sp = netexp if days > 364 else netexp/2 if days > 273 else netexp*0.2
    else:
        if borstat != "R": market = 0.0
        if hardcode: market = row["WREALVL"]
        netexp = row["OSPRIN"] + row["OTHERFEE"] - market
        sp = netexp if days > 364 or borstat in {"F","R","I","W"} else netexp/2 if days > 273 else netexp/5 if days > 89 and borstat == "Y" else 0.0
    row["MARKETVL"], row["NETEXP"], row["SP"] = market, netexp, max(0.0, sp)
    row["SPPL"] = max(0.0, row["SP"] - row["SPP2"]) if existing else row["SP"]
    if hardcode:
        if pd.notna(row.get("WSPPL")): row["SPPL"] = row["WSPPL"]
        if pd.notna(row.get("WSP")): row["SP"] = row["WSP"]
    row["RECOVER"], row["SPPW"] = (max(0.0, row["SPP2"]-row["SP"]), 0.0) if existing else (0.0, 0.0)
    if borstat == "W": row["SPPW"], row["SP"], row["MARKETVL"] = row["SPP2"], 0.0, 0.0
    if written:
        row["SPPL"], row["OTHERFEE"] = row["WSPPL"], 0.0
        if wdown != "Y":
            row["RECOVER"], row["SP"] = row["WRECOVER"], 0.0
            row["SPPW"] = sas_sum(row["SPP2"], row["SPPL"], -row["RECOVER"])
        else:
            row["SPPW"] = row["WSPPW"]
            if row["NETEXP"] <= 0: row["RECOVER"] = 0.0
            row["SP"] = sas_sum(row["SPP2"], row["SPPL"], -row["RECOVER"], -row["SPPW"])
            if row["NETEXP"] <= 0 and row["SP"] > 0: row["RECOVER"], row["SP"] = row["SP"], 0.0
    if val(row,"RESCHEIND","") == "Y":
        row["RECOVER"], row["SPPW"] = val(row,"WRECOVER"), val(row,"WSPPW")
        row["SP"] = sas_sum(row["SPP2"], row["SPPL"], -row["RECOVER"], -row["SPPW"])
    return row


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--input-dir",type=Path,default=DEFAULT_BASE); p.add_argument("--output-dir",type=Path,default=DEFAULT_OUTPUT_DIR)
    p.add_argument("--iis-file",type=Path,help="Optional explicit IIS SAS7BDAT path")
    p.add_argument("--iis-pattern",default="iis{mm}.sas7bdat"); p.add_argument("--loan-pattern",default="loan{mm}.sas7bdat")
    p.add_argument("--wsp2-file",default="wsp2.sas7bdat"); p.add_argument("--previous-pattern",default="sp2{mm}.sas7bdat"); p.add_argument("--branch-map",type=Path); p.add_argument("--no-console-report",action="store_true")
    a=p.parse_args(); a.output_dir.mkdir(parents=True,exist_ok=True); rd=pd.Timestamp(date.today()-timedelta(days=1)); mm=f"{rd.month:02d}"; prev=f"{(rd.month-2)%12+1:02d}"
    loan=read_sas(a.input_dir/a.loan_pattern.format(mm=mm)); wsp=read_sas(a.input_dir/a.wsp2_file).drop(columns=["NOTENO","NTBRCH"],errors="ignore"); wsp["_WSP"]=True
    data=loan.merge(wsp,on="ACCTNO",how="left",suffixes=("","_WSP")); data["WRITEOFF"]=np.where(data["_WSP"].fillna(False),"Y","N")
    iis_path = a.iis_file if a.iis_file else a.input_dir/a.iis_pattern.format(mm=mm)
    iis=read_table(iis_path)[["ACCTNO","IIS"]].drop_duplicates("ACCTNO"); data=data.merge(iis,on="ACCTNO",how="left",suffixes=("","_IIS")); data["IIS"]=data.get("IIS_IIS",data.get("IIS",0)).fillna(0)
    existing=data[data.get("EXIST","")=="Y"].apply(provision,axis=1,report_date=rd,existing=True); current=data[data.get("EXIST","")!="Y"].apply(provision,axis=1,report_date=rd,existing=False)
    out=pd.concat([existing,current],ignore_index=True,sort=False)
    if PIBB_PROFILE:
        out=out[((out["COSTCTR"]>=3000)&(out["COSTCTR"]<=3999))|out["COSTCTR"].isin([4043,4048])]
    else:
        out=out[((out["COSTCTR"]<3000)|(out["COSTCTR"]>3999))&~out["COSTCTR"].isin([4043,4048])&out["COSTCTR"].notna()]
    bm=load_branch_map(a.branch_map); out["BRANCH"]=out["NTBRCH"].map(lambda x:branch_label(x,bm)); out["LOANTYP"]=out["LOANTYPE"].map(LNTYP).fillna("OTHERS"); out["RISK"]=out.apply(risk,axis=1); out=out.drop_duplicates(["ACCTNO","NOTENO"])
    out.to_csv(a.output_dir/f"sp2{mm}.csv",index=False); measures=["CURBAL","UHC","NETBAL","IIS","OSPRIN","MARKETVL","NETEXP","SPP2","SPPL","RECOVER","SPPW","SP","OTHERFEE"]
    out.groupby(["LOANTYP","RISK","BRANCH"],dropna=False)[measures].sum().reset_index().to_csv(a.output_dir/f"{PROGRAM_NAME.lower()}_summary.csv",index=False)
    out.to_csv(a.output_dir/f"{PROGRAM_NAME.lower()}_detail.csv",index=False); report=write_original_report(out,rd,a.output_dir); print(f"{PROGRAM_NAME} processed {len(out):,} rows for {rd.date()}")
    if not a.no_console_report: print(report,end="")


if __name__=="__main__": main()
