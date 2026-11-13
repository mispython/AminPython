"""Send conventional job-07 extracts to DRR, matching the active JCL step."""
import argparse
from pathlib import Path
import subprocess

HOLDING = Path('/stgsrcsys/host/holding')
FILES = [(HOLDING / 'HPTXT1x.txt', 'WOFFHP1.TXT'),
         (HOLDING / 'HPTXT2x.txt', 'WOFFHP2.TXT')]
# DRR connection comes from the same control dataset as the supplied sample.
CONTROL = Path('/sasdata/dwh/control/ctl_dwh_sftp_info.sas7bdat')
BATCH = Path('/sasdata/dwh/logs/FTPBWOFF.txt')
FTP_LOG = Path('/sasdata/dwh/logs/FTPBWOFF_LOG.txt')
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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Show transfers without connecting')
    args = parser.parse_args()
    transfer(FILES, dry_run=args.dry_run)
