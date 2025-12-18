    # =====================================================
    # FROM3T5 – CALCULATE RATEA
    # =====================================================
    FROM3T5_SUM["RATEA"] = (
        FROM3T5_SUM["EXPECTEDREC"] / FROM3T5_SUM["OBDEFAULT"]
    ) * 100

    RATEA = float(FROM3T5_SUM["RATEA"].iloc[0])

    # =====================================================
    # FROM6AB – CALCULATE RATEB
    # =====================================================
    FROM6AB = MONTH6AB_GRP.copy()
    FROM6AB["IND"] = "COUNTRATE"

    FROM6AB["EXPECTEDREC_NEW"] = np.where(
        FROM6AB["CATEGORY"] == "SUCCESSFUL REPOSSESSION",
        (RECRATE * FROM6AB["OBDEFAULT"]) / 100,
        0
    )

    FROM6AB = FROM6AB[
        FROM6AB["CATEGORY"].isin([
            "CONTINUE PAYING",
            "SUCCESSFUL REPOSSESSION",
            "UNSUCCESSFUL REPOSSESSION"
        ])
    ]

    FROM6AB_SUM = (
        FROM6AB
        .groupby("IND", as_index=False)
        .agg(
            OBDEFAULT=("OBDEFAULT", "sum"),
            EXPECTEDREC_NEW=("EXPECTEDREC_NEW", "sum")
        )
    )

    FROM6AB_SUM["RATEB"] = (
        FROM6AB_SUM["EXPECTEDREC_NEW"] / FROM6AB_SUM["OBDEFAULT"]
    ) * 100

    RATEB = float(FROM6AB_SUM["RATEB"].iloc[0])

    # =====================================================
    # MONTH1T2_GRP
    # =====================================================
    MONTH1T2_GRP_ROWS = []

    def add_m1t2(category, rate, recrate, cap_zero=False):
        df = MONTH1T2.copy()
        df["CATEGORY"] = category
        df["GROUPIND"] = "OTHERS"
        df["SUBGIND"]  = "1-2 MTHS"
        df["RATE"]     = rate
        df["RECRATE"]  = recrate
        df["OBDEFAULT"] = df["BALANCE"] * (rate / 100)
        df["EXPECTEDREC"] = df["OBDEFAULT"] * (recrate / 100)
        df["CAPROVISION"] = (
            0 if cap_zero else df["OBDEFAULT"] - df["EXPECTEDREC"]
        )
        MONTH1T2_GRP_ROWS.append(df)

    add_m1t2("CONTINUE PAYING", 92.83, 100, cap_zero=True)
    add_m1t2("SUCCESSFUL REPOSSESSION", 2.39, RECRATE)
    add_m1t2("UNSUCCESSFUL REPOSSESSION", 4.78, 0.00)
    add_m1t2("- 3-5 MONTHS IN ARREARS", 2.28, round(RATEA, 2), cap_zero=True)
    add_m1t2("- >6 MONTHS IN ARREARS", 2.04, round(RATEB, 2), cap_zero=True)
    add_m1t2("- OTHERS", 0.46, 0.00, cap_zero=True)

    MONTH1T2_GRP = pd.concat(MONTH1T2_GRP_ROWS, ignore_index=True)

    MONTH1T2_GRP = (
        MONTH1T2_GRP
        .groupby(
            ["GROUPIND","SUBGIND","CATEGORY","RATE","RECRATE"],
            as_index=False
        )
        .agg(
            BALANCE=("BALANCE","sum"),
            OBDEFAULT=("OBDEFAULT","sum"),
            EXPECTEDREC=("EXPECTEDREC","sum"),
            CAPROVISION=("CAPROVISION","sum")
        )
    )

    # =====================================================
    # FROM1T2 – CALCULATE RATEC
    # =====================================================
    FROM1T2 = MONTH1T2_GRP.copy()
    FROM1T2["IND"] = "COUNTRATE"

    SUMOUTBAL = float(
        FROM1T2.loc[
            FROM1T2["CATEGORY"] == "UNSUCCESSFUL REPOSSESSION",
            "OBDEFAULT"
        ].iloc[0]
    )

    FROM1T2 = FROM1T2[
        FROM1T2["CATEGORY"].isin([
            "- 3-5 MONTHS IN ARREARS",
            "- >6 MONTHS IN ARREARS",
            "- OTHERS"
        ])
    ]

    FROM1T2_SUM = (
        FROM1T2
        .groupby("IND", as_index=False)
        .agg(
            OBDEFAULT=("OBDEFAULT","sum"),
            EXPECTEDREC=("EXPECTEDREC","sum")
        )
    )

    RATEC = (FROM1T2_SUM["EXPECTEDREC"].iloc[0] / SUMOUTBAL) * 100
    SUMRECBAL = FROM1T2_SUM["EXPECTEDREC"].iloc[0]

    # APPLY RATEC BACK
    mask = MONTH1T2_GRP["CATEGORY"] == "UNSUCCESSFUL REPOSSESSION"
    MONTH1T2_GRP.loc[mask, "EXPECTEDREC"] = SUMRECBAL
    MONTH1T2_GRP.loc[mask, "RECRATE"] = RATEC
    MONTH1T2_GRP.loc[mask, "CAPROVISION"] = (
        MONTH1T2_GRP.loc[mask, "OBDEFAULT"] - SUMRECBAL
    )

    # =====================================================
    # IRREGULAR_GRP
    # =====================================================
    IRREGUALR_GRP = IRREGULAR.copy()
    IRREGUALR_GRP["GROUPIND"] = "IRREGULAR"
    IRREGUALR_GRP["RECRATE"] = 0.00
    IRREGUALR_GRP["OBDEFAULT"] = IRREGUALR_GRP["BALANCE"]
    IRREGUALR_GRP["EXPECTEDREC"] = 0.00
    IRREGUALR_GRP["CAPROVISION"] = IRREGUALR_GRP["OBDEFAULT"]
    IRREGUALR_GRP["NO"] = 51

    IRREGUALR_GRP = (
        IRREGUALR_GRP
        .groupby(["GROUPIND","NO","RECRATE"], as_index=False)
        .agg(
            BALANCE=("BALANCE","sum"),
            OBDEFAULT=("OBDEFAULT","sum"),
            EXPECTEDREC=("EXPECTEDREC","sum"),
            CAPROVISION=("CAPROVISION","sum")
        )
    )
    IRREGUALR_GRP["GROUP"] = "IRREGUALR"

    # =====================================================
    # REPOSSESSED_GRP
    # =====================================================
    REPOSSESSED_GRP = REPOSSESSED.copy()
    REPOSSESSED_GRP["GROUPIND"] = "REPOSSESSED"
    REPOSSESSED_GRP["RECRATE"] = RECRATE
    REPOSSESSED_GRP["OBDEFAULT"] = REPOSSESSED_GRP["BALANCE"]
    REPOSSESSED_GRP["EXPECTEDREC"] = (
        REPOSSESSED_GRP["OBDEFAULT"] * (RECRATE / 100)
    )
    REPOSSESSED_GRP["CAPROVISION"] = (
        REPOSSESSED_GRP["OBDEFAULT"] - REPOSSESSED_GRP["EXPECTEDREC"]
    )
    REPOSSESSED_GRP["NO"] = 61

    REPOSSESSED_GRP = (
        REPOSSESSED_GRP
        .groupby(["GROUPIND","NO","RECRATE"], as_index=False)
        .agg(
            BALANCE=("BALANCE","sum"),
            OBDEFAULT=("OBDEFAULT","sum"),
            EXPECTEDREC=("EXPECTEDREC","sum"),
            CAPROVISION=("CAPROVISION","sum")
        )
    )
    REPOSSESSED_GRP["GROUP"] = "REPOSSESSED"

    # =====================================================
    # DEFICIT_GRP
    # =====================================================
    DEFICIT_GRP = DEFICIT.copy()
    DEFICIT_GRP["GROUPIND"] = "DEFICIT"
    DEFICIT_GRP["RECRATE"] = 0.00
    DEFICIT_GRP["OBDEFAULT"] = DEFICIT_GRP["BALANCE"]
    DEFICIT_GRP["EXPECTEDREC"] = 0.00
    DEFICIT_GRP["CAPROVISION"] = DEFICIT_GRP["OBDEFAULT"]
    DEFICIT_GRP["NO"] = 71

    DEFICIT_GRP = (
        DEFICIT_GRP
        .groupby(["GROUPIND","NO","RECRATE"], as_index=False)
        .agg(
            BALANCE=("BALANCE","sum"),
            OBDEFAULT=("OBDEFAULT","sum"),
            EXPECTEDREC=("EXPECTEDREC","sum"),
            CAPROVISION=("CAPROVISION","sum")
        )
    )
    DEFICIT_GRP["GROUP"] = "DEFICIT"

    # =====================================================
    # COMBINE + TOTAL
    # =====================================================
    COMBINE = pd.concat([
        CURRENT_GRP,
        MONTH1T2_GRP,
        MONTH3T5_GRP,
        MONTH6AB_GRP,
        IRREGUALR_GRP,
        REPOSSESSED_GRP,
        DEFICIT_GRP
    ], ignore_index=True)

    TOTAL = COMBINE.copy()
    TOTAL["GROUPIND"] = "TOTAL"
    TOTAL["NO"] = 81

    TOTAL_SUM = (
        TOTAL
        .groupby("GROUPIND", as_index=False)
        .agg(
            BALANCE=("BALANCE","sum"),
            OBDEFAULT=("OBDEFAULT","sum"),
            EXPECTEDREC=("EXPECTEDREC","sum")
        )
    )

    COMBINE = pd.concat([COMBINE, TOTAL_SUM], ignore_index=True)

    print("[EIFMNP41] PART 2 COMPLETED")
