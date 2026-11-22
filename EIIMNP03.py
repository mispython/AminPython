"""EIIMNP03 - IIS processing; paths and dates come from the calling WOF job."""

# Support functions are embedded; no INC folder or extra Python job is required.

import csv
import re
import math
from decimal import Decimal
from pathlib import Path


def sas_number(value):
    value = float(value)
    if not math.isfinite(value): raise ValueError('Numeric value exceeds SAS double range')
    return format(value, '.17g')




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
    """Shared-folder TXT export: SAS reads locally, without DataFrame transfer."""
    def __init__(self, config):
        self.config = config
        self.session = None

    def connect(self):
        if self.session is None:
            import saspy
            self.session = saspy.SASsession(**self.config)
        return self.session

    def write(self, path, rows, columns, character_columns, validate, schema):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        bridge = path.parent / 'sas_bridge'
        bridge.mkdir(exist_ok=True)
        text = bridge / (path.stem + '.txt')
        temporary = text.with_suffix('.txt.tmp')
        # Values are hex-encoded for character fields; preserve Latin-1 byte lengths.
        with temporary.open('w', encoding='ascii', newline='') as handle:
            writer = csv.writer(handle, lineterminator='\n')
            for row in rows:
                record = []
                for col in columns:
                    kind, width = schema[col]
                    value = row.get(col)
                    if value is None:
                        record.append('')
                    elif kind == 'Char':
                        encoded = str(value).encode('latin-1')
                        if len(encoded) > width:
                            raise ValueError(f'{path.stem}.{col}: value exceeds supplied length {width}')
                        record.append(encoded.ljust(width, b' ').hex())
                    else:
                        record.append(sas_number(value))
                writer.writerow(record)
        temporary.replace(text)
        quote = lambda v: "'" + str(v).replace("'", "''") + "'"
        lengths = '\n'.join(f'length {c} {"$" if schema[c][0] == "Char" else ""}{schema[c][1]};' for c in columns)
        formats = '\n'.join(f'format {c} {fmt};' for c, fmt in {'FDACCTNO': '10.', 'TRA_EFF_DT': 'Z6.'}.items() if c in columns)
        inputs = '\n'.join(f'{c} :$hex{schema[c][1] * 2}.' if schema[c][0] == 'Char' else f'{c} :best32.' for c in columns)
        member = '_w' + uuid.uuid4().hex[:20]
        stage = path.parent / (member + '.sas7bdat')
        session = self.connect()
        session.submit('%let _wof_encoding=%sysfunc(getoption(encoding));', results='TEXT')
        if session.symget('_wof_encoding').strip().upper() not in ('LATIN1', 'WLATIN1'):
            raise RuntimeError('This export preserves Latin-1 input lengths; configure the SASPy session with encoding LATIN1 or WLATIN1')
        try:
            code = f"""
libname wofout {quote(path.parent)};
data wofout.{member}(encoding='latin1');
{lengths}
{formats}
infile {quote(text)} dsd dlm=',' truncover termstr=lf lrecl=10485760;
input
{inputs}
;
run;
"""
            result = session.submit(code, results='TEXT')
            log = result['LOG']
            if re.search(r'^ERROR(?:\s|:)', log, re.MULTILINE) or int(session.SYSERR()) > 4:
                raise RuntimeError('SAS export failed: ' + log)
            if not stage.is_file():
                raise RuntimeError('SAS server must share the output and sas_bridge folder with Python')
            validate(stage, columns, len(rows))
            stage.replace(path)
        finally:
            stage.unlink(missing_ok=True)

    def close(self):
        if self.session is not None:
            self.session.endsas()
            self.session = None






"""Shared utilities for SAS7BDAT inputs and CSV working outputs.

CSV tables use uppercase columns, blank missing values and SAS numeric dates.
SAS BY merges are positional within groups, not SQL Cartesian joins.
"""
import argparse
import csv
import importlib.util
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


# Confirmed input types/lengths; PBB and PIBB share this schema.
def output_schema(context, name, columns):
    """Inherit metadata from SAS inputs; define only new fields explicitly."""
    cache = getattr(context, '_metadata_cache', None)
    if cache is None:
        cache = context._metadata_cache = {}
    def metadata(path):
        path = Path(path)
        if path not in cache:
            with context._sas_reader(path) as reader:
                cache[path] = {
                    str(col.name).upper(): ('Char' if col.ctype == b's' else 'Num', col.length)
                    for col in reader.columns
                }
        return cache[path]
    bank = Path(context.cfg['input_root'])
    def source(member):
        matches = [p for p in bank.glob('*.sas7bdat') if p.stem.upper() == member]
        if len(matches) != 1:
            raise FileNotFoundError(f'Expected one {member}.sas7bdat in {bank}')
        return metadata(matches[0])
    key = name.upper()
    if key == 'HPWOFF':
        schema = {k: ('Char' if k == 'WOFFDT' else 'Num', 8)
                  for k in ('ACCTNO', 'CAPBAL', 'WOFFDT', 'IIS', 'SPALLOW')}
    elif key == 'WOFFHP':
        schema = {'ACCTNO': ('Num', 8), 'WNAME': ('Char', 30)}
    elif key == 'REPTDATE' or key in ('TIIS', 'TAQ', 'TSP2'):
        schema = dict.fromkeys(columns, ('Num', 8))
    else:
        base = key
        if key in ('LOAN12', 'PLOAN12', 'WIIS', 'WAQ', 'WSP2'):
            day = (context.run_date - timedelta(days=1)).strftime('%d')
            note = Path(context.cfg['lnnote_root']) / f'enrh_ln_note_d{day}.sas7bdat'
            schema = dict(metadata(note))
            if key in ('LOAN12', 'PLOAN12'):
                opening = source('NPLOBAL')
                for field in 'ACCTNO NOTENO NTBRCH NAME LOANTYPE LOANSTAT IISP OIP SPP1 SPP2 CURBALP NETBALP EXIST UHCP'.split():
                    schema[field] = opening[field]
            else:
                schema.update(source(key))
        else:
            if key == 'IIS12': base = 'IIS'
            if key == 'SP212': base = 'SP2'
            schema = dict(source(base))
        # Derived fields defined by the original processing steps.
        additions = {'ISSDTE': ('Num', 8), 'BLDATE': ('Num', 8),
                     'DAYS': ('Num', 8), 'TERMCHG': ('Num', 8),
                     'CENSUS7': ('Char', 8), 'LOANTYP': ('Char', 20),
                     'RISK': ('Char', 13), 'CHKNPL': ('Num', 8)}
        for field in 'SUSPEND RECOVER RECC IISPW WOIW'.split():
            additions[field] = ('Num', 8)
        for field, definition in additions.items():
            schema.setdefault(field, definition)
    missing = set(columns) - set(schema)
    if missing:
        raise ValueError(f'{name}: input metadata or explicit definition needed for {sorted(missing)}')
    return {field: schema[field] for field in columns}



