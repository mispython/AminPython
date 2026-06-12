from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    RunConfig,
    add_close_and_account_counts,
    apply_cumulative,
    keep_open_or_closed_this_month,
    make_closed_extract,
    normalize_branch,
    normalize_open_indicator,
    read_dataset,
    reporting_dates,
    summary_by_branch_product,
    write_dataset,
    write_report,
)
from pbbdpfmt import ddcustcd


# PBBDPFMT and PBBELF are intentionally not combined into this job.
# They are maintained by another team and should remain as separate include-style modules.


SAVG_PRODUCT_RANGES = [
    (200, 207),  # 200,201,202,203,204,205,206,207
    (212, 216),  # 212,213,214,215,216
    (220, 223),  # 220,221,222,223
]
SAVG_PRODUCTS = {218}

CURR_PRODUCT_RANGES = [
    (5, 8),      # 5,6,7,8
    (13, 25),    # 13,14,15,16,17,18,19,20,21,22,23,24,25
    (32, 33),    # 32,33
    (45, 67),    # 45,46,47,48,49,50,...,67
    (70, 71),    # 70,71
    (73, 76),    # 73,74,75,76
    (90, 97),    # 90,91,92,93,94,95,96,97
    (100, 106),  # 100,101,102,103,104,105,106
    (108, 125),  # 108,109,...,125
    (137, 138),  # 137,138
    (150, 170),  # 150,151,...,170
    (174, 188),  # 174,175,...,188
    (191, 198),  # 191,192,...,198
]
CURR_PRODUCTS = {81}

FD_PRODUCT_RANGES = [
    (300, 316),  # 300,301,302,303,304,305,306,307,308,309,310,311,312,313,314,315,316
]
FD_PRODUCTS = {393, 394, 396}

DNBFI_KEEP = {f"{value:02d}" for value in [*range(4, 7), *range(30, 36), *range(37, 41), 45]}


def product_mask(product, ranges, values=()):
    mask = product.isin(values)
    for start, end in ranges:
        mask = mask | product.between(start, end)
    return mask


SAVG_CLOSED_COLUMNS = [
    "BRANCH", "ACCTNO", "OPENDT", "CLOSEDT",
    "OPENIND", "CURBAL", "CUSTCODE", "MTDAVBAL",
    "YTDAVBAL", "CUSTFISS", "DOBMNI", "PRODUCT",
    "CHGIND", "COSTCTR", "DEPTYPE", "DNBFISME",
    "INTPD", "INTPLAN", "INTRSTPD", "INTYTD",
    "LASTTRAN", "ORGCODE", "ORGTYPE", "PURPOSE",
    "RISKCODE", "SECOND", "SECTOR", "SERVICE",
    "STATE", "USER2", "USER3", "USER5",
    "STMT_CYCLE", "NXT_STMT_CYCLE_DT",
]


CURR_CLOSED_COLUMNS = [
    "BRANCH", "ACCTNO", "OPENDT", "CLOSEDT",
    "OPENIND", "CURBAL", "CUSTCODE", "MTDAVBAL",
    "YTDAVBAL", "CUSTFISS", "DOBMNI", "PRODUCT",
    "ACCPROF", "APPRLIMT", "CENSUST", "CHGIND",
    "COSTCTR", "DATE_LST_DEP", "DEPTYPE", "DNBFI_ORI",
    "DNBFISME", "FLATRATE", "INTPD", "INTPLAN",
    "INTRSTPD", "INTYTD", "L_DEP", "LASTTRAN",
    "LIMIT1", "LIMIT2", "LIMIT3", "LIMIT4",
    "LIMIT5", "MAXPROF", "ODINTACC", "ODINTCHR",
    "ODPLAN", "ORGCODE", "ORGTYPE", "PURPOSE",
    "RATE1", "RATE2", "RATE3", "RATE4",
    "RATE5", "RETURNS_Y", "RISKCODE", "SECOND",
    "SECTOR", "SERVICE", "STATE", "USER2",
    "USER3", "USER5", "DSR", "REPAY_TYPE_CD",
    "MTD_REPAID_AMT", "INDUSTRIAL_SECTOR_CD",
    "WRITE_DOWN_BAL", "MTD_DISBURSED_AMT",
    "MTD_REPAY_TYPE10_AMT", "MTD_REPAY_TYPE20_AMT",
    "MTD_REPAY_TYPE30_AMT", "MODIFIED_FACILITY_IND",
    "STMT_CYCLE", "NXT_STMT_CYCLE_DT", "INTPLAN_IBCA",
]