==============================================================================================================================

# EIFMNP42.py
# Python replacement for SAS program EIFMNP42

import pandas as pd
import numpy as np

# =========================================================
# ENTRY POINT
# =========================================================

def run():
    print("[EIFMNP42] STARTED")

    # -----------------------------------------------------
    # REPTDATE (same logic as SAS)
    # -----------------------------------------------------
    REPTDATE_DF = pd.read_parquet("/data/sap/PBB/MNILN/REPTDATE.parquet")
    REPTDATE = pd.to_datetime(REPTDATE_DF["REPTDATE"].iloc[0])

    DAY = REPTDATE.day
    if DAY <= 8:
        WK = "1"
    elif DAY <= 15:
        WK = "2"
    elif DAY <= 22:
        WK = "3"
    else:
        WK = "4"

    REPTMON  = f"{REPTDATE.month:02d}"
    NOWK     = WK
    REPTYEAR = f"{REPTDATE.year % 100:02d}"
    REPTDAY  = f"{REPTDATE.day:02d}"

    # PREVIOUS MONTH / YEAR END
    YEAREND  = pd.Timestamp(year=REPTDATE.year, month=1, day=1) - pd.Timedelta(days=1)
    PREVMON  = pd.Timestamp(year=REPTDATE.year, month=REPTDATE.month, day=1) - pd.Timedelta(days=1)

    LMON  = f"{YEAREND.month:02d}"
    LYEAR = f"{YEAREND.year % 100:02d}"
    REPTMON1  = f"{PREVMON.month:02d}"
    REPTYEAR1 = f"{PREVMON.year % 100:02d}"

    # -----------------------------------------------------
    # CREDSUB
    # -----------------------------------------------------
    CREDSUB = pd.read_parquet(
        f"/data/sap/PBB/CCRIS/CREDSUB/CREDMSUBAC{REPTMON}{REPTYEAR}.parquet"
    )

    CREDSUB = (
        CREDSUB[CREDSUB["FACILITY"].isin(["34331", "34332"])]
        .rename(columns={"ACCTNUM": "ACCTNO", "DAYSARR": "DAYARR"})
        [["ACCTNO", "DAYARR", "NOTENO"]]
    )

    # -----------------------------------------------------
    # HP DATA
    # -----------------------------------------------------
    HP = pd.read_parquet(
        f"/data/sap/PBB/HPDATAWH/HP{REPTMON}{NOWK}{REPTYEAR}.parquet"
    )

    HP = HP[HP["BALANCE"] > 0]
    HP["BRANCHABBR"] = HP["BRANCH"].astype(str).str.zfill(3)

    HP["IND"] = np.where(
        HP["PRODUCT"].isin([700,705,720,725,380,381]),
        "PBB",
        ""
    )

    HP = HP[HP["IND"] != ""]

    # -----------------------------------------------------
    # SORT + MERGE HP & CREDSUB
    # -----------------------------------------------------
    CREDSUB = (
        CREDSUB
        .sort_values(["ACCTNO","NOTENO","DAYARR"], ascending=[True,True,False])
        .drop_duplicates(["ACCTNO","NOTENO"])
    )

    HP = HP.sort_values(["ACCTNO","NOTENO"])

    HP = HP.merge(
        CREDSUB,
        on=["ACCTNO","NOTENO"],
        how="left"
    )

    # -----------------------------------------------------
    # CATEGORY ASSIGNMENT (exact SAS logic)
    # -----------------------------------------------------
    def assign_category(r):
        if r["DAYARR"] <= 30 and r["BORSTAT"] not in ["F","I","R","E","W","Z"] \
           and r["USER5"] != "N" and r["PAIDIND"] == "M":
            return "CURRENT"

        if 31 <= r["DAYARR"] <= 89 and r["BORSTAT"] not in ["F","I","R","E","W","Z"] \
           and r["USER5"] != "N" and r["PAIDIND"] == "M":
            return "1-2 MTHS"

        if r["BORSTAT"] not in ["F","I","R","E","W","Z"] and (
            (r["USER5"] == "N" and r["DAYARR"] <= 182) or
            (90 <= r["DAYARR"] <= 182)
        ) and r["PAIDIND"] == "M":
            return "3-5 MTHS"

        if r["BORSTAT"] not in ["F","I","R","E","W","Z"] and (
            (r["USER5"] == "N" and r["DAYARR"] >= 183) or
            (r["DAYARR"] >= 183)
        ) and r["PAIDIND"] == "M":
            return ">=6 MTHS"

        if r["BORSTAT"] == "I" and r["PAIDIND"] == "M":
            return "IRREGULAR"

        if r["BORSTAT"] == "R" and r["PAIDIND"] == "M":
            return "REPOSSESSED"

        if r["BORSTAT"] == "F" and r["PAIDIND"] == "M":
            return "DEFICIT"

        return ""

    HP["CATEGORY"] = HP.apply(assign_category, axis=1)
    HP = HP[HP["CATEGORY"] != ""]

    # -----------------------------------------------------
    # SUMMARY BALANCE BY CATEGORY
    # -----------------------------------------------------
    SUMBALOLD = (
        HP.groupby("CATEGORY", as_index=False)
          .agg(BALANCE=("BALANCE","sum"))
    )

    # -----------------------------------------------------
    # READ CAP PROVISION FROM EIFMNP41 OUTPUT
    # -----------------------------------------------------
    CAP1OLD = pd.read_parquet("/data/sap/PBB/NPL/HP/CAP1OLD.parquet")

    COUNTCAP = CAP1OLD.merge(SUMBALOLD, on="CATEGORY", how="left")
    COUNTCAP["CARATE"] = (COUNTCAP["CAPROVISION"] / COUNTCAP["BALANCE"]) * 100

    COUNTCAP.loc[
        COUNTCAP["CATEGORY"].isin([">=6 MTHS","IRREGULAR","DEFICIT"]),
        "CARATE"
    ] = 100

    # -----------------------------------------------------
    # APPLY CAP RATE TO ACCOUNT LEVEL
    # -----------------------------------------------------
    CAPOLD = HP.merge(
        COUNTCAP[["CATEGORY","CARATE"]],
        on="CATEGORY",
        how="left"
    )

    CAPOLD["CAP"] = (CAPOLD["BALANCE"] * CAPOLD["CARATE"]) / 100

    # -----------------------------------------------------
    # WRITE OUTPUT (NPL.CAPOLD&REPTMON&REPTYEAR)
    # -----------------------------------------------------
    CAPOLD.to_parquet(
        f"/data/sap/PBB/NPL/HP/CAPOLD{REPTMON}{REPTYEAR}.parquet",
        index=False
    )

    print("[EIFMNP42] COMPLETED")