class Context:
    def __init__(self, settings=None, run_date=None):
        from copy import deepcopy
        self.base = Path(__file__).resolve().parent
        if settings is None:
            raise ValueError('Run through EIIWOF04 or EIIWOF13; caller settings are required')
        self.cfg = deepcopy(settings)
        self._written_outputs = set()
        self._exported_members = set()
        self.encoding = self.cfg.get('encoding', 'utf-8')
        self._output_writer = None
        self._character_columns = set('NAME BORSTAT EXIST USER5 VINNO CENSUS7 PAIDIND REVERSED WDOWNIND RESCHEIND HARDCODE WRITEOFF BRANCH BRNO BRABBR LOANTYP RISK POSTNTRN GUAREND WNAME MATDATE WOFFDT'.split())
        self._character_columns.update(k.upper() for k in self.cfg.get('character_columns', []))
        # Annual business date. An explicit scheduled date permits controlled reruns.
        self.run_date = (date.fromisoformat(run_date) if isinstance(run_date, str)
                         else run_date or date.fromisoformat(self.cfg['run_date']))

    def reporting_date(self):
        # Use the scheduled date supplied by the calling main job.
        return self.run_date - timedelta(days=1)


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
        report_root = Path(self.cfg['reports']).resolve()
        report_target = Path(path).resolve()
        if report_root in report_target.parents:
            return
        if not self.cfg.get('output_root'): return
        root = self.holding().resolve()
        target = Path(path).resolve()
        if target != root and root not in target.parents:
            raise ValueError(f'Output must be within holding: {path}')
        source = Path(self.cfg['input_root'])
        source = (source if source.is_absolute() else self.base / source).resolve()
        if target == source or target.parent == source:
            raise ValueError('Refusing to overwrite a file in the input directory')



    def record_output(self, name):
        self._written_outputs.add(name.upper())

    def original_table(self, lib, name):
        directory = self.path('libraries', lib)
        matches = [p for p in directory.iterdir() if p.is_file() and p.name.lower() == (name + '.sas7bdat').lower()]
        if len(matches) != 1:
            raise FileNotFoundError(f'Expected exactly one original {name}.sas7bdat in {directory}')
        return matches[0]

    def input_table(self, lib, name):
        if lib not in ('NPL', 'NPL6'):
            return self.original_table(lib, name)
        if name.upper() in self.cfg.get('seed_inputs', []) and name.upper() not in self._written_outputs:
            # Explicit initial dataset for this job, copied unchanged by job 01.
            directory = self.holding()
            extension = self.cfg.get('seed_extension', '.sas7bdat')
            matches = [p for p in directory.iterdir() if p.is_file() and p.name.lower() == (name + extension).lower()]
            if len(matches) != 1:
                raise FileNotFoundError(f'Expected one {name}{extension} in {directory}')
            return matches[0]
        path = self.table(lib, name)
        if not path.is_file():
            raise FileNotFoundError(f'Required prior-job output missing: {path}')
        return path

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
        if path.suffix == '.sas7bdat':
            if self._output_writer is None:
                self._output_writer = SASOutput(self.cfg.get('saspy', {}))
            def validate(binary, expected, count):
                with self._sas_reader(binary) as reader:
                    if [str(k).upper() for k in reader.column_names] != expected or reader.row_count != count:
                        raise RuntimeError('SAS7BDAT validation failed: output columns or row count differ')
                    for col in reader.columns:
                        key = str(col.name).upper()
                        kind, width = schema[key]
                        expected_type = b's' if kind == 'Char' else b'd'
                        if col.ctype != expected_type or col.length != width:
                            raise RuntimeError(f'{name}.{key}: SAS type/length differs from supplied metadata')
            schema = output_schema(self, name, columns)
            self._output_writer.write(path, rows, columns, self._character_columns, validate, schema)
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





"""Shared SAS value/date/table utilities; business stages live in each MNP job."""
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from collections import defaultdict
from pathlib import Path
import calendar
import csv

import PBBLNFMT
import PBBELF
import NPLNTB

CHARACTERS = set('NAME BORSTAT EXIST USER5 VINNO CENSUS7 PAIDIND REVERSED WDOWNIND RESCHEIND HARDCODE WRITEOFF BRANCH LOANTYP RISK POSTNTRN GUAREND'.split())
INTERNAL = set('A B AA BB _N_ REPTDATE STYR STMTH ENYR ENMTH'.split())
EPOCH = date(1960, 1, 1)


class S:
    """SAS scalar: missing arithmetic propagates; numeric missing sorts low."""
    def __init__(self, value):
        self.value = value.value if isinstance(value,S) else value
        if isinstance(self.value,(int,float)):
            self.value = Decimal(str(self.value))

    def __bool__(self): return self.value not in (None, '', Decimal(0))
    def __repr__(self): return f'S({self.value!r})'
    def __str__(self): return '' if self.value is None else str(self.value)
    def __eq__(self,other):
        other=S(other).value
        if isinstance(self.value,str) and isinstance(other,str):return self.value.rstrip()==other.rstrip()
        return self.value==other
    def __ne__(self,other): return not self==other
    def __lt__(self,other):
        other=S(other).value
        if self.value is None:return other is not None
        if other is None:return False
        return self.value<other
    def __le__(self,other):return self==other or self<other
    def __gt__(self,other):return not self<=other
    def __ge__(self,other):return not self<other
    def _op(self,other,fn):
        a,b=self.value,S(other).value
        if a is None or b is None:return S(None)
        try:return S(fn(a,b))
        except (ZeroDivisionError,InvalidOperation):return S(None)
    def __add__(self,o):return self._op(o,lambda a,b:a+b)
    def __sub__(self,o):return self._op(o,lambda a,b:a-b)
    def __mul__(self,o):return self._op(o,lambda a,b:a*b)
    def __truediv__(self,o):return self._op(o,lambda a,b:a/b)
    def __neg__(self):return S(None if self.value is None else -self.value)
    def __matmul__(self,o):return S(str(self)+str(S(o)))


def N(value):
    value = S(value).value
    if value is None or str(value).strip() in ('','.'):return S(None)
    return S(Decimal(str(value)))


class Row(dict):
    def __init__(self,values=None):
        super().__init__()
        for k,v in (values or {}).items():self[k]=v
    def __getitem__(self,key):
        return super().get(key,S('') if key in CHARACTERS else S(None))
    def __setitem__(self,key,value):
        if not isinstance(value,S):
            if key in CHARACTERS:value=S('' if value is None else str(value))
            else:
                try:value=N(value)
                except InvalidOperation:value=S(value)
        super().__setitem__(key,value)
    def update(self,values):
        for k,v in values.items():self[k]=v
    def copy(self):return Row(self)
    def plain(self):return {k:v.value for k,v in self.items()}


def ssum(*values):
    valid=[S(v).value for v in values if S(v).value is not None]
    return S(sum(valid,Decimal(0))) if valid else S(None)


def as_date(value):
    value=S(value).value
    if value is None:return None
    if isinstance(value,str):return date.fromisoformat(value)
    return EPOCH+timedelta(days=int(value))


def year(value):
    dt=as_date(value);return S(dt.year if dt else None)
def month(value):
    dt=as_date(value);return S(dt.month if dt else None)
def day(value):
    dt=as_date(value);return S(dt.day if dt else None)
def sint(value):
    value=S(value).value;return S(int(value) if value is not None else None)
def literal_date(value):return S((datetime.strptime(value,'%d%b%Y').date()-EPOCH).days)


def next_date(issue,billing):
    issue,billing=as_date(issue),as_date(billing)
    if issue is None or billing is None:return S(None)
    yy=billing.year+(billing.month==12);mm=billing.month%12+1
    dd=min(issue.day,calendar.monthrange(yy,mm)[1])
    return S((date(yy,mm,dd)-EPOCH).days)


def substr(value,start,length):
    if S(start).value is None or S(length).value is None:return S('')
    return S(str(S(value))[int(S(start).value)-1:int(S(start).value)-1+int(S(length).value)])


def put(value,fmt):
    fmt=str(fmt).upper();v=S(value).value
    if fmt=='BRCHCD.':return S(PBBELF.put(v,'BRCHCD.'))
    if fmt=='LNTYP.':
        if v in (128,130,983,131,132):return S('HPD AITAB')
        if v in (700,705,380,381,993,996):return S('HPD CONVENTIONAL')
        if v is not None and 200<=v<=299:return S('HOUSING LOANS')
        return S('OTHERS')
    if fmt.startswith('Z'):
        width=int(fmt[1:-1])
        return S('.'.rjust(width,'0') if v is None else f'{int(v):0{width}d}')
    if fmt=='8.2':
        return S('       .' if v is None else f'{v.quantize(Decimal(".01"),rounding=ROUND_HALF_UP):8.2f}')
    raise ValueError('Unsupported format '+fmt)


