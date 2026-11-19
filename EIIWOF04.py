# Settings for EIIWOF04; edit these paths in this file.
INPUT_ROOT = '/exdwh/host/ln/npl_hp_sasdata/pibb'
OUTPUT_ROOT = '/exdwh/host/ln/npl_hp_sasdata/pibb/woff'
SASDATA_PATHS = {
    'SAP.PBB.NPL.HP.SASDATA': '/exdwh/host/ln/npl_hp_sasdata/pbb',
    'SAP.PIBB.NPL.HP.SASDATA': '/exdwh/host/ln/npl_hp_sasdata/pibb',
}
SEED_INPUTS = ['NPLOBAL', 'IIS11', 'SP211']


def job_settings():
    return {
        '_job_name': 'EIIWOF04', 'input_root': INPUT_ROOT, 'output_root': OUTPUT_ROOT,
        'backup_root': '/exdwh/host/ln/npl_hp_sasdata/pibb/backup',
        'output_format': 'parquet', 'output_suffix': 'x', 'batch_rows': 65536,
        'encoding': 'utf-8', 'output_encoding': 'utf-8', 'sas_encoding': 'infer',
        'sas_export': True, 'seed_inputs': list(SEED_INPUTS),
        'libraries': {
            'NPLA': SASDATA_PATHS['SAP.PIBB.NPL.HP.SASDATA'],
            'PBB': SASDATA_PATHS['SAP.PBB.NPL.HP.SASDATA'],
            'LOAN': '/sas/ln/dwh/enrichment', 'SASLN': '/dwh/ln_ln', 'HD': INPUT_ROOT,
            'NPL': OUTPUT_ROOT, 'NPL6': OUTPUT_ROOT,
        },
        'reports': '/dwh/ftp/drr',
        'files': {
            'WOFF': '/host_pq/loan/input/WRI2OFF_MIS.txt',
            'WOFFC': '/host_pq/loan/input/woff02.txt',
            'PATCH': '/host_pq/loan/input/woff03.txt',
            'WOFFACCT': '/dwh/ftp/drr/HPTXT1x.txt',
            'WOFFACC2': '/dwh/ftp/drr/HPTXT2x.txt',
        },
    }

"""EIIWOF04: initialize this job, then call the original MNP program sequence."""
import argparse
import logging
from pathlib import Path
import EIIMNP03
from EIIMNP03 import Context


def run(context):
    EIIMNP03.run(context)


# Input libraries and datasets for THIS job (equivalent to its JCL DD bindings).
INPUT_DATASETS = [('NPL', 'LOAN12'), ('NPL', 'WIIS'), ('NPL', 'IIS11'), ('NPL', 'PLOAN12')]
INPUT_FILES = []


def initialize(settings=None, run_date=None, context_type=Context):
    """This job owns its paths, reporting date and input preflight."""
    from copy import deepcopy
    cfg = job_settings()
    if settings is not None: cfg.update(deepcopy(settings))
    cfg['_job_name'] = 'EIIWOF04'
    cfg['seed_inputs'] = list(SEED_INPUTS)
    context = context_type(cfg, run_date=run_date)
    def local_path(value):
        path = Path(value)
        return (path if path.is_absolute() else context.base / path).resolve()
    try:
        input_root = local_path(context.cfg.get('input_root', '/exdwh/host/ln/npl_hp_sasdata/pibb'))
        output_root = local_path(context.cfg.get('output_root', '/exdwh/host/ln/npl_hp_sasdata/pibb/woff'))
        context.cfg['input_root'] = str(input_root)
        context.cfg['output_root'] = str(output_root)
        libraries = context.cfg.setdefault('libraries', {})
        libraries['NPL'] = str(output_root)  # Working x datasets
        context.cfg.setdefault('reports', '/dwh/ftp/drr')
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
    parser = argparse.ArgumentParser(description='EIIWOF04: initialize inputs and run')
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
