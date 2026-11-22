#!/usr/bin/env python3
"""EIIWOF03x - Test original loan processing with Parquet LNNOTE input."""
import argparse
from time import perf_counter
from pathlib import Path
import EIFMNP02x

RUN_DATE = "2026-12-27"
LNNOTE_ROOT = "/stgsrcsys/host/holding/pas"
SEED_ROOT = "/exdwh/host/ln/npl_hp_sasdata/pibb/woff"
OUTPUT_ROOT = "/stgsrcsys/host/holding/pas/test_eiiwof03x"


def job_settings():
    return {
        'run_date': RUN_DATE,
        'input_root': SEED_ROOT, 'seed_root': SEED_ROOT,
        'lnnote_root': LNNOTE_ROOT, 'lnnote_extension': '.parquet',
        'output_root': OUTPUT_ROOT, 'output_format': 'sas7bdat',
        'output_suffix': 'x', 'sas_encoding': 'infer', 'batch_rows': 50000,
        'seed_inputs': ['NPLOBAL', 'WIIS', 'WAQ', 'WSP2'],
        'libraries': {'LOAN': LNNOTE_ROOT, 'NPL6': OUTPUT_ROOT},
        'reports': OUTPUT_ROOT, 'files': {},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-date', default=RUN_DATE)
    args = parser.parse_args()
    started = perf_counter()
    context = EIFMNP02x.Context(job_settings(), run_date=args.run_date)
    try:
        for lib, member in [('LOAN', 'LNNOTE'), ('NPL6', 'NPLOBAL'),
                            ('NPL6', 'WIIS'), ('NPL6', 'WAQ'), ('NPL6', 'WSP2')]:
            print(f'Input {lib}.{member}: {context.input_table(lib, member)}', flush=True)
        print(f'Output folder: {OUTPUT_ROOT}', flush=True)
        EIFMNP02x.run(context)
        print(f'Completed in {perf_counter() - started:.1f} seconds', flush=True)
    finally:
        context.close()


if __name__ == '__main__':
    main()