def sas_input(value,fmt):
    if fmt!='MMDDYY8.':raise ValueError(fmt)
    raw=str(value)
    try:
        dt=date(int(raw[4:8]),int(raw[:2]),int(raw[2:4]))
        return S((dt-EPOCH).days)
    except (ValueError,TypeError):return S(None)


def sas_range(start,stop,step):
    a,b,d=(S(v).value for v in (start,stop,step))
    if a is None or b is None or d is None or d==0:return
    count=0
    while (a<=b if d>0 else a>=b):
        yield S(a);a+=d;count+=1
        if count>100000:raise ValueError('Unexpectedly large SAS DO range')


def read(c,lib,table):
    rows=[]
    for values in c.read(lib,table):
        if values.get('REPTDATE'):
            try:values['REPTDATE']=(date.fromisoformat(str(values['REPTDATE']))-EPOCH).days
            except ValueError:pass
        rows.append(Row(values))
    return rows


def project(rows,keep=None,drop=()):
    return [Row({k:r[k] for k in (keep or r.keys()) if k not in drop}) for r in rows]


def sort(rows,keys=('ACCTNO',),unique=False):
    return [Row(r) for r in sorted_rows(rows,keys,unique)]


def match(tables,flags,keys=('ACCTNO',)):
    for values,present in merge(tables,keys):
        r=Row(values)
        for name,value in zip(flags,present):
            if name:r[name]=int(value)
        yield r


def evaluate(fn,rows,c,params=None,keep=None,drop=(),retain=None):
    """Run a DATA-step row function, preserving explicit OUTPUT snapshots."""
    output=[];retained=dict(retain or {})
    for row in rows:
        r=Row(retained);r.update(row)
        if params:r.update(params)
        emitted=fn(r,c)
        for k in retained:retained[k]=r[k]
        for target,value in emitted:
            value=project([value],keep,drop)[0]
            for key in INTERNAL:value.pop(key,None)
            output.append((target,value))
    return output


def step(fn,rows,c,**kwargs):return [r for _,r in evaluate(fn,rows,c,**kwargs)]


def save(c,lib,name,rows,columns=None):
    columns=columns or list(dict.fromkeys(k for r in rows for k in r))
    c.write(lib,name,[r.plain() for r in rows],columns)


def apply_nplntb(row,c):return NPLNTB.apply(row)


def parameters(c):
    dt=c.reporting_date()
    return dt,{'REPTDATE':(dt-EPOCH).days,'STMTH':1,'STYR':dt.year,'ENMTH':12,'ENYR':dt.year-1}


def risk(row):
    if row['DAYS']>N(364) or row['BORSTAT']==S('W'):return S('BAD')
    if row['DAYS']>N(273):return S('DOUBTFUL')
    if row['DAYS']>N(182):return S('SUBSTANDARD 2')
    return S('SUBSTANDARD-1')


def islamic(rows):
    result=[]
    for r in rows:
        if N(3000)<=r['COSTCTR']<=N(3999) or r['COSTCTR'] in (N(4043),N(4048)):
            r=r.copy();r['RISK']=risk(r);result.append(r)
    return result


def rename(rows,mapping,drop=()):
    result=[]
    for row in rows:
        # DROP refers to old names, preceding input RENAME in SAS.
        result.append(Row({mapping.get(k,k):v for k,v in row.items() if k not in drop}))
    return result


def reports(c,program,rows,measures,dt):
    """Portable versions of both TABULATE tables and PRINT detail/totals."""
    ordered=sorted(rows,key=lambda r:(str(r['LOANTYP']),str(r['BRANCH']),str(r['RISK']),r['DAYS'],r['ACCTNO']))
    detailcols=list(dict.fromkeys(['LOANTYP','BRANCH','RISK','ACCTNO','NOTENO','NAME','DAYS','BORSTAT','VINNO','NETPROC']+measures))
    c.report(program+'_detail',[r.plain() for r in ordered],detailcols)
    summaries=[]
    for grouping,level in [(('LOANTYP','RISK','BRANCH'),'RISK_BRANCH'),(('LOANTYP','RISK'),'RISK_SUBTOTAL'),(('LOANTYP','BRANCH'),'BRANCH'),(('LOANTYP',),'TOTAL')]:
        groups=defaultdict(list)
        for r in rows:groups[tuple(str(r[k]) for k in grouping)].append(r)
        for key,group in sorted(groups.items()):
            out={'LEVEL':level,**dict(zip(grouping,key)),'NO_OF_ACCOUNT':len(group)}
            for col in measures:out[col]=ssum(*(r[col] for r in group)).value
            summaries.append(out)
    c.report(program+'_summary',summaries,['LEVEL','LOANTYP','RISK','BRANCH','NO_OF_ACCOUNT',*measures])
    detail_groups=defaultdict(list)
    for r in rows:detail_groups[tuple(str(r[k]) for k in ('LOANTYP','BRANCH','RISK'))].append(r)
    detail_totals=[]
    sumcols=list(dict.fromkeys((['NETPROC'] if program!='EIIMNP07' else [])+measures))
    for key,group in sorted(detail_groups.items()):
        detail_totals.append({**dict(zip(('LOANTYP','BRANCH','RISK'),key)),
                              **{col:ssum(*(r[col] for r in group)).value for col in sumcols}})
    c.report(program+'_detail_totals',detail_totals,['LOANTYP','BRANCH','RISK',*sumcols])
    # Include the report date separately so it does not alter data-table schemas.
    c.report(program+'_report_info',[{'PROGRAM':program,'AS_AT':dt.isoformat(),'BANK':'PUBLIC ISLAMIC BANK','ACCOUNTS':len(rows)}])


# Original program logic follows.
"""EIIMNP03: individual conversion of the supplied SAS program."""

def stage_1_loanwoff(r, c):
    out = []
    if r['LOANTYPE'] in ( N('380') , N('381') ):
        r['FEEAMT'] = r['FEETOT2']
    if r['AA']:
        r['WRITEOFF'] = S('Y')
    else:
        r['WRITEOFF'] = S('N')
    if r['LOANTYPE'] in ( N('983') , N('993') ):
        r['WDOWNIND'] = S('N')
    if r['IISP'] == S(None):
        r['IISP'] = N('0')
    if r['OIP'] == S(None):
        r['OIP'] = N('0')
    if r['EARNTERM'] in ( N('0') , S(None) ):
        r['EARNTERM'] = r['NOTETERM']
    out.append(('', r.copy()))
    return out

