"""EIIWOF02: WOFF text to TXT and SAS7BDAT. No deduplication."""
import argparse
from datetime import date
from decimal import Decimal
from pathlib import Path
import pandas as pd
import saspy
import re


# Job settings: edit paths here; no separate config.json is required.
INPUT_ROOT = Path('/host_pq/loan/input')
WOFF_FILE = Path('/host_pq/loan/input/WRI2OFF_MIS.txt')
OUTPUT_ROOT = Path('/exdwh/host/ln/npl_hp_sasdata/pibb/woff')
OUTPUT_SUFFIX = 'x'
ENCODING = 'utf-8'
RUN_DATE = "2026-12-27"
SAS_CONFIG = None  # Set to your configured SASPy profile name if needed.



def write_sas7bdat(accounts, output_folder, member):
    """Write a numeric ACCTNO dataset using the configured SASPy server."""
    frame = pd.DataFrame({
        "ACCTNO": [float(value) if value is not None else float("nan")
                   for value in accounts]
    }, dtype="float64")
    sas = (saspy.SASsession(cfgname=SAS_CONFIG)
           if SAS_CONFIG else saspy.SASsession())
    try:
        sas.saslib("outlib", path=str(output_folder))
        if re.search(r"^ERROR(?:\s|:)", sas.lastlog(), re.MULTILINE):
            raise RuntimeError("Cannot assign SAS output library. " + sas.lastlog())
        result = sas.dataframe2sasdata(frame, table=member, libref="outlib")
        log = sas.lastlog()
        if result is None or re.search(r"^ERROR(?:\s|:)", log, re.MULTILINE):
            raise RuntimeError("SAS7BDAT export failed. " + log)
        if not sas.exist(member, libref="outlib"):
            raise RuntimeError("SAS7BDAT output was not created.")
        print(f"SAS7BDAT created: {output_folder / (member + '.sas7bdat')}")
    finally:
        sas.endsas()

def run(settings=None, run_date=None):
    # Optional in-memory settings allow dummy tests without editing server paths.
    cfg = {
        'input_root': str(INPUT_ROOT), 'output_root': str(OUTPUT_ROOT),
        'files': {'WOFF': str(WOFF_FILE)}, 'output_suffix': OUTPUT_SUFFIX,
        'encoding': ENCODING, 'reports': '/dwh/ftp/drr',
    }
    if settings is not None:
        cfg.update(settings.cfg if hasattr(settings, 'cfg') else settings)
    base = getattr(settings, 'base', Path(__file__).resolve().parent)
    scheduled = date.fromisoformat(str(run_date or RUN_DATE))
    def path(value):
        p = Path(value)
        return (p if p.is_absolute() else base / p).resolve()
    holding = path(cfg['output_root'])
    source_root = path(cfg['input_root'])
    if holding == source_root or source_root in holding.parents:
        raise ValueError('Working output must be outside the input directory')
    def number(field):
        value = field.strip()
        return None if not value or value == '.' or (len(value) == 2 and value[0] == '.' and (value[1].isalpha() or value[1] == '_')) else Decimal(value.replace(',', ''))

    # SAS: INPUT @142 ACCTNO 10. @236 COSTCTR 4.; KEEP=ACCTNO.
    accounts = []
    with path(cfg['files']['WOFF']).open(encoding=cfg.get('encoding', 'utf-8')) as handle:
        for line_number, line in enumerate(handle, 1):
            if len(line.rstrip('\r\n')) < 239:
                raise ValueError(f'WOFF line {line_number}: record shorter than required fields')
            acct, cost = number(line[141:151]), number(line[235:239])
            if cost is not None and (3000 <= cost <= 3999 or cost in (4043, 4048)):
                accounts.append(acct)
    accounts.sort(key=lambda value: (value is not None, value or Decimal(0)))
    holding.mkdir(parents=True, exist_ok=True)
    member = 'woffhp' + cfg.get('output_suffix', 'x')
    if not member.isidentifier() or len(member) > 32:
        raise ValueError('Invalid output member name')
    # Plain text: one ACCTNO per line, no header; missing values use a blank line.
    text_target = path(cfg['reports']) / (member + '.txt')
    text_target.parent.mkdir(parents=True, exist_ok=True)
    text_stage = text_target.with_suffix('.txt.tmp')
    with text_stage.open('w', encoding='utf-8', newline='') as handle:
        handle.writelines(('' if value is None else format(value, 'f')) + '\n' for value in accounts)
    text_stage.replace(text_target)
    print(f"TXT created: {text_target}")
    write_sas7bdat(accounts, holding, member)
    print(f"EIIWOF02 completed. Records: {len(accounts)}")



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='WOFF text to sorted WOFFHP dataset')
    parser.add_argument('--run-date')
    args = parser.parse_args()
    run(run_date=args.run_date)

