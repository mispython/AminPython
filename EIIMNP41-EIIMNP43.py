import pandas as pd
import numpy as np

# ======================================================
# Helpers
# ======================================================

def summarize(df, keys):
    return (
        df.groupby(keys, as_index=False)
          .agg(
              BALANCE=("BALANCE", "sum"),
              OBDEFAULT=("OBDEFAULT", "sum"),
              EXPECTEDREC=("EXPECTEDREC", "sum"),
              CAPROVISION=("CAPROVISION", "sum")
          )
    )

# ======================================================
# Report date logic (macro replacement)
# ======================================================

def derive_report_vars(reptdate: pd.Timestamp):
    d = reptdate.day
    if d <= 8:
        wk = "1"
    elif d <= 15:
        wk = "2"
    elif d <= 22:
        wk = "3"
    else:
        wk = "4"

    return {
        "REPTMON": f"{reptdate.month:02d}",
        "NOWK": wk,
        "REPTYEAR": reptdate.strftime("%y")
    }

# ======================================================
# Read recovery rate
# ======================================================

def read_recrate(text_df):
    return float(text_df.iloc[0]["REC_RATE"])

# ======================================================
# Prepare HP + CCRIS
# ======================================================

def prepare_hp(hp, ccris):
    ccris = (
        ccris.query("FACILITY in ['34331','34332']")
             .rename(columns={"ACCTNUM": "ACCTNO", "DAYSARR": "DAYARR"})
             [["ACCTNO", "NOTENO", "DAYARR"]]
             .sort_values(["ACCTNO", "NOTENO", "DAYARR"],
                          ascending=[True, True, False])
             .drop_duplicates(["ACCTNO", "NOTENO"])
    )

    return (
        hp.sort_values(["ACCTNO", "NOTENO"])
          .merge(ccris, on=["ACCTNO", "NOTENO"], how="left")
    )

# ======================================================
# Bucket accounts
# ======================================================

def split_buckets(hp):
    base = (
        hp["PRODUCT"].isin([128, 130]) &
        (hp["BALANCE"] > 0) &
        (hp["PAIDIND"] == "M")
    )

    current = hp[
        base &
        (hp["DAYARR"] <= 30) &
        ~hp["BORSTAT"].isin(list("FIREWZ")) &
        (hp["USER5"] != "N")
    ]

    m1t2 = hp[
        base &
        hp["DAYARR"].between(31, 89) &
        ~hp["BORSTAT"].isin(list("FIREWZ")) &
        (hp["USER5"] != "N")
    ]

    m3t5 = hp[
        base &
        ~hp["BORSTAT"].isin(list("FIREWZ")) &
        (
            ((hp["USER5"] == "N") & (hp["DAYARR"] <= 182)) |
            hp["DAYARR"].between(90, 182)
        )
    ]

    m6ab = hp[
        base &
        ~hp["BORSTAT"].isin(list("FIREWZ")) &
        (hp["DAYARR"] >= 183)
    ]

    irregular = hp[(hp["BORSTAT"] == "I") & (hp["PAIDIND"] == "M")]
    repossessed = hp[(hp["BORSTAT"] == "R") & (hp["PAIDIND"] == "M")]
    deficit = hp[(hp["BORSTAT"] == "F") & (hp["PAIDIND"] == "M")]

    return current, m1t2, m3t5, m6ab, irregular, repossessed, deficit

# ======================================================
# Build group rows
# ======================================================

def build_grp(df, subg, rules):
    rows = []
    for _, r in df.iterrows():
        for cat, rate, recrate, capflag in rules:
            ob = r["BALANCE"] * rate / 100
            exp = ob * recrate / 100
            rows.append({
                "CATEGORY": cat,
                "GROUPIND": "OTHERS",
                "SUBGIND": subg,
                "RATE": rate,
                "RECRATE": recrate,
                "BALANCE": r["BALANCE"],
                "OBDEFAULT": ob,
                "EXPECTEDREC": exp,
                "CAPROVISION": ob - exp if capflag else 0
            })
    return pd.DataFrame(rows)

# ======================================================
# Rate calculations
# ======================================================