def stage_2_loan1(r, c):
    out = []
    if not (r['EXIST'] == S('Y')): return []
    r['IIS'] = N('0')
    r['SUSPEND'] = N('0')
    r['UHC'] = N('0')
    r['OI'] = N('0')
    r['OISUSP'] = N('0')
    r['RECOVER'] = N('0')
    r['OIRECV'] = N('0')
    r['OIRECC'] = N('0')
    r['OIW'] = N('0')
    if r['IISP'] == S(None):
        r['IISP'] = N('0')
    if r['OIP'] == S(None):
        r['OIP'] = N('0')
    if r['IISPW'] == S(None):
        r['IISPW'] = N('0')
    if r['WRITEOFF'] == S('Y') and r['WDOWNIND'] != S('Y'):
        r['BORSTAT'] = S('W')
    if r['BLDATE'] > N('0') and r['TERMCHG'] > N('0'):
        if r['DAYS'] > N('89') or r['BORSTAT'] in ( S('F') , S('R') , S('I') ) or ( r['USER5'] == S('N') and r['LOANTYPE'] not in ( N('983') , N('993') ) ):
            r['REMMTH1'] = r['EARNTERM'] - ( ( year ( r['BLDATE'] ) - year ( r['ISSDTE'] ) ) * N('12') + month ( r['BLDATE'] ) - month ( r['ISSDTE'] ) + N('1') )
            r['REMMTH2'] = r['EARNTERM'] - ( ( year ( r['REPTDATE'] ) - year ( r['ISSDTE'] ) ) * N('12') + month ( r['REPTDATE'] ) - month ( r['ISSDTE'] ) + N('1') )
            r['REMMTHS'] = r['EARNTERM'] - ( ( r['STYR'] - year ( r['ISSDTE'] ) ) * N('12') + r['STMTH'] - month ( r['ISSDTE'] ) + N('1') )
            if r['REMMTH2'] < N('0'):
                r['REMMTH2'] = N('0')
            if r['LOANTYPE'] in ( N('128') , N('130') ):
                r['REMMTH1'] = r['REMMTH1'] - N('3')
            else:
                r['REMMTH1'] = r['REMMTH1'] - N('1')
            if r['REMMTH1'] >= r['REMMTH2']:
                for _index in sas_range(r['REMMTH1'], r['REMMTH2'], - N('1')):
                    r['REMMTH'] = _index
                    r['IIS'] = ssum(r['IIS'], N('2') * ( r['REMMTH'] + N('1') ) * r['TERMCHG'] / ( r['EARNTERM'] * ( r['EARNTERM'] + N('1') ) ))
            r['OI'] = ssum ( r['FEETOT2'] , ( - N('1') ) * r['FEEAMTA'] , r['FEEAMT5'] )
            for _index in sas_range(r['REMMTHS'], r['REMMTH2'], - N('1')):
                r['REMMTH'] = _index
                r['SUSPEND'] = ssum(r['SUSPEND'], N('2') * ( r['REMMTH'] + N('1') ) * r['TERMCHG'] / ( r['EARNTERM'] * ( r['EARNTERM'] + N('1') ) ))
            if r['LOANTYPE'] not in ( N('128') , N('130') ):
                r['OISUSP'] = ssum ( r['FEEAMT'] , ( - N('1') ) * r['FEEAMTA'] , r['FEEAMT5'] )
            if r['REMMTH2'] > N('0'):
                r['UHC'] = r['REMMTH2'] * ( r['REMMTH2'] + N('1') ) * r['TERMCHG'] / ( r['EARNTERM'] * ( r['EARNTERM'] + N('1') ) )
    else:
        if r['DAYS'] > N('89') or r['BORSTAT'] in ( S('F') , S('R') , S('I') ) or ( r['USER5'] == S('N') and r['LOANTYPE'] not in ( N('983') , N('993') ) ):
            r['OI'] = ssum ( r['FEETOT2'] , ( - N('1') ) * r['FEEAMTA'] , r['FEEAMT5'] )
            r['OISUSP'] = ssum ( r['FEEAMT'] , ( - N('1') ) * r['FEEAMTA'] , r['FEEAMT5'] )
    if r['CURBAL'] == S(None):
        r['CURBAL'] = N('0')
    r['NETBAL'] = r['CURBAL'] - r['UHC']
    if r['NETBAL'] <= r['IISP']:
        if r['DAYS'] > N('89') or r['BORSTAT'] in ( S('F') , S('R') , S('I') ) or r['USER5'] == S('N'):
            r['IIS'] = r['NETBAL']
    if r['BORSTAT'] == S('W'):
        r['IISPW'] = r['IISP']
        r['OIW'] = r['OIP']
    else:
        r['RECOVER'] = r['IISP'] + r['SUSPEND'] - r['IIS']
        if r['RECOVER'] < N('0'):
            r['SUSPEND'] = r['SUSPEND'] - r['RECOVER']
            r['RECOVER'] = N('0')
        if r['RECOVER'] > r['IISP']:
            r['RECC'] = r['RECOVER'] - r['IISP']
            r['RECOVER'] = r['IISP']
        if r['LOANTYPE'] not in ( N('128') , N('130') ):
            r['OIRECV'] = r['OIP'] - r['OI']
            if r['OIRECV'] < N('0'):
                r['OISUSP'] = r['OISUSP'] - r['OIRECV']
                r['OIRECV'] = N('0')
            if r['OISUSP'] < N('0'):
                r['OIRECV'] = r['OIRECV'] - r['OISUSP']
            if r['OIRECV'] > r['OIP']:
                r['OIRECC'] = r['OIRECV'] - r['OIP']
                r['OIRECV'] = r['OIP']
    if r['TERMCHG'] == N('0'):
        if r['BORSTAT'] in ( S('R') , ):
            r['NETEXP'] = r['CURBAL'] - r['IISP'] - r['MARKETVL']
        else:
            r['NETEXP'] = r['CURBAL'] - r['IISP']
        if ( r['NETEXP'] > N('0') and r['DAYS'] > N('89') ) or r['BORSTAT'] in ( S('R') , ):
            r['IIS'] = r['RECOVER']
            r['RECOVER'] = N('0')
            r['OI'] = ssum ( r['FEETOT2'] , ( - N('1') ) * r['FEEAMTA'] , r['FEEAMT5'] )
            r['OIRECV'] = N('0')
    if r['LOANTYPE'] in ( N('131') , N('132') ):
        r['IIS'] = r['ACCRUAL']
    r['OISUSP'] = r['OIRECV'] + r['OIRECC'] + r['OIW'] - r['OIP'] + r['OI']
    if r['OISUSP'] < N('0'):
        r['OIRECV'] = r['OIRECV'] - r['OISUSP']
    if r['OIRECV'] > r['OIP']:
        r['OIRECC'] = r['OIRECV'] - r['OIP']
        r['OIRECV'] = r['OIP']
    r['OISUSP'] = r['OIRECV'] + r['OIRECC'] + r['OIW'] - r['OIP'] + r['OI']
    r['BRANCH'] = put ( r['NTBRCH'] , 'BRCHCD.' ) @ S(' ') @ put ( r['NTBRCH'] , 'Z3.' )
    r['LOANTYP'] = put ( r['LOANTYPE'] , 'LNTYP.' )
    if r['WRITEOFF'] == S('Y'):
        r['SUSPEND'] = r['WSUSPEND']
        r['OISUSP'] = r['WOISUSP']
        if r['WDOWNIND'] != S('Y'):
            r['RECOVER'] = r['WRECOVER']
            r['RECC'] = r['WRECC']
            r['OIRECV'] = r['WOIRECV']
            r['OIRECC'] = r['WOIRECC']
            r['IIS'] = N('0')
            r['IISPW'] = ssum ( r['IISP'] , r['SUSPEND'] , ( - N('1') ) * r['RECOVER'] , ( - N('1') ) * r['RECC'] )
            r['OI'] = N('0')
            r['OIW'] = ssum ( r['OIP'] , r['OISUSP'] , ( - N('1') ) * r['OIRECV'] , ( - N('1') ) * r['OIRECC'] )
        else:
            r['OISUSP'] = r['WOISUSP']
            r['IISPW'] = r['WIISPW']
            r['IIS'] = ssum ( r['IISP'] , r['SUSPEND'] , ( - N('1') ) * r['RECOVER'] , ( - N('1') ) * r['RECC'] , ( - N('1') ) * r['IISPW'] )
            if r['IIS'] < N('0'):
                r['RECOVER'] = N('0')
            r['IIS'] = ssum ( r['IISP'] , r['SUSPEND'] , ( - N('1') ) * r['RECOVER'] , ( - N('1') ) * r['RECC'] , ( - N('1') ) * r['IISPW'] )
            r['OIW'] = r['WOIW']
            r['OI'] = ssum ( r['OIP'] , r['OISUSP'] , ( - N('1') ) * r['OIRECV'] , ( - N('1') ) * r['OIRECC'] , ( - N('1') ) * r['OIW'] )
            if r['OI'] < N('0'):
                r['OIRECV'] = N('0')
                r['OIRECC'] = N('0')
            r['OI'] = ssum ( r['OIP'] , r['OISUSP'] , ( - N('1') ) * r['OIRECV'] , ( - N('1') ) * r['OIRECC'] , ( - N('1') ) * r['OIW'] )
        if r['OIP'] == S(None):
            r['OIP'] = N('0')
        if r['IISP'] == S(None):
            r['IISP'] = N('0')
        if r['SUSPEND'] == S(None):
            r['SUSPEND'] = N('0')
        if r['OISUSP'] == S(None):
            r['OISUSP'] = N('0')
        if r['RECOVER'] == S(None):
            r['RECOVER'] = N('0')
        if r['OIRECV'] == S(None):
            r['OIRECV'] = N('0')
        if r['RECC'] == S(None):
            r['RECC'] = N('0')
        if r['OIRECC'] == S(None):
            r['OIRECC'] = N('0')
    r['TOTIIS'] = r['IIS'] + r['OI']
    if r['RESCHEIND'] == S('Y'):
        r['SUSPEND'] = r['WSUSPEND']
        r['OISUSP'] = r['WOISUSP']
        r['RECOVER'] = r['WRECOVER']
        r['RECC'] = r['WRECC']
        r['OIRECV'] = r['WOIRECV']
        r['OIRECC'] = r['WOIRECC']
        r['IIS'] = ssum ( r['IISP'] , r['SUSPEND'] , ( - N('1') ) * r['RECOVER'] , ( - N('1') ) * r['RECC'] , ( - N('1') ) * r['IISPW'] )
        r['OI'] = ssum ( r['OIP'] , r['OISUSP'] , ( - N('1') ) * r['OIRECV'] , ( - N('1') ) * r['OIRECC'] , ( - N('1') ) * r['OIW'] )
        r['TOTIIS'] = r['IIS'] + r['OI']
    out.append(('', r.copy()))
    return out

