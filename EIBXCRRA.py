"""EIBXCRRA: retail credit-risk extract, translated from the supplied SAS.

Python 3.10+, pandas. Keep the three original format modules beside this file.
Inputs are read-only SAS7BDAT exports with original SAS column names.
Pass actual paths: --reptdate --current --overdft --lnnote and either --loan
or --sasd-dir (selects LOANmmw.sas7bdat using BNM.REPTDATE).
No previous-month date is inferred. DWH input paths are not yet provided.
--combined-entity-inputs applies ENTITY_CD NE 'PIBB' to CURRENT/OVERDFT/LNNOTE/LOAN;
omit for PBB-only exports matching the original libraries.

Outputs: EIBXCRRA_ACCTS.csv (replacement for E1271.ACCTS),
EIBXCRRA_CRR.csv and EIBXCRRA_XCRR.txt (80-character records plus LF).
Each CSV has a native SAS7BDAT companion written through configured SASPy.
--record-mode fb removes line delimiters for literal 80-byte fixed records.
Exact SAS numeric overflow formatting, special missing codes, character-length
truncation and host collating sequences require production reconciliation.
Oversize output fields fail explicitly rather than corrupting downstream input.
"""
import argparse
from collections import defaultdict
from datetime import date, timedelta
from numbers import Real
from pathlib import Path
import pandas as pd
import PBBLNFMT
import PBBDPFMT
import PBMISFMT

OD_EXCLUDED = {103,104,105,106,107,116,119,120,126,127,128,129,137,138,140,141,142,144,145,146,147,148,149,151,154,155,158,164,171,172,173,177,178,180,181,182,191,192,193,194,195,549,550}
OL_PRODUCTS = {103,116,119,120,137,138,154,155,192,193,194,195}
FL_PRODUCTS = {300,301,302,304,305,309,310,320,325,335,350,355,356,357,358,359,360,361,500,504,505,506,509,510,515,520,521,522,526,528,529,524,525,527,530,531,556,559,560,564,565,566,567,568,569,570,573}
HL_PRODUCTS = {110,111,112,113,114,115,116,117,118,120,139,140,141,142,143,225,226,244,245,246,247,200,201,204,205,209,210,211,212,214,215,219,220,227,228,230,231,232,233,234,235,236,237,238,239,240,241,242,243}
CA_COLUMNS = 'USER3 RISKCODE ORGCODE DAYSARR BRANCH ORGTYPE ACCTNO NAME PRODUCT BALANCE FAACRR CRRCODE'.split()
NOTE_COLUMNS = 'BRANCH BLDATE SCORE1 SCORE2 GRADE GRADEX ACCTNO NOTENO NAME PRODUCT'.split()
OL_COLUMNS = 'ACCTNO NOTENO APPRLIMT BALANCE RISKRTE CATG USER3 RISKCODE ORGCODE DAYSARR GRADE BRANCH GRADEX NAME PRODUCT FAACRR CRRCODE'.split()


def require(frame, columns, name):
    absent = set(columns) - set(frame)
    if absent:
        raise ValueError(f'{name}: missing columns {sorted(absent)}')


def text(series):
    return series.fillna('').astype(str).str.rstrip()


def num(series):
    return pd.to_numeric(series, errors='raise')


def read_sas(path):
    path = Path(path)
    if path.suffix.lower() != '.sas7bdat':
        raise ValueError(f'Input must be .sas7bdat: {path}')
    frame = pd.read_sas(path,format='sas7bdat',encoding='latin1')
    frame.columns = frame.columns.str.upper()
    if frame.columns.duplicated().any():
        raise ValueError(f'Duplicate column names: {path}')
    for col in frame.select_dtypes(include=['datetime','datetimetz']):
        frame[col] = (frame[col]-pd.Timestamp('1960-01-01')).dt.total_seconds()/86400
    return frame


def date_value(value):
    if pd.isna(value):
        raise ValueError('Missing REPTDATE')
    return date(1960,1,1)+timedelta(days=float(value)) if isinstance(value,Real) else pd.Timestamp(value).date()


def loan_member(reporting_date):
    week = {8:1,15:2,22:3}.get(reporting_date.day,4)
    return f'LOAN{reporting_date:%m}{week}'


