# Support functions are embedded; no INC folder or extra Python job is required.
"""Bounded Arrow output batches and explicit-schema SAS export, without SASPy."""
import csv
import re
import math
from decimal import Decimal
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq


def sas_number(value):
    value = float(value)
    if not math.isfinite(value): raise ValueError('Numeric value exceeds SAS double range')
    return format(value, '.17g')


def write_dual(path, rows, columns, characters, config):
    size = int(config.get('batch_rows', 65536))
    if size < 1: raise ValueError('batch_rows must be positive')
    if any(not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,31}', k) for k in columns):
        raise ValueError('Invalid SAS column name')
    # Decimal columns preserve Python calculations across job boundaries, without
    # introducing a float round-trip. SAS export uses its native numeric double.
    chars = set(characters) & set(columns)
    scales = dict.fromkeys(columns, 0)
    integers = dict.fromkeys(columns, 1)
    widths = dict.fromkeys(columns, 1)
    for row in rows:
        for k in columns:
            v = row.get(k)
            if v is None: continue
            if isinstance(v, str): chars.add(k)
            if k in chars:
                widths[k] = max(widths[k], len(str(v).encode('utf-8')))
            else:
                d = v if isinstance(v, Decimal) else Decimal(str(v))
                if not d.is_finite(): raise ValueError(f'Nonfinite numeric value in {k}')
                scales[k] = max(scales[k], -d.as_tuple().exponent)
                integers[k] = max(integers[k], d.adjusted() + 1)
    # A late string value makes the entire column character; include earlier values.
    for k in chars:
        widths[k] = max(1, max((len(str(r[k]).encode('utf-8')) for r in rows if r.get(k) is not None), default=1))
    fields = []
    for k in columns:
        precision = max(1, integers[k] + scales[k])
        if k not in chars and precision > 76:
            raise ValueError(f'{k}: decimal precision exceeds Arrow limit; refusing rounding')
        fields.append(pa.field(k, pa.string() if k in chars else
                               (pa.decimal128(max(1,precision),scales[k]) if precision <= 38 else
                                pa.decimal256(precision,scales[k]))))
    schema = pa.schema(fields)
    path.parent.mkdir(parents=True, exist_ok=True)
    stage = path.with_suffix('.parquet.tmp')
    export = bool(config.get('sas_export', True))
    bridge = path.parent / 'sas_bridge'
    data = bridge / (path.stem + '.csv')
    script = bridge / (path.stem + '.sas')
    data_stage = data.with_suffix('.csv.tmp')
    script_stage = script.with_suffix('.sas.tmp')
    try:
        if export:
            # HEX informats preserve leading spaces, quotes, delimiters and newlines.
            # SAS HEX informat width is limited to 32767 characters.
            if any(widths[k] > 16383 for k in chars):
                raise ValueError('SAS bridge supports character values up to 16383 UTF-8 bytes')
            if sum(widths[k]*2 if k in chars else 32 for k in columns) + len(columns) > 10485760:
                raise ValueError('SAS bridge row exceeds configured record length')
            bridge.mkdir(exist_ok=True)
        with pq.ParquetWriter(stage, schema, compression='zstd', use_dictionary=True) as writer:
            for start in range(0, len(rows), size):
                chunk = rows[start:start+size]
                arrays = []
                for field in schema:
                    k = field.name
                    values = [(None if r.get(k) is None else str(r[k])) if k in chars else
                              (None if r.get(k) is None else Decimal(str(r[k]))) for r in chunk]
                    arrays.append(pa.array(values, type=field.type))
                writer.write_table(pa.Table.from_arrays(arrays, schema=schema), row_group_size=size)
        if export:
            with data_stage.open('w', encoding='ascii', newline='') as handle:
                writer = csv.writer(handle, lineterminator='\n')
                for row in rows:
                    writer.writerow('' if row.get(k) is None else
                                    str(row[k]).encode('utf-8').ljust(widths[k], b' ').hex() if k in chars else sas_number(row[k])
                                    for k in columns)
            quote = lambda p: "'" + str(p).replace('\\', '/').replace("'", "''") + "'"
            lengths = '\n'.join(f'length {k} ${widths[k]};' if k in chars else f'length {k} 8;' for k in columns)
            inputs = '\n'.join(f'{k} :$hex{widths[k]*2}.' if k in chars else f'{k} :best32.' for k in columns)
            # DATA step uses an explicit schema: no PROC IMPORT type guessing/sample.
            code = f'''/* Generated export only: no business filters or calculations. */
options errorabend;
%macro export_table;
%if %upcase(%sysfunc(getoption(encoding))) ne UTF-8 %then %do;
  %put ERROR: Run SAS with -encoding utf-8 for the HEX character bridge.;
  %abort abend;
%end;
libname hout {quote(path.parent)};
data hout._export_tmp;
{lengths}
infile {quote(data)} dsd dlm=',' truncover termstr=lf lrecl=10485760;
input
{inputs}
;
if _error_ then abort abend;
run;
%if &syserr > 4 %then %abort abend;
%let dsid=%sysfunc(open(hout._export_tmp));
%let actual=%sysfunc(attrn(&dsid,nlobs));
%let rc=%sysfunc(close(&dsid));
%if &actual ne {len(rows)} %then %abort abend;
proc datasets library=hout nolist;
  delete {path.stem};
  change _export_tmp={path.stem};
quit;
%if &syserr > 4 %then %abort abend;
%put NOTE: Exported {path.stem} {len(rows)} observations.;
%mend;
%export_table;
'''
            script_stage.write_text(code, encoding='utf-8')
            data_stage.replace(data)
            script_stage.replace(script)
        stage.replace(path)
    finally:
        for temp in (stage, data_stage, script_stage):
            temp.unlink(missing_ok=True)


