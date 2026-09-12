"""Deposit range profile; translated from the supplied EIBMDPBR SAS job.

Inputs are SAS7BDAT files. Run --help for dataset arguments.
"""
import argparse
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from numbers import Real

import pandas as pd
import PBBLNFMT
import PBBDPFMT
import PBMISFMT

# %INC order matters: PBMISFMT replaces identically named earlier formats.
FORMATS = {**PBBLNFMT.FORMATS, **PBBDPFMT.FORMATS, **PBMISFMT.FORMATS}
BRANCHES = {2,3,4,5,6,7,8,9,13,15,18,19,20,24,25,26,28,33,36,37,38,40,41,42,44,45,54,56,57,58,60,66,68,78,79,90,94,110,123,129,130,135,136,145,153,157,168,179,183,185,187,198,200,207,216}
STFSA = {151,181,200,201,215}
STFCA = {*range(50,66),101,103,106,151,158,164,180,181,182}
FD_EXCLUSIONS = ((400,428),(448,469),(600,639),(720,740),(470,499),(548,573))
LIMITS = [50000,100000,200000,300000,400000,500000,600000,700000,800000,900000,1000000,2000000,3000000,4000000,5000000,6000000,7000000,8000000,9000000,10000000]
RANGE_LABELS = [
 ' 0.              BELOW RM 50,000 ',
 ' 1. RM  50,000 - BELOW RM100,000 ',
 ' 2. RM 100,000 - BELOW RM200,000 ',
 ' 3. RM 200,000 - BELOW RM300,000 ',
 ' 4. RM 300,000 - BELOW RM400,000 ',
 ' 5. RM 400,000 - BELOW RM500,000 ',
 ' 6. RM 500,000 - BELOW RM600,000 ',
 ' 7. RM 600,000 - BELOW RM700,000 ',
 ' 8. RM 700,000 - BELOW RM800,000 ',
 ' 9. RM 800,000 - BELOW RM900,000 ',
 '10. RM 900,000 - BELOW RM 1 MILL ',
 '11. RM  1 MILL - BELOW RM 2 MILL',
 '12. RM  2 MILL - BELOW RM 3 MILL',
 '13. RM  3 MILL - BELOW RM 4 MILL',
 '14. RM  4 MILL - BELOW RM 5 MILL',
 '15. RM  5 MILL - BELOW RM 6 MILL',
 '16. RM  6 MILL - BELOW RM 7 MILL',
 '17. RM  7 MILL - BELOW RM 8 MILL',
 '18. RM  8 MILL - BELOW RM 9 MILL',
 '19. RM  9 MILL - BELOW RM10 MILL',
 '20. RM 10 MILL & ABOVE           ']


def deposit_range(balance):
    return RANGE_LABELS[next((i for i, limit in enumerate(LIMITS) if balance < limit),20)]


def read_dataset(path, encoding):
    path = Path(path)
    if path.suffix.lower() != '.sas7bdat':
        raise ValueError(f'Expected .sas7bdat input: {path}')
    frame = pd.read_sas(path, format='sas7bdat', encoding=encoding)
    frame.columns = frame.columns.str.upper()
    if frame.columns.duplicated().any():
        raise ValueError(f'Duplicate column names in {path}')
    return frame


def require(frame, columns, name):
    absent = set(columns) - set(frame.columns)
    if absent:
        raise ValueError(f'{name}: missing columns {sorted(absent)}')


def key(value):
    if pd.isna(value):
        return None
    return value.rstrip() if isinstance(value, str) else value


def sas_merge(deposits, cis):
    """SAS BY match merge: zip each BY group and retain exhausted rows.

This intentionally avoids the Cartesian product of a SQL/pandas many-to-many
join. A CUSTNO read from CIS overwrites the deposit value on that iteration.
"""
    right = defaultdict(list)
    for row in cis.to_dict('records'):
        right[key(row['ACCTNO'])].append(row)
    left = defaultdict(list)
    for row in deposits.to_dict('records'):
        left[key(row['ACCTNO'])].append(row)
    result = []
    for account, rows in left.items():
        customers = right.get(account, [])
        retained = {}
        for i in range(max(len(rows), len(customers))):
            if i < len(rows):
                retained.update(rows[i])
            if i < len(customers):
                retained.update(customers[i])
            result.append(retained.copy())
    return pd.DataFrame(result, columns=['ACCTNO','CUSTNO','CURBAL','BRCHCD'])