def match_merge(left, right, keys, keep_side='left'):
    """SAS BY match merge with shared-field overwrite and exhausted-row retention."""
    columns = list(dict.fromkeys([*left.columns,*right.columns]))
    def groups(frame):
        result = defaultdict(list)
        for row in frame.sort_values(keys,kind='stable',na_position='first').to_dict('records'):
            key = tuple(None if pd.isna(row[k]) else row[k].rstrip() if isinstance(row[k],str) else row[k] for k in keys)
            result[key].append(row)
        return result
    lg, rg = groups(left), groups(right)
    selected = lg if keep_side=='left' else rg
    rows=[]
    for key in selected:
        a,b = lg.get(key,[]),rg.get(key,[])
        retained = dict.fromkeys(columns)
        for i in range(max(len(a),len(b))):
            if i<len(a): retained.update(a[i])
            if i<len(b): retained.update(b[i])
            rows.append(retained.copy())
    return pd.DataFrame(rows,columns=columns)


def grade(frame, primary, fallback):
    first=text(frame[primary]); second=text(frame[fallback])
    frame['GRADE'] = second.where(~first.str[:1].isin(list('ABCDE')),first)
    frame['GRADEX'] = frame.GRADE.str[:1]
    return frame


def build_accounts(current, overdft, lnnote, loan, reporting_date):
    require(current,[*set(CA_COLUMNS)-{'DAYSARR','BALANCE'},'CURBAL'],'CURRENT')
    require(overdft,['ACCTNO','LMTAMT','APPRLIMT','EXCESSDT'],'OVERDFT')
    require(lnnote,'ACCTNO NOTENO NAME PENDBRH LOANTYPE CORPCODE ORGTYPE BALANCE BLDATE SCORE1 SCORE2'.split(),'LNNOTE')
    require(loan,'ACCTNO NOTENO APPRLIMT BALANCE RISKRTE ACCTYPE'.split(),'LOAN')
    # SAS numeric missing compares below zero; retain those rows just as source.
    ca=current.loc[num(current.CURBAL).fillna(float('-inf'))<0].copy()
    ca['BALANCE']=num(ca.CURBAL).abs(); ca['DAYSARR']=0
    ca=ca[CA_COLUMNS]
    od=match_merge(ca,overdft[['ACCTNO','LMTAMT','APPRLIMT','EXCESSDT']],['ACCTNO'])
    od=od.loc[(num(od.APPRLIMT)>0)&(num(od.LMTAMT)>0)&(text(od.USER3)!='5')&~text(od.RISKCODE).isin(list('1234'))&~text(od.ORGCODE).isin(['001','1'])&~num(od.PRODUCT).isin(OD_EXCLUDED)].copy()
    od['CATG']='OD'; grade(od,'CRRCODE','FAACRR')
    note=lnnote.loc[(num(lnnote.NOTENO)>0)&(text(lnnote.CORPCODE)!='C')&(text(lnnote.ORGTYPE)!='E')&(num(lnnote.BALANCE)>1)].copy()
    note['BRANCH']=note.PENDBRH; note['PRODUCT']=note.LOANTYPE
    grade(note,'SCORE1','SCORE2'); note=note[NOTE_COLUMNS]
    ln=loan.loc[(num(loan.NOTENO)>0)&(num(loan.BALANCE)>1),['ACCTNO','NOTENO','APPRLIMT','BALANCE','RISKRTE']].copy()
    ln1=loan.loc[text(loan.ACCTYPE)=='OD'].drop(columns=['NAME','BRANCH','PRODUCT'],errors='ignore').copy()
    ol=match_merge(ca,ln1,['ACCTNO'],keep_side='right')
    ol=ol.loc[~num(ol.RISKRTE).isin([1,2,3,4])&(text(ol.ORGCODE)!='C')&(text(ol.ORGTYPE)!='E')&num(ol.PRODUCT).isin(OL_PRODUCTS)].copy()
    ol['CATG']='OL'; grade(ol,'CRRCODE','FAACRR'); ol=ol.reindex(columns=OL_COLUMNS)
    notes=match_merge(note,ln,['ACCTNO','NOTENO'])
    notes=notes.loc[~num(notes.RISKRTE).isin([1,2,3,4])].copy()
    days=(reporting_date-date(1960,1,1)).days
    bldate=num(notes.BLDATE)
    notes['DAYSARR']=(days-bldate).where(bldate>0,0).clip(lower=0)
    fl=notes.loc[num(notes.PRODUCT).isin(FL_PRODUCTS)].assign(CATG='FL')
    hl=notes.loc[num(notes.PRODUCT).isin(HL_PRODUCTS)].assign(CATG='HL')
    accounts=pd.concat([od,fl,hl,ol],ignore_index=True)
    accounts['ACCT']=1
    accounts['GRADEX']=accounts.GRADEX.where(accounts.GRADEX.isin(list('ABCDE')),'X')
    accounts['BRCHCD']=accounts.BRANCH.map(lambda x: PBMISFMT.BRCHCD(x).rstrip())
    return accounts