"""Write genuine SAS7BDAT through an existing SASPy connection profile.

SAS builds a unique table in remote WORK. Download it to a local staging file,
validate the binary, then atomically publish it in the Python host's holding dir.
"""
from pathlib import Path
from decimal import Decimal
import math
import ntpath
import posixpath
import re
import uuid


class SASOutput:
    def __init__(self, config):
        self.config = config
        self.session = None

    def connect(self):
        if self.session is None:
            try:
                import saspy
            except ImportError as exc:
                raise RuntimeError('SAS7BDAT output requires SASPy. Install requirements.txt and configure your SASPy profile.') from exc
            kwargs = {'cfgname': self.config.get('cfgname', 'default'), 'results': 'TEXT'}
            if self.config.get('cfgfile'):
                kwargs['cfgfile'] = self.config['cfgfile']
            self.session = saspy.SASsession(**kwargs)
        return self.session

    def write(self, path, rows, columns, character_columns, validate):
        import pandas as pd
        frame = pd.DataFrame(index=range(len(rows)))
        lengths = {}
        for column in columns:
            if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,31}', column):
                raise ValueError(f'Unsupported SAS column name: {column!r}')
            values = [row.get(column) for row in rows]
            text = column in character_columns
            if not text:
                for value in values:
                    if value is None or value == '': continue
                    try: Decimal(str(value))
                    except Exception:
                        text = True
                        break
            if text:
                values = ['' if v is None else str(v) for v in values]
                if any(any(ch in v for ch in ('\x01', '\x02', '\x03')) for v in values):
                    raise ValueError(f'{column}: contains reserved SASPy transfer control characters')
                frame[column] = pd.Series(values, dtype=object)
                lengths[column] = max([1] + [len(v.encode('utf-8')) for v in values])
                if lengths[column] > 32767:
                    raise ValueError(f'{column}: character value exceeds SAS length limit')
            else:
                values = [float('nan') if v is None or v == '' else float(v) for v in values]
                if any(math.isinf(v) for v in values):
                    raise ValueError(f'{column}: infinite values cannot be written to SAS')
                frame[column] = pd.Series(values, dtype='float64')
        session = self.connect()
        member = '_wof_' + uuid.uuid4().hex[:20]
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        stage = path.with_name('.' + path.stem + '_' + uuid.uuid4().hex[:8] + '.sas7bdat')
        try:
            dataset = session.dataframe2sasdata(frame, table=member, libref='WORK',
                                               results='TEXT', char_lengths=lengths,
                                               encode_errors='fail')
            if int(session.SYSERR()) > 4:
                raise RuntimeError('SAS returned an error while creating the output table')
            if dataset is None or not session.exist(member, 'WORK'):
                raise RuntimeError('SASPy did not create the output table in remote WORK')
            join = ntpath.join if '\\' in session.workpath else posixpath.join
            remote = join(session.workpath, member + '.sas7bdat')
            result = session.download(str(stage), remote, overwrite=True)
            if not result.get('Success') or not stage.is_file():
                raise RuntimeError('SASPy could not download the SAS7BDAT output from remote WORK')
            validate(stage, columns, len(rows))
            stage.replace(path)
        finally:
            if stage.exists(): stage.unlink()
            # Only the generated UUID table in this session's WORK is removed.
            try:
                session.submit(f'proc datasets lib=work nolist; delete {member}; quit;', results='TEXT')
            except Exception:
                pass

    def close(self):
        if self.session is not None:
            self.session.endsas()
            self.session = None