def calc_ratea(m3t5_grp):
    f = m3t5_grp[m3t5_grp["CATEGORY"].isin([
        "CONTINUE PAYING",
        "SUCCESSFUL REPOSSESSION",
        "UNSUCCESSFUL REPOSSESSION"
    ])]
    return round((f["EXPECTEDREC"].sum() / f["OBDEFAULT"].sum()) * 100, 2)

def calc_rateb(m6ab_grp, recrate):
    df = m6ab_grp.copy()
    df["EXPECTEDREC_NEW"] = np.where(
        df["CATEGORY"] == "SUCCESSFUL REPOSSESSION",
        df["OBDEFAULT"] * recrate / 100,
        0
    )
    f = df[df["CATEGORY"].isin([
        "CONTINUE PAYING",
        "SUCCESSFUL REPOSSESSION",
        "UNSUCCESSFUL REPOSSESSION"
    ])]
    return round((f["EXPECTEDREC_NEW"].sum() / f["OBDEFAULT"].sum()) * 100, 2)

def calc_ratec(m1t2_grp):
    sum_out = m1t2_grp.loc[
        m1t2_grp["CATEGORY"] == "UNSUCCESSFUL REPOSSESSION",
        "OBDEFAULT"
    ].sum()

    f = m1t2_grp[m1t2_grp["CATEGORY"].isin([
        "- 3-5 MONTHS IN ARREARS",
        "- >6 MONTHS IN ARREARS",
        "- OTHERS"
    ])]

    return (
        round((f["EXPECTEDREC"].sum() / sum_out) * 100, 2),
        f["EXPECTEDREC"].sum()
    )

# ======================================================
# Main EIIMNP41
# ======================================================

