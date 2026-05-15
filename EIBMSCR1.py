#!/usr/bin/env python3

import pandas as pd
from datetime import datetime
import os


# =========================================================
# PATH CONFIGURATION
# =========================================================

BASE_PATH = "Data_Warehouse/MIS/XMIS"

INPUT_PATH = f"{BASE_PATH}/input_testing_file"

OUTPUT_PATH = f"{BASE_PATH}/output"


# =========================================================
# FILE CONFIGURATION
# =========================================================

BRHFI_FILE = f"{INPUT_PATH}/BRHFI.csv"

SRSBR_FILE = f"{INPUT_PATH}/SRSBR.sas7bdat"

REPORT_FILE = f"{OUTPUT_PATH}/EIBMSCR1_REPORT.txt"


# =========================================================
# CREATE OUTPUT DIRECTORY
# =========================================================

os.makedirs(OUTPUT_PATH, exist_ok=True)


# =========================================================
# PRINT1 (MAINFRAME OUTPUT ROUTING EQUIVALENT)
# =========================================================

PRINT1 = {
    "CLASS": "K",
    "DEST": "LOCAL",
    "NAME": "ATTN: EN MOHD BADRAN SAADULLAH",
    "ROOM": "13TH FLOOR",
    "BUILDING": "MENARA PBB",
    "DEPT": "CARD PRODUCT & DEVELOPMENT"
}


# =========================================================
# REPORT DATE
# =========================================================

today = datetime.today()

RDATE = today.strftime("%d/%m/%Y")
RMM = today.strftime("%m")
RMON = today.strftime("%b%Y").upper()
RYY = today.strftime("%y")
RYEAR = today.strftime("%Y")


# =========================================================
# READ BRHFI CSV
# =========================================================

print("Reading BRHFI.csv ...")

BRH = pd.read_csv(
    BRHFI_FILE,
    dtype={
        "BRANCH": int,
        "BRCHCD": str
    }
)

BRH["BRCHCD"] = BRH["BRCHCD"].str.strip()


# =========================================================
# READ SRSBR SAS DATASET
# =========================================================

print("Reading SRSBR.sas7bdat ...")

SRSBR = pd.read_sas(
    SRSBR_FILE,
    format="sas7bdat"
)


# =========================================================
# DECODE BYTE COLUMNS
# =========================================================

for col in SRSBR.select_dtypes(include="object").columns:

    try:
        SRSBR[col] = SRSBR[col].str.decode("utf-8").str.strip()

    except Exception:
        pass


# =========================================================
# REPLACE NULL ONLY FOR NUMERIC COLUMNS
# =========================================================

print("Replacing missing numeric values with 0 ...")

numeric_cols = SRSBR.select_dtypes(include=["number"]).columns

SRSBR[numeric_cols] = SRSBR[numeric_cols].fillna(0)


# =========================================================
# SORT
# =========================================================

print("Sorting datasets ...")

BRH = BRH.sort_values("BRCHCD")

SRSBR = SRSBR.sort_values("BRCHCD")


# =========================================================
# MERGE
# =========================================================

print("Merging datasets ...")

SRS = pd.merge(
    SRSBR,
    BRH,
    on="BRCHCD",
    how="left"
)


# =========================================================
# FINAL SORT
# =========================================================

print("Final sorting ...")

SRS = SRS.sort_values(
    ["BRANCH", "STAFF", "PRODUCT"]
)


# =========================================================
# GENERATE REPORT
# =========================================================

print("Generating report ...")

with open(REPORT_FILE, "w", encoding="utf-8") as rpt:

    grouped = SRS.groupby("BRANCH")

    for branch, df in grouped:

        brchcd = df.iloc[0]["BRCHCD"]

        # =================================================
        # HEADER
        # =================================================

        rpt.write(
            "REPORT NO: STAFF PARTICIPATION UNDER SCR SCHEME BY BRANCH"
        )

        rpt.write(
            f"{'':40}REPORT DATE={RDATE}\n"
        )

        rpt.write("PROGRAM ID : EIBMSCR1\n")

        rpt.write(
            f"BRANCH=NO.: {int(branch):03d}   {brchcd}\n"
        )

        rpt.write(
            "---------------------------------------------------------------------------------------------------------------------------------\n"
        )

        rpt.write(
            f"{'STAFF':<8}"
            f"{'PRODUCT':<20}"
            f"{'C1CNT':>8}"
            f"{'C1BAL':>18}"
            f"{'C2CNT':>8}"
            f"{'C2BAL':>18}"
            f"{'C3CNT':>8}"
            f"{'C3BAL':>18}"
            f"{'C4CNT':>8}"
            f"{'C5CNT':>8}\n"
        )

        rpt.write(
            "---------------------------------------------------------------------------------------------------------------------------------\n"
        )

        # =================================================
        # INITIALIZE TOTALS
        # =================================================

        TC1CNT = 0
        TC1BAL = 0

        TC2CNT = 0
        TC2BAL = 0

        TC3CNT = 0
        TC3BAL = 0

        TC4CNT = 0
        TC5CNT = 0

        # =================================================
        # DETAIL RECORDS
        # =================================================

        for _, row in df.iterrows():

            TC1CNT += row["C1CNT"]
            TC1BAL += row["C1BAL"]

            TC2CNT += row["C2CNT"]
            TC2BAL += row["C2BAL"]

            TC3CNT += row["C3CNT"]
            TC3BAL += row["C3BAL"]

            TC4CNT += row["C4CNT"]
            TC5CNT += row["C5CNT"]

            rpt.write(
                f"{int(row['STAFF']):<8}"
                f"{str(row['PRODUCT']):<20}"
                f"{row['C1CNT']:>8.0f}"
                f"{row['C1BAL']:>18,.2f}"
                f"{row['C2CNT']:>8.0f}"
                f"{row['C2BAL']:>18,.2f}"
                f"{row['C3CNT']:>8.0f}"
                f"{row['C3BAL']:>18,.2f}"
                f"{row['C4CNT']:>8.0f}"
                f"{row['C5CNT']:>8.0f}\n"
            )

        # =================================================
        # BRANCH TOTAL
        # =================================================

        rpt.write(
            "---------------------------------------------------------------------------------------------------------------------------------\n"
        )

        rpt.write(
            f"{'BRANCH TOTAL=':<28}"
            f"{TC1CNT:>8.0f}"
            f"{TC1BAL:>18,.2f}"
            f"{TC2CNT:>8.0f}"
            f"{TC2BAL:>18,.2f}"
            f"{TC3CNT:>8.0f}"
            f"{TC3BAL:>18,.2f}"
            f"{TC4CNT:>8.0f}"
            f"{TC5CNT:>8.0f}\n"
        )

        rpt.write(
            "---------------------------------------------------------------------------------------------------------------------------------\n\n"
        )


# =========================================================
# PRINT1 OUTPUT INFO
# =========================================================

print("\n====================================")
print("PRINT1 OUTPUT ROUTING")
print("====================================")
print("CLASS :", PRINT1["CLASS"])
print("DEST  :", PRINT1["DEST"])
print("NAME  :", PRINT1["NAME"])
print("ROOM  :", PRINT1["ROOM"])
print("BUILD :", PRINT1["BUILDING"])
print("DEPT  :", PRINT1["DEPT"])
print("REPORT:", REPORT_FILE)
print("====================================")


# =========================================================
# OPTIONAL WINDOWS PRINT
# =========================================================

# os.startfile(REPORT_FILE, "print")


# =========================================================
# COMPLETED
# =========================================================

print(f"\nReport successfully generated:")
print(REPORT_FILE)
