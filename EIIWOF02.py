"""EIIWOF02: WOFF text -> selected, sorted ACCTNO dataset. No deduplication."""
import argparse
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
import pyarrow as pa 
import pyarrow.parquet as pq


# Job settings: edit paths here; no separate config.json is required.
INPUT_ROOT = Path('/stgsrcsys/host/uat')
WOFF_FILE = INPUT_ROOT / 'RBP2.B033.LN.WRI2.OFF.MIS'
OUTPUT_ROOT = Path('/stgsrcsys/host/holding')
OUTPUT_SUFFIX = 'x'
ENCODING = 'utf-8'
BATCH_ROWS = 65536


def run(settings=None, run_date=None):
    # Optional in-memory settings allow dummy tests without editing server paths.
    cfg = {
        'input_root': str(INPUT_ROOT), 'output_root': str(OUTPUT_ROOT),
        'files': {'WOFF': str(WOFF_FILE)}, 'output_suffix': OUTPUT_SUFFIX,
        'encoding': ENCODING, 'batch_rows': BATCH_ROWS,
    }
    if settings is not None:
        cfg.update(settings.cfg if hasattr(settings, 'cfg') else settings)
    base = getattr(settings, 'base', Path(__file__).resolve().parent)
    scheduled = run_date or getattr(settings, 'run_date', None) or datetime.now(timezone(timedelta(hours=8))).date()
    scheduled = date.fromisoformat(scheduled) if isinstance(scheduled, str) else scheduled
    if (scheduled.month, scheduled.day) != (12, 27):
        raise ValueError('Run date must be 27 December; use --run-date YYYY-12-27 for reruns')
    def path(value):
        p = Path(value)
        return (p if p.is_absolute() else base / p).resolve()
    holding = path(cfg['output_root'])
    source_root = path(cfg['input_root'])
    if holding == source_root or source_root in holding.parents:
        raise ValueError('Working output must be outside the input directory')
    if cfg.get('output_format', 'parquet') != 'parquet':
        raise ValueError('This job outputs Parquet and TXT')
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
    values = pa.array(accounts) if any(v is not None for v in accounts) else pa.array(accounts, type=pa.decimal128(10, 0))
    table = pa.table({'ACCTNO': values})
    holding.mkdir(parents=True, exist_ok=True)
    member = 'woffhp' + cfg.get('output_suffix', 'x')
    if not member.isidentifier() or len(member) > 32:
        raise ValueError('Invalid output member name')
    target = holding / (member + '.parquet')
    stage = target.with_suffix('.parquet.tmp')
    pq.write_table(table, stage, compression='zstd', row_group_size=int(cfg.get('batch_rows', 65536)))
    stage.replace(target)

    # Plain text: one ACCTNO per line, no header; missing values use a blank line.
    text_target = holding / (member + '.txt')
    text_stage = text_target.with_suffix('.txt.tmp')
    with text_stage.open('w', encoding='utf-8', newline='') as handle:
        handle.writelines(('' if value is None else format(value, 'f')) + '\n' for value in accounts)
    text_stage.replace(text_target)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='WOFF text to sorted WOFFHP dataset')
    parser.add_argument('--run-date')
    args = parser.parse_args()
    run(run_date=args.run_date)