def run_eiimnp41(hp, ccris, text_df, reptdate):
    recrate = read_recrate(text_df)
    hp = prepare_hp(hp, ccris)

    current, m1t2, m3t5, m6ab, irregular, repossessed, deficit = split_buckets(hp)

    current_grp = summarize(
        build_grp(current, "CURRENT", [
            ("SUCCESSFUL REPOSSESSION", 0.16, recrate, True),
            ("UNSUCCESSFUL REPOSSESSION", 0.36, recrate, True),
            ("- 3-5 MONTHS IN ARREARS", 0.21, recrate, False),
            ("- >6 MONTHS IN ARREARS", 0.15, recrate, False),
            ("- OTHERS", 0.00, recrate, False),
            ("CONTINUE PAYING", 99.48, 100, False),
        ]),
        ["GROUPIND", "SUBGIND", "CATEGORY", "RATE", "RECRATE"]
    )

    m3t5_grp = summarize(
        build_grp(m3t5, "3-5 MTHS", [
            ("CONTINUE PAYING", 0.00, 100, False),
            ("SUCCESSFUL REPOSSESSION", 64.50, recrate, True),
            ("UNSUCCESSFUL REPOSSESSION", 35.50, 0.00, True),
            ("- 3-5 MONTHS IN ARREARS", 6.23, 0.00, False),
            ("- >6 MONTHS IN ARREARS", 10.09, 0.00, False),
            ("- OTHERS", 19.18, 0.00, False),
        ]),
        ["GROUPIND", "SUBGIND", "CATEGORY", "RATE", "RECRATE"]
    )

    ratea = calc_ratea(m3t5_grp)

    m6ab_grp = summarize(
        build_grp(m6ab, ">=6 MTHS", [
            ("CONTINUE PAYING", 0.00, 100, False),
            ("SUCCESSFUL REPOSSESSION", 36.05, 0.00, True),
            ("UNSUCCESSFUL REPOSSESSION", 63.95, 0.00, True),
            ("- 3-5 MONTHS IN ARREARS", 1.31, 0.00, False),
            ("- >6 MONTHS IN ARREARS", 5.81, 0.00, False),
            ("- OTHERS", 56.83, 0.00, False),
        ]),
        ["GROUPIND", "SUBGIND", "CATEGORY", "RATE", "RECRATE"]
    )

    rateb = calc_rateb(m6ab_grp, recrate)

    m1t2_grp = summarize(
        build_grp(m1t2, "1-2 MTHS", [
            ("CONTINUE PAYING", 92.30, 100, False),
            ("SUCCESSFUL REPOSSESSION", 2.33, recrate, True),
            ("UNSUCCESSFUL REPOSSESSION", 5.37, 0.00, True),
            ("- 3-5 MONTHS IN ARREARS", 2.66, ratea, False),
            ("- >6 MONTHS IN ARREARS", 2.25, rateb, False),
            ("- OTHERS", 0.46, 0.00, False),
        ]),
        ["GROUPIND", "SUBGIND", "CATEGORY", "RATE", "RECRATE"]
    )

    ratec, sumrec = calc_ratec(m1t2_grp)
    mask = m1t2_grp["CATEGORY"] == "UNSUCCESSFUL REPOSSESSION"
    m1t2_grp.loc[mask, "EXPECTEDREC"] = sumrec
    m1t2_grp.loc[mask, "RECRATE"] = ratec
    m1t2_grp.loc[mask, "CAPROVISION"] = (
        m1t2_grp.loc[mask, "OBDEFAULT"] - sumrec
    )

    irregular_grp = summarize(
        irregular.assign(
            GROUPIND="IRREGULAR",
            OBDEFAULT=irregular["BALANCE"],
            EXPECTEDREC=0,
            CAPROVISION=irregular["BALANCE"]
        ),
        ["GROUPIND"]
    )

    repossessed_grp = summarize(
        repossessed.assign(
            GROUPIND="REPOSSESSED",
            OBDEFAULT=repossessed["BALANCE"],
            EXPECTEDREC=repossessed["BALANCE"] * recrate / 100,
            CAPROVISION=repossessed["BALANCE"] * (1 - recrate / 100)
        ),
        ["GROUPIND"]
    )

    deficit_grp = summarize(
        deficit.assign(
            GROUPIND="DEFICIT",
            OBDEFAULT=deficit["BALANCE"],
            EXPECTEDREC=0,
            CAPROVISION=deficit["BALANCE"]
        ),
        ["GROUPIND"]
    )

    combine = pd.concat([
        current_grp,
        m1t2_grp,
        m3t5_grp,
        m6ab_grp,
        irregular_grp,
        repossessed_grp,
        deficit_grp
    ], ignore_index=True)

    cap = (
        combine[combine["CATEGORY"].isin([
            "SUCCESSFUL REPOSSESSION",
            "UNSUCCESSFUL REPOSSESSION"
        ])]
        .groupby("SUBGIND", as_index=False)["CAPROVISION"]
        .sum()
        .rename(columns={"SUBGIND": "CATEGORY"})
    )

    return combine, cap



====================================================================================================================================================

import pandas as pd
import numpy as np
from datetime import datetime

# ======================================================
# 1. REPORT DATE DERIVATION
# ======================================================

def derive_report_vars(reptdate: pd.Timestamp):
    day = reptdate.day
    if day <= 8:
        wk = "1"
    elif day <= 15:
        wk = "2"
    elif day <= 22:
        wk = "3"
    else:
        wk = "4"

    prevmon = (reptdate.replace(day=1) - pd.Timedelta(days=1))
    yearend = pd.Timestamp(year=reptdate.year, month=1, day=1) - pd.Timedelta(days=1)

    return {
        "REPTDATE": reptdate,
        "REPTDAY": f"{reptdate.day:02d}",
        "REPTMON": f"{reptdate.month:02d}",
        "REPTYEAR": reptdate.strftime("%y"),
        "NOWK": wk,
        "REPTMON1": f"{prevmon.month:02d}",
        "REPTYEAR1": prevmon.strftime("%y"),
        "LMON": f"{yearend.month:02d}",
        "LYEAR": yearend.strftime("%y"),
        "DATE": reptdate.strftime("%d/%m/%y")
    }

# ======================================================
# 2. PREPARE HP DATA
# ======================================================

def prepare_hp(hp_df):
    hp = hp_df.copy()
    hp = hp[hp["BALANCE"] > 0]

    hp["IND"] = np.where(hp["PRODUCT"].isin([128, 130]), "PIBB", "")
    hp = hp[hp["IND"] != ""]

    return hp

