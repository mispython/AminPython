"""EIIWOF05: initialize this job, then call the original MNP program sequence."""
import argparse
import logging
from pathlib import Path
import EIFMNP06
from EIFMNP06 import Context


def run(context):
    EIFMNP06.run(context)


# Input libraries and datasets for THIS job (equivalent to its JCL DD bindings).
INPUT_DATASETS = [('NPL', 'LOAN12'), ('NPL', 'WSP2'), ('NPL', 'IIS12'), ('NPL', 'SP211'), ('NPL', 'PLOAN12')]
INPUT_FILES = []


def initialize(config_path, run_date=None, context_type=Context):
    """This job owns its paths, reporting date and input preflight."""
    context = context_type(config_path, run_date=run_date)
    def local_path(value):
        path = Path(value)
        return (path if path.is_absolute() else context.base / path).resolve()
    try:
        input_root = local_path(context.cfg.get('input_root', '/stgsrcsys/host/uat'))
        output_root = local_path(context.cfg.get('output_root', '/stgsrcsys/host/holding'))
        context.cfg['input_root'] = str(input_root)
        context.cfg['output_root'] = str(output_root)
        libraries = context.cfg.setdefault('libraries', {})
        libraries['NPL'] = str(output_root)  # Working x datasets
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
    parser = argparse.ArgumentParser(description='EIIWOF05: initialize inputs and run')
    parser.add_argument('--config', required=True)
    parser.add_argument('--run-date', help='Scheduled date YYYY-12-27; defaults to today in Singapore')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    context = initialize(args.config, args.run_date)
    try:
        run(context)
    finally:
        context.close()


if __name__ == '__main__':
    main()
