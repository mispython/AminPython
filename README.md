# Version 1: update original NPL directory

Job 14 final outputs WIIS, WSP2, WAQ and WOFFTOT go back to the original bank directory:
- EIIWOF14: /exdwh/host/ln/npl_hp_sasdata/pibb
- EIAWOF14: /exdwh/host/ln/npl_hp_sasdata/pbb

Final filenames have NO x suffix: wiis.parquet, wsp2.parquet, waq.parquet, wofftot.parquet. Generated SAS exports replace the matching wiis.sas7bdat, wsp2.sas7bdat, waq.sas7bdat and wofftot.sas7bdat in that directory. Intermediate x files remain in holding.

The SAS bridge is created under the final bank directory's sas_bridge subfolder. The export_EIIWOF14.sas / export_EIAWOF14.sas driver remains in holding and includes these final export scripts. Python completion alone does not update the original SAS7BDAT files.

Both folders contain all 42 Python files plus requirements.txt. Choose ONE complete folder for a deployment; do not mix job files between versions.

EIIWOF uses PIBB input /exdwh/host/ln/npl_hp_sasdata/pibb.
EIAWOF uses PBB input /exdwh/host/ln/npl_hp_sasdata/pbb.
Jobs 01–13, text reports and intermediate x datasets keep their existing flow through /stgsrcsys/host/holding. Job 01 backups remain /stgsrcsys/host/uat/pas. EIIWOFHD remains unchanged because its source is the separate SAP.PIBB.NPL.WOFF library, not NPL.HP.SASDATA.

Run Islamic and conventional batches separately, as requested; the working and backup folders are shared. Install dependencies with python -m pip install -r requirements.txt. Run controllers in order using --run-date YYYY-12-27 for the intended year.

Python's default writes Parquet and generates SAS export scripts. Actual SAS7BDAT files are updated only when the generated export driver is executed on the SAS server with UTF-8 encoding and access to the destination. Run each export driver before its bridge files are overwritten by a later run.

Validation of this packaging change covers Python syntax, destination routing and generated driver paths using isolated temporary directories. No production data was read or updated, and no live SAS execution or full data-flow rerun was performed.


## Additional jobs from the supplied FTP/HD flow

- FTPBWOFF.py: run after EIAWOF07 and before another bank's job 07 overwrites shared extracts. Uploads holding/HPTXT1x.txt to HPCC/WRITTEN-OFF/WOFFHP1.TXT and HPTXT2x.txt to WOFFHP2.TXT. Only the active DRR destination is implemented; the commented CCD destination is not executed. The duplicate FTPBWOFF block is represented by one job.
- EIAWOFHD.py: run after EIAWOF14. Reads MIS and original HD/HPWOFF; excludes cost centres 3000–3999, 4043, 4048; keeps missing cost centres per NOT IN. Appends the original history after new rows and deduplicates by ACCTNO so new rows win. Produces hpwoffx in holding, like the existing EIIWOFHD. The original HD source library is SAP.PBB.NPL.WOFF, distinct from the job-14 NPL.HP.SASDATA library.
- SFTPSUCC.py: run after EIAWOFHD once the success source is available. Reads RBP2.B033.LN.WRI2.OFF.LNOTES as text records from this version's INPUT_ROOT. This is an additional TEXT input from the new JCL, not a SAS7BDAT table. Keeps records with byte 1 = '1' and byte 81 != 'R', preserving order and spaces. Writes holding/LNOTES_SUCCESSx.txt and uploads it as HPCC/WRITTEN-OFF/HPWOffLoansRYYYYMMDD.TXT. The date is the scheduler/run date, not the previous data date; pass --run-date YYYY-MM-DD when rerunning.
- EIIWOFHD.py already existed and was retained.

DRR transfers now follow the supplied PSFTP sample. Both jobs read /sasdata/dwh/control/ctl_dwh_sftp_info.sas7bdat and select the single row whose HOST_DESC contains Data Report Repository (DRR). HOST_IP, SFTP_ID and SFTP_PW supply the connection; no separate host/password config is required. This control path remains the sample's path in both versions, independently of the business-input directory.

FTPBWOFF and SFTPSUCC each write their own batch and log under /sasdata/dwh/logs/<JOB>.txt and <JOB>_LOG.txt. Destination is HPCC/WRITTEN-OFF, as in the original JCL. Files are sent directly from holding; /dwh/ftp/drr was the sample's report output path and is not required for these existing extracts.

Requires pandas and installed psftp. Transfers use batch mode with the existing PuTTY host-key cache, or the optional verified HOST_KEY fingerprint. Unknown keys fail instead of automatically accepting them. Unlike the sample's -be option, a failed batch command stops the transfer. Password-bearing command lines are not printed on failure. The supplied sample's password authentication is retained.

Validate without sending:
- python FTPBWOFF.py --dry-run
- python SFTPSUCC.py --run-date 2026-12-27 --prepare-only

The Linux text files are transferred byte-for-byte. The original Co:Z servercp and linerule variables were not supplied, so confirm target encoding/newline requirements before deployment. SFTPSUCC defaults to newline-delimited ASCII-compatible records. If the source is raw fixed-length records, set RECORD_LENGTH from its actual DCB; this produces LF-separated output. Do not feed raw EBCDIC or RDW-prefixed mainframe records without converting the transport format first.

The supplied flow also names FTPWILNS, FTPWOLNS and FTPIWOFF, but supplies no JCL for them; no implementations for these names were invented. They remain external dependencies of the full scheduler flow.

New-job checks passed in isolated temporary directories: record selection, trailing-space/newline preservation, invalid-record handling, dated remote filename, transfer-plan generation, missing-configuration failure, and conventional HD selection/new-row deduplication. No real SFTP connection or live SAS execution was performed.

PSFTP revision validated with a simulated SAS control table and mocked subprocess: DRR row selection, per-job batch/log names, remote paths, CRLF batch syntax and failure handling passed. No real DRR login or transfer was performed.