# ======================================================
# 3. MERGE CCRIS
# ======================================================

def merge_ccris(hp, ccris):
    ccris = (
        ccris.query("FACILITY in ['34331','34332']")
             .rename(columns={"ACCTNUM": "ACCTNO", "DAYSARR": "DAYARR"})
             [["ACCTNO", "NOTENO", "DAYARR"]]
             .sort_values(["ACCTNO", "NOTENO", "DAYARR"], ascending=[True, True, False])
             .drop_duplicates(["ACCTNO", "NOTENO"])
    )

    return (
        hp.sort_values(["ACCTNO", "NOTENO"])
          .merge(ccris, on=["ACCTNO", "NOTENO"], how="left")
    )

# ======================================================
# 4. CATEGORY ASSIGNMENT
# ======================================================

def assign_category(df):
    d = df.copy()
    d["CATEGORY"] = ""

    cond = d["PAIDIND"] == "M"

    d.loc[
        (d["DAYARR"] <= 30) &
        ~d["BORSTAT"].isin(list("FIREWZ")) &
        (d["USER5"] != "N") & cond,
        "CATEGORY"
    ] = "CURRENT"

    d.loc[
        d["DAYARR"].between(31, 89) &
        ~d["BORSTAT"].isin(list("FIREWZ")) &
        (d["USER5"] != "N") & cond,
        "CATEGORY"
    ] = "1-2 MTHS"

    d.loc[
        (~d["BORSTAT"].isin(list("FIREWZ"))) &
        (((d["USER5"] == "N") & (d["DAYARR"] <= 182)) |
         (d["DAYARR"].between(90, 182))) & cond,
        "CATEGORY"
    ] = "3-5 MTHS"

    d.loc[
        (~d["BORSTAT"].isin(list("FIREWZ"))) &
        (((d["USER5"] == "N") & (d["DAYARR"] >= 183)) |
         (d["DAYARR"] >= 183)) & cond,
        "CATEGORY"
    ] = ">=6 MTHS"

    d.loc[(d["BORSTAT"] == "I") & cond, "CATEGORY"] = "IRREGULAR"
    d.loc[(d["BORSTAT"] == "R") & cond, "CATEGORY"] = "REPOSSESSED"
    d.loc[(d["BORSTAT"] == "F") & cond, "CATEGORY"] = "DEFICIT"

    return d[d["CATEGORY"] != ""]

# ======================================================
# 5. APPLY CAP RATE
# ======================================================

def apply_cap_rate(pibb, icountcap):
    df = pibb.merge(icountcap, on="CATEGORY", how="left")

    df["CAP"] = (df["BALANCE"] * df["CARATE"]) / 100
    return df

# ======================================================
# 6. OPENING VS CLOSING BALANCE
# ======================================================

def compare_open_close(openbal, current):
    df = openbal.merge(
        current,
        on=["ACCTNO", "NOTENO"],
        how="outer",
        suffixes=("_OPEN", "")
    )

    df["STATUS"] = np.select(
        [
            df["OPEN_BALANCE"].notna() & df["CAP"].isna(),
            df["OPEN_BALANCE"].isna() & df["CAP"].notna()
        ],
        ["P", "C"],
        default=""
    )

    df.loc[df["STATUS"] == "P", "CATEGORY"] = df["CATEGORY1"]

    df["CAP"] = df["CAP"].fillna(0)
    df["OPEN_BALANCE"] = df["OPEN_BALANCE"].fillna(0)

    df["CHARCAP"] = df["CAP"] - df["OPEN_BALANCE"]

    df["SUSPEND"] = np.where(df["CHARCAP"] > 0, df["CHARCAP"], 0)
    df["WRBACK"] = np.where(df["CHARCAP"] < 0, -df["CHARCAP"], 0)

    df["NET"] = df["SUSPEND"] - df["WRBACK"]
    df["WRIOFF_BAL"] = 0

    return df

# ======================================================
# 7. WRITE-OFF PROCESS (QUARTER ONLY)
# ======================================================