def stage_3_loan2(r, c):
    out = []
    if not (r['EXIST'] != S('Y')): return []
    r['IIS'] = N('0')
    r['UHC'] = N('0')
    r['OI'] = N('0')
    if r['WRITEOFF'] == S('Y') and r['WDOWNIND'] != S('Y'):
        r['BORSTAT'] = S('W')
    if r['BLDATE'] > N('0') and r['TERMCHG'] > N('0') or ( r['USER5'] == S('N') and r['LOANTYPE'] not in ( N('983') , N('993') ) ):
        r['REMMTH1'] = r['EARNTERM'] - ( ( year ( r['BLDATE'] ) - year ( r['ISSDTE'] ) ) * N('12') + month ( r['BLDATE'] ) - month ( r['ISSDTE'] ) + N('1') )
        r['REMMTH2'] = r['EARNTERM'] - ( ( year ( r['REPTDATE'] ) - year ( r['ISSDTE'] ) ) * N('12') + month ( r['REPTDATE'] ) - month ( r['ISSDTE'] ) + N('1') )
        if r['REMMTH2'] < N('0'):
            r['REMMTH2'] = N('0')
        if r['LOANTYPE'] in ( N('128') , N('130') ):
            r['REMMTH1'] = r['REMMTH1'] - N('3')
        else:
            r['REMMTH1'] = r['REMMTH1'] - N('1')
        if r['REMMTH1'] >= r['REMMTH2']:
            for _index in sas_range(r['REMMTH1'], r['REMMTH2'], - N('1')):
                r['REMMTH'] = _index
                r['IIS'] = ssum(r['IIS'], N('2') * ( r['REMMTH'] + N('1') ) * r['TERMCHG'] / ( r['EARNTERM'] * ( r['EARNTERM'] + N('1') ) ))
        if r['REMMTH2'] > N('0'):
            r['UHC'] = r['REMMTH2'] * ( r['REMMTH2'] + N('1') ) * r['TERMCHG'] / ( r['EARNTERM'] * ( r['EARNTERM'] + N('1') ) )
    else:
        r['REMMTH2'] = r['EARNTERM'] - ( ( year ( r['REPTDATE'] ) - year ( r['ISSDTE'] ) ) * N('12') + month ( r['REPTDATE'] ) - month ( r['ISSDTE'] ) + N('1') )
        if r['REMMTH2'] < N('0'):
            r['REMMTH2'] = N('0')
        if r['REMMTH2'] > N('0'):
            r['UHC'] = r['REMMTH2'] * ( r['REMMTH2'] + N('1') ) * r['TERMCHG'] / ( r['EARNTERM'] * ( r['EARNTERM'] + N('1') ) )
    r['OI'] = ssum ( r['FEETOT2'] , ( - N('1') ) * r['FEEAMTA'] , r['FEEAMT5'] )
    if r['LOANTYPE'] in ( N('131') , N('132') ):
        r['IIS'] = r['ACCRUAL']
    r['SUSPEND'] = r['IIS']
    r['OISUSP'] = r['OI']
    r['NETBAL'] = r['CURBAL'] - r['UHC']
    if r['WRITEOFF'] == S('Y'):
        r['SUSPEND'] = r['WSUSPEND']
        r['OISUSP'] = r['WOISUSP']
        if r['WDOWNIND'] != S('Y'):
            r['RECOVER'] = r['WRECOVER']
            r['RECC'] = r['WRECC']
            r['OIRECV'] = r['WOIRECV']
            r['OIRECC'] = r['WOIRECC']
            r['IIS'] = N('0')
            r['IISPW'] = ssum ( r['IISP'] , r['SUSPEND'] , ( - N('1') ) * r['RECOVER'] , ( - N('1') ) * r['RECC'] )
            r['OI'] = N('0')
            r['OIW'] = ssum ( r['OIP'] , r['OISUSP'] , ( - N('1') ) * r['OIRECV'] , ( - N('1') ) * r['OIRECC'] )
        else:
            r['OISUSP'] = r['WOISUSP']
            r['IISPW'] = r['WIISPW']
            r['IIS'] = ssum ( r['IISP'] , r['SUSPEND'] , ( - N('1') ) * r['RECOVER'] , ( - N('1') ) * r['RECC'] , ( - N('1') ) * r['IISPW'] )
            if r['IIS'] < N('0'):
                r['RECOVER'] = N('0')
            r['IIS'] = ssum ( r['IISP'] , r['SUSPEND'] , ( - N('1') ) * r['RECOVER'] , ( - N('1') ) * r['RECC'] , ( - N('1') ) * r['IISPW'] )
            r['OIW'] = r['WOIW']
            r['OI'] = ssum ( r['OIP'] , r['OISUSP'] , ( - N('1') ) * r['OIRECV'] , ( - N('1') ) * r['OIRECC'] , ( - N('1') ) * r['OIW'] )
            if r['OI'] < N('0'):
                r['OIRECV'] = N('0')
                r['OIRECC'] = N('0')
            r['OI'] = ssum ( r['OIP'] , r['OISUSP'] , ( - N('1') ) * r['OIRECV'] , ( - N('1') ) * r['OIRECC'] , ( - N('1') ) * r['OIW'] )
        if r['OIP'] == S(None):
            r['OIP'] = N('0')
        if r['IISP'] == S(None):
            r['IISP'] = N('0')
        if r['SUSPEND'] == S(None):
            r['SUSPEND'] = N('0')
        if r['OISUSP'] == S(None):
            r['OISUSP'] = N('0')
        if r['RECOVER'] == S(None):
            r['RECOVER'] = N('0')
        if r['OIRECV'] == S(None):
            r['OIRECV'] = N('0')
        if r['RECC'] == S(None):
            r['RECC'] = N('0')
        if r['OIRECC'] == S(None):
            r['OIRECC'] = N('0')
    r['TOTIIS'] = r['IIS'] + r['OI']
    r['BRANCH'] = put ( r['NTBRCH'] , 'BRCHCD.' ) @ S(' ') @ put ( r['NTBRCH'] , 'Z3.' )
    r['LOANTYP'] = put ( r['LOANTYPE'] , 'LNTYP.' )
    if r['RESCHEIND'] == S('Y'):
        r['SUSPEND'] = r['WSUSPEND']
        r['OISUSP'] = r['WOISUSP']
        r['RECOVER'] = r['WRECOVER']
        r['RECC'] = r['WRECC']
        r['OIRECV'] = r['WOIRECV']
        r['OIRECC'] = r['WOIRECC']
        r['IIS'] = ssum ( r['IISP'] , r['SUSPEND'] , ( - N('1') ) * r['RECOVER'] , ( - N('1') ) * r['RECC'] , ( - N('1') ) * r['IISPW'] )
        r['OI'] = ssum ( r['OIP'] , r['OISUSP'] , ( - N('1') ) * r['OIRECV'] , ( - N('1') ) * r['OIRECC'] , ( - N('1') ) * r['OIW'] )
        r['TOTIIS'] = r['IIS'] + r['OI']
    out.append(('', r.copy()))
    return out

