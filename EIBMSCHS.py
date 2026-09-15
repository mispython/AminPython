"""EIBMSCHS: individual job; all input paths must be .sas7bdat.
Requires pandas. Inputs are read-only, using original SAS column names.
No fixed-position text parsing or CSV input is used.
Outputs: CSV + native SAS7BDAT through SASPy, plus text (and ZIP for EIBRCRRD).
See SAS7BDAT_INPUTS.md for schemas and CONVERSION_NOTES.md for source anomalies.
"""
import argparse
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import pandas as pd

METRICS = ['C1CNT','C1BAL','C2CNT','C2BAL','C3CNT','C3BAL']
PRODUCT_METRICS = ['S1CNT','C1CNT','C1BAL','S2CNT','C2CNT','C2BAL','S3CNT','C3CNT','C3BAL']
CHARS = set('BRCHCD HOE REGNID REGION PRODUCT NCORE CATG GRADE GRADEX NAME SCORE1 SCORE2 CRRCODE FAACRR TAG AANUM STAFX1 STAFX2 STAFX3 SECO XCORE'.split())


def require(df, cols):
    missing = set(cols)-set(df)
    if missing:
        raise ValueError(f'Missing input columns: {sorted(missing)}')


def read_table(path):
    """Read a SAS7BDAT input only; preserve native numeric types and precision."""
    path = Path(path)
    if path.suffix.lower() != '.sas7bdat':
        raise ValueError(f'Input must be .sas7bdat, not CSV/text: {path}')
    df = pd.read_sas(path, format='sas7bdat', encoding='latin1')
    df.columns = df.columns.str.upper()
    if df.columns.duplicated().any():
        raise ValueError(f'Duplicate column names after normalization: {path}')
    for col in df.select_dtypes(include=['object','string']):
        # SAS character comparisons ignore trailing blanks. Do not stringify numbers.
        df[col] = df[col].map(lambda v: v.rstrip() if isinstance(v,str) else v)
        if col in CHARS:
            df[col] = df[col].fillna('')
    return df


def reporting_date(path):
    df=read_table(path); require(df,['REPTDATE'])
    if df.empty or pd.isna(df.REPTDATE.iloc[-1]):
        raise ValueError('REPTDATE is empty/missing')
    v=df.REPTDATE.iloc[-1]
    if isinstance(v,(pd.Timestamp,date)):
        return pd.Timestamp(v).date()
    return date(1960,1,1)+timedelta(days=float(v))


def numeric(field,decimals=0):
    field=field.strip()
    if not field or field=='.': return float('nan')
    value=float(field)
    return value/(10**decimals) if decimals and '.' not in field and 'E' not in field.upper() else value


def read_columns(path, layout):
    """Use original INPUT field names from the SAS7BDAT columns, not offsets.

    Positions/widths in layout document the original source only. Numeric SAS
    values are already decoded: never divide them by an implied decimal factor.
    """
    df = read_table(path)
    require(df, [name for name, _, _, _ in layout])
    df = df[[name for name, _, _, _ in layout]].copy()
    for name, _, _, kind in layout:
        if kind == 'char':
            populated = df[name].dropna()
            if not populated.map(lambda v:isinstance(v,str)).all():
                raise ValueError(f'{path}: {name} must be a SAS character column')
            df[name] = df[name].fillna('').str.rstrip()
        elif not pd.api.types.is_numeric_dtype(df[name]):
            raise ValueError(f'{path}: {name} must be a SAS numeric column')
    return df


def branch_file(path,with_name=False):
    layout=[('BRANCH',2,3,0),('BRCHCD',6,3,'char')]
    if with_name: layout.append(('BRNAME',12,30,'char'))
    return read_columns(path,layout)


def merge_by(left,right,keys):
    """SAS match merge, retaining exhausted records and input membership."""
    columns=list(dict.fromkeys([*left.columns,*right.columns]))
    def groups(df):
        groups=defaultdict(list)
        for row in df.sort_values(keys,kind='stable',na_position='first').to_dict('records'):
            key=tuple(None if pd.isna(row[k]) else row[k] for k in keys)
            groups[key].append(row)
        return groups
    a,b=groups(left),groups(right); rows=[]
    for key in dict.fromkeys([*a,*b]):
        aa,bb=a.get(key,[]),b.get(key,[])
        retained=dict.fromkeys(columns)
        for i in range(max(len(aa),len(bb))):
            if i<len(aa): retained.update(aa[i])
            if i<len(bb): retained.update(bb[i])
            rows.append(dict(retained,_LEFT=bool(aa),_RIGHT=bool(bb)))
    return pd.DataFrame(rows,columns=[*columns,'_LEFT','_RIGHT'])