def apply_writeoff(df, iwoff):
    df = df.merge(iwoff[["ACCTNO", "WRIOFF_BAL"]], on="ACCTNO", how="left")
    df["WRITEOFF"] = np.where(df["WRIOFF_BAL"].notna(), "Y", "N")
    df["WRIOFF_BAL"] = df["WRIOFF_BAL"].fillna(0)

    mask = (df["STATUS"] == "P") & (df["WRITEOFF"] == "Y")

    df.loc[mask, "SUSPEND"] = np.maximum(
        df.loc[mask, "WRIOFF_BAL"] - df.loc[mask, "OPEN_BALANCE"], 0
    )

    df.loc[mask, "WRBACK"] = np.maximum(
        df.loc[mask, "OPEN_BALANCE"] - df.loc[mask, "WRIOFF_BAL"], 0
    )

    df["NET"] = df["SUSPEND"] - df["WRBACK"]
    return df

# ======================================================
# 8. BRANCH SUMMARY (PROC TABULATE EQUIVALENT)
# ======================================================

def branch_summary(df):
    return (
        df.groupby("BRANCH1", as_index=False)
          .agg(
              NO=("ACCTNO", "count"),
              BALANCE=("BALANCE", "sum"),
              OPEN_BALANCE=("OPEN_BALANCE", "sum"),
              SUSPEND=("SUSPEND", "sum"),
              WRBACK=("WRBACK", "sum"),
              WRIOFF_BAL=("WRIOFF_BAL", "sum"),
              CAP=("CAP", "sum"),
              NET=("NET", "sum")
          )
    )

# ======================================================
# 9. MAIN ENTRY
# ======================================================

def run_eiimnp42(
    hp,
    ccris,
    icountcap,
    openbal,
    iwoff=None,
    reptdate=None
):
    rept_vars = derive_report_vars(reptdate)

    hp = prepare_hp(hp)
    hp = merge_ccris(hp, ccris)
    pibb = assign_category(hp)

    current = apply_cap_rate(pibb, icountcap)
    full = compare_open_close(openbal, current)

    if iwoff is not None:
        full = apply_writeoff(full, iwoff)

    summary = branch_summary(full)

    return {
        "DETAIL": full,
        "SUMMARY": summary,
        "REPTVARS": rept_vars
    }






====================================================================================================================================================


import pandas as pd
import numpy as np

# ======================================================
# 1. REPORT DATE DERIVATION
# ======================================================

def derive_report_vars(reptdate: pd.Timestamp):
    day = reptdate.day
    if day <= 8:
        wk = "1"
    elif day <= 15:
        wk = "2"
    elif day <= 22:
        wk = "3"
    else:
        wk = "4"

    return {
        "REPTDAY": f"{reptdate.day:02d}",
        "REPTMON": f"{reptdate.month:02d}",
        "REPTYEAR": reptdate.strftime("%y"),
        "NOWK": wk,
        "DATE": reptdate.strftime("%d/%m/%y")
    }

# ======================================================
# 2. CATEGORY ORDERING (NO)
# ======================================================

CATEGORY_ORDER = {
    "CURRENT": 1,
    "1-2 MTHS": 2,
    "3-5 MTHS": 3,
    ">=6 MTHS": 4,
    "IRREGULAR": 5,
    "REPOSSESSED": 6,
    "DEFICIT": 7
}

def assign_category_no(df):
    out = df.copy()
    out["NO"] = out["CATEGORY"].map(CATEGORY_ORDER)
    return out.sort_values("NO")

# ======================================================
# 3. TABULATE EQUIVALENT (CATEGORY × BRANCH)
# ======================================================