def stage_4_loan1(r, c):
    out = []
    r['IISPCUM'] = N('0')
    r['OIPCUM'] = N('0')
    r['POI'] = N('0')
    out.append(('', r.copy()))
    return out

def stage_5_loan2(r, c):
    out = []
    r['IISPCUM'] = N('0')
    r['OIPCUM'] = N('0')
    r['POI'] = N('0')
    out.append(('', r.copy()))
    return out

def stage_6_iisprev(r, c):
    out = []
    if r['LOANTYPE'] in ( N('128') , N('130') , N('131') , N('132') , N('380') , N('381') , N('390') , N('700') , N('705') , N('720') , N('725') , N('983') , N('993') , N('996') ) and r['PAIDIND'] == S('P'):
        r.update(apply_nplntb(r, c))
    r['BRANCH'] = put ( r['NTBRCH'] , 'BRCHCD.' ) @ S(' ') @ put ( r['NTBRCH'] , 'Z3.' )
    if r['PDAYS'] == S(None):
        r['PDAYS'] = N('0')
    if r['PSUSPEND'] == S(None):
        r['PSUSPEND'] = N('0')
    if r['POISUSP'] == S(None):
        r['POISUSP'] = N('0')
    if r['PIISP'] == S(None):
        r['PIISP'] = N('0')
    if r['POIP'] == S(None):
        r['POIP'] = N('0')
    if r['POI'] == S(None):
        r['POI'] = N('0')
    out.append(('', r.copy()))
    return out

def stage_7_loan1_drop_pdays(r, c):
    out = []
    if not (( ( r['A'] and r['B'] ) or ( r['B'] and not r['A'] ) ) and r['EXIST'] == S('Y')): return []
    if ( ( r['B'] and not r['A'] ) or ( r['CURBAL'] <= N('0') and r['POI'] <= N('0') ) ) and r['BORSTAT'] not in ( S('F') , S('I') , S('R') , S('W') , S('S') ):
        r['IISP'] = r['PIISP']
        r['RECOVER'] = r['IISP']
        r['SUSPEND'] = r['PSUSPEND']
        r['RECC'] = r['SUSPEND']
        r['OIP'] = r['POIP']
        r['OIRECV'] = r['OIP']
        r['OISUSP'] = r['POISUSP']
        r['OIRECC'] = r['OISUSP']
        r['CURBAL'] = N('0')
        r['NETBAL'] = N('0')
        r['DAYS'] = N('0')
        r['OI'] = ssum ( r['OIP'] , r['OISUSP'] , ( - N('1') ) * r['OIRECV'] , ( - N('1') ) * r['OIRECC'] , ( - N('1') ) * r['OIW'] )
        r['IIS'] = ssum ( r['IISP'] , r['SUSPEND'] , ( - N('1') ) * r['RECOVER'] , ( - N('1') ) * r['RECC'] , ( - N('1') ) * r['IISPW'] )
        r['TOTIIS'] = r['IIS'] + r['OI']
        out.append(('', r.copy()))
    else:
        if r['BORSTAT'] in ( S('W') , ) or r['RESCHEIND'] == S('Y'):
            out.append(('', r.copy()))
        else:
            if ( r['A'] and r['B'] ):
                if ( r['DAYS'] < N('90') and r['PDAYS'] < N('90') ):
                    if r['USER5'] == S('N') and r['IIS'] < r['IISP']:
                        r['SUSPEND'] = N('0')
                        r['RECOVER'] = r['IISP'] - r['IIS']
                        r['RECC'] = N('0')
                    if r['USER5'] == S('N') and r['IIS'] >= r['IISP']:
                        r['SUSPEND'] = r['IIS'] - r['IISP']
                        r['RECOVER'] = N('0')
                        r['RECC'] = N('0')
                    if r['USER5'] == S('N') and r['IISP'] == N('0'):
                        r['SUSPEND'] = r['IIS']
                        r['RECC'] = r['IIS'] - r['SUSPEND']
                    if r['USER5'] == S('N') and r['OI'] < r['OIP']:
                        r['OISUSP'] = N('0')
                        r['OIRECV'] = r['OIP'] - r['OI']
                        r['OIRECC'] = N('0')
                    if r['USER5'] == S('N') and r['OI'] >= r['OIP']:
                        r['OISUSP'] = r['OI'] - r['OIP']
                        r['OIRECV'] = N('0')
                        r['OIRECC'] = N('0')
                    if r['USER5'] == S('N') and r['OIP'] == N('0'):
                        r['OISUSP'] = r['OI']
                        r['OIRECC'] = r['OI'] - r['OISUSP']
                    out.append(('', r.copy()))
                if r['DAYS'] < N('90') and r['PDAYS'] >= N('90'):
                    if r['BORSTAT'] not in ( S('F') , S('I') , S('R') ):
                        r['SUSPEND'] = r['PSUSPEND']
                        r['RECC'] = r['PSUSPEND']
                        r['OISUSP'] = r['POISUSP']
                        r['OIRECC'] = r['POISUSP']
                        r['TOTIIS'] = r['IIS'] + r['OI']
                    if r['USER5'] == S('N') and r['IIS'] < r['IISP']:
                        r['SUSPEND'] = N('0')
                        r['RECOVER'] = r['IISP'] - r['IIS']
                        r['RECC'] = N('0')
                    if r['USER5'] == S('N') and r['IIS'] >= r['IISP']:
                        r['SUSPEND'] = r['IIS'] - r['IISP']
                        r['RECOVER'] = N('0')
                        r['RECC'] = N('0')
                    if r['USER5'] == S('N') and r['IISP'] == N('0'):
                        r['SUSPEND'] = r['IIS']
                        r['RECC'] = r['IIS'] - r['SUSPEND']
                    if r['USER5'] == S('N') and r['OI'] < r['OIP']:
                        r['OISUSP'] = N('0')
                        r['OIRECV'] = r['OIP'] - r['OI']
                        r['OIRECC'] = N('0')
                    if r['USER5'] == S('N') and r['OI'] >= r['OIP']:
                        r['OISUSP'] = r['OI'] - r['OIP']
                        r['OIRECV'] = N('0')
                        r['OIRECC'] = N('0')
                    if r['USER5'] == S('N') and r['OIP'] == N('0'):
                        r['OISUSP'] = r['OI']
                        r['OIRECC'] = r['OI'] - r['OISUSP']
                    out.append(('', r.copy()))
                if r['DAYS'] >= N('90') and r['PDAYS'] < N('90'):
                    if r['BORSTAT'] not in ( S('F') , S('I') , S('R') ):
                        r['RECC'] = r['PRECC']
                        r['RECOVER'] = r['PRECOVER']
                        r['SUSPEND'] = ssum ( r['IIS'] , r['IISP'] , ( - N('1') ) * r['RECOVER'] , r['RECC'] )
                        if r['SUSPEND'] < N('0'):
                            r['RECOVER'] = ssum ( r['RECOVER'] , ( - N('1') ) * r['SUSPEND'] )
                            r['SUSPEND'] = N('0')
                            if r['RECOVER'] > r['IISP']:
                                r['RECC'] = ssum ( r['RECC'] , r['RECOVER'] - r['IISP'] )
                        r['OIRECC'] = r['POIRECC']
                        r['OIRECV'] = r['POIRECV']
                        r['OISUSP'] = ssum ( r['OI'] , r['OIP'] , ( - N('1') ) * r['OIRECV'] , r['OIRECC'] )
                        if r['OISUSP'] < N('0'):
                            r['OIRECV'] = ssum ( r['OIRECV'] , ( - N('1') ) * r['OISUSP'] )
                            r['OISUSP'] = N('0')
                            if r['OIRECV'] > r['OIP']:
                                r['OIRECC'] = ssum ( r['OIRECC'] , r['OIRECV'] - r['OIP'] )
                        r['TOTIIS'] = r['IIS'] + r['OI']
                    if r['USER5'] == S('N') and r['IIS'] < r['IISP']:
                        r['SUSPEND'] = N('0')
                        r['RECOVER'] = r['IISP'] - r['IIS']
                        r['RECC'] = N('0')
                    if r['USER5'] == S('N') and r['IIS'] >= r['IISP']:
                        r['SUSPEND'] = r['IIS'] - r['IISP']
                        r['RECOVER'] = N('0')
                        r['RECC'] = N('0')
                    if r['USER5'] == S('N') and r['IISP'] == N('0'):
                        r['SUSPEND'] = r['IIS']
                        r['RECC'] = r['IIS'] - r['SUSPEND']
                    if r['USER5'] == S('N') and r['OI'] < r['OIP']:
                        r['OISUSP'] = N('0')
                        r['OIRECV'] = r['OIP'] - r['OI']
                        r['OIRECC'] = N('0')
                    if r['USER5'] == S('N') and r['OI'] >= r['OIP']:
                        r['OISUSP'] = r['OI'] - r['OIP']
                        r['OIRECV'] = N('0')
                        r['OIRECC'] = N('0')
                    if r['USER5'] == S('N') and r['OIP'] == N('0'):
                        r['OISUSP'] = r['OI']
                        r['OIRECC'] = r['OI'] - r['OISUSP']
                    out.append(('', r.copy()))
                if r['DAYS'] >= N('90') and r['PDAYS'] >= N('90'):
                    if r['BORSTAT'] not in ( S('F') , S('I') , S('R') ):
                        r['RECOVER'] = r['PRECOVER']
                        r['RECC'] = r['PRECC']
                        r['SUSPEND'] = ssum ( r['IIS'] , ( - N('1') ) * r['IISP'] , r['RECOVER'] , r['RECC'] )
                        if r['SUSPEND'] < N('0'):
                            r['RECOVER'] = ssum ( r['RECOVER'] , ( - N('1') ) * r['SUSPEND'] )
                            r['SUSPEND'] = N('0')
                            if r['RECOVER'] > r['IISP']:
                                r['RECC'] = ssum ( r['RECC'] , r['RECOVER'] , ( - N('1') ) * r['IISP'] )
                        r['OIRECV'] = r['POIRECV']
                        r['OIRECC'] = r['POIRECC']
                        r['OISUSP'] = ssum ( r['OI'] , ( - N('1') ) * r['OIP'] , r['OIRECV'] , r['OIRECC'] )
                        if r['OISUSP'] < N('0'):
                            r['OIRECV'] = ssum ( r['OIRECV'] , ( - N('1') ) * r['OISUSP'] )
                            r['OISUSP'] = N('0')
                            if r['OIRECV'] > r['OIP']:
                                r['OIRECC'] = ssum ( r['OIRECC'] , r['OIRECV'] , ( - N('1') ) * r['OIP'] )
                        r['TOTIIS'] = r['IIS'] + r['OI']
                    out.append(('', r.copy()))
                if r['USER5'] == S('N') and r['IIS'] == N('0') and r['IISP'] == N('0'):
                    r['SUSPEND'] = r['IIS']
    return out

