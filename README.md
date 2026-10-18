# Run the 22 Python files directly

All settings are inside each job. No config file, JSON tracking file or INC folder is required. Set INPUT_ROOT and OUTPUT_ROOT near the top of each job if deployment paths differ. Input dataset bindings are listed in INPUT_DATASETS; SEED_INPUTS identifies datasets read from the job-01 copies in pas.

Defaults:

- Original input: /stgsrcsys/host/uat
- Initial copies: /stgsrcsys/host/uat/pas
- Processing output: /stgsrcsys/host/holding
- Run date: 27 December, Singapore time; report/data date: 26 December.

Install dependencies once:

```
python -m pip install -r requirements.txt
```

Run each job in its original order; each initializes its own inputs. On 27 December:

```
python EIIWOF01.py
python EIIWOF02.py
python EIIWOF03.py
```

Continue through EIIWOF14, plus EIIWOFHD. The wrapper jobs call the appropriate MNP programs. For a controlled rerun, add --run-date YYYY-12-27. There is no --config argument.

## Explicit input routing

- Job 01 copies the 11 required original SAS files unchanged to pas. It creates no datasets in holding and no tracking files.
- Job 03 / initial EIFMNP02 reads NPLOBAL, WIIS, WAQ and WSP2 from pas, and LNNOTE from the original input directory.
- IIS11 and SP211 always come from pas when read as working-library history.
- Job 12 reads NPLOBAL from pas, but WIIS/WAQ/WSP2 from the prior jobs' outputs in holding.
- Other working dataset reads use the specified x.parquet files in holding. Missing required outputs raise an error; there is no automatic fallback.
- NPLA, LOAN, SASLN and HD source reads continue to use their original SAS datasets.

No tracking file checks the year or completion of previous jobs. Run the complete chain against the intended year's snapshots in order; do not mix output files from different runs. Job 01 does not delete old holding outputs. Rerunning the full chain replaces the files it produces.

## Outputs

EIIWOF02 produces only woffhpx.parquet and woffhpx.txt (one ACCTNO per line, no header; a missing ACCTNO is a blank line). It does not produce CSV reports or SAS scripts. Other jobs retain their existing output behavior, including EIIWOF08's updated WOFFHP dataset.

Jobs requiring SAS7BDAT prepare typed bridge files and a driver named export_<JOB>.sas in holding, for example export_EIIWOF03.sas. Submit that job's driver on the SAS server with UTF-8 encoding after the Python job completes. No export_all.sas or JSON manifest is used. The driver only includes datasets written by that job invocation. If later jobs overwrite a dataset, use its latest producer's export and reconcile the SAS log before consuming the result. Do not run SAS export concurrently with Python writes.

Dummy Python flow tests passed. Live SAS execution and financial reconciliation against original SAS results remain required. Calculation/filter conditions were not changed for this settings/routing revision.