def build_profile(saving, current, fd, cisdp, cissa):
    for name, df in [('SAVING',saving),('CURRENT',current),('FD',fd)]:
        require(df, ['ACCTNO','CURBAL','BRANCH','OPENIND', 'INTPLAN' if name=='FD' else 'PRODUCT'],name)
    for name, df in [('CISDP.DEPOSIT',cisdp),('CISSA.DEPOSIT',cissa)]:
        require(df,['ACCTNO','CUSTNO'],name)
    cis = pd.concat([cisdp[['ACCTNO','CUSTNO']],cissa[['ACCTNO','CUSTNO']]],ignore_index=True).copy()
    # SAS character comparisons ignore trailing blanks.
    for col in ['ACCTNO','CUSTNO']:
        cis[col] = cis[col].map(key)
    cis = cis.sort_values(['CUSTNO','ACCTNO'],kind='stable',na_position='first').drop_duplicates(['CUSTNO','ACCTNO'])
    cis = cis.sort_values('ACCTNO',kind='stable',na_position='first')
    fd_mask = pd.Series(True,index=fd.index)
    for low, high in FD_EXCLUSIONS:
        fd_mask &= ~fd.INTPLAN.between(low,high)
    dp = pd.concat([saving.loc[~saving.PRODUCT.isin(STFSA)],current.loc[~current.PRODUCT.isin(STFCA)],fd.loc[fd_mask]],ignore_index=True)
    dp = dp.loc[dp.BRANCH.isin(BRANCHES) & ~dp.OPENIND.map(key).isin(['B','C','P'])].copy()
    dp['BRCHCD'] = dp.BRANCH.map(lambda x: PBMISFMT.format_value('BRCHCD',x).rstrip())
    cols = ['ACCTNO','CURBAL','BRCHCD'] + (['CUSTNO'] if 'CUSTNO' in dp.columns else [])
    dp = dp[cols].sort_values('ACCTNO',kind='stable',na_position='first')
    merged = sas_merge(dp,cis)
    merged['CUSTNO'] = merged.CUSTNO.map(key)
    merged['CURBAL'] = pd.to_numeric(merged.CURBAL,errors='raise')
    # SAS SUM statement starts at zero, ignoring missing CURBAL.
    customers = merged.groupby(['BRCHCD','CUSTNO'],dropna=False,sort=False).CURBAL.sum().reset_index(name='BALANCE')
    customers['DRANGE'] = customers.BALANCE.map(deposit_range)
    customers['ACCT'] = 1
    profile = customers.groupby(['BRCHCD','DRANGE'],dropna=True)[['ACCT','BALANCE']].sum().reset_index()
    return profile.sort_values(['BRCHCD','DRANGE']).reset_index(drop=True)


def report_date(frame):
    require(frame,['REPTDATE'],'REPTDATE')
    if frame.empty or pd.isna(frame.REPTDATE.iloc[-1]):
        raise ValueError('REPTDATE must contain a nonmissing reporting date')
    value = frame.REPTDATE.iloc[-1]  # CALL SYMPUT is overwritten by each row.
    if isinstance(value,Real):
        return date(1960,1,1)+timedelta(days=float(value))
    return pd.Timestamp(value).date()


def render_report(profile, reporting_date):
    lines = ['PUBLIC BANK BERHAD','DEVELOPMENT OF WEALTH MANAGEMENT CENTRES ',
             'DEPOSIT RANGE PROFILE BY SELECTED BRANCHES-'+reporting_date.strftime('%d/%m/%y'),'',
             f'{"BRH":5} {"DEPOSIT RANGE":35} {"NO. OF CUSTOMER":>15} {"OUTSTANDING AMOUNT":>20}', '-'*78]
    for branch, group in profile.groupby('BRCHCD',sort=True):
        for i, row in enumerate(group.itertuples(index=False)):
            lines.append(f'{branch if i==0 else "":5} {row.DRANGE:35} {row.ACCT:15,.0f} {row.BALANCE:20,.2f}')
        lines.extend([' '*9+'-'*65,f'{"TOTAL":41} {group.ACCT.sum():15,.0f} {group.BALANCE.sum():20,.2f}',' '*9+'-'*65,''])
    # Equivalent fixed-width record length to JCL LRECL=133; no ASA control byte.
    return '\n'.join(line.ljust(133) for line in lines)+'\n'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for dataset in ['reptdate','saving','current','fd','cisdp','cissa']:
        parser.add_argument('--'+dataset,required=True,type=Path,help='Path to '+dataset.upper()+'.sas7bdat')
    parser.add_argument('--encoding',default='latin1',help='SAS text encoding; default latin1')
    parser.add_argument('--output-dir',type=Path,default=Path('report_output'))
    args=parser.parse_args()
    datasets={name:read_dataset(getattr(args,name),args.encoding) for name in ['reptdate','saving','current','fd','cisdp','cissa']}
    reporting_date=report_date(datasets.pop('reptdate'))
    profile=build_profile(**datasets)
    args.output_dir.mkdir(parents=True,exist_ok=True)
    profile.to_csv(args.output_dir/'DPBR.csv',index=False,float_format='%.2f')
    totals=profile.groupby('BRCHCD')[['ACCT','BALANCE']].sum().reset_index()
    totals.to_csv(args.output_dir/'DPBR_branch_totals.csv',index=False,float_format='%.2f')
    (args.output_dir/'DPBR_report.txt').write_text(render_report(profile,reporting_date),encoding='utf-8')
    print(f'Created {len(profile)} profile rows in {args.output_dir.resolve()}')


if __name__=='__main__':
    main()
