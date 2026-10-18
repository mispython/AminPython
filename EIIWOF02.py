"""EIIWOF02: WOFF text -> selected, sorted ACCTNO dataset. No deduplication."""
import argparse
import json
from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq


def run(config, run_date=None):
    # Accept the normal config filename or a context from the dummy test harness.
    config_path = Path(config.config_path if hasattr(config, 'config_path') else config).resolve()
    cfg = json.loads(config_path.read_text(encoding='utf-8-sig'))
    scheduled = run_date or getattr(config, 'run_date', None) or datetime.now(timezone(timedelta(hours=8))).date()
    scheduled = date.fromisoformat(scheduled) if isinstance(scheduled, str) else scheduled
    if (scheduled.month, scheduled.day) != (12, 27):
        raise ValueError('Run date must be 27 December; use --run-date YYYY-12-27 for reruns')
    def path(value):
        p = Path(value)
        return (p if p.is_absolute() else config_path.parent / p).resolve()
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

    # Register this output so later original jobs can find it in the current batch.
    manifest = holding / 'batch_state.json'
    state = json.loads(manifest.read_text()) if manifest.exists() else {}
    if state.get('run_date') != scheduled.isoformat():
        state = {'run_date': scheduled.isoformat(), 'outputs': {}}
    state['outputs']['WOFFHP'] = target.name
    state['sas_export_excluded'] = sorted(set(state.get('sas_export_excluded', [])) | {'WOFFHP'})
    temp = manifest.with_suffix('.json.tmp')
    temp.write_text(json.dumps(state, indent=2), encoding='utf-8')
    temp.replace(manifest)
    # If rerun, remove any prior WOFFHP entry from the existing export driver.
    driver = holding / 'export_all.sas'
    if driver.exists():
        lines = driver.read_text(encoding='utf-8').splitlines(keepends=True)
        driver_stage = driver.with_suffix('.sas.tmp')
        driver_stage.write_text(''.join(line for line in lines if member + '.sas' not in line), encoding='utf-8')
        driver_stage.replace(driver)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='WOFF text to sorted WOFFHP dataset')
    parser.add_argument('--config', required=True)
    parser.add_argument('--run-date')
    args = parser.parse_args()
    run(args.config, args.run_date)
