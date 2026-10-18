# Settings for EIIWOF03; edit these paths in this file.
INPUT_ROOT = '/stgsrcsys/host/uat'
OUTPUT_ROOT = '/stgsrcsys/host/holding'
LNNOTE_ROOT = '/sas/ln/dwh/enrichment'
SEED_INPUTS = ['NPLOBAL', 'IIS11', 'SP211', 'WIIS', 'WAQ', 'WSP2']


def job_settings():
    return {
        '_job_name': 'EIIWOF03', 'input_root': INPUT_ROOT, 'output_root': OUTPUT_ROOT,
        'lnnote_root': LNNOTE_ROOT,
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

"""EIIWOF03: initialize this job, then call the original MNP program sequence."""
import argparse
import logging
from pathlib import Path
import EIFMNP02
from EIFMNP02 import Context


def run(context):
    EIFMNP02.run(context)


# Input libraries and datasets for THIS job (equivalent to its JCL DD bindings).
INPUT_DATASETS = [('LOAN', 'LNNOTE'), ('NPL6', 'NPLOBAL'), ('NPL6', 'WIIS'), ('NPL6', 'WAQ'), ('NPL6', 'WSP2')]
INPUT_FILES = []


def initialize(settings=None, run_date=None, context_type=Context):
    """This job owns its paths, reporting date and input preflight."""
    from copy import deepcopy
    cfg = job_settings()
    if settings is not None: cfg.update(deepcopy(settings))
    cfg['_job_name'] = 'EIIWOF03'
    cfg['seed_inputs'] = list(SEED_INPUTS)
    context = context_type(cfg, run_date=run_date)
    def local_path(value):
        path = Path(value)
        return (path if path.is_absolute() else context.base / path).resolve()
    try:
        input_root = local_path(context.cfg.get('input_root', '/stgsrcsys/host/uat'))
        output_root = local_path(context.cfg.get('output_root', '/stgsrcsys/host/holding'))
        context.cfg['input_root'] = str(input_root)
        context.cfg['output_root'] = str(output_root)
        libraries = context.cfg.setdefault('libraries', {})
        libraries['LOAN'] = str(local_path(context.cfg['lnnote_root']))
        libraries['NPL6'] = str(output_root)  # Working x datasets
        context.cfg.setdefault('reports', str(output_root / 'reports'))
        context.cfg.setdefault('output_format', 'parquet')
        context.cfg.setdefault('output_suffix', 'x')
        context.reporting_date()  # 27 December run; 26 December data.
        context.input_paths = {
            f'{library}.{member}': context.input_table(library, member)
            for library, member in INPUT_DATASETS
        }
        for name in INPUT_FILES:
            path = context.path('files', name)
            if not path.is_file():
                raise FileNotFoundError(path)
            context.input_paths[name] = path
        return context
    except Exception:
        context.close()
        raise


def main():
    parser = argparse.ArgumentParser(description='EIIWOF03: initialize inputs and run')
    parser.add_argument('--run-date', help='Scheduled date YYYY-12-27; defaults to today in Singapore')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    context = initialize(run_date=args.run_date)
    try:
        run(context)
    finally:
        context.close()


if __name__ == '__main__':
    main()