def stage_8_iisprev(r, c):
    out = []
    if not (r['PIISP'] == N('0') and r['POIP'] == N('0') and r['EXIST'] != S('Y')): return []
    r['BRANCH'] = put ( r['NTBRCH'] , 'BRCHCD.' ) @ S(' ') @ put ( r['NTBRCH'] , 'Z3.' )
    out.append(('', r.copy()))
    return out

def stage_9_loan2_drop_pdays(r, c):
    out = []
    if ( r['B'] and not r['A'] ):
        r['IISP'] = r['PIISP']
        r['RECOVER'] = r['IISP']
        r['SUSPEND'] = r['PSUSPEND']
        r['RECC'] = r['SUSPEND']
        r['OIP'] = r['POIP']
        r['OIRECV'] = r['OIP']
        r['OISUSP'] = r['POISUSP']
        r['OIRECC'] = r['OISUSP']
        r['CURBAL'] = N('0')
        r['NETBAL'] = N('0')
        r['DAYS'] = N('0')
        r['OI'] = ssum ( r['OIP'] , r['OISUSP'] , ( - N('1') ) * r['OIRECV'] , ( - N('1') ) * r['OIRECC'] , ( - N('1') ) * r['OIW'] )
        r['IIS'] = ssum ( r['IISP'] , r['SUSPEND'] , ( - N('1') ) * r['RECOVER'] , ( - N('1') ) * r['RECC'] , ( - N('1') ) * r['IISPW'] )
        r['TOTIIS'] = r['IIS'] + r['OI']
        out.append(('', r.copy()))
    if ( r['A'] and not r['B'] ) and ( r['DAYS'] >= N('90') or r['BORSTAT'] in ( S('F') , S('I') , S('R') , S('W') ) or r['USER5'] == S('N') ):
        out.append(('', r.copy()))
    if r['BORSTAT'] in ( S('W') , ) or r['RESCHEIND'] == S('Y'):
        out.append(('', r.copy()))
    if ( r['A'] and r['B'] ) and r['BORSTAT'] not in ( S('W') , ):
        if r['DAYS'] < N('90') and r['PDAYS'] < N('90'):
            if r['BORSTAT'] not in ( S('F') , S('I') , S('R') ):
                r['SUSPEND'] = r['PSUSPEND']
                r['RECC'] = r['PSUSPEND']
                r['OISUSP'] = r['POISUSP']
                r['OIRECC'] = r['POISUSP']
                r['TOTIIS'] = r['IIS'] + r['OI']
            if r['USER5'] == S('N') and r['IIS'] < r['IISP']:
                r['SUSPEND'] = N('0')
                r['RECOVER'] = r['IISP'] - r['IIS']
                r['RECC'] = N('0')
            if r['USER5'] == S('N') and r['IIS'] >= r['IISP']:
                r['SUSPEND'] = r['IIS'] - r['IISP']
                r['RECOVER'] = N('0')
                r['RECC'] = N('0')
            if r['USER5'] == S('N') and r['IISP'] == N('0'):
                r['SUSPEND'] = r['IIS']
                r['RECC'] = r['IIS'] - r['SUSPEND']
            if r['USER5'] == S('N') and r['OI'] < r['OIP']:
                r['OISUSP'] = N('0')
                r['OIRECV'] = r['OIP'] - r['OI']
                r['OIRECC'] = N('0')
            if r['USER5'] == S('N') and r['OI'] >= r['OIP']:
                r['OISUSP'] = r['OI'] - r['OIP']
                r['OIRECV'] = N('0')
                r['OIRECC'] = N('0')
            if r['USER5'] == S('N') and r['OIP'] == N('0'):
                r['OISUSP'] = r['OI']
                r['OIRECC'] = r['OI'] - r['OISUSP']
            else:
                r['SUSPEND'] = ssum ( r['SUSPEND'] , r['RECC'] )
                r['OISUSP'] = ssum ( r['OISUSP'] , r['OIRECC'] )
            out.append(('', r.copy()))
        if r['DAYS'] < N('90') and r['PDAYS'] >= N('90'):
            if r['BORSTAT'] not in ( S('F') , S('I') , S('R') ):
                r['SUSPEND'] = r['PSUSPEND']
                r['RECC'] = r['PSUSPEND']
                r['OISUSP'] = r['POISUSP']
                r['OIRECC'] = r['POISUSP']
                r['OI'] = ssum ( r['OIP'] , r['OISUSP'] , ( - N('1') ) * r['OIRECV'] , ( - N('1') ) * r['OIRECC'] , ( - N('1') ) * r['OIW'] )
                r['IIS'] = ssum ( r['IISP'] , r['SUSPEND'] , ( - N('1') ) * r['RECOVER'] , ( - N('1') ) * r['RECC'] , ( - N('1') ) * r['IISPW'] )
                r['TOTIIS'] = r['IIS'] + r['OI']
            if r['USER5'] == S('N') and r['IIS'] < r['IISP']:
                r['SUSPEND'] = N('0')
                r['RECOVER'] = r['IISP'] - r['IIS']
                r['RECC'] = N('0')
            if r['USER5'] == S('N') and r['IIS'] >= r['IISP']:
                r['SUSPEND'] = r['IIS'] - r['IISP']
                r['RECOVER'] = N('0')
                r['RECC'] = N('0')
            if r['USER5'] == S('N') and r['IISP'] == N('0'):
                r['SUSPEND'] = r['IIS']
                r['RECC'] = r['IIS'] - r['SUSPEND']
            if r['USER5'] == S('N') and r['OI'] < r['OIP']:
                r['OISUSP'] = N('0')
                r['OIRECV'] = r['OIP'] - r['OI']
                r['OIRECC'] = N('0')
            if r['USER5'] == S('N') and r['OI'] >= r['OIP']:
                r['OISUSP'] = r['OI'] - r['OIP']
                r['OIRECV'] = N('0')
                r['OIRECC'] = N('0')
            if r['USER5'] == S('N') and r['OIP'] == N('0'):
                r['OISUSP'] = r['OI']
                r['OIRECC'] = r['OI'] - r['OISUSP']
            out.append(('', r.copy()))
        if r['DAYS'] >= N('90') and r['PDAYS'] < N('90'):
            if r['BORSTAT'] not in ( S('F') , S('I') , S('R') ):
                r['RECC'] = ssum ( r['RECC'] , r['PRECC'] )
                r['SUSPEND'] = ssum ( r['SUSPEND'] , r['RECC'] )
                r['OIRECC'] = ssum ( r['OIRECC'] , r['POIRECC'] )
                r['OISUSP'] = ssum ( r['OISUSP'] , r['OIRECC'] )
                r['TOTIIS'] = r['IIS'] + r['OI']
            if r['USER5'] == S('N') and r['IIS'] < r['IISP']:
                r['SUSPEND'] = N('0')
                r['RECOVER'] = r['IISP'] - r['IIS']
                r['RECC'] = N('0')
            if r['USER5'] == S('N') and r['IIS'] >= r['IISP']:
                r['SUSPEND'] = r['IIS'] - r['IISP']
                r['RECOVER'] = N('0')
                r['RECC'] = N('0')
            if r['USER5'] == S('N') and r['IISP'] == N('0'):
                r['SUSPEND'] = r['IIS']
                r['RECC'] = r['IIS'] - r['SUSPEND']
            if r['USER5'] == S('N') and r['OI'] < r['OIP']:
                r['OISUSP'] = N('0')
                r['OIRECV'] = r['OIP'] - r['OI']
                r['OIRECC'] = N('0')
            if r['USER5'] == S('N') and r['OI'] >= r['OIP']:
                r['OISUSP'] = r['OI'] - r['OIP']
                r['OIRECV'] = N('0')
                r['OIRECC'] = N('0')
            if r['USER5'] == S('N') and r['OIP'] == N('0'):
                r['OISUSP'] = r['OI']
                r['OIRECC'] = r['OI'] - r['OISUSP']
            out.append(('', r.copy()))
        if r['DAYS'] >= N('90') and r['PDAYS'] >= N('90'):
            if r['BORSTAT'] not in ( S('F') , S('I') , S('R') ):
                r['RECC'] = ssum ( r['RECC'] , r['PRECC'] )
                r['SUSPEND'] = ssum ( r['SUSPEND'] , r['RECC'] )
                r['OIRECC'] = ssum ( r['OIRECC'] , r['POIRECC'] )
                r['OISUSP'] = ssum ( r['OISUSP'] , r['OIRECC'] )
                r['TOTIIS'] = r['IIS'] + r['OI']
            out.append(('', r.copy()))
        if r['USER5'] == S('N') and r['IIS'] == N('0') and r['IISP'] == N('0'):
            r['SUSPEND'] = r['IIS']
    return out