==============================================================================================================================

# EIFMNP43.py
# Python replacement for SAS program EIFMNP43

import pandas as pd

# =========================================================
# ENTRY POINT
# =========================================================

def run():
    print("[EIFMNP43] STARTED")

    # -----------------------------------------------------
    # REPTDATE (same as SAS)
    # -----------------------------------------------------
    REPTDATE_DF = pd.read_parquet("/data/sap/PBB/MNILN/REPTDATE.parquet")
    REPTDATE = pd.to_datetime(REPTDATE_DF["REPTDATE"].iloc[0])

    DAY = REPTDATE.day
    if DAY <= 8:
        WK = "1"
    elif DAY <= 15:
        WK = "2"
    elif DAY <= 22:
        WK = "3"
    else:
        WK = "4"

    REPTMON  = f"{REPTDATE.month:02d}"
    REPTYEAR = f"{REPTDATE.year % 100:02d}"
    REPTDAY  = f"{REPTDATE.day:02d}"

    DATE = f"{REPTDAY}/{REPTMON}/{REPTYEAR}"

    # -----------------------------------------------------
    # READ NPL.CAPOLD&REPTMON&REPTYEAR
    # -----------------------------------------------------
    BYCAT = pd.read_parquet(
        f"/data/sap/PBB/NPL/HP/CAPOLD{REPTMON}{REPTYEAR}.parquet"
    )

    # -----------------------------------------------------
    # ASSIGN NO (same order as SAS)
    # -----------------------------------------------------
    def category_no(cat):
        return {
            "CURRENT": 1,
            "1-2 MTHS": 2,
            "3-5 MTHS": 3,
            ">=6 MTHS": 4,
            "IRREGULAR": 5,
            "REPOSSESSED": 6,
            "DEFICIT": 7
        }.get(cat, 99)

    BYCAT["NO"] = BYCAT["CATEGORY"].map(category_no)

    # -----------------------------------------------------
    # SORT BY NO (PROC SORT)
    # -----------------------------------------------------
    BYCAT = BYCAT.sort_values("NO")

    # -----------------------------------------------------
    # PROC TABULATE replacement
    # CLASS NO CATEGORY BRANCH1
    # VAR BALANCE OPEN_BALANCE SUSPEND WRBACK WRIOFF_BAL CAP NET
    # -----------------------------------------------------
    TABULATE = (
        BYCAT
        .groupby(["NO", "CATEGORY", "BRANCH1"], as_index=False)
        .agg(
            BALANCE=("BALANCE", "sum"),
            OPEN_BALANCE=("OPEN_BALANCE", "sum"),
            SUSPEND=("SUSPEND", "sum"),
            WRBACK=("WRBACK", "sum"),
            WRIOFF_BAL=("WRIOFF_BAL", "sum"),
            CAP=("CAP", "sum"),
            NET=("NET", "sum")
        )
    )

    # -----------------------------------------------------
    # SUB TOTAL BY CATEGORY (ALL='SUB TOTAL')
    # -----------------------------------------------------
    SUB_TOTAL = (
        TABULATE
        .groupby(["NO", "CATEGORY"], as_index=False)
        .agg(
            BALANCE=("BALANCE", "sum"),
            OPEN_BALANCE=("OPEN_BALANCE", "sum"),
            SUSPEND=("SUSPEND", "sum"),
            WRBACK=("WRBACK", "sum"),
            WRIOFF_BAL=("WRIOFF_BAL", "sum"),
            CAP=("CAP", "sum"),
            NET=("NET", "sum")
        )
    )

    SUB_TOTAL["BRANCH1"] = "SUB TOTAL"

    # -----------------------------------------------------
    # GRAND TOTAL (ALL='GRAND TOTAL')
    # -----------------------------------------------------
    GRAND_TOTAL = (
        TABULATE
        .agg(
            BALANCE=("BALANCE", "sum"),
            OPEN_BALANCE=("OPEN_BALANCE", "sum"),
            SUSPEND=("SUSPEND", "sum"),
            WRBACK=("WRBACK", "sum"),
            WRIOFF_BAL=("WRIOFF_BAL", "sum"),
            CAP=("CAP", "sum"),
            NET=("NET", "sum")
        )
        .to_frame()
        .T
    )

    GRAND_TOTAL["NO"] = 99
    GRAND_TOTAL["CATEGORY"] = "GRAND TOTAL"
    GRAND_TOTAL["BRANCH1"] = "GRAND TOTAL"

    # -----------------------------------------------------
    # COMBINE ALL
    # -----------------------------------------------------
    FINAL_REPORT = pd.concat(
        [TABULATE, SUB_TOTAL, GRAND_TOTAL],
        ignore_index=True
    )

    FINAL_REPORT = FINAL_REPORT.sort_values(["NO", "CATEGORY", "BRANCH1"])

    # -----------------------------------------------------
    # OUTPUT (equivalent to SASLIST)
    # -----------------------------------------------------
    FINAL_REPORT.to_csv(
        f"/data/sap/PBB/OUTPUT/CAPCATE_OLD_TEXT.csv",
        index=False
    )

    print("[EIFMNP43] COMPLETED")