FD_CLOSED_COLUMNS = [
    "BRANCH", "ACCTNO", "OPENDT", "CLOSEDT",
    "OPENIND", "CURBAL", "CUSTCODE", "MTDAVBAL",
    "YTDAVBAL", "CUSTFISS", "DOBMNI", "PRODUCT",
    "COSTCTR", "DEPTYPE", "DNBFISME", "INTPD",
    "INTPLAN", "INTRSTPD", "INTYTD", "LASTTRAN",
    "ORGCODE", "ORGTYPE", "PURPOSE", "RISKCODE",
    "SECOND", "SECTOR", "SERVICE", "STATE",
    "USER2", "USER3", "USER5",
    "STMT_CYCLE", "NXT_STMT_CYCLE_DT",
]

SAVG_SUMMARY_COLUMNS = ["OPENMH", "CURBAL", "NOACCT", "CLOSEMH", "BCLOSE", "CCLOSE"]
CURR_SUMMARY_COLUMNS = ["OPENMH", "CLOSEMH", "NOACCT", "CURBAL", "BCLOSE", "CCLOSE"]
FD_SUMMARY_COLUMNS = ["OPENMH", "CLOSEMH", "NOACCT", "NOCD", "CURBAL"]

SAVG_REPORT_COLUMNS = [
    ("OPENMH", "CURRENT MONTH OPENED", "count"),
    ("OPENCUM", "CUMULATIVE OPENED", "count"),
    ("CLOSEMH", "CURRENT MONTH CLOSED", "count"),
    ("BCLOSE", "CLOSED BY BANK", "count"),
    ("CCLOSE", "CLOSED BY CUSTOMER", "count"),
    ("CLOSECUM", "CUMULATIVE CLOSED", "count"),
    ("NOACCT", "NO.OF ACCTS", "count"),
    ("CURBAL", "TOTAL (RM) O/S", "money"),
    ("NETCHGMH", "NET CHANGE FOR THE MONTH", "count"),
    ("NETCHGYR", "NET CHANGE YEAR TO DATE", "count"),
]

CURR_REPORT_COLUMNS = [
    ("OPENMH", "CURRENT MONTH OPENED", "count"),
    ("OPENCUM", "CUMULATIVE OPENED", "count"),
    ("CLOSEMH", "CURRENT MONTH CLOSED", "count"),
    ("BCLOSE", "CLOSED BY BANK", "count"),
    ("CCLOSE", "CLOSED BY CUSTOMER", "count"),
    ("CLOSECUM", "CUMULATIVE CLOSED", "count"),
    ("NOACCT", "NO. OF ACCTS", "count"),
    ("CURBAL", "TOTAL(RM) O/S", "money"),
    ("NETCHGMH", "NET CHANGE FOR THE MONTH", "count"),
    ("NETCHGYR", "NET CHANGE YEAR TO DATE", "count"),
]

FD_REPORT_COLUMNS = [
    ("OPENMH", "CURRENT MONTH OPENED", "count"),
    ("OPENCUM", "CUMULATIVE OPENED", "count"),
    ("CLOSEMH", "CURRENT MONTH CLOSED", "count"),
    ("CLOSECUM", "CUMULATIVE CLOSED", "count"),
    ("NOACCT", "NO.OF ACCTS", "count"),
    ("NOCD", "NO.OF CDS", "count"),
    ("CURBAL", "TOTAL (RM) O/S", "money"),
    ("NETCHGMH", "NET CHANGE FOR THE MONTH", "count"),
    ("NETCHGYR", "NET CHANGE YEAR TO DATE", "count"),
]


