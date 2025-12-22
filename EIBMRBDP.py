import os
import pandas as pd

# ============================================================
# CONFIG
# ============================================================

INPUT = "input"
OUTPUT = "output"

OUTPUT_PARQUETS = [
    "EIBMRB01.parquet", "EIBMRB02.parquet", "EIBMRB03.parquet",
    "EIBMRB04.parquet", "EIBMRB05.parquet", "EIBMRB06.parquet",
    "EIBMRB07.parquet", "EIBMRB8A.parquet", "EIBMRB8B.parquet",
    "EIBMRB09.parquet"
]

OUTPUT_REPORTS = [
    "EIBMRB01_REPORT.txt", "EIBMRB02_REPORT.txt", "EIBMRB03_REPORT.txt",
    "EIBMRB04_REPORT.txt", "EIBMRB05_REPORT.txt", "EIBMRB06_REPORT.txt",
    "EIBMRB07_REPORT.txt", "EIBMRB8A_REPORT.txt", "EIBMRB8B_REPORT.txt",
    "EIBMRB09_REPORT.txt"
]

# ============================================================
# MAIN (JCL replacement)
# ============================================================

def main():
    os.makedirs(OUTPUT, exist_ok=True)

    # ---- DELETE STEP (IEFBR14 equivalent) ----
    for f in OUTPUT_PARQUETS + OUTPUT_REPORTS:
        try:
            os.remove(os.path.join(OUTPUT, f))
        except FileNotFoundError:
            pass

    # ---- RUN JOBS IN JCL ORDER ----
    eibmrb01()
    eibmrb02()
    eibmrb03()
    eibmrb04()
    eibmrb05()
    eibmrb06()
    eibmrb07()
    eibmrb08()
    eibmrb09()


# ============================================================
# COMMON: REPORT DATE
# ============================================================

def get_reptdate():
    return pd.read_parquet(f"{INPUT}/DEPO_REPTDATE.parquet").iloc[0]["REPTDATE"]


# ============================================================
# EIBMRB01
# ============================================================

def eibmrb01():
    rpt = get_reptdate()

    misfd = pd.read_parquet(f"{INPUT}/MISFD_FCYFD.parquet")
    mis2fd = pd.read_parquet(f"{INPUT}/MIS2FD_FCYFD.parquet")

    fcy = mis2fd[["ACCTNO", "CUSTCODE", "OPENDT"]]
    df = misfd.merge(fcy, on="ACCTNO", how="left")

    df = df[(df["CURCODE"] != "MYR") & (df["CURBAL"] > 0)]
    df["CURBAL"] = df["CURBAL"] / 1000

    mask = (
        (df["OPENDT"].dt.year == rpt.year) &
        (df["OPENDT"].dt.month == rpt.month) &
        (df["CLOSEDAT"].dt.year == df["OPENDT"].dt.year) &
        (df["CLOSEDAT"].dt.month == df["OPENDT"].dt.month)
    )
    df = df[~mask]

    out = df.groupby(["REPTDATE", "CURCODE"]).agg(
        TOT_AMT_OS_RM=("CURBAL", "sum"),
        NO_OF_ACCT=("CURBAL", "count")
    ).reset_index()

    out.to_parquet(f"{OUTPUT}/EIBMRB01.parquet", index=False)

    with open(f"{OUTPUT}/EIBMRB01_REPORT.txt", "w") as f:
        f.write("REPORT ID : EIBMRB01\n")
        f.write("DAILY TOTAL OUTSTANDING BALANCE/ACCOUNT ON FCY FD\n")
        f.write(f"AS AT {rpt:%d/%m/%Y}\n\n")
        f.write("DATE;CUR;TOTAL AMT (RM 000);NO OF ACCT\n")
        for _, r in out.iterrows():
            f.write(
                f"{r.REPTDATE:%d/%m/%Y};{r.CURCODE};"
                f"{r.TOT_AMT_OS_RM:,.2f};{int(r.NO_OF_ACCT)}\n"
            )


# ============================================================
# EIBMRB02
# ============================================================

def eibmrb02():
    rpt = get_reptdate()

    depo = pd.read_parquet(f"{INPUT}/DEPO.parquet")
    idepo = pd.read_parquet(f"{INPUT}/IDEPO.parquet")

    df = pd.concat([depo, idepo], ignore_index=True)
    df = df[df["CURBAL"] > 0]

    out = df.groupby("BRANCH").agg(
        TOT_OUTSTANDING=("CURBAL", "sum")
    ).reset_index()

    out.to_parquet(f"{OUTPUT}/EIBMRB02.parquet", index=False)

    with open(f"{OUTPUT}/EIBMRB02_REPORT.txt", "w") as f:
        f.write("REPORT ID : EIBMRB02\n")
        f.write("MONTHLY SA/CA/FD OUTSTANDING AMOUNT\n")
        f.write(f"AS AT {rpt:%d/%m/%Y}\n\n")
        f.write("BRANCH;TOTAL (RM)\n")
        for _, r in out.iterrows():
            f.write(f"{r.BRANCH};{r.TOT_OUTSTANDING:,.2f}\n")