# EIFMNP44.py
# Python replacement for SAS program EIFMNP44
# Interface CAP to ECCRIS for all accounts
==============================================================================================================================
import pandas as pd

# =========================================================
# ENTRY POINT
# =========================================================

def run():
    print("[EIFMNP44] STARTED")

    # -----------------------------------------------------
    # REPTDATE (same logic as SAS)
    # -----------------------------------------------------
    REPTDATE_DF = pd.read_parquet("/data/sap/PBB/MNILN/REPTDATE.parquet")
    REPTDATE = pd.to_datetime(REPTDATE_DF["REPTDATE"].iloc[0])

    DAY = REPTDATE.day
    if DAY <= 8:
        WK = "1"
    elif DAY <= 15:
        WK = "2"
    elif DAY <= 22:
        WK = "3"
    else:
        WK = "4"

    REPTMON  = f"{REPTDATE.month:02d}"
    REPTYEAR = f"{REPTDATE.year % 100:02d}"

    # -----------------------------------------------------
    # READ NPL.CAPOLD&REPTMON&REPTYEAR
    # -----------------------------------------------------
    CAPOLD = pd.read_parquet(
        f"/data/sap/PBB/NPL/HP/CAPOLD{REPTMON}{REPTYEAR}.parquet"
    )

    # -----------------------------------------------------
    # WRITE FIXED-WIDTH CCRIS FILE
    # (matches SAS PUT positions exactly)
    # -----------------------------------------------------
    output_path = "/data/sap/PBB/OUTPUT/FSAS5_OLD_TEXT.txt"

    with open(output_path, "w") as f:
        for _, r in CAPOLD.iterrows():

            acctno = str(int(r["ACCTNO"])).ljust(10)          # @001 10
            noteno = str(int(r["NOTENO"])).zfill(5)           # @012 Z5
            branch = str(int(r["BRANCH"])).zfill(5)           # @018 Z5
            capval = f"{r['CAP']:20.2f}"                       # @024 20.2
            aano   = str(r["AANO"]).ljust(13)                 # @045 $CHAR13

            line = (
                acctno +
                noteno +
                branch +
                capval +
                aano
            )

            f.write(line + "\n")

    print(f"[EIFMNP44] OUTPUT WRITTEN: {output_path}")
    print("[EIFMNP44] COMPLETED")



==============================================================================================================================
