# 01_update_original

## Input paths

| Input | Path |
|---|---|
| PBB NPL source members | /exdwh/host/ln/npl_hp_sasdata/pbb |
| PIBB NPL source members | /exdwh/host/ln/npl_hp_sasdata/pibb |
| PBB HPWOFF | /exdwh/host/ln/npl_hp_sasdata/pbb/hpwoff.sas7bdat |
| PIBB HPWOFF | /exdwh/host/ln/npl_hp_sasdata/pibb/hpwoff.sas7bdat |
| MIS (jobs 02, 14, HD) | /host_pq/loan/input/WRI2OFF_MIS.txt |
| LNNOTE (jobs 03, 07, 12) | /sas/ln/dwh/enrichment/enrh_ln_note_d26.sas7bdat |
| Previous balance (job 07) | /dwh/ln_ln/ln11426.sas7bdat |
| Exclusions (job 08) | /host_pq/loan/input/woff02.txt |
| Patch (job 11) | /host_pq/loan/input/woff03.txt |
| Success records (SFTPSUCC) | /host_pq/loan/input/WRI2OFF_LNOTES.txt |
| DRR control | /sasdata/dwh/control/ctl_dwh_sftp_info.sas7bdat |

Original NPL members: nplobal, wiis, waq, wsp2, iis, aq, sp2, iis11, sp211, wofftot (all .sas7bdat). Job 01 now copies HPWOFF for both banks as well. Backups use the relevant bank directory/backup. Initial working seed reads use those copies; later stages use prior-job Parquet outputs in the relevant bank directory/woff.

LNNOTE day suffix uses scheduled run date minus one day. The previous-balance filename ln11426.sas7bdat is the explicit file supplied by the user, configured as PREVIOUS_LOAN_FILE in each job 07; update that setting for a different snapshot/year. No separate lnnote.sas7bdat input is required.

## Text layouts restored from original SAS

- Job 08: WNAME at 61 length 30; ACCTNO at 91 length 10; first line included. Keep ACCTNO > 0, exclude matching accounts.
- EIIWOF11: first line included; ACCTNO at 91 length 10; WSPPL at 121, WRECOVER at 151, WSPPW at 181, each COMMA13.2. Only WSP2 patch is active in original Islamic SAS.
- EIAWOF11: FIRSTOBS=12 skips 11 report header lines. ACCTNO at 6 length 10; provision fields at 292, 317, 342, each COMMA13.2. IIS fields SUSPEND, RECOVER, RECC, IISPW, WOISUSP, WOIRECV, WOIRECC, WOIW at 92, 117, 142, 167, 192, 217, 242, 267, each COMMA13.2. Both WSP2 and WIIS patches are active. Keep ACCTNO > 0; retain only accounts already in the respective hardcode dataset.

The same woff03.txt path is used by separate bank runs; supply the layout matching that bank. Business selection and merge rules are retained.

## Output paths

| Kind | Islamic / EIIWOF | Conventional / EIAWOF |
|---|---|---|
| Working datasets | /exdwh/host/ln/npl_hp_sasdata/pibb/woff | /exdwh/host/ln/npl_hp_sasdata/pbb/woff |
| Job 01 backup | /exdwh/host/ln/npl_hp_sasdata/pibb/backup | /exdwh/host/ln/npl_hp_sasdata/pbb/backup |
| Reports and text extracts | /dwh/ftp/drr | /dwh/ftp/drr |

All generated CSV reports and job-02 TXT outputs go to /dwh/ftp/drr. Job-07 HPTXT1x.txt/HPTXT2x.txt and SFTPSUCC LNOTES_SUCCESSx.txt also use that directory. FTPBWOFF reads its text inputs there. Writing a report locally does not automatically upload it: only the supplied FTPBWOFF and SFTPSUCC jobs perform their specified transfers. The original job conditions and calculation rules are unchanged.

Shared report/extract filenames must be consumed before running the other bank's reports. Working datasets and backup files are now separated by bank. Initial seed reads use the relevant backup folder; subsequent jobs read x.parquet outputs from the relevant woff folder. Job 01 only copies original input files and does not generate working Parquet datasets.

Final outputs from job 14 (WIIS, WSP2, WAQ, WOFFTOT) and HD (HPWOFF) return to /exdwh/host/ln/npl_hp_sasdata/pibb or /pbb, without x suffix. Their SAS bridge files are under the destination bank directory/sas_bridge.

Export drivers export_<JOB>.sas are written under the relevant bank's woff folder. Python writes Parquet and prepares export scripts; actual SAS7BDAT files are generated/replaced only when these drivers run on the SAS server with UTF-8 encoding. Install dependencies with python -m pip install -r requirements.txt. Run controllers in their original sequence with --run-date YYYY-12-27 for reruns.

Each folder has 42 Python files. Copy one complete version, not a mixture. EIIWOF03/12 and EIAWOF03/12 call shared EIFMNP02 and supply their own bank settings. Shared EIFMNP02's direct defaults are PIBB, so normally invoke it through the appropriate controller. EIIWOF04/05/06/13 use EIIMNP03/06/07; EIAWOF04/05/06/13 use EIFMNP03/06/07. PBBLNFMT, PBBELF and NPLNTB are shared imports.

## DRR

FTPBWOFF runs after EIAWOF07 and sends /dwh/ftp/drr/HPTXT1x.txt and HPTXT2x.txt as WOFFHP1.TXT/WOFFHP2.TXT. SFTPSUCC follows conventional HD once the success source exists; it retains position 1 = '1' and position 81 != 'R', then sends HPWOffLoansRYYYYMMDD.TXT using its scheduler date. Both use HPCC/WRITTEN-OFF on DRR.

Connections are read from the control dataset above: unique HOST_DESC containing Data Report Repository (DRR), fields HOST_IP, SFTP_ID and SFTP_PW. Uses psftp in batch mode with cached host key or optional verified HOST_KEY. Batch/log files are /sasdata/dwh/logs/<JOB>.txt and <JOB>_LOG.txt. No passwords are printed in command errors. Use FTPBWOFF --dry-run or SFTPSUCC --prepare-only to avoid sending.

Input text is assumed ASCII-compatible with newline-delimited records. SFTPSUCC also supports explicit RECORD_LENGTH for fixed records. Transport encoding/line endings and live DRR access have not been verified. FTPWILNS, FTPWOLNS and FTPIWOFF appear in the supplied flow but their source JCL has not been supplied.

## Validation

Current changes passed syntax checks, evaluated input settings, dummy fixed-width parsing and merges (including EIA FIRSTOBS=12), and isolated HD output/export-driver routing checks in both versions. No production input was read or overwritten, no SAS driver executed, and no live SFTP transfer made. Full data-flow reconciliation against SAS remains outstanding.

Latest routing checks passed for 70 job configurations and eight final-output/export-driver combinations. All 84 Python files across both versions parse. Validation used temporary local paths; no live SAS or SFTP execution was performed.

Input-root cleanup: every job now uses its bank source directory as the NPL input root; job 02 and SFTPSUCC use /host_pq/loan/input. LOAN points to /sas/ln/dwh/enrichment and SASLN to /dwh/ln_ln. Explicit snapshot filenames remain unchanged. No legacy staging-system path remains in this version. Working output is allowed in the bank woff subdirectory; direct source writes remain limited to the existing final-output routes.
