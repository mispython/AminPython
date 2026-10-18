"""EIIWOF01: copy original datasets unchanged to uat/pas. No data conversion."""
import argparse
import json
import shutil
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

SEED_MEMBERS = ['NPLOBAL', 'WIIS', 'WAQ', 'WSP2', 'IIS', 'AQ', 'SP2', 'IIS11', 'SP211']
INPUT_DATASETS = [('NPLA', name) for name in SEED_MEMBERS + ['WOFFTOT']] + [('HD', 'HPWOFF')]


def initialize(config_path, run_date=None, context_type=None):
    config_path = Path(config_path).resolve()
    cfg = json.loads(config_path.read_text(encoding='utf-8-sig'))
    scheduled = run_date or datetime.now(timezone(timedelta(hours=8))).date()
    scheduled = date.fromisoformat(scheduled) if isinstance(scheduled, str) else scheduled
    if (scheduled.month, scheduled.day) != (12, 27):
        raise ValueError('Run date must be 27 December; use --run-date YYYY-12-27 for reruns')
    def path(value):
        p = Path(value)
        return (p if p.is_absolute() else config_path.parent / p).resolve()
    input_root = path(cfg.get('input_root', '/stgsrcsys/host/uat'))
    output_root = path(cfg.get('output_root', '/stgsrcsys/host/holding'))
    if output_root == input_root or input_root in output_root.parents:
        raise ValueError('Holding must be outside the input directory')
    if context_type is not None:  # Test-only input adapter; production uses SAS files.
        context = context_type(config_path, run_date=scheduled)
    else:
        context = SimpleNamespace(cfg=cfg, base=config_path.parent, config_path=config_path,
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
    holding = Path(context.cfg['output_root'])
    holding.mkdir(parents=True, exist_ok=True)
    state_path = holding / 'batch_state.json'
    state = {'run_date': context.run_date.isoformat(), 'outputs': {}, 'seed_sources': {}}
    def save_state():
        stage = state_path.with_suffix('.json.tmp')
        stage.write_text(json.dumps(state, indent=2), encoding='utf-8')
        stage.replace(state_path)
    save_state()  # Old working outputs must not be reused after a batch restart.
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
        if member in SEED_MEMBERS:
            state['seed_sources'][member] = str(target.resolve())
    save_state()  # Register copied inputs only after every copy succeeds.


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Copy original datasets to uat/pas without conversion')
    parser.add_argument('--config', required=True)
    parser.add_argument('--run-date')
    args = parser.parse_args()
    context = initialize(args.config, args.run_date)
    try:
        run(context)
    finally:
        context.close()