"""Prepare a SAS export driver for the current batch, or check completed copies."""
import argparse,json
from pathlib import Path


def prepare(c, check=False, quiet=False):
    import pyarrow.parquet as pq
    c.reporting_date()
    state=json.loads(c._state_path().read_text())
    if state.get('run_date') != c.run_date.isoformat(): raise ValueError('Wrong batch year')
    if not state.get('outputs'): raise ValueError('No outputs in batch')
    lines=['/* Run after Python jobs finish; never run concurrently with them. */']
    for name, filename in state['outputs'].items():
        p=c.input_table('NPL',name)
        if p.suffix != '.parquet': raise ValueError('Expected parquet output')
        if check:
            expected=pq.ParquetFile(p).metadata.num_rows
            binary=p.with_suffix('.sas7bdat')
            if binary.stat().st_mtime < p.stat().st_mtime: raise ValueError(f'Stale SAS copy: {binary}')
            with c._sas_reader(binary) as reader:
                if reader.row_count != expected or [str(k).upper() for k in reader.column_names] != pq.read_schema(p).names:
                    raise ValueError(f'SAS output count/schema mismatch: {binary}')
        else:
            script=c.holding()/'sas_bridge'/(p.stem+'.sas')
            if not script.exists(): raise FileNotFoundError(script)
            lines.append("%include '"+str(script).replace('\\','/').replace("'","''")+"';")
    if not check:
        driver=c.holding()/'export_all.sas'
        temp=driver.with_suffix('.sas.tmp')
        temp.write_text('\n'.join(lines)+'\n',encoding='utf-8')
        temp.replace(driver)
        if not quiet: print(f'Run on SAS server: sas -encoding utf-8 -sysin {driver}')
    else: print('SAS copies: freshness, row count and column order checks passed. Reconcile values separately.')



"""Shared utilities for SAS7BDAT inputs and CSV working outputs.

CSV tables use uppercase columns, blank missing values and SAS numeric dates.
SAS BY merges are positional within groups, not SQL Cartesian joins.
"""
import argparse
import csv
import importlib.util
import json
import logging
import re
import shutil
import sys
from collections import defaultdict
from itertools import groupby
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

LOG = logging.getLogger(__name__)
EPOCH = date(1960, 1, 1)


def num(value):
    if value is None or isinstance(value, Decimal): return value
    text = str(value).strip()
    if text in ('', '.') or (len(text)==2 and text[0]=='.' and (text[1].isalpha() or text[1]=='_')):
        return None
    try:
        return Decimal(str(value).strip().replace(',', ''))
    except InvalidOperation as exc:
        raise ValueError(f'Invalid numeric value: {value!r}') from exc