def nway(df,keys,metrics=METRICS):
    df=df.copy()
    require(df,keys)
    for col in metrics:
        if col not in df: df[col]=0.0
        df[col]=pd.to_numeric(df[col],errors='raise').fillna(0)
    for col in keys:
        if col in CHARS: df[col]=df[col].replace('',None)
    return df.groupby(keys,dropna=True,sort=True)[metrics].sum().reset_index()


def zero_metrics(df,metrics=METRICS):
    df=df.copy()
    for col in metrics:
        if col not in df: df[col]=0.0
        df[col]=pd.to_numeric(df[col],errors='raise').fillna(0)
    return df


def staff_counts(df):
    df=zero_metrics(df)
    require(df,['NCORE'])
    for i,code in enumerate('XCN',1): df[f'S{i}CNT']=(df.NCORE==code).astype(int)
    return df


def put_line(fields,width=133):
    chars=[' ']*width
    for position,value in fields:
        value=str(value)
        if position-1+len(value)>width: raise ValueError('Output line exceeds declared width')
        chars[position-1:position-1+len(value)]=value
    return ''.join(chars)


def fmt(value,width,decimals=0,commas=False):
    if pd.isna(value): return '.'.rjust(width)
    result=format(float(value),f'{"," if commas else ""}.{decimals}f')
    return result.rjust(width) if len(result)<=width else '*'*width


# Native SAS output uses a configured SASPy session on the same filesystem.
_OUTPUT_SAS = None


def output_session():
    global _OUTPUT_SAS
    if _OUTPUT_SAS is None:
        import atexit
        import os
        try:
            import saspy
        except ImportError as exc:
            raise RuntimeError('CSV + SAS7BDAT output requires saspy and a configured SAS session. See SAS7BDAT_INPUTS.md.') from exc
        config = os.environ.get('SASPY_CFGNAME')
        _OUTPUT_SAS = saspy.SASsession(**({'cfgname': config} if config else {}))
        atexit.register(_OUTPUT_SAS.endsas)
    return _OUTPUT_SAS


def dump(df, path):
    """Write CSV and native SAS7BDAT; never change the input DataFrame."""
    import os
    import re
    import tempfile
    path = Path(path)
    if path.suffix.lower() != '.csv':
        raise ValueError('Output path must have a .csv suffix')
    member = path.stem.lower()
    if not re.fullmatch(r'[a-z_][a-z0-9_]{0,31}', member):
        raise ValueError(f'Invalid SAS output member: {member}')
    frame = df.copy(deep=True)
    if frame.columns.duplicated().any() or any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,31}', str(c)) for c in frame):
        raise ValueError('Output columns must be unique SAS V7 names')
    if not len(frame.columns):
        raise ValueError('Cannot write a SAS dataset without columns')
    char_lengths = {}
    for col in frame:
        series = frame[col]
        if pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series):
            values = series.dropna()
            known_chars = set('BRCHCD HOE REGNID REGION NCORE CATG GRADE GRADEX NAME SCORE1 SCORE2 CRRCODE FAACRR TAG AANUM STAFX1 STAFX2 STAFX3 SECO XCORE EXCESSD'.split())
            if not values.map(lambda v: isinstance(v, str)).all() or (values.empty and col not in known_chars and not (col == 'PRODUCT' and 'NCORE' in frame)):
                # Object columns of numeric values can result from SAS merges.
                frame[col] = pd.to_numeric(series, errors='raise').astype(float)
                continue
            length = max(1, max((len(v.encode('utf-8')) for v in values), default=0))
            if length > 32767:
                raise ValueError(f'{col}: exceeds SAS character length 32767')
            char_lengths[col] = length
            frame[col] = series.fillna('')
        elif pd.api.types.is_bool_dtype(series):
            frame[col] = series.astype(float)
    sas = output_session()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Staging in the destination prevents a failed SAS write replacing old output.
    with tempfile.TemporaryDirectory(prefix='.sas_output_', dir=path.parent) as staging:
        folder = Path(staging).resolve()
        csv_path = folder / path.name
        frame.to_csv(csv_path, index=False, float_format='%.17g')
        sas.saslib('PYOUT', path=str(folder))
        if frame.empty:
            lengths = ' '.join(f'{c} ${char_lengths[c]}' if c in char_lengths else f'{c} 8' for c in frame)
            result = sas.submit(f'data PYOUT.{member}; length {lengths}; stop; run;', results='TEXT')
            if re.search(r'^ERROR(?:\s|\d|:)', result.get('LOG', ''), re.M):
                raise RuntimeError(result['LOG'])
        else:
            result = sas.df2sd(frame, table=member, libref='PYOUT', char_lengths=char_lengths or None, encode_errors='fail')
            if result is None:
                raise RuntimeError(f'SAS failed to write {member}; inspect SAS log')
        native = folder / (member + '.sas7bdat')
        if not native.is_file():
            raise RuntimeError('SAS7BDAT output not found. SASPy must use SAS with access to the same output filesystem as Python.')
        with pd.read_sas(native, format='sas7bdat', iterator=True, encoding='latin1') as check:
            if check.row_count != len(frame) or list(check.column_names) != list(frame.columns):
                raise RuntimeError(f'SAS output row count/schema mismatch: {member}')
        sas.submit('libname PYOUT clear;', results='TEXT')
        os.replace(native, path.with_suffix('.sas7bdat'))
        os.replace(csv_path, path)
    print(f'Written {path} and {path.with_suffix(".sas7bdat")}', flush=True)