# ============================================================
# EIBMRB03
# ============================================================

def eibmrb03():
    rpt = get_reptdate()

    cur = pd.concat([
        pd.read_parquet(f"{INPUT}/DEPO_CURRENT.parquet"),
        pd.read_parquet(f"{INPUT}/IDEPO_CURRENT.parquet")
    ])

    cis = pd.read_parquet(f"{INPUT}/CIS_DEPOSIT.parquet")

    cur = cur[
        (cur["CURCODE"] == "MYR") &
        (~cur["CUSTCODE"].isin([77, 78, 95, 96])) &
        (cur["OPENDT"].dt.year == rpt.year) &
        (cur["OPENDT"].dt.month == rpt.month)
    ]

    cur = cur.merge(cis[["ACCTNO", "CUSTNAME"]], on="ACCTNO", how="left")

    cur.to_parquet(f"{OUTPUT}/EIBMRB03.parquet", index=False)

    with open(f"{OUTPUT}/EIBMRB03_REPORT.txt", "w") as f:
        f.write("REPORT ID : EIBMRB03\n")
        f.write("LISTING OF NEW CA OPENED FOR THE MONTH\n")
        f.write(f"AS AT {rpt:%d/%m/%Y}\n\n")
        f.write("BRANCH;ACCTNO;NAME;BAL;OPEN DATE\n")
        for _, r in cur.iterrows():
            f.write(
                f"{r.BRANCH};{r.ACCTNO};{r.CUSTNAME};"
                f"{r.CURBAL:,.2f};{r.OPENDT:%d/%m/%Y}\n"
            )


# ============================================================
# EIBMRB04
# ============================================================

def eibmrb04():
    rpt = get_reptdate()

    fd = pd.concat([
        pd.read_parquet(f"{INPUT}/DEPO_FD.parquet"),
        pd.read_parquet(f"{INPUT}/IDEPO_FD.parquet")
    ])

    cis = pd.read_parquet(f"{INPUT}/CIS_DEPOSIT.parquet")

    fd = fd[
        (fd["CURCODE"] == "MYR") &
        (fd["OPENDT"].dt.year == rpt.year) &
        (fd["OPENDT"].dt.month == rpt.month)
    ]

    fd = fd.merge(cis[["ACCTNO", "CUSTNAME"]], on="ACCTNO", how="left")

    fd.to_parquet(f"{OUTPUT}/EIBMRB04.parquet", index=False)

    with open(f"{OUTPUT}/EIBMRB04_REPORT.txt", "w") as f:
        f.write("REPORT ID : EIBMRB04\n")
        f.write("LISTING OF NEW FD OPENED FOR THE MONTH\n")
        f.write(f"AS AT {rpt:%d/%m/%Y}\n\n")
        f.write("BRANCH;ACCTNO;NAME;BAL;OPEN DATE\n")
        for _, r in fd.iterrows():
            f.write(
                f"{r.BRANCH};{r.ACCTNO};{r.CUSTNAME};"
                f"{r.CURBAL:,.2f};{r.OPENDT:%d/%m/%Y}\n"
            )


# ============================================================
# EIBMRB05
# ============================================================

def eibmrb05():
    rpt = get_reptdate()

    df = pd.concat([
        pd.read_parquet(f"{INPUT}/DEPO.parquet"),
        pd.read_parquet(f"{INPUT}/IDEPO.parquet"),
        pd.read_parquet(f"{INPUT}/MISFD_FCYFD.parquet")
    ])

    out = df.groupby("BRANCH").agg(
        TOT_BALANCE=("CURBAL", "sum")
    ).reset_index()

    out.to_parquet(f"{OUTPUT}/EIBMRB05.parquet", index=False)

    with open(f"{OUTPUT}/EIBMRB05_REPORT.txt", "w") as f:
        f.write("REPORT ID : EIBMRB05\n")
        f.write("MONTH END REPORT BY BRANCH (FCY FD & FCY CA)\n")
        f.write(f"AS AT {rpt:%d/%m/%Y}\n\n")
        f.write("BRANCH;TOTAL BALANCE\n")
        for _, r in out.iterrows():
            f.write(f"{r.BRANCH};{r.TOT_BALANCE:,.2f}\n")


# ============================================================
# EIBMRB06
# ============================================================