def delete_previous_outputs(config: RunConfig) -> None:
    # Original JCL DELETE step:
    #   SAP.PIBB.OPCL.CURR
    #   SAP.PIBB.OPCL.FD
    #   SAP.PIBB.OPCL.SAVG
    for name in ["IOPCLCURR.TXT", "IOPCLFDAC.TXT", "IOPCLSAVG.TXT"]:
        path = config.output_dir / name
        if path.exists():
            path.unlink()


def run_savg(config: RunConfig) -> dict[str, Path]:
    dates = reporting_dates(config.deposit_dir)

    savg = read_dataset(config.deposit_dir, "SAVING")
    savg = savg[product_mask(savg["PRODUCT"], SAVG_PRODUCT_RANGES, SAVG_PRODUCTS)].copy()
    savg = normalize_branch(savg, delete_227=True)
    savg = normalize_open_indicator(savg)
    savg = keep_open_or_closed_this_month(savg)
    savg = add_close_and_account_counts(savg, bank_customer_split=True)

    savg["CUSTFISS"] = 0
    closed_path = write_dataset(
        make_closed_extract(savg, SAVG_CLOSED_COLUMNS),
        config.mis_dir,
        f"SAVGC{dates['REPTMON']}",
    )

    savg = summary_by_branch_product(savg, SAVG_SUMMARY_COLUMNS)

    previous = None
    if dates["REPTMON"] > "01":
        previous = read_dataset(config.mis_dir, f"SAVGF{dates['REPTMON1']}")
    savg = apply_cumulative(savg, previous, remap_227_to_81=True)

    final_path = write_dataset(savg, config.mis_dir, f"SAVGF{dates['REPTMON']}")
    report_path = write_report(
        savg,
        config.output_dir / "IOPCLSAVG.TXT",
        f"SAVINGS ACCOUNT OPENED/CLOSED FOR THE MONTH AS AT {dates['RDATE']}",
        SAVG_REPORT_COLUMNS,
    )
    return {"closed": closed_path, "final": final_path, "report": report_path}


def current_product_mask(product):
    return product_mask(product, CURR_PRODUCT_RANGES, CURR_PRODUCTS)


def run_curr(config: RunConfig) -> dict[str, Path]:
    dates = reporting_dates(config.deposit_dir)

    curr = read_dataset(config.deposit_dir, "CURRENT")
    curr.loc[curr["BRANCH"] == 996, "BRANCH"] = 168
    curr.loc[curr["BRANCH"] == 250, "BRANCH"] = 92
    curr = curr[current_product_mask(curr["PRODUCT"])].copy()
    curr = normalize_open_indicator(curr)
    curr = keep_open_or_closed_this_month(curr)
    curr = add_close_and_account_counts(curr, bank_customer_split=True)

    curr["CUSTFISS"] = curr["CUSTCODE"].map(ddcustcd)
    curr.loc[curr["PRODUCT"].eq(104), "CUSTFISS"] = "02"
    curr.loc[curr["PRODUCT"].eq(105), "CUSTFISS"] = "81"
    curr["DNBFI_ORI"] = curr.get("DNBFISME")
    curr.loc[~curr["CUSTFISS"].isin(DNBFI_KEEP), "DNBFISME"] = "0"

    closed_path = write_dataset(
        make_closed_extract(curr, CURR_CLOSED_COLUMNS),
        config.mis_dir,
        f"CURRC{dates['REPTMON']}",
    )

    curr = summary_by_branch_product(curr, CURR_SUMMARY_COLUMNS)

    previous = None
    if dates["REPTMON"] > "01":
        previous = read_dataset(config.mis_dir, f"CURRF{dates['REPTMON1']}")
    curr = apply_cumulative(curr, previous)

    final_path = write_dataset(curr, config.mis_dir, f"CURRF{dates['REPTMON']}")
    report_path = write_report(
        curr,
        config.output_dir / "IOPCLCURR.TXT",
        f"CURRENT ACCOUNT OPENED/CLOSED FOR THE MONTH AS AT {dates['RDATE']}",
        CURR_REPORT_COLUMNS,
    )
    return {"closed": closed_path, "final": final_path, "report": report_path}