def account(value):
    v = num(value)
    return '' if v is None else str(int(v))


def rnd(value):
    v = num(value)
    return None if v is None else v.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)


def sas_sum(*values):
    valid = [n for v in values if (n := num(v)) is not None]
    return sum(valid, Decimal(0)) if valid else None


def subtract(a, b):
    a, b = num(a), num(b)
    return None if a is None or b is None else a - b


def sas_add(a, b):
    a, b = num(a), num(b)
    return None if a is None or b is None else a + b


def sort_key(row, keys):
    return tuple((0, Decimal(0)) if (n := num(row.get(k))) is None else (1, n) for k in keys)


def sorted_rows(rows, keys=('ACCTNO',), unique=False):
    rows = sorted(rows, key=lambda r: sort_key(r, keys))
    if not unique:
        return rows
    result, previous = [], None
    for row in rows:
        key = sort_key(row, keys)
        if key != previous:
            result.append(row)
            previous = key
    return result


def merge(tables, keys=('ACCTNO',)):
    """SAS match merge: max group length with retained values and IN flags."""
    # Stable sorting preserves source order within duplicate BY groups.
    schemas = []
    streams = []
    for table in tables:
        schema = set()
        for row in table: schema.update(row)
        schemas.append(schema)
        streams.append(iter(groupby(sorted_rows(table, keys), lambda r: sort_key(r, keys))))
    heads = [next(stream, None) for stream in streams]
    all_columns = set().union(*schemas)
    while any(head is not None for head in heads):
        key = min(head[0] for head in heads if head is not None)
        flags = [head is not None and head[0] == key for head in heads]
        buckets = [list(head[1]) if present else [] for head, present in zip(heads, flags)]
        state = dict.fromkeys(all_columns)
        for i in range(max(map(len, buckets))):
            for bucket in buckets:
                if i < len(bucket): state.update(bucket[i])
            yield dict(state), flags
        for i, present in enumerate(flags):
            if present: heads[i] = next(streams[i], None)


def keep(row, columns):
    return {k: row.get(k) for k in columns.split()}