IIS_COLUMNS = ['BRANCH', 'NTBRCH', 'ACCTNO', 'NOTENO', 'NAME', 'NETPROC', 'CURBAL', 'BORSTAT', 'DAYS', 'IIS', 'UHC', 'NETBAL', 'IISP', 'SUSPEND', 'RECOVER', 'RECC', 'IISPW', 'OIP', 'OISUSP', 'OI', 'OIRECV', 'OIRECC', 'OIW', 'TOTIIS', 'LOANTYP', 'EXIST', 'COSTCTR', 'PENDBRH', 'USER5', 'WDOWNIND', 'RESCHEIND', 'ACCRUAL']
PREVIOUS_NAMES = dict(DAYS='PDAYS',SUSPEND='PSUSPEND',OISUSP='POISUSP',IISP='PIISP',OIP='POIP',OI='POI',RECC='PRECC',OIRECC='POIRECC',RECOVER='PRECOVER',OIRECV='POIRECV')
PREVIOUS_DROP = 'PDAYS PSUSPEND POISUSP PIISP POIP PRECC POIRECC PRECOVER POIRECV'.split()

def run(c):
    dt,params=parameters(c);mm=f'{dt.month:02d}';prev=f'{(dt.month-2)%12+1:02d}'
    loan=read(c,'NPL','LOAN'+mm)
    hardcode=project(read(c,'NPL','WIIS'),drop=('NOTENO','NTBRCH'))
    merged=step(stage_1_loanwoff,match([loan,hardcode],[None,'AA']),c)
    existing=step(stage_2_loan1,merged,c,params=params,keep=IIS_COLUMNS)
    current=step(stage_3_loan2,merged,c,params=params,keep=IIS_COLUMNS)
    if dt.month==1:
        existing=step(stage_4_loan1,existing,c)
        current=step(stage_5_loan2,current,c)
    else:
        previous=sort(rename(read(c,'NPL','IIS'+prev),PREVIOUS_NAMES,drop=('POI',)),('ACCTNO','NOTENO'),True)
        previous=step(stage_6_iisprev,previous,c)
        existing=step(stage_7_loan1_drop_pdays,match([previous,existing],['B','A']),c,drop=PREVIOUS_DROP)
        performing=project(read(c,'NPL','PLOAN'+mm),'ACCTNO NOTENO CURBAL DAYS BORSTAT NTBRCH COSTCTR'.split())
        previous=step(stage_8_iisprev,match([previous,performing],['A','B']),c)
        current=sort(current,('ACCTNO','NOTENO'))
        current=step(stage_9_loan2_drop_pdays,match([previous,current],['B','A']),c,drop=PREVIOUS_DROP)
    combined=sort(islamic(existing+current),('ACCTNO','NOTENO'),True)
    columns=list(dict.fromkeys(IIS_COLUMNS+['RISK']+[k for r in combined for k in r]))
    for name in ('IIS'+mm,'IIS'):save(c,'NPL',name,combined,columns)
    reports(c,'EIIMNP03',combined,'CURBAL UHC NETBAL IISP SUSPEND RECOVER RECC IISPW IIS OIP OISUSP OIRECV OIRECC OIW OI TOTIIS'.split(),dt)




if __name__ == '__main__':
    raise SystemExit('Run EIIWOF04 or EIIWOF13; EIIMNP03 receives settings from its caller.')
