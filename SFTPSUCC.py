"""Select successful write-off records, then send the dated file to DRR."""
import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import subprocess

INPUT_ROOT = Path('/stgsrcsys/host/uat')
SOURCE_FILE = INPUT_ROOT / 'RBP2.B033.LN.WRI2.OFF.LNOTES'
HOLDING = Path('/stgsrcsys/host/holding')
OUTPUT_FILE = HOLDING / 'LNOTES_SUCCESSx.txt'
# None = newline-delimited ASCII-compatible records, preserving bytes and spaces.
# For fixed records without separators, set the source record length from its DCB.
RECORD_LENGTH = None
FIXED_RECORD_NEWLINE = b'\n'

# DRR connection comes from the same control dataset as the supplied sample.
CONTROL = Path('/sasdata/dwh/control/ctl_dwh_sftp_info.sas7bdat')
BATCH = Path('/sasdata/dwh/logs/SFTPSUCC.txt')
FTP_LOG = Path('/sasdata/dwh/logs/SFTPSUCC_LOG.txt')
SFTP_EXECUTABLE = 'psftp'
REMOTE_DIRECTORY = 'HPCC/WRITTEN-OFF'
HOST_KEY = ''  # Optional verified fingerprint; otherwise use the PuTTY host-key cache.


def quote(value):
    value = str(value).replace('\\', '/')
    if any(ch in value for ch in '\r\n\x00"'):
        raise ValueError('Invalid PSFTP path')
    return '"' + value + '"'


def read_connection():
    import pandas as pd
    ctl = pd.read_sas(CONTROL, format='sas7bdat', encoding='utf-8')
    ctl.columns = [str(col).strip().upper() for col in ctl.columns]
    required = {'HOST_DESC', 'SFTP_PW', 'SFTP_ID', 'HOST_IP'}
    if not required.issubset(ctl.columns):
        raise ValueError('DRR control dataset is missing required columns')
    rows = ctl[ctl['HOST_DESC'].fillna('').str.contains(
        'Data Report Repository (DRR)', regex=False)]
    if len(rows) != 1:
        raise RuntimeError(f'Expected one DRR row; found {len(rows)}')
    row = rows.iloc[0]
    def field(name):
        value = row[name]
        if pd.isna(value):
            raise ValueError('Missing ' + name + ' in DRR control dataset')
        value = value.decode('utf-8') if isinstance(value, bytes) else str(value)
        value = value.strip()
        if not value or any(ch in value for ch in '\r\n\x00'):
            raise ValueError('Invalid ' + name + ' in DRR control dataset')
        return value
    host, user, password = field('HOST_IP'), field('SFTP_ID'), field('SFTP_PW')
    if host.startswith('-') or user.startswith('-') or '@' in host or '@' in user:
        raise ValueError('Invalid DRR host/user')
    return host, user, password


def transfer(files, dry_run=False):
    for source, remote in files:
        if not Path(source).is_file():
            raise FileNotFoundError(source)
    batch = 'cd ' + quote(REMOTE_DIRECTORY) + '\r\n'
    batch += ''.join('put ' + quote(Path(source).resolve()) + ' ' + quote(remote) + '\r\n'
                     for source, remote in files)
    if dry_run:
        print(batch, end='')
        return batch
    host, user, password = read_connection()
    BATCH.parent.mkdir(parents=True, exist_ok=True)
    FTP_LOG.parent.mkdir(parents=True, exist_ok=True)
    BATCH.write_bytes(batch.encode('utf-8'))
    command = [SFTP_EXECUTABLE, '-batch', '-pw', password,
               user + '@' + host, '-b', str(BATCH)]
    if HOST_KEY:
        command.extend(['-hostkey', HOST_KEY])
    # Use the existing PuTTY host-key cache (or HOST_KEY); fail on unknown keys.
    # Batch errors stop the job. Never print the command, which contains a password.
    try:
        with FTP_LOG.open('w', encoding='utf-8') as log:
            subprocess.run(command, stdin=subprocess.DEVNULL, stdout=log,
                           stderr=subprocess.STDOUT, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f'DRR transfer failed (exit {exc.returncode}); see {FTP_LOG}') from None
    return batch


def extract(source=SOURCE_FILE, target=OUTPUT_FILE):
    source, target = Path(source), Path(target)
    if source.resolve() == target.resolve():
        raise ValueError('Output must not overwrite the original LNOTES input')
    if RECORD_LENGTH is not None and RECORD_LENGTH < 81:
        raise ValueError('RECORD_LENGTH must be at least 81')
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.with_suffix(target.suffix + '.tmp')
    total = selected = 0
    try:
        with source.open('rb') as reader, stage.open('wb') as writer:
            records = iter(lambda: reader.read(RECORD_LENGTH), b'') if RECORD_LENGTH else reader
            for raw in records:
                total += 1
                body = raw if RECORD_LENGTH else raw.rstrip(b'\r\n')
                if len(body) < 81 or (RECORD_LENGTH and len(raw) != RECORD_LENGTH):
                    raise ValueError(f'LNOTES record {total}: invalid record length')
                # DFSORT INCLUDE=(1,1,CH,EQ,C'1',AND,81,1,CH,NE,C'R').
                if body[0:1] == b'1' and body[80:81] != b'R':
                    writer.write(raw + FIXED_RECORD_NEWLINE if RECORD_LENGTH else raw)
                    selected += 1
        stage.replace(target)
    finally:
        stage.unlink(missing_ok=True)
    return total, selected


def run(run_date=None, prepare_only=False):
    scheduled = (date.fromisoformat(run_date) if isinstance(run_date, str) else run_date)
    scheduled = scheduled or datetime.now(timezone(timedelta(hours=8))).date()
    total, selected = extract(SOURCE_FILE, OUTPUT_FILE)
    remote = f'HPWOffLoansR{scheduled:%Y%m%d}.TXT'
    print(f'Selected {selected} of {total} records: {OUTPUT_FILE}')
    if not prepare_only:
        transfer([(OUTPUT_FILE, remote)])
    return OUTPUT_FILE, remote


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-date', help='Scheduler date YYYY-MM-DD used in remote filename')
    parser.add_argument('--prepare-only', action='store_true', help='Create local extract without SFTP')
    args = parser.parse_args()
    run(args.run_date, args.prepare_only)
