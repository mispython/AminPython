#!/usr/bin/env python3
"""EIIWOF01 — Copy fail asal PIBB ke folder BACKUP dan WOFF."""

from pathlib import Path
import shutil

SOURCE = Path("/exdwh/host/ln/npl_hp_sasdata/pibb")
BACKUP = SOURCE / "backup"
WOFF = SOURCE / "woff"


def main():
    BACKUP.mkdir(exist_ok=True)
    WOFF.mkdir(exist_ok=True)

    # Copy fail sahaja; tidak termasuk subfolder.
    for file in SOURCE.iterdir():
        if file.is_file():
            shutil.copy2(file, BACKUP / file.name)
            shutil.copy2(file, WOFF / file.name)
            print(f"Copied: {file.name}")

    print("EIIWOF01 selesai.")


if __name__ == "__main__":
    main()


1                                                          The SAS System                          16:29 Thursday, November 19, 2026

1          ;*';*";*/;quit;run;
2          OPTIONS PAGENO=MIN;
3          %LET _CLIENTTASKLABEL='Program 2';
4          %LET _CLIENTPROCESSFLOWNAME='Standalone Not In Project';
5          %LET _CLIENTPROJECTPATH='';
6          %LET _CLIENTPROJECTPATHHOST='';
7          %LET _CLIENTPROJECTNAME='';
8          %LET _SASPROGRAMFILE='';
9          %LET _SASPROGRAMFILEHOST='';
10         
11         ODS _ALL_ CLOSE;
12         OPTIONS DEV=SVG;
13         GOPTIONS XPIXELS=0 YPIXELS=0;
14         %macro HTML5AccessibleGraphSupported;
15             %if %_SAS_VERCOMP_FV(9,4,4, 0,0,0) >= 0 %then ACCESSIBLE_GRAPH;
16         %mend;
17         FILENAME EGHTML TEMP;
18         ODS HTML5(ID=EGHTML) FILE=EGHTML
19             OPTIONS(BITMAP_MODE='INLINE')
20             %HTML5AccessibleGraphSupported
21             ENCODING='utf-8'
22             STYLE=HTMLBlue
23             NOGTITLE
24             NOGFOOTNOTE
25             GPATH=&sasworklocation
26         ;
NOTE: Writing HTML5(EGHTML) Body file: EGHTML
27         


28         data _null_;
29                 infile "
30         cd /sas/python/virt_edw;
31         source bin/activate;
32         python /stgsrcsys/host/holding/pas/EIIWOF01.py
33         " pipe;
34                 input;
35                 put _infile_;
36         run;

NOTE: The infile "cd /sas/python/virt_edw;source bin/activate;python /stgsrcsys/host/holding/pas/EIIWOF01.py" is:
      Pipe command="cd /sas/python/virt_edw;source bin/activate;python /stgsrcsys/host/holding/pas/EIIWOF01.py"

SyntaxError: Non-UTF-8 code starting with '\x97' in file /stgsrcsys/host/holding/pas/EIIWOF01.py on line 2, but no encoding declared
; see https://python.org/dev/peps/pep-0263/ for details
NOTE: 1 record was read from the infile "cd /sas/python/virt_edw;source bin/activate;python 
      /stgsrcsys/host/holding/pas/EIIWOF01.py".
      The minimum record length was 187.
      The maximum record length was 187.
NOTE: DATA statement used (Total process time):
      real time           1.52 seconds
      cpu time            0.00 seconds
      

37         
38         
39         %LET _CLIENTTASKLABEL=;
40         %LET _CLIENTPROCESSFLOWNAME=;
2                                                          The SAS System                          16:29 Thursday, November 19, 2026

41         %LET _CLIENTPROJECTPATH=;
42         %LET _CLIENTPROJECTPATHHOST=;
43         %LET _CLIENTPROJECTNAME=;
44         %LET _SASPROGRAMFILE=;
45         %LET _SASPROGRAMFILEHOST=;
46         
47         ;*';*";*/;quit;run;
48         ODS _ALL_ CLOSE;
49         
50         
51         QUIT; RUN;
52         