class Context:
    def __init__(self, path, run_date=None):
        self.config_path = Path(path).resolve()
        self.base = self.config_path.parent
        self.cfg = json.loads(self.config_path.read_text(encoding='utf-8-sig'))
        self.encoding = self.cfg.get('encoding', 'utf-8')
        self._output_writer = None
        self._character_columns = set('NAME BORSTAT EXIST USER5 VINNO CENSUS7 PAIDIND REVERSED WDOWNIND RESCHEIND HARDCODE WRITEOFF BRANCH BRNO BRABBR LOANTYP RISK POSTNTRN GUAREND WNAME MATDATE WOFFDT'.split())
        self._character_columns.update(k.upper() for k in self.cfg.get('character_columns', []))
        # Annual business date. An explicit scheduled date permits controlled reruns.
        self.run_date = (date.fromisoformat(run_date) if isinstance(run_date, str)
                         else run_date or datetime.now(timezone(timedelta(hours=8))).date())

    def reporting_date(self):
        if (self.run_date.month, self.run_date.day) != (12, 27):
            raise ValueError('Annual job runs on 27 December (Singapore time). '
                             'For a test/rerun, pass --run-date YYYY-12-27 for the intended run year.')
        return date(self.run_date.year, 12, 26)

    def path(self, group, name):
        p = Path(self.cfg[group][name])
        return p if p.is_absolute() else self.base / p

    def table(self, lib, name):
        """All routed writes go to holding, regardless of source library alias."""
        if self.cfg.get('output_root'):
            suffix = self.cfg.get('output_suffix', 'x')
            extension = self.cfg.get('output_format', 'sas7bdat')
            if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]{0,31}', name + suffix):
                raise ValueError(f'Invalid output SAS member name: {name + suffix}')
            if extension not in ('sas7bdat', 'csv', 'parquet'):
                raise ValueError('output_format must be sas7bdat, parquet or csv')
            return self.holding() / (name.lower() + suffix + '.' + extension)
        return self.path('libraries', lib) / (name.upper() + '.csv')

    def holding(self):
        p = Path(self.cfg['output_root'])
        return p if p.is_absolute() else self.base / p

    def assert_output_path(self, path):
        if not self.cfg.get('output_root'): return
        root = self.holding().resolve()
        target = Path(path).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f'Output must be within holding: {path}')
        source = Path(self.cfg['input_root'])
        source = (source if source.is_absolute() else self.base / source).resolve()
        if target == source or source in target.parents:
            raise ValueError('Refusing to overwrite a file in the input directory')

    def _state_path(self):
        return self.holding() / 'batch_state.json'

    def record_output(self, name):
        if not self.cfg.get('output_root'): return
        path = self._state_path()
        state = json.loads(path.read_text()) if path.exists() else {}
        key = self.run_date.isoformat()
        if state.get('run_date') != key: state = {'run_date': key, 'outputs': {}}
        state['outputs'][name.upper()] = self.table('NPL', name).name
        temp = path.with_suffix('.json.tmp')
        temp.write_text(json.dumps(state, indent=2), encoding='utf-8')
        temp.replace(path)
        if self.cfg.get('output_format') == 'parquet' and self.cfg.get('sas_export', True):
            prepare(self, quiet=True)

    def reset_outputs(self):
        """Start a new batch manifest without deleting unrelated holding files."""
        self.assert_output_path(self._state_path())
        self.holding().mkdir(parents=True, exist_ok=True)
        self._state_path().write_text(json.dumps({'run_date': self.run_date.isoformat(), 'outputs': {}}), encoding='utf-8')

    def original_table(self, lib, name):
        directory = self.path('libraries', lib)
        matches = [p for p in directory.iterdir() if p.is_file() and p.name.lower() == (name + '.sas7bdat').lower()]
        if len(matches) != 1:
            raise FileNotFoundError(f'Expected exactly one original {name}.sas7bdat in {directory}')
        return matches[0]

    def input_table(self, lib, name):
        if self.cfg.get('output_root'):
            if lib in ('NPL', 'NPL6'):
                path = self.table(lib, name)
                state_path = self._state_path()
                state = json.loads(state_path.read_text()) if state_path.exists() else {}
                if (state.get('run_date') != self.run_date.isoformat()
                        or state.get('outputs', {}).get(name.upper()) != path.name or not path.exists()):
                    raise FileNotFoundError(f'Prior job output is missing for this batch: {path}. Run its producing job first (EIIWOF01 initializes working snapshots).')
                return path
            # Original aliases never pick up holding outputs, even after job 14.
            return self.original_table(lib, name)
        directory = self.path('libraries', lib)
        # Generated tables override the original SAS snapshot on later stages.
        for suffix in ('.csv', '.sas7bdat'):
            expected = (name + suffix).lower()
            matches = [p for p in directory.iterdir() if p.is_file() and p.name.lower() == expected]
            if len(matches) > 1:
                raise ValueError(f'Ambiguous table files: {matches}')
            if matches:
                return matches[0]
        raise FileNotFoundError(f'{directory}: expected {name}.sas7bdat or a generated {name}.csv')

    def _sas_reader(self, path):
        try:
            from pandas.io.sas.sas7bdat import SAS7BDATReader
        except ImportError as exc:
            raise RuntimeError('SAS7BDAT inputs require pandas. Run: python -m pip install -r requirements.txt') from exc
        # Preserve SAS numeric dates: business logic uses days since 1960-01-01.
        return SAS7BDATReader(path, convert_dates=False,
                             encoding=self.cfg.get('sas_encoding', 'latin-1'))

    def schema_path(self, path):
        if path.suffix.lower() == '.parquet':
            import pyarrow.parquet as pq
            import pyarrow as pa
            schema = pq.read_schema(path)
            columns = schema.names
            self._character_columns.update(f.name for f in schema if pa.types.is_string(f.type))
        elif path.suffix.lower() == '.sas7bdat':
            with self._sas_reader(path) as reader:
                columns = [str(k).upper() for k in reader.column_names]
                self._character_columns.update(k for k,t in zip(columns,reader._column_types) if t == b's')
        else:
            with path.open(encoding=self.encoding, newline='') as f:
                columns = [k.upper() for k in next(csv.reader(f), [])]
        if not columns or len(set(columns)) != len(columns):
            raise ValueError(f'Missing or duplicate table columns: {path}')
        return columns

    def schema(self, lib, name):
        return self.schema_path(self.input_table(lib, name))

    def read(self, lib, name):
        return self.read_path(self.input_table(lib, name))

    def read_path(self, path):
        path = Path(path)
        if path.suffix.lower() == '.parquet':
            import pyarrow.parquet as pq
            self.schema_path(path)
            result = []
            for batch in pq.ParquetFile(path).iter_batches(batch_size=self.cfg.get('batch_rows', 65536)):
                result.extend(batch.to_pylist())
            return result
        if path.suffix.lower() == '.sas7bdat':
            with self._sas_reader(path) as reader:
                import pandas as pd
                columns = [str(k).upper() for k in reader.column_names]
                self._character_columns.update(k for k,t in zip(columns,reader._column_types) if t == b's')
                if len(set(columns)) != len(columns):
                    raise ValueError(f'Duplicate SAS columns: {path}')
                rows = []
                while True:
                    frame = reader.read(self.cfg.get('batch_rows', 65536))
                    if frame is None or frame.empty: break
                    for values in frame.itertuples(index=False, name=None):
                        row = {}
                        for key, value in zip(columns, values):
                            if pd.isna(value): value = None
                            elif isinstance(value, bytes): value = value.decode(self.cfg.get('encoding', 'utf-8')).rstrip()
                            elif isinstance(value, str): value = value.rstrip()
                            elif hasattr(value, 'item'): value = value.item()
                            row[key] = value
                        rows.append(row)
                return rows
        if path.suffix.lower() != '.csv':
            raise ValueError(f'Expected a SAS7BDAT table or generated CSV: {path}')
        with path.open(encoding=self.encoding, newline='') as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError(f'Missing CSV header: {f.name}')
            if len({k.upper() for k in reader.fieldnames}) != len(reader.fieldnames):
                raise ValueError(f'Duplicate CSV columns: {f.name}')
            return [{k.upper(): (None if v == '' else v) for k, v in r.items()} for r in reader]

    def input_rows(self, name, required, optional=()):
        """External exclusion/patch tables: columns, not fixed text offsets."""
        path = self.path('files', name)
        columns = self.schema_path(path)
        mapping = {k.upper():v.upper() for k,v in self.cfg.get('column_mappings', {}).get(name, {}).items()}
        missing = [key for key in required if mapping.get(key, key) not in columns]
        if missing:
            raise ValueError(f'{path}: missing columns {missing}; configure column_mappings.{name} if names differ')
        return [{key:r.get(mapping.get(key,key)) for key in (*required,*optional)} for r in self.read_path(path)]

    def write(self, lib, name, rows, columns=None):
        path = self.table(lib, name)
        self.assert_output_path(path)
        rows = rows if isinstance(rows, list) else list(rows)
        columns = columns or list(dict.fromkeys(k for r in rows for k in r))
        if not columns: raise ValueError(f'Column schema required for {name}')
        if path.suffix == '.parquet':
            write_dual(path, rows, columns, self._character_columns, self.cfg)
        elif path.suffix == '.sas7bdat':
            if self._output_writer is None:
                self._output_writer = SASOutput(self.cfg.get('saspy', {}))
            def validate(binary, expected, count):
                with self._sas_reader(binary) as reader:
                    if [str(k).upper() for k in reader.column_names] != expected or reader.row_count != count:
                        raise RuntimeError('SAS7BDAT validation failed: output columns or row count differ')
            self._output_writer.write(path, rows, columns, self._character_columns, validate)
        else:
            self.write_csv(path, rows, columns)
        self.record_output(name)

    def close(self):
        if self._output_writer is not None:
            self._output_writer.close()

    def write_csv(self, path, rows, columns=None, delimiter=','):
        self.assert_output_path(path)
        rows = rows if isinstance(rows, list) else list(rows)
        columns = columns or list(dict.fromkeys(k for r in rows for k in r))
        if not columns:
            raise ValueError(f'Column schema required for empty table: {path}')
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + '.tmp')
        with tmp.open('w', encoding=self.cfg.get('output_encoding', 'utf-8'), newline='') as f:
            writer = csv.DictWriter(f, fieldnames=columns, delimiter=delimiter, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows)
        tmp.replace(path)

    def report(self, job, rows, columns=None):
        p = Path(self.cfg.get('reports', 'reports'))
        p = p if p.is_absolute() else self.base / p
        self.write_csv(p / (job + '.csv'), rows, columns)

    def fixed(self, name, fields):
        rows = []
        with self.path('files', name).open(encoding=self.encoding, newline='') as f:
            for line_no, line in enumerate(f, 1):
                line = line.rstrip('\r\n')
                if len(line) < max(start + width - 1 for _, start, width, _ in fields):
                    raise ValueError(f'{name} line {line_no}: record shorter than required fields')
                row = {}
                for key, start, width, typ in fields:
                    value = line[start-1:start-1+width].strip()
                    if typ == 'char':
                        row[key] = value or None
                    elif typ == 'money':
                        n = num(value)
                        row[key] = n if n is None or '.' in value else n / 100
                    else:
                        row[key] = num(value)
                rows.append(row)
        return rows


