# Settings for EIIWOF01; edit these paths in this file.
INPUT_ROOT = '/stgsrcsys/host/uat'
OUTPUT_ROOT = '/stgsrcsys/host/holding'
SEED_INPUTS = ['NPLOBAL', 'IIS11', 'SP211']


def job_settings():
    return {
        '_job_name': 'EIIWOF01', 'input_root': INPUT_ROOT, 'output_root': OUTPUT_ROOT,
        'output_format': 'parquet', 'output_suffix': 'x', 'batch_rows': 65536,
        'encoding': 'utf-8', 'output_encoding': 'utf-8', 'sas_encoding': 'infer',
        'sas_export': True, 'seed_inputs': list(SEED_INPUTS),
        'libraries': {key: (OUTPUT_ROOT if key in ('NPL','NPL6') else INPUT_ROOT)
                      for key in ('NPLA','LOAN','SASLN','HD','NPL','NPL6')},
        'reports': str(Path(OUTPUT_ROOT) / 'reports'),
        'files': {
            'WOFF': str(Path(INPUT_ROOT) / 'RBP2.B033.LN.WRI2.OFF.MIS'),
            'WOFFC': str(Path(INPUT_ROOT) / 'woff02.sas7bdat'),
            'PATCH': str(Path(INPUT_ROOT) / 'woff03.sas7bdat'),
            'WOFFACCT': str(Path(OUTPUT_ROOT) / 'HPTXT1x.txt'),
            'WOFFACC2': str(Path(OUTPUT_ROOT) / 'HPTXT2x.txt'),
        },
    }

"""EIIWOF01: copy original datasets unchanged to uat/pas. No data conversion."""
import argparse
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

SEED_MEMBERS = ['NPLOBAL', 'WIIS', 'WAQ', 'WSP2', 'IIS', 'AQ', 'SP2', 'IIS11', 'SP211']
INPUT_DATASETS = [('NPLA', name) for name in SEED_MEMBERS + ['WOFFTOT']] + [('HD', 'HPWOFF')]


def initialize(settings=None, run_date=None, context_type=None):
    from copy import deepcopy
    cfg = job_settings()
    if settings is not None: cfg.update(deepcopy(settings))
    base = Path(__file__).resolve().parent
    scheduled = run_date or datetime.now(timezone(timedelta(hours=8))).date()
    scheduled = date.fromisoformat(scheduled) if isinstance(scheduled, str) else scheduled
    if (scheduled.month, scheduled.day) != (12, 27):
        raise ValueError('Run date must be 27 December; use --run-date YYYY-12-27 for reruns')
    def path(value):
        p = Path(value)
        return (p if p.is_absolute() else base / p).resolve()
    input_root = path(cfg.get('input_root', '/stgsrcsys/host/uat'))
    output_root = path(cfg.get('output_root', '/stgsrcsys/host/holding'))
    if output_root == input_root or input_root in output_root.parents:
        raise ValueError('Holding must be outside the input directory')
    if context_type is not None:  # Test-only input adapter; production uses SAS files.
        context = context_type(cfg, run_date=scheduled)
    else:
        context = SimpleNamespace(cfg=cfg, base=base,
                                  run_date=scheduled, close=lambda: None)
        def original_table(library, member):
            directory = path(cfg.get('libraries', {}).get(library, str(input_root)))
            matches = [p for p in directory.iterdir() if p.is_file() and p.name.lower() == member.lower() + '.sas7bdat']
            if len(matches) != 1:
                raise FileNotFoundError(f'Expected one {member}.sas7bdat in {directory}')
            return matches[0]
        context.original_table = original_table
    context.cfg['input_root'] = str(input_root)
    context.cfg['output_root'] = str(output_root)
    context.input_paths = {f'{lib}.{name}': context.original_table(lib, name) for lib, name in INPUT_DATASETS}
    return context


def run(context):
    source_root = Path(context.cfg['input_root']).resolve()
    destination = source_root / 'pas'
    if destination.resolve() != destination:
        raise ValueError('pas must not redirect through a symlink')
    sources = [(name, context.original_table(lib, name)) for lib, name in INPUT_DATASETS]
    destination.mkdir(parents=True, exist_ok=True)
    for member, source in sources:
        target = destination / source.name  # Preserve filename; no x suffix.
        stage = destination / ('.' + source.name + '.tmp')
        if stage.is_symlink():
            raise ValueError('Copy temporary path must not be a symlink')
        try:
            shutil.copy2(source, stage)
            stage.replace(target)
        finally:
            stage.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Copy original datasets to uat/pas without conversion')
    parser.add_argument('--run-date')
    args = parser.parse_args()
    context = initialize(run_date=args.run_date)
    try:
        run(context)
    finally:
        context.close()