def tabulate_by_category(df):
    """
    Equivalent to PROC TABULATE:
    NO * CATEGORY * BRANCH1
    """

    summary = (
        df.groupby(
            ["NO", "CATEGORY", "BRANCH1"],
            as_index=False
        )
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

    return summary

# ======================================================
# 4. SUBTOTALS BY CATEGORY
# ======================================================

def category_subtotal(df):
    subtotal = (
        df.groupby(
            ["NO", "CATEGORY"],
            as_index=False
        )
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

    subtotal["BRANCH1"] = "SUB TOTAL"
    return subtotal

# ======================================================
# 5. GRAND TOTAL
# ======================================================

def grand_total(df):
    total = df.agg({
        "BALANCE": "sum",
        "OPEN_BALANCE": "sum",
        "SUSPEND": "sum",
        "WRBACK": "sum",
        "WRIOFF_BAL": "sum",
        "CAP": "sum",
        "NET": "sum"
    }).to_frame().T

    total["NO"] = 99
    total["CATEGORY"] = "GRAND TOTAL"
    total["BRANCH1"] = "GRAND TOTAL"
    return total

# ======================================================
# 6. MAIN ENTRY (EIIMNP43)
# ======================================================

def run_eiimnp43(icap_df, reptdate):
    """
    icap_df : DataFrame equivalent to NPL.ICAPOLD&REPTMON&REPTYEAR
    """

    rept_vars = derive_report_vars(reptdate)

    # Assign ordering
    df = assign_category_no(icap_df)

    # Detail (CATEGORY × BRANCH)
    detail = tabulate_by_category(df)

    # Subtotals
    subtotals = category_subtotal(detail)

    # Grand total
    gtotal = grand_total(detail)

    # Combine all
    final = pd.concat(
        [detail, subtotals, gtotal],
        ignore_index=True
    ).sort_values(["NO", "CATEGORY", "BRANCH1"])

    return {
        "DETAIL": detail,
        "SUBTOTAL": subtotals,
        "GRAND_TOTAL": gtotal,
        "FINAL": final,
        "REPTVARS": rept_vars
    }













====================================================================================================================================================








import pandas as pd
from datetime import datetime

# ======================================================
# 1. REPORT DATE DERIVATION (same logic as SAS)
# ======================================================

def derive_report_vars(reptdate: pd.Timestamp):
    day = reptdate.day
    if day <= 8:
        wk = "1"
    elif day <= 15:
        wk = "2"
    elif day <= 22:
        wk = "3"
    else:
        wk = "4"

    return {
        "REPTDAY": f"{reptdate.day:02d}",
        "REPTMON": f"{reptdate.month:02d}",
        "REPTYEAR": reptdate.strftime("%y"),
        "NOWK": wk
    }

# ======================================================
# 2. FIXED-WIDTH FORMATTER (PUT @xxx equivalent)
# ======================================================

def format_ccris_line(row):
    """
    SAS:
    PUT @001 ACCTNO  10.
        @012 NOTENO  Z5.
        @018 BRANCH  Z5.
        @024 CAP     20.2
        @045 AANO    $CHAR13.
    """

    acctno = f"{int(row['ACCTNO']):>10}"
    noteno = f"{int(row['NOTENO']):05d}"
    branch = f"{int(row['BRANCH']):05d}"
    cap = f"{row['CAP']:>20.2f}"
    aano = f"{str(row['AANO']):<13}"

    return (
        acctno +
        noteno +
        branch +
        cap +
        aano
    )

# ======================================================
# 3. MAIN EIIMNP44 PROCESS
# ======================================================

def run_eiimnp44(
    icap_df: pd.DataFrame,
    reptdate: pd.Timestamp,
    output_file: str
):
    """
    icap_df : DataFrame equivalent to NPL.ICAPOLD&REPTMON&REPTYEAR
    output_file : CCRIS interface file path
    """

    # Derive macro-like variables (for compatibility)
    rept_vars = derive_report_vars(reptdate)

    # Ensure required columns exist
    required_cols = ["ACCTNO", "NOTENO", "BRANCH", "CAP", "AANO"]
    missing = [c for c in required_cols if c not in icap_df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    # Write CCRIS file (equivalent to DATA _NULL_ FILE CCRIS)
    with open(output_file, "w", encoding="ascii") as f:
        for _, row in icap_df.iterrows():
            line = format_ccris_line(row)
            f.write(line + "\n")

    return {
        "OUTPUT_FILE": output_file,
        "REPTVARS": rept_vars,
        "RECORD_COUNT": len(icap_df)
    }







====================================================================================================================================================