def hp(row):
    cost = num(row.get('COSTCTR'))
    return cost is not None and (3000 <= cost <= 3999 or cost in (4043, 4048))


def report_date(rows):
    if not rows:
        raise ValueError('REPTDATE must contain at least one observation')
    value = rows[-1]['REPTDATE']
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        n = num(value)
        if n is None:
            raise ValueError('Missing REPTDATE')
        return EPOCH + timedelta(days=int(n))


def run_cli(job, run):
    parser = argparse.ArgumentParser(description=f'Run converted {job}')
    parser.add_argument('--config', required=True,
                        help='JSON path; data paths resolve beside this file')
    parser.add_argument('--run-date', help='Scheduled run date YYYY-12-27; omit for today in Singapore')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    context = None
    try:
        context = Context(args.config, run_date=args.run_date)
        as_at = context.reporting_date()
        LOG.info('Starting %s; scheduled run %s; data/report date %s', job, context.run_date, as_at)
        run(context)
        LOG.info('Completed %s', job)
    except Exception as exc:
        LOG.error('%s failed: %s', job, exc)
        sys.exit(1)
    finally:
        if context is not None:
            context.close()


# Original program logic follows.
"""EIIWOF10: independently runnable job with its own processing logic."""
from pathlib import Path
from decimal import Decimal
from datetime import date
import csv
import shutil


def run(c):
    for target, temp in [('WSP2','TSP2'),('WIIS','TIIS'),('WAQ','TAQ')]:
        old, new = c.read('NPLA',target), c.read('NPL',temp)
        columns = list(dict.fromkeys(k for r in old + new for k in r))
        if not columns:
            columns = c.schema('NPLA',target)
        c.write('NPL',target,sorted_rows(old + new),columns)



# Input libraries and datasets for THIS job (equivalent to its JCL DD bindings).
INPUT_DATASETS = [('NPLA', 'WIIS'), ('NPLA', 'WAQ'), ('NPLA', 'WSP2'), ('NPL', 'TIIS'), ('NPL', 'TAQ'), ('NPL', 'TSP2')]
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
        libraries['NPLA'] = str(local_path(libraries.get('NPLA', str(input_root))))
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
    parser = argparse.ArgumentParser(description='EIIWOF10: initialize inputs and run')
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
