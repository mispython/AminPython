# EIFMNPCA.py
# JCL replacement for job EIFMNPCA

import pandas as pd

# =========================================================
# DD DSN MAPPING  (from EIFMNPCA JCL)
# =========================================================

BASE = "/data/sap"

LIB = {
    # INPUTS
    "LOAN": f"{BASE}/PBB/MNILN",
    "HP": f"{BASE}/PBB/HPDATAWH",
    "NPL": f"{BASE}/PBB/NPL/HP",
    "CCRIS": f"{BASE}/PBB/CCRIS/CREDSUB",
    "TEXT": f"{BASE}/PBB/RECRATE",

    # OUTPUTS (NEW,CATLG,DELETE)
    "OUTPUT": f"{BASE}/PBB/OUTPUT"
}

# =========================================================
# SAS RUNTIME REPLACEMENT (io_utils)
# =========================================================

def read_df(path):
    return pd.read_parquet(path)

def write_df(df, path):
    df.to_parquet(path, index=False)

def log(msg):
    print(f"[EIFMNPCA] {msg}")

# =========================================================
# DELETE OLD OUTPUTS (IEFBR14 equivalent)
# =========================================================

def delete_old_outputs():
    import os

    files = [
        f"{LIB['OUTPUT']}/CAPCAMP_OLD_TEXT.txt",
        f"{LIB['OUTPUT']}/CAPBRCH_OLD_TEXT.txt",
        f"{LIB['OUTPUT']}/CAPCATE_OLD_TEXT.txt",
        f"{LIB['OUTPUT']}/FSAS5_OLD_TEXT.txt",
    ]

    for f in files:
        if os.path.exists(f):
            os.remove(f)
            log(f"Deleted {f}")

# =========================================================
# EXECUTION ORDER (same as JCL)
# =========================================================

def run():
    log("EIFMNPCA JOB STARTED")

    delete_old_outputs()

    from EIFMNP41 import run as EIFMNP41
    from EIFMNP42 import run as EIFMNP42
    from EIFMNP43 import run as EIFMNP43
    from EIFMNP44 import run as EIFMNP44

    EIFMNP41()
    EIFMNP42()
    EIFMNP43()
    EIFMNP44()

    log("EIFMNPCA JOB COMPLETED")

# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":
    run()
