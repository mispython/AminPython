import pandas as pd
import numpy as np

# =====================================================
# Utilities
# =====================================================

def summarize(df, keys):
    return (
        df.groupby(keys, as_index=False)
          .agg({
              "BALANCE": "sum",
              "OBDEFAULT": "sum",
              "EXPECTEDREC": "sum",
              "CAPROVISION": "sum"
          })
    )

# =====================================================
# PART 1
# =====================================================

def derive_report_period(reptdate):
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
        "REPTMON": f"{reptdate.month:02d}",
        "NOWK": wk,
        "REPTYEAR": reptdate.strftime("%y")
    }

def prepare_hp(hp, ccris):
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

    m3t5 = hp[
        base &
        ~hp["BORSTAT"].isin(list("FIREWZ")) &
        (
            ((hp["USER5"] == "N") & (hp["DAYARR"] <= 182)) |
            (hp["DAYARR"].between(90, 182))
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

    return current, m3t5, m6ab, irregular, repossessed, deficit

def build_grp(df, subgroup, rules):
    rows = []
    for _, r in df.iterrows():
        for cat, rate, recrate, cap in rules:
            ob = r["BALANCE"] * rate / 100
            exp = ob * recrate / 100
            rows.append({
                "CATEGORY": cat,
                "GROUPIND": "OTHERS",
                "SUBGIND": subgroup,
                "RATE": rate,
                "RECRATE": recrate,
                "BALANCE": r["BALANCE"],
                "OBDEFAULT": ob,
                "EXPECTEDREC": exp,
                "CAPROVISION": ob - exp if cap else 0
            })
    return pd.DataFrame(rows)

# =====================================================
# RATE CALCULATIONS
# =====================================================

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

# =====================================================
# MAIN PIPELINE
# =====================================================

def run_eiimnp41(hp, ccris, recrate):
    hp = prepare_hp(hp, ccris)

    current, m3t5, m6ab, irregular, repossessed, deficit = split_buckets(hp)

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
        build_grp(current, "1-2 MTHS", [
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







====================================================================================================================================================













====================================================================================================================================================















====================================================================================================================================================