def eibmrb06():
    rpt = get_reptdate()

    df = pd.read_parquet(f"{INPUT}/MISFD_FCYFD.parquet")
    cis = pd.read_parquet(f"{INPUT}/CIS_DEPOSIT.parquet")

    df = df[
        (df["CURCODE"] != "MYR") &
        (df["OPENDT"].dt.year == rpt.year) &
        (df["OPENDT"].dt.month == rpt.month)
    ]

    df = df.merge(cis[["ACCTNO", "CUSTNAME"]], on="ACCTNO", how="left")

    df.to_parquet(f"{OUTPUT}/EIBMRB06.parquet", index=False)

    with open(f"{OUTPUT}/EIBMRB06_REPORT.txt", "w") as f:
        f.write("REPORT ID : EIBMRB06\n")
        f.write("LISTING OF NEW FCY FD OPENED FOR THE MONTH\n")
        f.write(f"AS AT {rpt:%d/%m/%Y}\n\n")
        f.write("BRANCH;ACCTNO;NAME;BAL;OPEN DATE;CUR\n")
        for _, r in df.iterrows():
            f.write(
                f"{r.BRANCH};{r.ACCTNO};{r.CUSTNAME};"
                f"{r.CURBAL:,.2f};{r.OPENDT:%d/%m/%Y};{r.CURCODE}\n"
            )


# ============================================================
# EIBMRB07
# ============================================================

def eibmrb07():
    rpt = get_reptdate()

    df = pd.concat([
        pd.read_parquet(f"{INPUT}/DEPO_CURRENT.parquet"),
        pd.read_parquet(f"{INPUT}/IDEPO_CURRENT.parquet")
    ])

    cis = pd.read_parquet(f"{INPUT}/CIS_DEPOSIT.parquet")

    df = df[
        (df["CURCODE"] != "MYR") &
        (df["OPENDT"].dt.year == rpt.year) &
        (df["OPENDT"].dt.month == rpt.month)
    ]

    df = df.merge(cis[["ACCTNO", "CUSTNAME"]], on="ACCTNO", how="left")

    df.to_parquet(f"{OUTPUT}/EIBMRB07.parquet", index=False)

    with open(f"{OUTPUT}/EIBMRB07_REPORT.txt", "w") as f:
        f.write("REPORT ID : EIBMRB07\n")
        f.write("LISTING OF NEW FCY CA OPENED FOR THE MONTH\n")
        f.write(f"AS AT {rpt:%d/%m/%Y}\n\n")
        f.write("BRANCH;ACCTNO;NAME;BAL;OPEN DATE;CUR\n")
        for _, r in df.iterrows():
            f.write(
                f"{r.BRANCH};{r.ACCTNO};{r.CUSTNAME};"
                f"{r.CURBAL:,.2f};{r.OPENDT:%d/%m/%Y};{r.CURCODE}\n"
            )


# ============================================================
# EIBMRB08
# ============================================================

def eibmrb08():
    rpt = get_reptdate()

    w = pd.read_parquet(f"{INPUT}/MIS_FDWDRW.parquet")

    rm = w[w["CURCODE"] == "MYR"]
    fcy = w[w["CURCODE"] != "MYR"]

    rm.to_parquet(f"{OUTPUT}/EIBMRB8A.parquet", index=False)
    fcy.to_parquet(f"{OUTPUT}/EIBMRB8B.parquet", index=False)

    for name, df in [("EIBMRB8A", rm), ("EIBMRB8B", fcy)]:
        with open(f"{OUTPUT}/{name}_REPORT.txt", "w") as f:
            f.write(f"REPORT ID : {name}\n")
            f.write("MONTHLY FD RECEIPTS WITHDRAWALS\n")
            f.write(f"AS AT {rpt:%d/%m/%Y}\n\n")
            f.write("ACCTNO;AMOUNT;REASON;PRODUCT\n")
            for _, r in df.iterrows():
                f.write(
                    f"{r.ACCTNO};{r.TRANAMT:,.2f};"
                    f"{r.RSONCODE};{r.PRODCD}\n"
                )


# ============================================================
# EIBMRB09
# ============================================================

def eibmrb09():
    rpt = get_reptdate()

    w = pd.read_parquet(f"{INPUT}/MIS_FDWDRW.parquet")
    rm = w[w["CURCODE"] == "MYR"]

    out = rm.groupby(["RSONCODE", "PRODCD"]).agg(
        COUNT=("TRANAMT", "count"),
        AMOUNT=("TRANAMT", "sum")
    ).reset_index()

    out.to_parquet(f"{OUTPUT}/EIBMRB09.parquet", index=False)

    with open(f"{OUTPUT}/EIBMRB09_REPORT.txt", "w") as f:
        f.write("REPORT ID : EIBMRB09\n")
        f.write("MONTHLY FD WITHDRAWALS BY PRODUCT TYPE\n")
        f.write(f"AS AT {rpt:%d/%m/%Y}\n\n")
        f.write("REASON;PRODUCT;COUNT;AMOUNT\n")
        for _, r in out.iterrows():
            f.write(
                f"{r.RSONCODE};{r.PRODCD};"
                f"{int(r.COUNT)};{r.AMOUNT:,.2f}\n"
            )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