def run_fd(config: RunConfig) -> dict[str, Path]:
    dates = reporting_dates(config.deposit_dir)

    fdc = read_dataset(config.fd_dir, "FD")
    fdc = fdc[fdc["OPENIND"].isin(["O", "D"])].copy()
    fdc = fdc.sort_values("ACCTNO")
    fdc = fdc.groupby("ACCTNO", as_index=False).size().rename(columns={"size": "NOCD"})

    fd = read_dataset(config.deposit_dir, "FD")
    fd = normalize_branch(fd, delete_227=True)
    fd = fd[product_mask(fd["PRODUCT"], FD_PRODUCT_RANGES, FD_PRODUCTS)].copy()
    fd = normalize_open_indicator(fd)
    fd = keep_open_or_closed_this_month(fd)
    fd = add_close_and_account_counts(fd, bank_customer_split=False)

    fd["CUSTFISS"] = 0
    closed_path = write_dataset(
        make_closed_extract(fd, FD_CLOSED_COLUMNS),
        config.mis_dir,
        f"FDC{dates['REPTMON']}",
    )

    fd = fdc.merge(fd, on="ACCTNO", how="right")
    fd["NOCD"] = fd["NOCD"].fillna(0)
    fd = summary_by_branch_product(fd, FD_SUMMARY_COLUMNS)

    previous = None
    if dates["REPTMON"] > "01":
        previous = read_dataset(config.mis_dir, f"FDF{dates['REPTMON1']}")
    fd = apply_cumulative(fd, previous)

    final_path = write_dataset(fd, config.mis_dir, f"FDF{dates['REPTMON']}")
    report_path = write_report(
        fd,
        config.output_dir / "IOPCLFDAC.TXT",
        f"FD ACCOUNT OPENED/CLOSED FOR THE MONTH AS AT {dates['RDATE']}",
        FD_REPORT_COLUMNS,
    )
    return {"closed": closed_path, "final": final_path, "report": report_path}


def run(config: RunConfig) -> dict[str, dict[str, Path]]:
    delete_previous_outputs(config)
    return {
        "EIIMDPN1": run_savg(config),
        "EIIMDPN2": run_curr(config),
        "EIIMDPN3": run_fd(config),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combined Python conversion of EIIMRPTC with EIIMDPN1, EIIMDPN2, and EIIMDPN3 in one job."
    )
    parser.add_argument(
        "--deposit-dir",
        required=True,
        type=Path,
        help="Folder containing REPTDATE, SAVING, CURRENT, and FD datasets.",
    )
    parser.add_argument("--fd-dir", required=True, type=Path, help="Folder containing the FD certificate dataset.")
    parser.add_argument("--mis-dir", required=True, type=Path, help="Folder for MIS monthly input/output datasets.")
    parser.add_argument("--output-dir", required=True, type=Path, help="Folder for IOPCLSAVG/CURR/FDAC text reports.")
    parser.add_argument(
        "--branch-file",
        type=Path,
        default=None,
        help="Optional BRHFILE fixed-width input, for example /stgsrcsys/host/uat/DBRANCH.TXT.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = RunConfig(
        deposit_dir=args.deposit_dir,
        fd_dir=args.fd_dir,
        mis_dir=args.mis_dir,
        output_dir=args.output_dir,
        branch_file=args.branch_file,
    )
    results = run(config)
    for step, files in results.items():
        print(step)
        for label, path in files.items():
            print(f"  {label}: {path}")


if __name__ == "__main__":
    main()