def base_parser(description):
    p=argparse.ArgumentParser(description=description)
    p.add_argument('--reptdate',required=True,type=Path)
    p.add_argument('--output-dir',type=Path,default=Path('/stgsrcsys/host/holding'))
    return p


def save_report(lines,path):
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')


def category_line(row,product_counts=False,total_label=None):
    fields=[(2,total_label or str(row.get('PRODUCT',''))[:20])]
    if not product_counts and total_label is None:
        fields=[(2,fmt(row.get('STAFF'),5)),(10,str(row.get('PRODUCT',''))[:20])]
    for i in range(1,4):
        offset=(i-1)*36
        if product_counts:
            fields.append((23+offset if total_label else 24+offset,fmt(row.get(f'S{i}CNT',0),6 if total_label else 5)))
        fields.extend([(31+offset if total_label else 32+offset,fmt(row.get(f'C{i}CNT',0),6 if total_label else 5)),(40+offset,fmt(row.get(f'C{i}BAL',0),16,2,True))])
    return put_line(fields)


def category_report(df,job,dt,group_keys,product_counts=False,source_grand_bug=False):
    metrics=PRODUCT_METRICS if product_counts else METRICS
    lines=[]
    for key,part in df.groupby(group_keys,dropna=False,sort=True):
        lines.extend([put_line([(1,'SUMMARY REPORT ON STAFF PARTICIPATION UNDER SCR SCHEME')]),
                      put_line([(1,f'PROGRAM ID: {job}  REPORT DATE: {dt:%d/%m/%Y}')]),
                      put_line([(1,str(dict(zip(group_keys,key if isinstance(key,tuple) else (key,))))[:130])]),
                      put_line([(24,'CATEGORY 1'),(60,'CATEGORY 2 CORE'),(96,'CATEGORY 2 NON-CORE')]),
                      put_line([(2,'PRODUCT' if product_counts else 'STAFF   PRODUCT'),(24,'STAFF ACCTS     YTD BALANCE' if product_counts else '      ACCTS     YTD BALANCE'),(60,'STAFF ACCTS     YTD BALANCE' if product_counts else '      ACCTS     YTD BALANCE'),(96,'STAFF ACCTS     YTD BALANCE' if product_counts else '      ACCTS     YTD BALANCE')])])
        lines.extend(category_line(row,product_counts) for row in part.to_dict('records'))
        lines.append(category_line(part[metrics].sum().to_dict(),product_counts,'BRANCH TOTAL=' if 'BRCHCD' in group_keys else 'DEPT/DIV TOTAL='))
        if 'REGNID' in group_keys:
            # Emit region total only on the final branch of that region.
            region=key[0] if isinstance(key,tuple) else key
            region_rows=df.loc[df.REGNID==region]
            if part.BRCHCD.iloc[-1]==region_rows.BRCHCD.iloc[-1]:
                lines.append(category_line(region_rows[metrics].sum().to_dict(),product_counts,'REGION TOTAL='))
    if not df.empty:
        grand=df[metrics].sum().to_dict()
        if source_grand_bug: grand['S3CNT']=grand['S2CNT']
        lines.append(category_line(grand,product_counts,'GRAND TOTAL='))
    return lines

def transform(srs, branches=None):
    require(srs, ['PRODUCT','STAFF'])
    srs=zero_metrics(srs)
    return nway(srs,['HOE', 'STAFF', 'PRODUCT'],METRICS)

def main():
    p=base_parser(__doc__)
    p.add_argument('--srs',required=True,type=Path,help='SRSBR' if False else 'SRSHO')
    args=p.parse_args(); output_session(); dt=reporting_date(args.reptdate)
    result=transform(read_table(args.srs),None)
    lines=category_report(result,'EIBMSCHS',dt,['HOE'],product_counts=False,source_grand_bug=False)
    lines.insert(0,'REPORT FROM 1 SEPT 2006 - 31 DEC 2006'.ljust(133))  # Literal source title retained.
    args.output_dir.mkdir(parents=True,exist_ok=True)
    dump(result,args.output_dir/'EIBMSCHS.csv')
    save_report(lines,args.output_dir/'EIBMSCHS_report.txt')


if __name__=='__main__':
    main()