def build_crr(accounts):
    rows=[]
    for branch in range(2,269):
        code=PBMISFMT.BRCHCD(branch).rstrip()
        if not code or '1' <= code <= '270':
            continue
        for rating in 'ABCDEX':
            for category in ['FL','HL','OD','OL']:
                rows.append((branch,rating,category,code))
    grid=pd.DataFrame(rows,columns=['BRANCH','GRADEX','CATG','BRCHCD'])
    data=accounts.copy()
    data['BALANCE']=num(data.BALANCE)
    totals=data.groupby(['BRANCH','GRADEX','CATG'],dropna=True)[['ACCT','BALANCE']].sum().reset_index()
    result=grid.merge(totals,on=['BRANCH','GRADEX','CATG'],how='left',validate='one_to_one')
    result[['ACCT','BALANCE']]=result[['ACCT','BALANCE']].fillna(0)
    return result.sort_values(['BRANCH','GRADEX','CATG']).reset_index(drop=True)


def render_crr(crr):
    records=[]
    for row in crr.itertuples(index=False):
        count=f'{row.ACCT:8.0f}'; balance=f'{row.BALANCE:12.2f}'
        if len(count)>8 or len(balance)>12:
            raise ValueError(f'Output width exceeded for branch {row.BRANCH}, {row.GRADEX}/{row.CATG}')
        record=f'{row.BRANCH:3.0f} {row.GRADEX:1} {row.CATG:2} {count}  {balance}'
        records.append(record.ljust(80))
    return records


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

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['reptdate','current','overdft','lnnote']:
        parser.add_argument('--'+name,required=True,type=Path)
    source=parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--loan',type=Path)
    source.add_argument('--sasd-dir',type=Path)
    parser.add_argument('--combined-entity-inputs',action='store_true')
    parser.add_argument('--output-dir',type=Path,default=Path('/stgsrcsys/host/holding'))
    parser.add_argument('--record-mode',choices=['lines','fb'],default='lines')
    args=parser.parse_args(); output_session()
    dates=read_sas(args.reptdate); require(dates,['REPTDATE'],'REPTDATE')
    if dates.empty: raise ValueError('Empty REPTDATE')
    reporting_date=date_value(dates.REPTDATE.iloc[-1])
    member=loan_member(reporting_date)
    loan_path=args.loan
    if loan_path is None:
        choices=[p for p in args.sasd_dir.iterdir() if p.name.lower()==member.lower()+'.sas7bdat']
        if len(choices)!=1: raise ValueError(f'Expected one {member}.sas7bdat under {args.sasd_dir}')
        loan_path=choices[0]
    print(f'REPTDATE={reporting_date}; SASD member={member}; input={loan_path}',flush=True)
    data={name:read_sas(getattr(args,name)) for name in ['current','overdft','lnnote']}
    data['loan']=read_sas(loan_path)
    if args.combined_entity_inputs:
        for name,frame in data.items():
            require(frame,['ENTITY_CD'],name)
            data[name]=frame.loc[text(frame.ENTITY_CD)!='PIBB'].copy()
    accounts=build_accounts(**data,reporting_date=reporting_date)
    crr=build_crr(accounts)
    records=render_crr(crr)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    dump(accounts,args.output_dir/'EIBXCRRA_ACCTS.csv')
    dump(crr,args.output_dir/'EIBXCRRA_CRR.csv')
    payload=('\n'.join(records)+'\n') if args.record_mode=='lines' and records else ''.join(records)
    (args.output_dir/'EIBXCRRA_XCRR.txt').write_bytes(payload.encode('ascii'))
    print(f'Written {len(accounts):,} account rows and {len(crr):,} CRR records to {args.output_dir}')


if __name__=='__main__':
    main()
