//EIAWOF13  JOB MISEIS,EIFMNPL0,COND=(0,LT),CLASS=A,MSGCLASS=X,
//         NOTIFY=&SYSUID
//*
//LABEL    OUTPUT CLASS=K,
//         NAME='CIK ROSEDAH',
//         ROOM='22TH FLOOR',
//         BUILDING='MENARA PBB',
//         DEPT='HP CREDIT CONTROL DEPARTMENT',
//         ADDRESS=('MENARA PUBLIC BANK',
//         '146 JALAN AMPANG','50450 KUALA LUMPUR'),
//         DEST=S1.LOCAL
//**********************************************************************
//EIFMNP03 EXEC SAS609,REGION=6M,WORK='120000,8000'
//PGM      DD DSN=SAP.BNM.PROGRAM,DISP=SHR
//NPL      DD DSN=SAP.PBB.NPL.HP.SASDATA.WOFF,DISP=OLD
//*SASLIST  DD SYSOUT=(,),OUTPUT=(*.LABEL)
//SYSIN    DD DSN=SAP.BNM.PROGRAM(EIFMNP03),DISP=SHR
//**********************************************************************
//EIFMNP06 EXEC SAS609,REGION=6M,WORK='120000,8000'
//PGM      DD DSN=SAP.BNM.PROGRAM,DISP=SHR
//NPL      DD DSN=SAP.PBB.NPL.HP.SASDATA.WOFF,DISP=OLD
//*SASLIST  DD SYSOUT=(,),OUTPUT=(*.LABEL)
//SYSIN    DD DSN=SAP.BNM.PROGRAM(EIFMNP06),DISP=SHR
//**********************************************************************
//EIFMNP07 EXEC SAS609,REGION=6M,WORK='120000,8000'
//PGM      DD DSN=SAP.BNM.PROGRAM,DISP=SHR
//NPL      DD DSN=SAP.PBB.NPL.HP.SASDATA.WOFF,DISP=OLD
//*SASLIST  DD SYSOUT=(,),OUTPUT=(*.LABEL)
//SYSIN    DD DSN=SAP.BNM.PROGRAM(EIFMNP07),DISP=SHR
//**********************************************************************
//*
//






*+--------------------------------------------------------------+
 |  PROGRAM : EIFMNP03                                          |
 |  DATE    : 12.03.98                                          |
 |  MODIFY  : ESMR 2004-720, 2004-579, 2006-1048                |
 |  REPORT  : MOVEMENTS OF INTEREST IN SUSPENSE FOR THE MONTH   |
 |            ENDING                                            |
 +--------------------------------------------------------------+;
OPTIONS NOCENTER YEARCUTOFF=1950;
*;
%INC PGM(PBBLNFMT);
%INC PGM(PBBELF);
*;
PROC FORMAT;
   VALUE LNTYP 128,130,983             = 'HPD AITAB'
               700,705,380,381,993,996,
               720,725                 = 'HPD CONVENTIONAL'
               200-299                 = 'HOUSING LOANS'
               OTHER   = 'OTHERS';
*;
*------------------------------------------------*
*  MACRO FOR CALCULATING NEXT BLDATE             *
*------------------------------------------------*;
%MACRO DCLVAR;
   RETAIN D1-D12 31 D4 D6 D9 D11 30;
   ARRAY LDAY D1-D12;
%MEND DCLVAR;
*;
%MACRO NXTBLDT;
   DD = DAY(ISSDTE);
   MM = MONTH(BLDATE) + 1;
   YY = YEAR(BLDATE);
   IF MM > 12 THEN DO;
      MM = 1; YY + 1;
   END;
   IF MM = 2 THEN
      IF MOD(YY,4) = 0 THEN D2 = 29;
      ELSE D2 = 28;
   IF DD > LDAY(MM) THEN DD = LDAY(MM);
   BLDATE = MDY(MM,DD,YY);
%MEND NXTBLDT;
*;
  /*
*------------------------------------------------*
*  MACRO FOR CALCULATING OVERDUE INTEREST        *
*------------------------------------------------*;
%MACRO OVINT(I);
   IF LOANTYPE = 705 THEN DO;
      IF NOTETERM > 12 THEN TERM = 12;
      ELSE TERM = NOTETERM;
      TRATE = NOTETERM*INTRATE;
      APR = TRATE*(300*TERM+TRATE)/
            ((NOTETERM*TRATE)+(150*TERM*(NOTETERM+1)))*12/TERM;
      RATE = (APR+1)/100;
   END;
   ELSE RATE = 8/100;
   BILAMT = BILPAY;
   BILAMTL = ORGBAL-BILPAY*(NOTETERM-1);
   OITEMP = 0; BLDTE = BLDATE;
   DO REMMTH = REMMTH&I TO REMMTH2 BY -1;
      IF REMMTH = 0 THEN AMT = BILAMTL;
      ELSE AMT = BILAMT;
      %NXTBLDT
      OITEMP + AMT*RATE*(REPTDATE-BLDATE)/365;
   END;
   BLDATE = BLDTE;
%MEND OVINT;
*; */
DATA REPTDATE;
   SET NPL.REPTDATE;
   IF MONTH(REPTDATE) = 1 THEN MM1 = 12;
   ELSE MM1 = MONTH(REPTDATE)-1;
   CALL SYMPUT('RDATE',PUT(REPTDATE,WORDDATX18.));
   CALL SYMPUT('REPTMON',PUT(MONTH(REPTDATE),Z2.));
   CALL SYMPUT('PREVMON',PUT(MM1,Z2.));
RUN;
*;
*------------------------------------------------*
*  MERGE WITH WRITTEN OFF ACCOUNT                *
*------------------------------------------------*;
PROC SORT DATA=NPL.LOAN&REPTMON;BY ACCTNO;
PROC SORT DATA=NPL.WIIS;BY ACCTNO;
DATA LOANWOFF;
   MERGE NPL.LOAN&REPTMON NPL.WIIS (IN=AA DROP=NOTENO NTBRCH);
   BY ACCTNO;
   IF LOANTYPE IN (380,381) THEN FEEAMT = FEETOT2;
   IF AA THEN WRITEOFF = 'Y';ELSE WRITEOFF = 'N';
   IF LOANTYPE IN (983,993) THEN WDOWNIND = 'N';
   IF IISP = . THEN IISP = 0;
   IF OIP = . THEN OIP = 0;
   IF EARNTERM IN (0,.) THEN EARNTERM = NOTETERM;
RUN;
*------------------------------------------------*
*  CALCULATE IIS FOR EXISTING NPL ACCOUNTS       *
*------------------------------------------------*;
DATA LOAN1;
   KEEP BRANCH NTBRCH ACCTNO NOTENO NAME NETPROC CURBAL BORSTAT DAYS
        IIS UHC NETBAL IISP SUSPEND RECOVER RECC IISPW OIP OISUSP OI
        OIRECV OIRECC OIW TOTIIS LOANTYP EXIST COSTCTR PENDBRH USER5
        WDOWNIND RESCHEIND ACCRUAL;
   LENGTH LOANTYP $20;
   RETAIN STMTH 1 STYR;
   %DCLVAR
  * SET NPL.LOAN&REPTMON;
   SET LOANWOFF;
   IF _N_ = 1 THEN DO;
      SET REPTDATE;
      STYR = YEAR(REPTDATE);
   END;
   IF EXIST = 'Y';
   IIS = 0; SUSPEND = 0; UHC = 0; OI = 0; OISUSP = 0; RECOVER = 0;
   OIRECV = 0; OIRECC=0; OIW = 0;
   IF IISP = . THEN IISP = 0;
   IF OIP = . THEN OIP = 0;
   IF IISPW = . THEN IISPW = 0;
   IF WRITEOFF = 'Y' AND WDOWNIND ^= 'Y' THEN BORSTAT ='W';
   IF BLDATE > 0 & TERMCHG > 0 THEN DO;
      IF DAYS >  89 | BORSTAT IN ('F','R','I')
      OR (USER5 = 'N' AND LOANTYPE NOT IN (983,993)) THEN DO;
         REMMTH1 = EARNTERM - ((YEAR(BLDATE) - YEAR(ISSDTE))*12 +
                   MONTH(BLDATE) - MONTH(ISSDTE) + 1);
         REMMTH2 = EARNTERM - ((YEAR(REPTDATE) - YEAR(ISSDTE))*12 +
                   MONTH(REPTDATE) - MONTH(ISSDTE) + 1);
         REMMTHS = EARNTERM - ((STYR - YEAR(ISSDTE))*12 +
                   STMTH - MONTH(ISSDTE) + 1);
         IF REMMTH2 < 0 THEN REMMTH2 = 0;
         IF LOANTYPE IN (128,130) THEN REMMTH1 = REMMTH1 - 3;
         ELSE REMMTH1 = REMMTH1 - 1;
         IF REMMTH1 >= REMMTH2 THEN DO;
            DO REMMTH = REMMTH1 TO REMMTH2 BY -1;
               IIS + 2*(REMMTH+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
            END;
         END;
       *  OI = FEETOT2;
         OI = SUM(FEETOT2,(-1)*FEEAMTA,FEEAMT5);
         DO REMMTH = REMMTHS TO REMMTH2 BY -1;
            SUSPEND + 2*(REMMTH+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
         END;
         IF LOANTYPE NOT IN (128,130) THEN DO;
       OISUSP = SUM(FEEAMT,(-1)*FEEAMTA,FEEAMT5);
         END;
         IF REMMTH2 > 0 THEN
            UHC = REMMTH2*(REMMTH2+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
      END;
   END;
   ELSE IF DAYS >  89 | BORSTAT IN ('F','R','I')
   OR (USER5 = 'N' AND LOANTYPE NOT IN (983,993)) THEN DO;
       OI = SUM(FEETOT2,(-1)*FEEAMTA,FEEAMT5);
       OISUSP = SUM(FEEAMT,(-1)*FEEAMTA,FEEAMT5);
   END;
   IF CURBAL = . THEN CURBAL = 0;
   NETBAL = CURBAL - UHC;
   IF NETBAL <= IISP THEN
      IF DAYS >  89 | BORSTAT IN ('F','R','I')
      OR USER5 = 'N' THEN
         IIS = NETBAL;
   IF BORSTAT = 'W' THEN DO;
      IISPW = IISP; OIW = OIP;
   END;
   ELSE DO;
      RECOVER = IISP + SUSPEND - IIS;
      IF RECOVER < 0 THEN DO;
         SUSPEND = SUSPEND - RECOVER;
         RECOVER = 0;
      END;
      IF RECOVER > IISP THEN DO;
         RECC = RECOVER - IISP;
         RECOVER = IISP;
      END;
      IF LOANTYPE NOT IN (128,130) THEN DO;
         OIRECV = OIP - OI;
         IF OIRECV < 0 THEN DO;
            OISUSP = OISUSP - OIRECV;
            OIRECV = 0;
         END;
         IF OISUSP LT 0 THEN OIRECV = OIRECV - OISUSP;
         IF OIRECV > OIP THEN DO;
            OIRECC = OIRECV - OIP;
            OIRECV = OIP;
         END;
      END;
   END;
   IF TERMCHG = 0 THEN DO;
      IF BORSTAT IN ('R') THEN NETEXP = CURBAL - IISP - MARKETVL;
         ELSE NETEXP = CURBAL - IISP;
      IF (NETEXP > 0 & DAYS > 89) | BORSTAT IN ('R') THEN DO;
         IIS = RECOVER; RECOVER = 0;
         OI = SUM(FEETOT2,(-1)*FEEAMTA,FEEAMT5);OIRECV = 0;
      END;
   END;
   IF LOANTYPE IN (720,725) THEN IIS = ACCRUAL;
   OISUSP = OIRECV + OIRECC + OIW - OIP + OI;
   IF OISUSP LT 0 THEN OIRECV = OIRECV - OISUSP;
   IF OIRECV > OIP THEN DO;
      OIRECC = OIRECV - OIP;
      OIRECV = OIP;
   END;
   OISUSP = OIRECV + OIRECC + OIW - OIP + OI;
   BRANCH = PUT(NTBRCH,BRCHCD.)||' '||PUT(NTBRCH,Z3.);
   LOANTYP = PUT(LOANTYPE,LNTYP.);
   IF WRITEOFF = 'Y' THEN DO;
      SUSPEND = WSUSPEND;
      OISUSP  = WOISUSP;
      IF WDOWNIND ^= 'Y' THEN DO;
         RECOVER = WRECOVER;
         RECC    = WRECC;
         OIRECV  = WOIRECV;
         OIRECC  = WOIRECC;
         IIS = 0;
         IISPW   = SUM(IISP,SUSPEND,(-1)*RECOVER,(-1)*RECC);
         OI = 0;
         OIW     = SUM(OIP,OISUSP,(-1)*OIRECV,(-1)*OIRECC);
      END;
      ELSE DO;
         OISUSP  = WOISUSP;
         IISPW   = WIISPW;
         IIS     = SUM(IISP,SUSPEND,(-1)*RECOVER,(-1)*RECC,(-1)*IISPW);
         IF IIS < 0 THEN RECOVER = 0;
         IIS     = SUM(IISP,SUSPEND,(-1)*RECOVER,(-1)*RECC,(-1)*IISPW);
         OIW     = WOIW;
         OI      = SUM(OIP,OISUSP,(-1)*OIRECV,(-1)*OIRECC,(-1)*OIW);
         IF OI < 0 THEN DO;
            OIRECV = 0;
            OIRECC = 0;
         END;
         OI      = SUM(OIP,OISUSP,(-1)*OIRECV,(-1)*OIRECC,(-1)*OIW);
      END;
      IF OIP = . THEN OIP = 0;IF IISP = . THEN IISP = 0;
      IF SUSPEND = . THEN SUSPEND = 0;IF OISUSP = . THEN OISUSP = 0;
      IF RECOVER = . THEN RECOVER = 0;IF OIRECV = . THEN OIRECV = 0;
      IF RECC = . THEN RECC = 0;IF OIRECC = . THEN OIRECC = 0;
   END;
   TOTIIS = IIS + OI;

 IF RESCHEIND = 'Y' THEN DO;
      SUSPEND = WSUSPEND;
      OISUSP  = WOISUSP;
      RECOVER = WRECOVER;
      RECC    = WRECC;
      OIRECV  = WOIRECV;
      OIRECC  = WOIRECC;
      IIS     = SUM(IISP,SUSPEND,(-1)*RECOVER,(-1)*RECC,(-1)*IISPW);
      OI      = SUM(OIP,OISUSP,(-1)*OIRECV,(-1)*OIRECC,(-1)*OIW);
      TOTIIS = IIS + OI;
      END;
*;
*------------------------------------------------*
*  CALCULATE IIS FOR CURRENT NPL ACCOUNTS        *
*------------------------------------------------*;
DATA LOAN2;
   KEEP BRANCH NTBRCH ACCTNO NOTENO NAME NETPROC CURBAL BORSTAT DAYS
        IIS UHC NETBAL IISP SUSPEND RECOVER RECC IISPW OIP OISUSP OI
        OIRECV OIRECC OIW TOTIIS LOANTYP EXIST COSTCTR PENDBRH USER5
        WDOWNIND RESCHEIND ACCRUAL;
   LENGTH LOANTYP $20;
   %DCLVAR
   SET LOANWOFF;
 * SET NPL.LOAN&REPTMON;
   IF _N_ = 1 THEN SET REPTDATE;
   IF EXIST ^= 'Y';
   IIS = 0; UHC = 0; OI = 0;
   IF WRITEOFF = 'Y' AND WDOWNIND ^= 'Y' THEN BORSTAT ='W';
   IF BLDATE > 0 & TERMCHG > 0 OR (USER5 = 'N' AND
   LOANTYPE NOT IN (983,993)) THEN DO;
      REMMTH1 = EARNTERM - ((YEAR(BLDATE) - YEAR(ISSDTE))*12 +
                MONTH(BLDATE) - MONTH(ISSDTE) + 1);
      REMMTH2 = EARNTERM - ((YEAR(REPTDATE) - YEAR(ISSDTE))*12 +
                MONTH(REPTDATE) - MONTH(ISSDTE) + 1);
      IF REMMTH2 < 0 THEN REMMTH2 = 0;
      IF LOANTYPE IN (128,130) THEN
           REMMTH1 = REMMTH1 - 3;
      ELSE REMMTH1 = REMMTH1 - 1;
      IF REMMTH1 >= REMMTH2 THEN DO;
         DO REMMTH = REMMTH1 TO REMMTH2 BY -1;
            IIS + 2*(REMMTH+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
         END;
      END;
      IF REMMTH2 > 0 THEN
         UHC = REMMTH2*(REMMTH2+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
   END;
   ELSE DO;
      REMMTH2 = EARNTERM - ((YEAR(REPTDATE) - YEAR(ISSDTE))*12 +
                MONTH(REPTDATE) - MONTH(ISSDTE) + 1);
      IF REMMTH2 < 0 THEN REMMTH2 = 0;
      IF REMMTH2 > 0 THEN
         UHC = REMMTH2*(REMMTH2+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
   END;
   OI = SUM(FEETOT2,(-1)*FEEAMTA,FEEAMT5);
   IF LOANTYPE IN (720,725) THEN IIS = ACCRUAL;
   SUSPEND = IIS;
   OISUSP = OI;
   NETBAL = CURBAL - UHC;
   IF WRITEOFF = 'Y' THEN DO;
      SUSPEND = WSUSPEND;
      OISUSP  = WOISUSP;
      IF WDOWNIND ^= 'Y' THEN DO;
         RECOVER = WRECOVER;
         RECC    = WRECC;
         OIRECV  = WOIRECV;
         OIRECC  = WOIRECC;
         IIS = 0;
         IISPW   = SUM(IISP,SUSPEND,(-1)*RECOVER,(-1)*RECC);
         OI = 0;
         OIW     = SUM(OIP,OISUSP,(-1)*OIRECV,(-1)*OIRECC);
      END;
      ELSE DO;
         OISUSP  = WOISUSP;
         IISPW   = WIISPW;
         IIS     = SUM(IISP,SUSPEND,(-1)*RECOVER,(-1)*RECC,(-1)*IISPW);
         IF IIS < 0 THEN RECOVER = 0;
         IIS     = SUM(IISP,SUSPEND,(-1)*RECOVER,(-1)*RECC,(-1)*IISPW);
         OIW     = WOIW;
         OI      = SUM(OIP,OISUSP,(-1)*OIRECV,(-1)*OIRECC,(-1)*OIW);
         IF OI < 0 THEN DO;
            OIRECV = 0;
            OIRECC = 0;
         END;
         OI      = SUM(OIP,OISUSP,(-1)*OIRECV,(-1)*OIRECC,(-1)*OIW);
      END;
      IF OIP = . THEN OIP = 0;IF IISP = . THEN IISP = 0;
      IF SUSPEND = . THEN SUSPEND = 0;IF OISUSP = . THEN OISUSP = 0;
      IF RECOVER = . THEN RECOVER = 0;IF OIRECV = . THEN OIRECV = 0;
      IF RECC = . THEN RECC = 0;IF OIRECC = . THEN OIRECC = 0;
   END;
   TOTIIS = IIS + OI;
   BRANCH = PUT(NTBRCH,BRCHCD.)||' '||PUT(NTBRCH,Z3.);
   LOANTYP = PUT(LOANTYPE,LNTYP.);

 IF RESCHEIND = 'Y' THEN DO;
      SUSPEND = WSUSPEND;
      OISUSP  = WOISUSP;
      RECOVER = WRECOVER;
      RECC    = WRECC;
      OIRECV  = WOIRECV;
      OIRECC  = WOIRECC;
      IIS     = SUM(IISP,SUSPEND,(-1)*RECOVER,(-1)*RECC,(-1)*IISPW);
      OI      = SUM(OIP,OISUSP,(-1)*OIRECV,(-1)*OIRECC,(-1)*OIW);
      TOTIIS = IIS + OI;
      END;
*;
*------------------------------------------------*
*  COMPARE PREVIOUS MONTH NPL ACCOUNTS (MAY 05)  *
*------------------------------------------------*;
%MACRO MONTHLY;
   %IF "&REPTMON" EQ "01" %THEN %DO;
      DATA LOAN1;
         SET LOAN1;
         IISPCUM = 0;
         OIPCUM = 0;
         POI = 0;
      RUN;
      DATA LOAN2;
         SET LOAN2;
         IISPCUM = 0;
         OIPCUM = 0;
         POI = 0;
      RUN;
   %END;
   %ELSE %DO;
      PROC SORT DATA=NPL.IIS&PREVMON (DROP=POI
         RENAME=(DAYS=PDAYS SUSPEND=PSUSPEND OISUSP=POISUSP
                 IISP=PIISP OIP=POIP OI=POI RECC=PRECC
                 OIRECC=POIRECC RECOVER=PRECOVER OIRECV=POIRECV))
         OUT=IISPREV NODUPKEY;
      BY ACCTNO NOTENO; RUN;

      DATA IISPREV;
         SET IISPREV;
             IF LOANTYPE IN (128,130,131,132,380,381,390,
                             700,705,720,725,983,993,996)
             AND PAIDIND='P' THEN DO;
             %INC PGM(NPLNTB);
             END;
         BRANCH = PUT(NTBRCH,BRCHCD.)||' '||PUT(NTBRCH,Z3.);
         IF PDAYS = . THEN PDAYS = 0;
         IF PSUSPEND = . THEN PSUSPEND = 0;
         IF POISUSP = . THEN POISUSP = 0;
         IF PIISP = . THEN PIISP = 0;
         IF POIP = . THEN POIP = 0;
         IF POI = . THEN POI = 0;
      RUN;
      ********************
      *** EXISTING NPL ***
      ********************;
      PROC SORT DATA=LOAN1; BY ACCTNO; RUN;
      DATA LOAN1(DROP=PDAYS PSUSPEND POISUSP PIISP POIP PRECC
                 POIRECC PRECOVER POIRECV);
         MERGE IISPREV(IN=B) LOAN1(IN=A);
         BY ACCTNO;
         IF ((A AND B) OR (B AND NOT A)) AND EXIST = 'Y';

         *** A/C SETTLE FOR EXISTING NPL ***;
         IF ((B AND NOT A) OR (CURBAL LE 0 AND POI LE 0)) AND
            BORSTAT NOT IN ('F','I','R','W','S') THEN DO;
            IISP=PIISP;
            RECOVER=IISP;
            SUSPEND=PSUSPEND;
            RECC=SUSPEND;
            OIP=POIP;
            OIRECV=OIP;
            OISUSP=POISUSP;
            OIRECC=OISUSP;
            CURBAL=0;
            NETBAL=0;
            DAYS=0;
            OI  = SUM(OIP,OISUSP,(-1)*OIRECV,(-1)*OIRECC,(-1)*OIW);
            IIS = SUM(IISP,SUSPEND,(-1)*RECOVER,(-1)*RECC,(-1)*IISPW);
            TOTIIS = IIS + OI;
            OUTPUT;
         END;
         ELSE DO;
            IF BORSTAT IN ('W') OR RESCHEIND='Y' THEN DO;
               OUTPUT;
            END;
            ELSE DO;
               IF (A AND B) THEN DO;
                  *** CONTINUE PERFORMING ***;
                  IF (DAYS LT 90 AND PDAYS LT 90) THEN DO;
                     SUSPEND=IIS;
                  IF USER5 = 'N' AND IIS < IISP THEN DO;
                     SUSPEND = 0;
                     RECOVER = IISP - IIS;
                  RECC = 0;
                  END;
                  IF USER5 = 'N' AND IIS >= IISP THEN DO;
                     SUSPEND = IIS - IISP;
                     RECOVER = 0;
                     RECC = 0;
                  END;
                  IF USER5 = 'N' AND IISP = 0 THEN DO;
                     SUSPEND = IIS;
                     RECC = IIS - SUSPEND;
                  END;
                  IF USER5 = 'N' AND OI < OIP THEN DO;
                     OISUSP = 0;
                     OIRECV = OIP - OI;
                     OIRECC = 0;
                  END;
                  IF USER5 = 'N' AND OI >= OIP THEN DO;
                     OISUSP = OI - OIP;
                     OIRECV = 0;
                     OIRECC = 0;
                  END;
                  IF USER5 = 'N' AND OIP = 0 THEN DO;
                     OISUSP = OI;
                     OIRECC = OI - OISUSP;
                  END;
                  OUTPUT;
                  END;
                  *** TURN PERFORMING ***;
                  IF (DAYS LT 90 AND PDAYS GE 90) THEN DO;
                     IF BORSTAT NOT IN ('F','I','R') THEN DO;
                        SUSPEND = PSUSPEND;
                        RECC    = PSUSPEND;
                        OISUSP  = POISUSP;
                        OIRECC  = POISUSP;
                        TOTIIS = IIS + OI;
                     END;
                     IF USER5 = 'N' AND IIS < IISP THEN DO;
                        SUSPEND = 0;
                        RECOVER = IISP - IIS;
                        RECC = 0;
                     END;
                     IF USER5 = 'N' AND IIS >= IISP THEN DO;
                        SUSPEND = IIS - IISP;
                        RECOVER = 0;
                        RECC = 0;
                     END;
                     IF USER5 = 'N' AND IISP = 0 THEN DO;
                        SUSPEND = IIS;
                        RECC = IIS - SUSPEND;
                     END;
                     IF USER5 = 'N' AND OI < OIP THEN DO;
                        OISUSP = 0;
                        OIRECV = OIP - OI;
                        OIRECC = 0;
                     END;
                     IF USER5 = 'N' AND OI >= OIP THEN DO;
                        OISUSP = OI - OIP;
                        OIRECV = 0;
                        OIRECC = 0;
                     END;
                     IF USER5 = 'N' AND OIP = 0 THEN DO;
                        OISUSP = OI;
                        OIRECC = OI - OISUSP;
                     END;
                     OUTPUT;
                  END;
                  *** TURN NPL FR PERFORMING ***;
                  IF DAYS GE 90 AND PDAYS LT 90 THEN DO;
                     IF BORSTAT NOT IN ('F','I','R') THEN DO;
                        RECC = PRECC;
                        RECOVER = PRECOVER;
                        SUSPEND = SUM(IIS,IISP,(-1)*RECOVER,RECC);
                        IF SUSPEND < 0 THEN DO;
                           RECOVER = SUM(RECOVER,(-1)*SUSPEND);
                           SUSPEND = 0;
                           IF RECOVER GT IISP THEN DO;
                              RECC = SUM(RECC,RECOVER-IISP);
                           END;
                        END;
                        OIRECC = POIRECC;
                        OIRECV = POIRECV;
                        OISUSP = SUM(OI,OIP,(-1)*OIRECV,OIRECC);
                        IF OISUSP < 0 THEN DO;
                           OIRECV = SUM(OIRECV,(-1)*OISUSP);
                           OISUSP = 0;
                           IF OIRECV GT OIP THEN DO;
                              OIRECC = SUM(OIRECC,OIRECV-OIP);
                           END;
                        END;
                        TOTIIS = IIS + OI;
                     END;
                     IF USER5 = 'N' AND IIS < IISP THEN DO;
                        SUSPEND = 0;
                        RECOVER = IISP - IIS;
                        RECC = 0;
                     END;
                     IF USER5 = 'N' AND IIS >= IISP THEN DO;
                        SUSPEND = IIS - IISP;
                        RECOVER = 0;
                        RECC = 0;
                     END;
                     IF USER5 = 'N' AND IISP = 0 THEN DO;
                        SUSPEND = IIS;
                        RECC = IIS - SUSPEND;
                     END;
                     IF USER5 = 'N' AND OI < OIP THEN DO;
                        OISUSP = 0;
                        OIRECV = OIP - OI;
                        OIRECC = 0;
                     END;
                     IF USER5 = 'N' AND OI >= OIP THEN DO;
                        OISUSP = OI - OIP;
                        OIRECV = 0;
                        OIRECC = 0;
                     END;
                     IF USER5 = 'N' AND OIP = 0 THEN DO;
                        OISUSP = OI;
                        OIRECC = OI - OISUSP;
                     END;
                     OUTPUT;
                  END;
                  *** CONTINUE NPL ***;
                  IF DAYS GE 90 AND PDAYS GE 90 THEN DO;
                     IF BORSTAT NOT IN ('F','I','R') THEN DO;
                        RECOVER = PRECOVER;
                        RECC = PRECC;
                        SUSPEND = SUM(IIS,(-1)*IISP,RECOVER,RECC);
                        IF SUSPEND < 0 THEN DO;
                           RECOVER = SUM(RECOVER,(-1)*SUSPEND);
                           SUSPEND = 0;
                           IF RECOVER GT IISP THEN DO;
                              RECC = SUM(RECC,RECOVER,(-1)*IISP);
                           END;
                        END;
                        OIRECV = POIRECV;
                        OIRECC = POIRECC;
                        OISUSP = SUM(OI,(-1)*OIP,OIRECV, OIRECC);
                        IF OISUSP < 0 THEN DO;
                           OIRECV = SUM(OIRECV,(-1)*OISUSP);
                           OISUSP = 0;
                           IF OIRECV  GT OIP THEN DO;
                              OIRECC = SUM(OIRECC,OIRECV,(-1)*OIP);
                           END;
                        END;
                        TOTIIS = IIS + OI;
                     END;
                     OUTPUT;
                  END;
               END;
            END;
         END;
      RUN;
      *******************
      *** CURRENT NPL ***
      *******************;
      PROC SORT DATA=NPL.PLOAN&REPTMON OUT=PLOAN
         (KEEP=ACCTNO NOTENO CURBAL DAYS BORSTAT NTBRCH COSTCTR);
         BY ACCTNO;
      RUN;
      DATA IISPREV;
         MERGE IISPREV(IN=A) PLOAN(IN=B);
         BY ACCTNO;
         IF PIISP EQ 0 AND POIP EQ 0 AND EXIST NE 'Y';
         BRANCH = PUT(NTBRCH,BRCHCD.)||' '||PUT(NTBRCH,Z3.);
      RUN;

      PROC SORT DATA=LOAN2; BY ACCTNO NOTENO; RUN;
      DATA LOAN2(DROP=PDAYS PSUSPEND POISUSP PIISP POIP PRECC
                 POIRECC PRECOVER POIRECV);
         MERGE IISPREV(IN=B) LOAN2(IN=A);
         BY ACCTNO;
         IF (B AND NOT A) THEN DO;
            *** A/C SETTLE FOR EXISTING NPL ***;
               IISP=PIISP;
               RECOVER=IISP;
               SUSPEND=PSUSPEND;
               RECC=SUSPEND;
               OIP=POIP;
               OIRECV=OIP;
               OISUSP=POISUSP;
               OIRECC=OISUSP;
               CURBAL=0;
               NETBAL=0;
               DAYS=0;
               OI  = SUM(OIP,OISUSP,(-1)*OIRECV,(-1)*OIRECC,(-1)*OIW);
              IIS = SUM(IISP,SUSPEND,(-1)*RECOVER,(-1)*RECC,(-1)*IISPW);
               TOTIIS = IIS + OI;
               OUTPUT;
         END;

         *** NEW NPL FOR THE MTH ***;
         IF (A AND NOT B) AND
            (DAYS GE 90 OR BORSTAT IN ('F','I','R','W') OR USER5='N')
            THEN OUTPUT;

         IF BORSTAT IN ('W') OR RESCHEIND='Y' THEN OUTPUT;
         IF (A AND B) AND BORSTAT NOT IN ('W') THEN DO;
            *** CONTINUE PERFORMING ***;
            IF (DAYS LT 90 AND PDAYS LT 90) THEN DO;
               IF BORSTAT NOT IN ('F','I','R') THEN DO;
                  SUSPEND = PSUSPEND;
                  RECC    = PSUSPEND;
                  OISUSP  = POISUSP;
                  OIRECC  = POISUSP;
                  TOTIIS = IIS + OI;
               END;
               IF USER5 = 'N' AND IIS < IISP THEN DO;
                  SUSPEND = 0;
                  RECOVER = IISP - IIS;
                  RECC = 0;
               END;
               IF USER5 = 'N' AND IIS >= IISP THEN DO;
                  SUSPEND = IIS - IISP;
                  RECOVER = 0;
                  RECC = 0;
               END;
               IF USER5 = 'N' AND IISP = 0 THEN DO;
                  SUSPEND = IIS;
                  RECC = IIS - SUSPEND;
               END;
               IF USER5 = 'N' AND OI < OIP THEN DO;
                  OISUSP = 0;
                  OIRECV = OIP - OI;
                  OIRECC = 0;
               END;
               IF USER5 = 'N' AND OI >= OIP THEN DO;
                  OISUSP = OI - OIP;
                  OIRECV = 0;
                  OIRECC = 0;
               END;
               IF USER5 = 'N' AND OIP = 0 THEN DO;
                  OISUSP = OI;
                  OIRECC = OI - OISUSP;
               END;
               ELSE DO;
                  SUSPEND = SUM(SUSPEND,RECC);
                  OISUSP = SUM(OISUSP,OIRECC);
               END;
              OUTPUT;
            END;

            *** TURN PERFORMING FR NPL ***;
            IF (DAYS LT 90 AND PDAYS GE 90) THEN DO;
               IF BORSTAT NOT IN ('F','I','R') THEN DO;
                  SUSPEND = PSUSPEND;
                  RECC    = PSUSPEND;
                  OISUSP  = POISUSP;
                  OIRECC  = POISUSP;
                  OI  = SUM(OIP,OISUSP,(-1)*OIRECV,
                            (-1)*OIRECC,(-1)*OIW);
                  IIS = SUM(IISP,SUSPEND,(-1)*RECOVER,
                            (-1)*RECC,(-1)*IISPW);
                  TOTIIS = IIS + OI;
               END;
               IF USER5 = 'N' AND IIS < IISP THEN DO;
                  SUSPEND = 0;
                  RECOVER = IISP - IIS;
                  RECC = 0;
               END;
               IF USER5 = 'N' AND IIS >= IISP THEN DO;
                  SUSPEND = IIS - IISP;
                  RECOVER = 0;
                  RECC = 0;
               END;
               IF USER5 = 'N' AND IISP = 0 THEN DO;
                  SUSPEND = IIS;
                  RECC = IIS - SUSPEND;
               END;
               IF USER5 = 'N' AND OI < OIP THEN DO;
                  OISUSP = 0;
                  OIRECV = OIP - OI;
                  OIRECC = 0;
               END;
               IF USER5 = 'N' AND OI >= OIP THEN DO;
                  OISUSP = OI - OIP;
                  OIRECV = 0;
                  OIRECC = 0;
               END;
               IF USER5 = 'N' AND OIP = 0 THEN DO;
                  OISUSP = OI;
                  OIRECC = OI - OISUSP;
               END;
               OUTPUT;
            END;

            *** TURN NPL FR PERFORMING ***;
            IF DAYS GE 90 AND PDAYS LT 90 THEN DO;
               IF BORSTAT NOT IN ('F','I','R') THEN DO;
                  RECC    = SUM(RECC,PRECC);
                  SUSPEND = SUM(SUSPEND,RECC);
                  OIRECC  = SUM(OIRECC,POIRECC);
                  OISUSP  = SUM(OISUSP,OIRECC);
                  TOTIIS = IIS + OI;
               END;
               IF USER5 = 'N' AND IIS < IISP THEN DO;
                  SUSPEND = 0;
                  RECOVER = IISP - IIS;
                  RECC = 0;
               END;
               IF USER5 = 'N' AND IIS >= IISP THEN DO;
                  SUSPEND = IIS - IISP;
                  RECOVER = 0;
                  RECC = 0;
               END;
               IF USER5 = 'N' AND IISP = 0 THEN DO;
                  SUSPEND = IIS;
                  RECC = IIS - SUSPEND;
               END;
               IF USER5 = 'N' AND OI < OIP THEN DO;
                  OISUSP = 0;
                  OIRECV = OIP - OI;
                  OIRECC = 0;
               END;
               IF USER5 = 'N' AND OI >= OIP THEN DO;
                  OISUSP = OI - OIP;
                  OIRECV = 0;
                  OIRECC = 0;
               END;
               IF USER5 = 'N' AND OIP = 0 THEN DO;
                  OISUSP = OI;
                  OIRECC = OI - OISUSP;
               END;
               OUTPUT;
            END;

            *** CONTINUE NPL ***;
            IF DAYS GE 90 AND PDAYS GE 90 THEN DO;
               IF BORSTAT NOT IN ('F','I','R') THEN DO;
                  RECC    = SUM(RECC,PRECC);
                  SUSPEND = SUM(SUSPEND,RECC);
                  OIRECC  = SUM(OIRECC,POIRECC);
                  OISUSP  = SUM(OISUSP,OIRECC);
                  TOTIIS = IIS + OI;
               END;
               OUTPUT;
            END;
         END;
      RUN;
   %END;
%MEND MONTHLY;
%MONTHLY;

*------------------------------------------------*
*  COMBINE EXISTING & CURRENT NPL ACCOUNTS       *
*------------------------------------------------*;
DATA LOAN3 NPL.IIS&REPTMON NPL.IIS;
   SET LOAN1 LOAN2;
   LENGTH RISK $13;
   IF DAYS > 364 OR BORSTAT = 'W' THEN RISK = 'BAD';
   ELSE IF DAYS > 273 THEN RISK = 'DOUBTFUL';
   ELSE IF DAYS > 182 THEN RISK = 'SUBSTANDARD 2';
   ELSE IF DAYS < 90 AND USER5='N' THEN RISK = 'SUBSTANDARD-1';
   ELSE RISK = 'SUBSTANDARD-1';
   WHERE (COSTCTR < 3000 OR COSTCTR > 3999) AND
          COSTCTR NOT IN (4043,4048) AND
          COSTCTR NE .;
RUN;
PROC SORT DATA=LOAN3 NODUPKEY;BY ACCTNO NOTENO;RUN;
PROC SORT DATA=NPL.IIS&REPTMON NODUPKEY;BY ACCTNO NOTENO;RUN;
PROC SORT DATA=NPL.IIS NODUPKEY;BY ACCTNO NOTENO;RUN;
*------------------------------------------------*
*  PRODUCE REPORTS                               *
*------------------------------------------------*;
OPTIONS NOCENTER NODATE NONUMBER MISSING=0;
%LET TBL1=(EXISTING);
%LET TBL2=(CURRENT);
%LET TBL3=(EXISTING AND CURRENT);
%LET TTL=MOVEMENTS OF INTEREST IN SUSPENSE FOR THE MONTH ENDING;
*;
%MACRO TBLS;
   %DO I = 3 %TO 3;
      PROC TABULATE DATA=LOAN&I FORMAT=COMMA15.2 MISSING NOSEPS;
         CLASS LOANTYP RISK BRANCH;
         VAR CURBAL UHC NETBAL IISP SUSPEND RECOVER RECC IISPW IIS
             OIP OISUSP OIRECV OIRECC OIW OI TOTIIS;
         TABLE LOANTYP=' ',
               RISK=' '*(BRANCH=' ' ALL='SUB-TOTAL') ALL='TOTAL',
               N='NO OF ACCOUNT'*F=COMMA7.
               SUM=' '*
               (CURBAL='CURRENT BAL (A)'
                UHC='UNEARNED HIRING CHARGES (B)'
                NETBAL='NET BAL (A-B=C)')
               SUM='MOVEMENTS OF INTEREST IN SUSPENSE'*
               (IISP='OPENING BAL FOR FINANCIAL YEAR (D)'
                SUSPEND='INTEREST SUSPENDED DURING THE PERIOD (E)'
                RECOVER='WRITTEN BACK TO PROFIT & LOSS (F)'
                RECC='REVERSAL OF CURRENT YEAR IIS (G)'
                IISPW='WRITTEN OFF (H)'
                IIS='IIS CLOSING BAL (D+E-F-G-H=I)')
               SUM='MOVEMENTS OF OVERDUE INTEREST'*
               (OIP='OPENING BAL FOR FINANCIAL YEAR (J)'
                OISUSP='OI SUSPENDED DURING THE PERIOD (K)'
                OIRECV='WRITTEN BACK TO PROFIT & LOSS (L)'
                OIRECC='REVERSAL OF CURRENT YEAR OI (M)'
                OIW='WRITTEN OFF (N)'
                OI='OI CLOSING BAL (J+K-L-M-N=O)')
               SUM=' '*TOTIIS='TOTAL CLOSING BAL AS AT RPT DATE (I+O)'
               / BOX='RISK        BRANCH' RTS=29;
         TABLE LOANTYP=' ', BRANCH=' ' ALL='TOTAL',
               N='NO OF ACCOUNT'*F=COMMA7.
               SUM=' '*
               (CURBAL='CURRENT BAL (A)'
                UHC='UNEARNED HIRING CHARGES (B)'
                NETBAL='NET BAL (A-B=C)')
               SUM='MOVEMENTS OF INTEREST IN SUSPENSE'*
               (IISP='OPENING BAL FOR FINANCIAL YEAR (D)'
                SUSPEND='INTEREST SUSPENDED DURING THE PERIOD (E)'
                RECOVER='WRITTEN BACK TO PROFIT & LOSS (F)'
                RECC='REVERSAL OF CURRENT YEAR IIS (G)'
                IISPW='WRITTEN OFF (H)'
                IIS='IIS CLOSING BAL (D+E-F-G-H=I)')
               SUM='MOVEMENTS OF OVERDUE INTEREST'*
               (OIP='OPENING BAL FOR FINANCIAL YEAR (J)'
                OISUSP='OI SUSPENDED DURING THE PERIOD (K)'
                OIRECV='WRITTEN BACK TO PROFIT & LOSS (L)'
                OIRECC='REVERSAL OF CURRENT YEAR OI (M)'
                OIW='WRITTEN OFF (N)'
                OI='OI CLOSING BAL (J+K-L-M-N=O)')
               SUM=' '*TOTIIS='TOTAL CLOSING BAL AS AT RPT DATE (I+O)'
               / BOX='BRANCH' RTS=9;
         TITLE1 'PUBLIC BANK - (NPL FROM 3 MONTHS & ABOVE) - NEW';
         TITLE2 &TTL &RDATE &&TBL&I;
   %END;
%MEND TBLS;
*;
%MACRO DTLS;
   %DO I = 3 %TO 3;
      PROC SORT DATA=LOAN&I;
         BY LOANTYP BRANCH RISK DAYS ACCTNO;
*;
        PROC PRINT LABEL N;

         FORMAT NETPROC CURBAL UHC NETBAL IISP SUSPEND RECOVER
                RECC IISPW IIS OIP OISUSP OIRECV OIRECC OIW OI
                TOTIIS COMMA15.2;
         LABEL ACCTNO  = 'MNI ACCOUNT NO'
               DAYS    = 'NO OF DAYS PAST DUE'
               BORSTAT = 'BORROWER''S STATUS'
               NETPROC = 'LIMIT'
               CURBAL  = 'CURRENT BAL (A)'
               UHC     = 'UNEARNED HIRING CHARGES (B)'
               NETBAL  = 'NET BAL (A-B=C)'
               IISP    = 'OPENING BAL FOR FINANCIAL YEAR (D)'
               SUSPEND = 'INTEREST SUSPENDED DURING THE PERIOD (E)'
               RECOVER = 'WRITTEN BACK TO PROFIT & LOSS (F)'
               RECC    = 'REVERSAL OF CURRENT YEAR IIS (G)'
               IISPW   = 'WRITTEN OFF (H)'
               IIS     = 'IIS CLOSING BAL (D+E-F-G-H=I)'
               OIP     = 'OPENING BAL FOR FINANCIAL YEAR (J)'
               OISUSP  = 'OI SUSPENDED DURING THE PERIOD (K)'
               OIRECV  = 'WRITTEN BACK TO PROFIT & LOSS (L)'
               OIRECC  = 'REVERSAL OF CURRENT YEAR OI (M)'
               OIW     = 'WRITTEN OFF (N)'
               OI      = 'OI CLOSING BAL (J+K-L-M-N=O)'
               TOTIIS  = 'TOTAL CLOSING BAL AS AT RPT DATE (I+O)';
         VAR ACCTNO NAME DAYS BORSTAT NETPROC CURBAL UHC NETBAL
             IISP SUSPEND RECOVER RECC IISPW IIS OIP OISUSP OIRECV
             OIRECC OIW OI TOTIIS;
         BY LOANTYP BRANCH RISK;
         PAGEBY BRANCH;
         SUMBY RISK;
         SUM NETPROC CURBAL UHC NETBAL IISP SUSPEND RECOVER
             RECC IISPW IIS OIP OISUSP OIRECV OIRECC OIW OI TOTIIS;
         TITLE1 'PUBLIC BANK - (NPL FROM 3 MONTHS & ABOVE) - NEW';
         TITLE2 &TTL &RDATE &&TBL&I;
   %END;
%MEND DTLS;
*;
%TBLS;
    /* DISCONTINUE AS PER LETTER DATED 26/08/03 FR STATISTICS */
%DTLS;

















*+--------------------------------------------------------------+
 |  PROGRAM : EIFMNP06                                          |
 |  DATE    : 18.03.98                                          |
 |  MODIFY  : ESMR 2004-720, 2004-579, 2006-1048, 2006-1281     |
 |  REPORT  : MOVEMENTS OF SPECIFIC PROVISION FOR THE MONTH     |
 |            ENDING (BASED ON DEPRECIATED PURCHASE PRICE       |
 |            FOR UNSCHEDULED GOODS)                            |
 +--------------------------------------------------------------+;
OPTIONS YEARCUTOFF=1950;
*;
%INC PGM(PBBLNFMT);
%INC PGM(PBBELF);
*;
PROC FORMAT;
   VALUE LNTYP 128,130,983             = 'HPD AITAB'
               700,705,993,996,380,381,
               720,725                 = 'HPD CONVENTIONAL'
               200-299                 = 'HOUSING LOANS'
               OTHER   = 'OTHERS';
*;
DATA REPTDATE;
   SET NPL.REPTDATE;
   IF MONTH(REPTDATE) = 1 THEN MM1 = 12;
   ELSE MM1 = MONTH(REPTDATE)-1;
   CALL SYMPUT('RDATE',PUT(REPTDATE,WORDDATX18.));
   CALL SYMPUT('REPTMON',PUT(MONTH(REPTDATE),Z2.));
   CALL SYMPUT('PREVMON',PUT(MM1,Z2.));
RUN;
*------------------------------------------------*
*  MERGE WITH WRITTEN OFF ACCOUNT                *
*------------------------------------------------*;
PROC SORT DATA=NPL.LOAN&REPTMON;BY ACCTNO;
PROC SORT DATA=NPL.WSP2;BY ACCTNO;
PROC SORT DATA=NPL.IIS&REPTMON (KEEP=ACCTNO IIS) OUT=IIS;
   BY ACCTNO;
DATA LOANWOFF;
   MERGE NPL.LOAN&REPTMON NPL.WSP2 (IN=AA DROP=NOTENO NTBRCH);
   BY ACCTNO;
   IF LOANTYPE IN (983,993) THEN WDOWNIND = 'N';
 /*  IF BB THEN HARDCODE = 'N';ELSE HARDCODE = 'N'; */
   IF AA THEN WRITEOFF='Y'; ELSE WRITEOFF='N';
   IF EARNTERM IN (0,.) THEN EARNTERM = NOTETERM;
*;
DATA LOANWOFF;
   MERGE LOANWOFF(IN=A) IIS;
   BY ACCTNO;
   IF A;
RUN;
*;

*------------------------------------------------*
*  CALCULATE SP FOR EXISTING NPL ACCOUNTS        *
*------------------------------------------------*;
DATA LOAN1;
   KEEP BRANCH NTBRCH ACCTNO NOTENO NAME DAYS BORSTAT NETPROC CURBAL
        UHC NETBAL IIS OSPRIN MARKETVL NETEXP SPP2 SPPL RECOVER
        SPPW SP LOANTYP VINNO CENSUS7 OTHERFEE EXIST COSTCTR USER5
        PENDBRH WDOWNIND RESCHEIND;
   LENGTH LOANTYP $20;
   RETAIN STMTH 1 STYR;
   SET LOANWOFF;
 * SET NPL.LOAN&REPTMON;
   IF _N_ = 1 THEN DO;
      SET REPTDATE;
      STYR = YEAR(REPTDATE);
   END;
   IF EXIST = 'Y';
   UHC = 0;
   IF WRITEOFF = 'Y' AND WDOWNIND ^= 'Y' THEN BORSTAT ='W';
   IF BLDATE > 0 & TERMCHG > 0 THEN DO;
      IF DAYS > 89 | BORSTAT IN ('F','R','I') OR USER5 = 'N' THEN DO;
         REMMTH1 = EARNTERM - ((YEAR(BLDATE) - YEAR(ISSDTE))*12 +
                   MONTH(BLDATE) - MONTH(ISSDTE) + 1);
         REMMTH2 = EARNTERM - ((YEAR(REPTDATE) - YEAR(ISSDTE))*12 +
                   MONTH(REPTDATE) - MONTH(ISSDTE) + 1);
         REMMTHS = EARNTERM - ((STYR - YEAR(ISSDTE))*12 +
                   STMTH - MONTH(ISSDTE) + 1);
         IF REMMTH2 < 0 THEN REMMTH2 = 0;
         IF LOANTYPE IN (128,130) THEN
              REMMTH1 = REMMTH1 - 3;
         ELSE REMMTH1 = REMMTH1 - 1;
   /*    IF REMMTH1 >= REMMTH2 THEN
            DO REMMTH = REMMTH1 TO REMMTH2 BY -1;
               IS = 2*(REMMTH+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
               IF REMMTH > REMMTHS THEN IISPREV + IS;
               ELSE IIS + IS;
            END;    */
         IF REMMTH2 > 0 THEN
            UHC = REMMTH2*(REMMTH2+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
      END;
   END;
 *  IF TERMCHG = 0 THEN IISPREV = IISP;
   IF CURBAL = . THEN CURBAL = 0;
   NETBAL = CURBAL - UHC;
   OSPRIN = CURBAL - UHC - IIS;
   IF LOANTYPE IN (380,381) THEN OTHERFEE = SUM(FEEAMT,(-1)*FEETOT2);
   ELSE OTHERFEE = SUM(FEEAMT8,(-1)*FEETOT2,FEEAMTA,(-1)*FEEAMT5);
   IF OTHERFEE < 0 THEN OTHERFEE = 0;
   IF LOANTYPE IN (983,993) THEN OTHERFEE = 0;
   IF APPVALUE > 0 & (LOANTYPE IN (705,128,700,130,380,381,720,725)
      | CENSUS7 = '9') &
      (DAYS > 89 OR USER5 = 'N') &
      BORSTAT NOT IN ('F','R','I','Y','W')
      AND LOANTYPE NOT IN (983,993) THEN DO;
      AGE = INT(YEAR(REPTDATE) - YEAR(ISSDTE) +
            (MONTH(REPTDATE) - MONTH(ISSDTE)) / 12);
      IF CENSUS7 ^='9' THEN
         MARKETVL = APPVALUE - APPVALUE * AGE * 0.2;
      IF HARDCODE = 'Y' THEN DO;
         MARKETVL = WREALVL;
      END;
      IF MARKETVL < 0 THEN MARKETVL = 0;
      IF DAYS > 273 THEN NETEXP = OSPRIN + OTHERFEE;
      ELSE NETEXP = OSPRIN + OTHERFEE - MARKETVL;
  /*  IF LOANTYPE IN (128,130) THEN NETEXP = OSPRIN - MARKETVL;
      ELSE DO;
         IF DAYS > 273 THEN NETEXP = OSPRIN;
         ELSE NETEXP = OSPRIN - MARKETVL;
      END; */
      SELECT;
         WHEN (DAYS>364) SP = NETEXP;
         WHEN (DAYS>273) SP = NETEXP / 2;
         WHEN (DAYS> 89) SP = NETEXP * 0.2;
         WHEN (DAYS< 90) SP = NETEXP * 0.2;
         OTHERWISE SP = 0;
      END;
   END;
   ELSE DO;
      IF BORSTAT NOT IN ('R') THEN MARKETVL = 0;
      IF HARDCODE = 'Y' THEN DO;
         MARKETVL = WREALVL;
      END;
      NETEXP = OSPRIN + OTHERFEE - MARKETVL;
      IF DAYS > 364 OR BORSTAT IN ('F','R','I','W') THEN
         SP = NETEXP;
      ELSE IF DAYS > 273 THEN SP = NETEXP / 2;
      ELSE IF DAYS > 89 AND BORSTAT = 'Y' THEN SP = NETEXP / 5;
      ELSE SP = 0;
   END;
   IF SP < 0 THEN SP = 0;
   SPPL = SP - SPP2;
   IF SPPL < 0 THEN SPPL = 0;
   IF HARDCODE = 'Y' THEN DO;
      IF WSPPL NE . THEN SPPL = WSPPL;
      IF WSP NE . THEN SP = WSP;
   END;
   IF BORSTAT = 'W' THEN DO;
      SPPW = SPP2;
      SP   = 0;
      MARKETVL = 0;
   END;
   ELSE RECOVER = SPP2 - SP;
   IF RECOVER < 0 THEN RECOVER = 0;
   BRANCH = PUT(NTBRCH,BRCHCD.)||' '||PUT(NTBRCH,Z3.);
   LOANTYP = PUT(LOANTYPE,LNTYP.);
   IF WRITEOFF = 'Y' THEN DO;
      SPPL = WSPPL;
      OTHERFEE = 0;
      IF WDOWNIND ^= 'Y' THEN DO;
         RECOVER = WRECOVER;
         SP   = 0;
         SPPW = SUM(SPP2,SPPL,(-1)*RECOVER);
      END;
      ELSE DO;
         SPPW = WSPPW;
         IF NETEXP <= 0 THEN RECOVER = 0;
         SP = SUM(SPP2,SPPL,(-1)*RECOVER,(-1)*SPPW);
         IF NETEXP <=0 AND SP > 0 THEN DO;
            RECOVER = SP;
            SP = 0;
         END;
      END;
   END;
 IF RESCHEIND = 'Y' THEN DO;
      SPLL    = WSPLL;
      RECOVER = WRECOVER;
      SPPW    = WSPPW;
      SP      = SUM(SPP2,SPPL,(-1)*RECOVER,(-1)*SPPW);
      END;
*;
*------------------------------------------------*
*  CALCULATE SP FOR CURRENT NPL ACCOUNTS         *
*------------------------------------------------*;
DATA LOAN2;
   KEEP BRANCH NTBRCH ACCTNO NOTENO NAME DAYS BORSTAT NETPROC CURBAL
        UHC NETBAL IIS OSPRIN MARKETVL NETEXP SPP2 SPPL RECOVER
        SPPW SP LOANTYP VINNO CENSUS7 OTHERFEE EXIST COSTCTR USER5
        PENDBRH WDOWNIND RESCHEIND;
   LENGTH LOANTYP $20;
   RETAIN STMTH 1 STYR;
   SET LOANWOFF;
 * SET NPL.LOAN&REPTMON;
   IF _N_ = 1 THEN DO;
      SET REPTDATE;
      STYR = YEAR(REPTDATE);
   END;
   IF EXIST ^= 'Y';
 * IF DAYS > 182 OR BORSTAT NOT IN (' ','S');
   UHC = 0;
   IF WRITEOFF = 'Y' AND WDOWNIND ^= 'Y' THEN BORSTAT ='W';
   IF BLDATE > 0 & TERMCHG > 0 THEN DO;
      REMMTH1 = EARNTERM - ((YEAR(BLDATE) - YEAR(ISSDTE))*12 +
                MONTH(BLDATE) - MONTH(ISSDTE) + 1);
      REMMTH2 = EARNTERM - ((YEAR(REPTDATE) - YEAR(ISSDTE))*12 +
                MONTH(REPTDATE) - MONTH(ISSDTE) + 1);
      REMMTHS = EARNTERM - ((STYR - YEAR(ISSDTE))*12 +
                STMTH - MONTH(ISSDTE) + 1);
      IF REMMTH2 < 0 THEN REMMTH2 = 0;
      IF LOANTYPE IN (128,130) THEN
           REMMTH1 = REMMTH1 - 3;
      ELSE REMMTH1 = REMMTH1 - 1;
  /*    IF REMMTH1 >= REMMTH2 THEN
         DO REMMTH = REMMTH1 TO REMMTH2 BY -1;
            IS = 2*(REMMTH+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
            IF REMMTH > REMMTHS THEN IISPREV + IS;
            ELSE IIS + IS;
         END;      */
      IF REMMTH2 > 0 THEN
         UHC = REMMTH2*(REMMTH2+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
   END;
   ELSE DO;
      REMMTH2 = EARNTERM - ((YEAR(REPTDATE) - YEAR(ISSDTE))*12 +
                MONTH(REPTDATE) - MONTH(ISSDTE) + 1);
      IF REMMTH2 < 0 THEN REMMTH2 = 0;
      IF REMMTH2 > 0 THEN
         UHC = REMMTH2*(REMMTH2+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
   END;
   NETBAL = CURBAL - UHC;
   OSPRIN = CURBAL - UHC - IIS;
   IF LOANTYPE IN (380,381) THEN OTHERFEE = SUM(FEEAMT,(-1)*FEETOT2);
   ELSE OTHERFEE = SUM(FEEAMT8,(-1)*FEETOT2,FEEAMTA,(-1)*FEEAMT5);
   IF OTHERFEE < 0 THEN OTHERFEE = 0;
   IF LOANTYPE IN (983,993) THEN OTHERFEE = 0;
   IF APPVALUE > 0 & (LOANTYPE IN (705,130,700,128,380,381,720,725) |
      CENSUS7 = '9') &
      (DAYS > 89 OR USER5 = 'N') &
      BORSTAT NOT IN ('F','R','I','Y','W')
      AND LOANTYPE NOT IN (983,993) THEN DO;
      AGE = INT(YEAR(REPTDATE) - YEAR(ISSDTE) +
            (MONTH(REPTDATE) - MONTH(ISSDTE)) / 12);
      IF CENSUS7 ^= '9' THEN
         MARKETVL = APPVALUE - APPVALUE * AGE * 0.2;
      IF HARDCODE = 'Y' THEN DO;
         MARKETVL = WREALVL;
      END;
      IF MARKETVL < 0 THEN MARKETVL = 0;
      IF DAYS > 273 THEN NETEXP = OSPRIN + OTHERFEE;
      ELSE NETEXP = OSPRIN + OTHERFEE - MARKETVL;
 /*   IF LOANTYPE IN (705,130) THEN NETEXP = OSPRIN - MARKETVL;
      ELSE DO;
         IF DAYS > 273 THEN NETEXP = OSPRIN;
         ELSE NETEXP = OSPRIN - MARKETVL;
      END; */
      SELECT;
         WHEN (DAYS>364) SP = NETEXP;
         WHEN (DAYS>273) SP = NETEXP / 2;
         WHEN (DAYS> 89) SP = NETEXP * 0.2;
         WHEN (DAYS< 90) SP = NETEXP * 0.2;
         OTHERWISE SP = 0;
      END;
   END;
   ELSE DO;
      IF BORSTAT NOT IN ('R') THEN MARKETVL = 0;
      IF HARDCODE = 'Y' THEN DO;
         MARKETVL = WREALVL;
      END;
      NETEXP = OSPRIN + OTHERFEE - MARKETVL;
      IF DAYS > 364 OR BORSTAT IN ('F','R','I','W') THEN
         SP = NETEXP;
      ELSE IF DAYS > 273 THEN SP = NETEXP / 2;
      ELSE IF DAYS > 89 AND BORSTAT = 'Y' THEN SP = NETEXP / 5;
      ELSE SP = 0;
   END;
   IF SP < 0 THEN SP = 0;
   SPPL = SP;
   IF HARDCODE = 'Y' THEN DO;
      IF WSPPL NE . THEN SPPL = WSPPL;
      IF WSP NE . THEN SP = WSP;
   END;
   BRANCH = PUT(NTBRCH,BRCHCD.)||' '||PUT(NTBRCH,Z3.);
   LOANTYP = PUT(LOANTYPE,LNTYP.);
   IF WRITEOFF = 'Y' THEN DO;
      SPPL = WSPPL;
      OTHERFEE = 0;
      IF WDOWNIND ^= 'Y' THEN DO;
         RECOVER = WRECOVER;
         SP   = 0;
         SPPW = SUM(SPP2,SPPL,(-1)*RECOVER);
      END;
      ELSE DO;
         SPPW = WSPPW;
         IF NETEXP <= 0 THEN RECOVER = 0;
         SP = SUM(SPP2,SPPL,(-1)*RECOVER,(-1)*SPPW);
         IF NETEXP <=0 AND SP > 0 THEN DO;
            RECOVER = SP;
            SP = 0;
         END;
      END;
   END;

 IF RESCHEIND = 'Y' THEN DO;
      SPLL    = WSPLL;
      RECOVER = WRECOVER;
      SPPW    = WSPPW;
      SP      = SUM(SPP2,SPPL,(-1)*RECOVER,(-1)*SPPW);
      END;
*;
*------------------------------------------------*
*  COMPARE PREVIOUS MONTH NPL ACCOUNTS (JUL 05)  *
*------------------------------------------------*;
%MACRO MONTHLY;
   %IF "&REPTMON" EQ "01" %THEN %DO;
      DATA LOAN1;
         SET LOAN1;
         SPPLCUM = 0;
      RUN;
      DATA LOAN2;
         SET LOAN2;
         SPPLCUM = 0;
      RUN;
   %END;
   %ELSE %DO;
      PROC SORT DATA=NPL.SP2&PREVMON
         (RENAME=(DAYS=PDAYS SPP2=PSPP2 SPPL=PSPPL SP=PSP
                  RECOVER=PRECOVER BORSTAT=PBORSTAT))
         OUT=SP2PREV NODUPKEY;
      BY ACCTNO NOTENO; RUN;

      DATA SP2PREV;
         SET SP2PREV;
             IF LOANTYPE IN (128,130,131,132,380,381,390,
                             700,705,720,725,983,993,996)
             AND PAIDIND='P' THEN DO;
             %INC PGM(NPLNTB);
             END;
         BRANCH = PUT(NTBRCH,BRCHCD.)||' '||PUT(NTBRCH,Z3.);
         IF PDAYS = . THEN PDAYS = 0;
         IF PSPP2 = . THEN PSPP2 = 0;
         IF PSPPL = . THEN PSPPL = 0;
         IF PSP = . THEN PSP = 0;
         IF PRECOVER = . THEN PRECOVER = 0;
      RUN;
      ********************
      *** EXISTING NPL ***
      ********************;
      PROC SORT DATA=LOAN1; BY ACCTNO; RUN;
      DATA LOAN1(DROP=PDAYS PSPPL PSP PSPP2 PRECOVER PBORSTAT);
         MERGE SP2PREV(IN=B) LOAN1(IN=A);
         BY ACCTNO;
         IF ((A AND B) OR (B AND NOT A)) AND EXIST = 'Y';

         *** A/C SETTLE FOR EXISTING NPL ***;
         IF ((B AND NOT A) OR (CURBAL LE 0 AND PSP LE 0)) AND
            BORSTAT NOT IN ('F','I','R','W','S') THEN DO;
            SPPL=PSPPL;
            RECOVER=SUM(PSPP2,PSPPL);
            CURBAL=0;
            NETBAL=0;
            UHC=0;
            IIS=0;
            MARKETVL=0;
            OSPRIN = SUM(CURBAL,(-1)*UHC,(-1)*IIS);
            NETEXP = SUM(OSPRIN,(-1)*MARKETVL);
            DAYS=0;
            SP = SUM(SPP2,SPPL,(-1)*RECOVER,(-1)*SPPW);
            OUTPUT;
         END;
         ELSE DO;
            IF BORSTAT IN ('W') OR RESCHEIND='Y' THEN DO;
               OUTPUT;
            END;
            ELSE DO;
               IF (A AND B) THEN DO;
                  *** CONTINUE PERFORMING ***;
                  IF (DAYS LT 90 AND PDAYS LT 90) THEN DO;
                     IF BORSTAT NOT IN ('F','I','R') THEN DO;
                        SPPL=PSPPL;
                        RECOVER=SUM(PSPP2,PSPPL);
                     END;
                     IF USER5 = 'N' AND  SPP2 >= SP THEN DO;
                        SPPL=0;
                        RECOVER = SPP2 - SP;
                     END;
                     IF USER5 = 'N' AND SPP2 < SP THEN DO;
                        SPPL = SP-SPP2;
                        RECOVER = 0;
                     END;
                     OUTPUT;
                  END;
                  *** TURN PERFORMING ***;
                  IF (DAYS LT 90 AND PDAYS GE 90) THEN DO;
                     IF BORSTAT NOT IN ('F','I','R') THEN DO;
                        IIS=0;
                        IF USER5 NE 'N' THEN MARKETVL=0;
                        OSPRIN = SUM(CURBAL,(-1)*UHC,(-1)*IIS);
                        NETEXP = SUM(OSPRIN,(-1)*MARKETVL);
                        SPPL = PSPPL;
                        RECOVER = SUM(PSPP2,PSPPL);
                     END;
                     IF USER5 = 'N' AND  SPP2 >= SP THEN DO;
                        SPPL=0;
                        RECOVER = SPP2 - SP;
                     END;
                     IF USER5 = 'N' AND SPP2 < SP THEN DO;
                        SPPL = SP-SPP2;
                        RECOVER = 0;
                     END;
                     OUTPUT;
                  END;
                  *** TURN NPL FR PERFORMING ***;
                  IF DAYS GE 90 AND PDAYS LT 90 THEN DO;
                     IF BORSTAT NOT IN ('F','I','R') THEN DO;
                        SPPL = SUM(SP,PSPPL);
                        RECOVER = SUM(PSPPL,PSPP2);
                     END;
                     IF USER5 = 'N' AND  SPP2 >= SP THEN DO;
                        SPPL=0;
                        RECOVER = SPP2 - SP;
                     END;
                     IF USER5 = 'N' AND SPP2 < SP THEN DO;
                        SPPL = SP-SPP2;
                        RECOVER = 0;
                     END;
                     OUTPUT;
                  END;
                  *** CONTINUE NPL ***;
                  IF DAYS GE 90 AND PDAYS GE 90 THEN DO;
                     IF BORSTAT NOT IN ('F','I','R') THEN DO;
                        SPPL = SUM(SP,(-1)*PSPP2);
                        IF SPPL LT 0 THEN DO;
                           RECOVER = SPPL*(-1);
                           SPPL = 0;
                        END;
                     END;
                     OUTPUT;
                  END;
               END;
            END;
         END;
      RUN;
      *******************
      *** CURRENT NPL ***
      *******************;
      PROC SORT DATA=NPL.PLOAN&REPTMON OUT=PLOAN
         (KEEP=ACCTNO NOTENO CURBAL DAYS BORSTAT NTBRCH COSTCTR);
         BY ACCTNO;
      RUN;
      DATA SP2PREV;
         MERGE SP2PREV(IN=A) PLOAN(IN=B);
         BY ACCTNO;
         IF PSPP2 EQ 0 AND EXIST NE 'Y' ;
         BRANCH = PUT(NTBRCH,BRCHCD.)||' '||PUT(NTBRCH,Z3.);
      RUN;

      PROC SORT DATA=LOAN2; BY ACCTNO NOTENO; RUN;
      DATA LOAN2(DROP=PDAYS PSPPL PSP PSPP2 PRECOVER PBORSTAT);
         MERGE SP2PREV(IN=B) LOAN2(IN=A);
         BY ACCTNO;

         IF (B AND NOT A) THEN DO;
            *** A/C SETTLE FOR EXISTING NPL ***;
               SPPL=PSPPL;
               RECOVER=SUM(PSPP2,PSPPL);
               CURBAL=0;
               NETBAL=0;
               UHC=0;
               IIS=0;
               MARKETVL=0;
               OSPRIN = SUM(CURBAL,(-1)*UHC,(-1)*IIS);
               NETEXP = SUM(OSPRIN,(-1)*MARKETVL);
               DAYS=0;
               SP = SUM(SPP2,SPPL,(-1)*RECOVER,(-1)*SPPW);
               OUTPUT;
            END;

         *** NEW NPL FOR THE MTH ***;
         IF (A AND NOT B) AND
            (DAYS GE 90 OR BORSTAT IN ('F','I','R','W') OR USER5='N')
            THEN OUTPUT;

         IF (A AND B) THEN DO;
            IF BORSTAT IN ('W') OR RESCHEIND='Y' THEN DO;
               OUTPUT;
            END;
            ELSE DO;
               *** CONTINUE PERFORMING ***;
               IF (DAYS LT 90 AND PDAYS LT 90) THEN DO;
                  IF BORSTAT NOT IN ('F','I','R') THEN DO;
                     SPPL=PSPPL;
                     RECOVER=PRECOVER;
                  END;
                  IF BORSTAT IN ('F','I','R') THEN DO;
                     RECOVER = PRECOVER;
                     SPPL = SUM(SP,RECOVER);
                  END;
                  IF USER5 = 'N' AND  SPP2 >= SP THEN DO;
                     SPPL=0;
                     RECOVER = SPP2 - SP;
                  END;
                  IF USER5 = 'N' AND SPP2 < SP THEN DO;
                     SPPL = SP-SPP2;
                     RECOVER = 0;
                  END;
                  OUTPUT;
               END;

               *** TURN PERFORMING ***;
               IF (DAYS LT 90 AND PDAYS GE 90) THEN DO;
                  IF BORSTAT NOT IN ('F','I','R') THEN DO;
                     IIS=0;
                     MARKETVL=0;
                     OSPRIN = SUM(CURBAL,(-1)*UHC,(-1)*IIS);
                     NETEXP = SUM(OSPRIN,(-1)*MARKETVL);
                     SPPL    = PSPPL;
                     RECOVER = PSPPL;
                  END;
                  IF USER5 = 'N' AND  SPP2 >= SP THEN DO;
                     SPPL=0;
                     RECOVER = SPP2 - SP;
                  END;
                  IF USER5 = 'N' AND SPP2 < SP THEN DO;
                     SPPL = SP-SPP2;
                     RECOVER = 0;
                  END;
                  OUTPUT;
               END;

               *** TURN NPL FR PERFORMING ***;
               IF DAYS GE 90 AND PDAYS LT 90 THEN DO;
                  IF BORSTAT NOT IN ('F','I','R') THEN DO;
                     SPPL = SUM(SP,PSPPL);
                     RECOVER = PSPPL;
                  END;
                  IF USER5 = 'N' AND  SPP2 >= SP THEN DO;
                     SPPL=0;
                     RECOVER = SPP2 - SP;
                  END;
                  IF USER5 = 'N' AND SPP2 < SP THEN DO;
                     SPPL = SP-SPP2;
                     RECOVER = 0;
                  END;
                  OUTPUT;
               END;

               *** CONTINUE NPL ***;
               IF (DAYS GE 90 AND PDAYS GE 90) THEN DO;
                  RECOVER = PRECOVER;
                  SPPL = SUM(SP,RECOVER);
                  OUTPUT;
               END;
            END;
         END;
      RUN;
   %END;
%MEND MONTHLY;
%MONTHLY;
*------------------------------------------------*
*  COMBINE EXISTING & CURRENT NPL ACCOUNTS       *
*------------------------------------------------*;
DATA LOAN3 NPL.SP2&REPTMON NPL.SP2;
   SET LOAN1 LOAN2;
   LENGTH RISK $13;
   IF DAYS > 364 OR BORSTAT = 'W' THEN RISK = 'BAD';
   ELSE IF DAYS > 273 THEN RISK = 'DOUBTFUL';
   ELSE IF DAYS > 182 THEN RISK = 'SUBSTANDARD 2';
   ELSE IF DAYS < 90 AND USER5 ='N' THEN RISK = 'SUBSTANDARD-1';
   ELSE RISK = 'SUBSTANDARD-1';
   WHERE (COSTCTR < 3000 OR COSTCTR > 3999) AND
          COSTCTR NOT IN (4043,4048) AND
          COSTCTR NE .;

RUN;
PROC SORT DATA=LOAN3 NODUPKEY;BY ACCTNO NOTENO;RUN;
*------------------------------------------------*
*  PRODUCE REPORTS                               *
*------------------------------------------------*;
OPTIONS NOCENTER NODATE NONUMBER MISSING=0;
%LET TBL1=(EXISTING);
%LET TBL2=(CURRENT);
%LET TBL3=(EXISTING AND CURRENT);
%LET TTL=MOVEMENTS OF SPECIFIC PROVISION FOR THE MONTH ENDING;
*;
%MACRO TBLS;
   %DO I = 3 %TO 3;
      PROC TABULATE DATA=LOAN&I FORMAT=COMMA14.2 MISSING NOSEPS;
         CLASS LOANTYP RISK BRANCH;
         VAR CURBAL UHC NETBAL IIS OSPRIN MARKETVL NETEXP
             SPP2 SPPL RECOVER SPPW SP OTHERFEE;
         TABLE LOANTYP=' ',
               RISK=' '*(BRANCH=' ' ALL='SUB-TOTAL') ALL='TOTAL',
               N='NO OF ACCOUNT'*F=COMMA7.
               SUM=' '*(CURBAL='CURRENT BAL (A)'
                        UHC='UNEARNED HIRING CHARGES (B)'
                        NETBAL='NET BAL (A-B=C)'
                        IIS='IIS (E)'
                        OSPRIN='PRINCIPAL OUTSTANDING (C-E=F)'
                        OTHERFEE = 'OTHER FEES'
                        MARKETVL='REALISABLE VALUE (G)'
                        NETEXP='NET EXPOSURE (F-G=H)'
                        SPP2='OPENING BAL FOR FINANCIAL YEAR (I)'
                        SPPL='PROVISION MADE AGAINST PROFIT & LOSS (J)'
                        RECOVER='WRITTEN BACK TO PROFIT & LOSS (K)'
                        SPPW='WRITTEN OFF AGAINST PROVISION (L)'
                        SP='CLOSING BAL AS AT RPT DATE (I+J-K-L)')
               / BOX='RISK        BRANCH' RTS=29;
         TABLE LOANTYP=' ', BRANCH=' ' ALL='TOTAL',
               N='NO OF ACCOUNT'*F=COMMA7.
               SUM=' '*(CURBAL='CURRENT BAL (A)'
                        UHC='UNEARNED HIRING CHARGES (B)'
                        NETBAL='NET BAL (A-B=C)'
                        IIS='IIS (E)'
                        OSPRIN='PRINCIPAL OUTSTANDING (C-E=F)'
                        OTHERFEE = 'OTHER FEES'
                        MARKETVL='REALISABLE VALUE (G)'
                        NETEXP='NET EXPOSURE (F-G=H)'
                        SPP2='OPENING BAL FOR FINANCIAL YEAR (I)'
                        SPPL='PROVISION MADE AGAINST PROFIT & LOSS (J)'
                        RECOVER='WRITTEN BACK TO PROFIT & LOSS (K)'
                        SPPW='WRITTEN OFF AGAINST PROVISION (L)'
                        SP='CLOSING BAL AS AT RPT DATE (I+J-K-L)')
               / BOX='BRANCH' RTS=9;
         TITLE1 'PUBLIC BANK - (NPL FROM 3 MONTHS & ABOVE) - NEW';
         TITLE2 &TTL &RDATE &&TBL&I;
         ** TITLE3 '(BASED ON DEPRECIATED PP FOR UNSCHEDULED GOODS)';
   %END;
%MEND TBLS;
*;
%MACRO DTLS;
   %DO I = 3 %TO 3;
      PROC SORT DATA=LOAN&I;
         BY LOANTYP BRANCH RISK DAYS ACCTNO;
*;
      PROC PRINT LABEL N;
         FORMAT NETPROC CURBAL UHC NETBAL IIS OSPRIN MARKETVL
                NETEXP SPP2 SPPL RECOVER SPPW SP OTHERFEE COMMA14.2;
         LABEL ACCTNO   = 'MNI ACCOUNT NO'
               VINNO    = 'AA NUMBER'
               DAYS     = 'NO OF DAYS PAST DUE'
               BORSTAT  = 'BORROWER''S STATUS'
               NETPROC  = 'LIMIT'
               CURBAL   = 'CURRENT BAL (A)'
               UHC      = 'UNEARNED HIRING CHARGES (B)'
               NETBAL   = 'NET BAL (A-B=C)'
               IIS      = 'IIS (E)'
               OSPRIN   = 'PRINCIPAL OUTSTANDING (C-E=F)'
               OTHERFEE = 'OTHER FEES'
               MARKETVL = 'REALISABLE VALUE (G)'
               NETEXP   = 'NET EXPOSURE (F-G=H)'
               SPP2     = 'OPENING BAL FOR FINANCIAL YEAR (I)'
               SPPL     = 'PROVISION MADE AGAINST PROFIT & LOSS (J)'
               RECOVER  = 'WRITTEN BACK TO PROFIT & LOSS (K)'
               SPPW     = 'WRITTEN OFF AGAINST PROVISION (L)'
               SP       = 'CLOSING BAL AS AT RPT DATE (I+J-K-L)';
         VAR ACCTNO NAME VINNO DAYS BORSTAT NETPROC CURBAL UHC
             NETBAL OTHERFEE
             IIS OSPRIN MARKETVL NETEXP SPP2 SPPL RECOVER SPPW SP;
         BY LOANTYP BRANCH RISK;
         PAGEBY BRANCH;
         SUMBY RISK;
         SUM NETPROC CURBAL UHC NETBAL IIS OSPRIN MARKETVL
             NETEXP SPP2 SPPL RECOVER SPPW SP OTHERFEE;
         TITLE1 'PUBLIC BANK - (NPL FROM 3 MONTHS & ABOVE) - NEW';
         TITLE2 &TTL &RDATE &&TBL&I;
         ** TITLE3 '(BASED ON DEPRECIATED PP FOR UNSCHEDULED GOODS)';
   %END;
%MEND DTLS;
*;
%TBLS;
  /* DISCONTINUE AS PER LETTER DATED 26/08/03 FR STATISTICS */
%DTLS;



























*+--------------------------------------------------------------+
 |  PROGRAM : EIFMNP07                                          |
 |  DATE    : 03.04.98                                          |
 |  MODIFY  : ESMR 2004-720, 2004-579, 2006-1048                |
 |  REPORT  : STATISTICS ON ASSET QUALITY - MOVEMENTS IN NPL    |
 +--------------------------------------------------------------+;
OPTIONS YEARCUTOFF=1950;
*;
%INC PGM(PBBLNFMT);
%INC PGM(PBBELF);
*;
PROC FORMAT;
   VALUE LNTYP 128,130,983             = 'HPD AITAB'
               700,705,993,996,380,381,
               720,725                 = 'HPD CONVENTIONAL'
               200-299                 = 'HOUSING LOANS'
               OTHER   = 'OTHERS';
*;
*------------------------------------------------*
*  MACRO FOR CALCULATING NEXT BLDATE             *
*------------------------------------------------*;
%MACRO DCLVAR;
   RETAIN D1-D12 31 D4 D6 D9 D11 30;
   ARRAY LDAY D1-D12;
%MEND DCLVAR;
*;
%MACRO NXTBLDT;
   DD = DAY(ISSDTE);
   MM = MONTH(BLDATE) + 1;
   YY = YEAR(BLDATE);
   IF MM > 12 THEN DO;
      MM = 1; YY + 1;
   END;
   IF MM = 2 THEN
      IF MOD(YY,4) = 0 THEN D2 = 29;
      ELSE D2 = 28;
   IF DD > LDAY(MM) THEN DD = LDAY(MM);
   BLDATE = MDY(MM,DD,YY);
%MEND NXTBLDT;
*;
*------------------------------------------------*
*  GET REPTDATE                                  *
*------------------------------------------------*;
DATA REPTDATE;
   SET NPL.REPTDATE;
   CALL SYMPUT('RDATE',PUT(REPTDATE,WORDDATX18.));
   CALL SYMPUT('REPTMON',PUT(MONTH(REPTDATE),Z2.));
RUN;
*;
*------------------------------------------------*
*  MERGE WITH WRITTEN OFF ACCOUNT                *
*------------------------------------------------*;
PROC SORT DATA=NPL.LOAN&REPTMON;BY ACCTNO;
PROC SORT DATA=NPL.WAQ;BY ACCTNO;
DATA LOANWOFF;
   MERGE NPL.LOAN&REPTMON NPL.WAQ (IN=AA DROP=NOTENO NTBRCH);
   BY ACCTNO;
   IF AA THEN WRITEOFF = 'Y';ELSE WRITEOFF = 'N';
   IF LOANTYPE IN (983,993) THEN WDOWNIND = 'N';
   IF EARNTERM IN (0,.) THEN EARNTERM = NOTETERM;
*;
*------------------------------------------------*
*  CAL STATISTICS FOR EXISTING NPL ACCOUNTS      *
*------------------------------------------------*;
DATA LOAN1;
   KEEP BRANCH ACCTNO NOTENO NAME DAYS CURBALP CURBAL NETBALP NEWNPL
        ACCRINT RECOVER PL NPLW NPL LOANTYPE LOANTYP OIP ADJUST USER5
        BORSTAT COSTCTR PENDBRH;
   LENGTH LOANTYP $20;
   RETAIN NEWNPL 0 STMTH 1 ENMTH 12 STYR ENYR;
   %DCLVAR
   SET LOANWOFF;
 * SET NPL.LOAN&REPTMON;
   IF _N_ = 1 THEN DO;
      SET REPTDATE;
      STYR = YEAR(REPTDATE);
      ENYR = STYR - 1;
   END;
   IF EXIST = 'Y';
   IF WRITEOFF = 'Y' AND WDOWNIND ^= 'Y' THEN BORSTAT ='W';
   IF CURBAL = . THEN CURBAL = 0;
   ACCRINT = 0; UHC = 0; OI = 0; RECOVER = 0; PL = 0;
   REMMTH1=0;REMMTH2=0;REMMTHS=0;
   * IF LOANTYPE IN (380,381) THEN ADJUST = FEEAMT - FEETOT2;
   * ELSE ADJUST = FEEAMT8 - FEETOT2;
   ADJUST = FEEAMT - FEETOT2;
   IF DAYS <  90 & BORSTAT IN (' ','A','C','S','T','Y') & CURBAL >= 0
      & USER5 NE 'N' OR LOANTYPE IN (983,993) THEN DO;
      PL = NETBALP;
      IF DAYS = 0 AND CURBAL = 0 THEN DO;
         RECOVER = NETBALP;
         PL = 0;
      END;
   END;
   ELSE DO;
      IF LOANTYPE IN (380,381) THEN OI = FEEAMT;
      ELSE OI = FEEAMT;
      ACCRINT = FEEYTD;
      IF BORSTAT = 'F' THEN CURBALP = CURBALP - UHCP;
      IF TERMCHG > 0 OR (USER5 = 'N'
      AND LOANTYPE NOT IN (983,993)) THEN DO;
         REMMTH1 = EARNTERM - ((YEAR(BLDATE) - YEAR(ISSDTE))*12 +
                   MONTH(BLDATE) - MONTH(ISSDTE) + 1);
         REMMTH2 = EARNTERM - ((YEAR(REPTDATE) - YEAR(ISSDTE))*12 +
                   MONTH(REPTDATE) - MONTH(ISSDTE) + 1);
         REMMTHS = EARNTERM - ((STYR - YEAR(ISSDTE))*12 +
                   STMTH - MONTH(ISSDTE) + 1);
         IF REMMTH2 < 0 THEN REMMTH2 = 0;
         REMMTH1 = REMMTH1 - 1;
         IF REMMTHS >= REMMTH2 THEN
            DO REMMTH = REMMTHS TO REMMTH2 BY -1;
               ACCRINT + 2*(REMMTH+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
            END;
         IF REMMTH2 > 0 THEN
            UHC = REMMTH2*(REMMTH2+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
      END;
      IF BORSTAT = 'W' THEN NPLW = NETBALP;
      ELSE RECOVER = CURBALP - CURBAL + FEEPDYTD;
      IF RECOVER < 0 THEN DO;
         CURBALP = CURBALP - RECOVER;
         RECOVER = 0;
      END;
      NPL = CURBAL - UHC + OI;
      IF BORSTAT = 'W' THEN NPL = 0;
   END;
   BRANCH = PUT(NTBRCH,BRCHCD.)||' '||PUT(NTBRCH,Z3.);
   LOANTYP = PUT(LOANTYPE,LNTYP.);
   IF WRITEOFF = 'Y' OR LOANTYPE IN (983,993)THEN DO;
      ACCRINT = WACCRINT;
      NEWNPL = WNEWNPL;
      ADJUST = 0;
      IF WDOWNIND ^= 'Y' THEN DO;
         RECOVER = WRECOVER;
         PL = 0;
         NPL = 0;
         NPLW = SUM(NETBALP,NEWNPL,ACCRINT,(-1)*RECOVER,(-1)*PL);
      END;
      ELSE DO;
         NPLW = WNPLW;
         NPL  = SUM(NETBALP,NEWNPL,ACCRINT,(-1)*RECOVER,
                   (-1)*NPLW,(-1)*PL);
      END;
   END;
*;
*------------------------------------------------*
*  CAL STATISTICS FOR CURRENT NPL ACCOUNTS       *
*------------------------------------------------*;
DATA LOAN2;
   KEEP BRANCH ACCTNO NOTENO NAME DAYS CURBALP CURBAL NETBALP NEWNPL
        ACCRINT RECOVER PL NPLW NPL LOANTYPE LOANTYP OIP ADJUST USER5
        BORSTAT COSTCTR PENDBRH;
   LENGTH LOANTYP $20;
   RETAIN STMTH 1 ENMTH 12 STYR ENYR;
   %DCLVAR
   SET LOANWOFF;
 * SET NPL.LOAN&REPTMON;
   IF _N_ = 1 THEN DO;
      SET REPTDATE;
      STYR = YEAR(REPTDATE);
      ENYR = STYR - 1;
   END;
   REMMTH1=0;REMMTH2=0;
   IF EXIST ^= 'Y';
   UHC = 0; OI = 0;
   ADJUST = 0;
   /* IF LOANTYPE IN (380,381) THEN ADJUST = FEEAMT - FEETOT2;
   ELSE ADJUST = FEEAMT8 - FEETOT2; */
   IF WRITEOFF = 'Y' AND WDOWNIND ^= 'Y' THEN BORSTAT ='W';
   IF BLDATE > 0 & TERMCHG > 0 OR USER5 = 'N' THEN DO;
      REMMTH1 = EARNTERM - ((YEAR(BLDATE) - YEAR(ISSDTE))*12 +
                MONTH(BLDATE) - MONTH(ISSDTE) + 1);
      REMMTH2 = EARNTERM - ((YEAR(REPTDATE) - YEAR(ISSDTE))*12 +
                MONTH(REPTDATE) - MONTH(ISSDTE) + 1);
      IF REMMTH2 < 0 THEN REMMTH2 = 0;
      REMMTH1 = REMMTH1 - 1;
      IF REMMTH2 > 0 THEN
         UHC = REMMTH2*(REMMTH2+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
   END;
   ELSE DO;
      REMMTH2 = EARNTERM - ((YEAR(REPTDATE) - YEAR(ISSDTE))*12 +
                MONTH(REPTDATE) - MONTH(ISSDTE) + 1);
      IF REMMTH2 > 0 THEN
         UHC = REMMTH2*(REMMTH2+1)*TERMCHG/(EARNTERM*(EARNTERM+1));
   END;
   IF LOANTYPE IN (380,381) THEN OI = FEEAMT;
   ELSE OI = FEEAMT;
   NEWNPL = CURBAL - UHC + OI;
   NPL = NEWNPL;
   BRANCH = PUT(NTBRCH,BRCHCD.)||' '||PUT(NTBRCH,Z3.);
   LOANTYP = PUT(LOANTYPE,LNTYP.);
   IF WRITEOFF = 'Y' OR LOANTYPE IN (983,993)THEN DO;
      ACCRINT = WACCRINT;
      NEWNPL = WNEWNPL;
      ADJUST = 0;
      IF WDOWNIND ^= 'Y' THEN DO;
         RECOVER = WRECOVER;
         PL = 0;
         NPL = 0;
         NPLW = SUM(NETBALP,NEWNPL,ACCRINT,(-1)*RECOVER,(-1)*PL);
      END;
      ELSE DO;
         NPLW = WNPLW;
         NPL  = SUM(NETBALP,NEWNPL,ACCRINT,(-1)*RECOVER,
                   (-1)*NPLW,(-1)*PL);
      END;
   END;
*;
*------------------------------------------------*
*  COMBINE EXISTING & CURRENT NPL ACCOUNTS       *
*  CREATE VALUE TO CHECK DISCREPANCIES           *
*------------------------------------------------*;
DATA LOAN NPL.AQ;
   ARRAY VBL NETBALP NEWNPL ACCRINT RECOVER PL NPLW NPL;
   SET LOAN1 LOAN2;
   LENGTH RISK $13;
   IF DAYS > 364 OR BORSTAT = 'W' THEN RISK = 'BAD';
   ELSE IF DAYS > 273 THEN RISK = 'DOUBTFUL';
   ELSE IF DAYS > 182 THEN RISK = 'SUBSTANDARD 2';
   ELSE IF DAYS < 90 AND USER5='N' THEN RISK = 'SUBSTANDARD-1';
   ELSE RISK = 'SUBSTANDARD-1';
   DO OVER VBL;
      IF VBL = . THEN VBL = 0;
   END;
   CHKNPL = NETBALP+NEWNPL+ACCRINT-RECOVER-PL-NPLW;
   WHERE (COSTCTR < 3000 OR COSTCTR > 3999) AND
          COSTCTR NOT IN (4043,4048) AND
          COSTCTR NE .;
*;
*------------------------------------------------*
*  PRODUCE REPORTS                               *
*------------------------------------------------*;
OPTIONS NOCENTER NODATE NONUMBER MISSING=0;

PROC TABULATE DATA=LOAN FORMAT=COMMA17.2 MISSING NOSEPS;
   CLASS LOANTYP RISK BRANCH;
   VAR CURBALP CURBAL NETBALP NEWNPL PL ACCRINT RECOVER NPLW NPL ADJUST;
   TABLE LOANTYP=' ',
         RISK=' '*(BRANCH=' ' ALL='SUB-TOTAL') ALL='TOTAL',
         N='NO OF ACCOUNT'*F=COMMA7.
         SUM=' '*(CURBALP='BAL AS AT PREV YEAR (WITH UHC)'
                  CURBAL='BAL AS AT END OF RPT DATE (WITH UHC)'
                  NETBALP='NET BAL AS AT PREV YEAR (A)'
                  NEWNPL='NEW NPL DURING CURRENT YEAR (B)'
                  ACCRINT='ACCRUED INTEREST (C)'
                  RECOVER='RECOVERIES (D)'
                  PL='NPL CLASSIFIED AS PERFORMING (E)'
                  NPLW='NPL WRITTEN-OFF (F)'
                  ADJUST='ADJUSTMENT'
                  NPL='NPL AS AT END OF RPT DATE (A+B+C-D-E-F)')
         / BOX='RISK        BRANCH' RTS=29;
   TABLE LOANTYP=' ', BRANCH=' ' ALL='TOTAL',
         N='NO OF ACCOUNT'*F=COMMA7.
         SUM=' '*(CURBALP='BAL AS AT PREV YEAR (WITH UHC)'
                  CURBAL='BAL AS AT END OF RPT DATE (WITH UHC)'
                  NETBALP='NET BAL AS AT PREV YEAR (A)'
                  NEWNPL='NEW NPL DURING CURRENT YEAR (B)'
                  ACCRINT='ACCRUED INTEREST (C)'
                  RECOVER='RECOVERIES (D)'
                  PL='NPL CLASSIFIED AS PERFORMING (E)'
                  NPLW='NPL WRITTEN-OFF (F)'
                  ADJUST='ADJUSTMENT'
                  NPL='NPL AS AT END OF RPT DATE (A+B+C-D-E-F)')
         / BOX='BRANCH' RTS=10;
   TITLE1 'PUBLIC BANK - (NPL FROM 3 MONTHS & ABOVE)';
   TITLE2 'STATISTICS ON ASSET QUALITY - MOVEMENTS IN NPL' &RDATE;
*;

PROC SORT DATA=LOAN;
   BY LOANTYP BRANCH RISK DAYS ACCTNO;
*;
PROC PRINT LABEL N;
   FORMAT CURBALP CURBAL NETBALP NEWNPL ACCRINT RECOVER PL NPLW NPL
          COMMA14.2;
   LABEL ACCTNO  = 'MNI ACCOUNT NO'
         DAYS    = 'NO OF DAYS PAST DUE'
         CURBALP = 'BAL AS AT PREV YEAR (WITH UHC)'
         CURBAL  = 'BAL AS AT END OF RPT DATE (WITH UHC)'
         NETBALP = 'NET BAL AS AT PREV YEAR (A)'
         NEWNPL  = 'NEW NPL DURING CURRENT YEAR (B)'
         ACCRINT = 'ACCRUED INTEREST (C)'
         RECOVER = 'RECOVERIES (D)'
         PL      = 'NPL CLASSIFIED AS PERFORMING (E)'
         NPLW    = 'NPL WRITTEN-OFF (F)'
         ADJUST  = 'ADJUSTMENT'
         NPL     = 'NPL AS AT END OF RPT DATE (A+B+C-D-E-F)';
   VAR ACCTNO NAME DAYS CURBALP CURBAL NETBALP NEWNPL ACCRINT RECOVER
       PL NPLW NPL ADJUST;
   BY LOANTYP BRANCH RISK;
   PAGEBY BRANCH;
   SUMBY RISK;
   SUM CURBALP CURBAL NETBALP NEWNPL ACCRINT RECOVER PL NPLW NPL ADJUST;
*;
*------------------------------------------------*
*  PRODUCE DISCREPANCY REPORT                    *
*------------------------------------------------*;
  /*
PROC PRINT LABEL N;
   FORMAT CURBALP CURBAL NETBALP NEWNPL ACCRINT RECOVER PL NPLW NPL
          CHKNPL COMMA14.2;
   LABEL ACCTNO  = 'MNI ACCOUNT NO'
         DAYS    = 'NO OF DAYS PAST DUE'
         CURBALP = 'BAL AS AT PREV YEAR (WITH UHC)'
         CURBAL  = 'BAL AS AT END OF RPT DATE (WITH UHC)'
         NETBALP = 'NET BAL AS AT PREV YEAR (A)'
         NEWNPL  = 'NEW NPL DURING CURRENT YEAR (B)'
         ACCRINT = 'ACCRUED INTEREST (C)'
         RECOVER = 'RECOVERIES (D)'
         PL      = 'NPL CLASSIFIED AS PERFORMING (E)'
         NPLW    = 'NPL WRITTEN-OFF (F)'
         NPL     = 'NPL AS AT END OF RPT DATE (A+B+C-D-E-F)'
         CHKNPL  = '(A+B+C-D-E-F)';
   VAR ACCTNO NAME DAYS CURBALP CURBAL NETBALP NEWNPL ACCRINT RECOVER
       PL NPLW NPL CHKNPL;
   BY LOANTYP BRANCH RISK;
   WHERE ROUND(CHKNPL,0.01) ^= ROUND(NPL,0.01);
   TITLE1 'PUBLIC BANK - (NPL FROM 3 MONTHS & ABOVE)';
   TITLE2 'STATISTICS ON ASSET QUALITY - MOVEMENTS IN NPL' &RDATE;
   TITLE3 '(DISCREPANCY REPORT)';    */




this is nplntb


      *** TRANSFER OF BRANCH ***;
   /* IF  PENDBRH=236 THEN PENDBRH=069; ELSE
      IF  PENDBRH=033 THEN PENDBRH=140; ELSE
      IF  PENDBRH=048 THEN PENDBRH=113; ELSE
      IF  PENDBRH=107 THEN PENDBRH=171; ELSE
      IF  PENDBRH=111 THEN PENDBRH=231; ELSE
      IF  PENDBRH=138 THEN PENDBRH=094; ELSE
      IF  PENDBRH=162 THEN PENDBRH=036; ELSE
      IF  PENDBRH=184 THEN PENDBRH=032; ELSE
      IF  PENDBRH=223 THEN PENDBRH=024; ELSE
      IF  PENDBRH=227 THEN PENDBRH=081; ELSE
      IF  PENDBRH=229 THEN PENDBRH=151; ELSE
      IF  PENDBRH=240 THEN PENDBRH=133; ELSE
      IF  PENDBRH=241 THEN PENDBRH=019; ELSE
      IF  PENDBRH=246 THEN PENDBRH=146; ELSE
      IF  PENDBRH=250 THEN PENDBRH=092; ELSE
      IF  PENDBRH=051 THEN PENDBRH=209; ELSE
      IF  PENDBRH=173 THEN PENDBRH=056; ELSE   ESMR:2009-1451
      IF  PENDBRH=255 THEN PENDBRH=068;        ESMR:2009-2086 */
   /* IF  PENDBRH=200 THEN PENDBRH=122;        ESMR:2010-3206 */

   /* IF   NTBRCH=236 THEN  NTBRCH=069; ELSE
      IF   NTBRCH=033 THEN  NTBRCH=140; ELSE
      IF   NTBRCH=048 THEN  NTBRCH=113; ELSE
      IF   NTBRCH=107 THEN  NTBRCH=171; ELSE
      IF   NTBRCH=111 THEN  NTBRCH=231; ELSE
      IF   NTBRCH=138 THEN  NTBRCH=094; ELSE
      IF   NTBRCH=162 THEN  NTBRCH=036; ELSE
      IF   NTBRCH=184 THEN  NTBRCH=032; ELSE
      IF   NTBRCH=223 THEN  NTBRCH=024; ELSE
      IF   NTBRCH=227 THEN  NTBRCH=081; ELSE
      IF   NTBRCH=229 THEN  NTBRCH=151; ELSE
      IF   NTBRCH=240 THEN  NTBRCH=133; ELSE
      IF   NTBRCH=241 THEN  NTBRCH=019; ELSE
      IF   NTBRCH=246 THEN  NTBRCH=146; ELSE
      IF   NTBRCH=250 THEN  NTBRCH=092; ELSE
      IF   NTBRCH=253 THEN  NTBRCH=266; ELSE
      IF   NTBRCH=051 THEN  NTBRCH=209; ELSE
      IF   NTBRCH=173 THEN  NTBRCH=056; ELSE   ESMR:2009-1451
      IF   NTBRCH=255 THEN  NTBRCH=068;        ESMR:2009-2086 */
   /* IF   NTBRCH=200 THEN  NTBRCH=122;        ESMR:2010-3206 */

   /* IF   COSTCTR=236  THEN  COSTCTR=069; ELSE
      IF   COSTCTR=033  THEN  COSTCTR=140; ELSE
      IF   COSTCTR=048  THEN  COSTCTR=113; ELSE
      IF   COSTCTR=107  THEN  COSTCTR=171; ELSE
      IF   COSTCTR=111  THEN  COSTCTR=231; ELSE
      IF   COSTCTR=138  THEN  COSTCTR=094; ELSE
      IF   COSTCTR=162  THEN  COSTCTR=036; ELSE
      IF   COSTCTR=184  THEN  COSTCTR=032; ELSE
      IF   COSTCTR=223  THEN  COSTCTR=024; ELSE
      IF   COSTCTR=227  THEN  COSTCTR=081; ELSE
      IF   COSTCTR=229  THEN  COSTCTR=151; ELSE
      IF   COSTCTR=240  THEN  COSTCTR=133; ELSE
      IF   COSTCTR=241  THEN  COSTCTR=019; ELSE
      IF   COSTCTR=246  THEN  COSTCTR=146; ELSE
      IF   COSTCTR=250  THEN  COSTCTR=092; ELSE
      IF   COSTCTR=253  THEN  COSTCTR=266; ELSE
      IF   COSTCTR=051  THEN  COSTCTR=209; ELSE
      IF   COSTCTR=173  THEN  COSTCTR=056; ELSE   ESMR:2009-1451
      IF   COSTCTR=255  THEN  COSTCTR=068;        ESMR:2009-2086 */
   /* IF   COSTCTR=200  THEN  COSTCTR=122;        ESMR:2010-3206 */

   /* IF   COSTCTR=3236  THEN  COSTCTR=3069; ELSE
      IF   COSTCTR=3033  THEN  COSTCTR=3140; ELSE
      IF   COSTCTR=3048  THEN  COSTCTR=3113; ELSE
      IF   COSTCTR=3107  THEN  COSTCTR=3171; ELSE
      IF   COSTCTR=3111  THEN  COSTCTR=3231; ELSE
      IF   COSTCTR=3138  THEN  COSTCTR=3094; ELSE
      IF   COSTCTR=3162  THEN  COSTCTR=3036; ELSE
      IF   COSTCTR=3184  THEN  COSTCTR=3032; ELSE
      IF   COSTCTR=3223  THEN  COSTCTR=3024; ELSE
      IF   COSTCTR=3227  THEN  COSTCTR=3081; ELSE
      IF   COSTCTR=3229  THEN  COSTCTR=3151; ELSE
      IF   COSTCTR=3240  THEN  COSTCTR=3133; ELSE
      IF   COSTCTR=3241  THEN  COSTCTR=3019; ELSE
      IF   COSTCTR=3246  THEN  COSTCTR=3146; ELSE
      IF   COSTCTR=3250  THEN  COSTCTR=3092; ELSE
      IF   COSTCTR=3253  THEN  COSTCTR=3266; ELSE
      IF   COSTCTR=3051  THEN  COSTCTR=3209; ELSE
      IF   COSTCTR=3173  THEN  COSTCTR=3056; ELSE   ESMR:2009-1451
      IF   COSTCTR=3255  THEN  COSTCTR=3068;        ESMR:2009-2086 */
   /* IF   COSTCTR=3200  THEN  COSTCTR=3122;        ESMR:2010-3206 */

      *** SETUP OF HP CENTRE ***;
   /* IF  PENDBRH=024 THEN PENDBRH=800; ELSE
      IF  PENDBRH=045 THEN PENDBRH=800; ELSE
      IF  PENDBRH=016 THEN PENDBRH=800; ELSE
      IF  PENDBRH=060 THEN PENDBRH=801; ELSE
      IF  PENDBRH=121 THEN PENDBRH=801; ELSE
      IF  PENDBRH=204 THEN PENDBRH=801; ELSE
      IF  PENDBRH=154 THEN PENDBRH=801; ELSE
      IF  PENDBRH=053 THEN PENDBRH=802; ELSE
      IF  PENDBRH=120 THEN PENDBRH=802; ELSE
      IF  PENDBRH=170 THEN PENDBRH=802; ELSE
      IF  PENDBRH=252 THEN PENDBRH=802; ELSE
      IF  PENDBRH=033 THEN PENDBRH=803; ELSE
      IF  PENDBRH=140 THEN PENDBRH=803; ELSE
      IF  PENDBRH=228 THEN PENDBRH=803; ELSE
      IF  PENDBRH=007 THEN PENDBRH=804; ELSE
      IF  PENDBRH=089 THEN PENDBRH=804; ELSE
      IF  PENDBRH=216 THEN PENDBRH=804; ELSE
      IF  PENDBRH=217 THEN PENDBRH=804; ELSE
      IF  PENDBRH=037 THEN PENDBRH=805; ELSE
      IF  PENDBRH=079 THEN PENDBRH=805; ELSE
      IF  PENDBRH=110 THEN PENDBRH=805; ELSE
      IF  PENDBRH=010 THEN PENDBRH=806; ELSE
      IF  PENDBRH=238 THEN PENDBRH=806; ELSE
      IF  PENDBRH=004 THEN PENDBRH=807; ELSE
      IF  PENDBRH=172 THEN PENDBRH=807; ELSE
      IF  PENDBRH=231 THEN PENDBRH=807; ELSE
      IF  PENDBRH=171 THEN PENDBRH=808; ELSE
      IF  PENDBRH=253 THEN PENDBRH=808; ELSE
      IF  PENDBRH=265 THEN PENDBRH=808; ELSE
      IF  PENDBRH=266 THEN PENDBRH=808; ELSE
      IF  PENDBRH=005 THEN PENDBRH=809; ELSE
      IF  PENDBRH=049 THEN PENDBRH=809; ELSE
      IF  PENDBRH=080 THEN PENDBRH=809; ELSE
      IF  PENDBRH=046 THEN PENDBRH=811; ELSE
      IF  PENDBRH=168 THEN PENDBRH=811; ELSE
      IF  PENDBRH=196 THEN PENDBRH=811; ELSE
      IF  PENDBRH=002 THEN PENDBRH=812; ELSE
      IF  PENDBRH=248 THEN PENDBRH=812; ELSE
      IF  PENDBRH=129 THEN PENDBRH=812; ELSE
      IF  PENDBRH=038 THEN PENDBRH=812; ELSE
      IF  PENDBRH=066 THEN PENDBRH=812; ELSE
      IF  PENDBRH=226 THEN PENDBRH=812; ELSE
      IF  PENDBRH=032 THEN PENDBRH=813; ELSE
      IF  PENDBRH=185 THEN PENDBRH=813; ELSE
      IF  PENDBRH=125 THEN PENDBRH=815; ELSE
      IF  PENDBRH=019 THEN PENDBRH=815; ELSE
      IF  PENDBRH=036 THEN PENDBRH=815; ELSE
      IF  PENDBRH=124 THEN PENDBRH=816; ELSE
      IF  PENDBRH=148 THEN PENDBRH=816; ELSE
      IF  PENDBRH=018 THEN PENDBRH=816; ELSE
      IF  PENDBRH=035 THEN PENDBRH=816; ELSE
      IF  PENDBRH=267 THEN PENDBRH=816; ELSE
      IF  PENDBRH=006 THEN PENDBRH=817; ELSE
      IF  PENDBRH=054 THEN PENDBRH=817; ELSE
      IF  PENDBRH IN (040,169,225,230,232,262)
                      THEN PENDBRH=818; ELSE
      IF  PENDBRH IN (268,199,133,020,127)
                      THEN PENDBRH=814; ELSE
      IF  PENDBRH IN (008,264)
                      THEN PENDBRH=819; ELSE
      IF  PENDBRH IN (009,123,244)
                      THEN PENDBRH=823; ELSE
      IF  PENDBRH IN (135,078,153,025,081)
                      THEN PENDBRH=820; ELSE
      IF  PENDBRH IN (151,015,103,096,145)
                      THEN PENDBRH=822; ELSE
      IF  PENDBRH IN (094,041,128,141)
                      THEN PENDBRH=821; ELSE
      IF  PENDBRH IN (057,164)
                      THEN PENDBRH=824; ELSE
      IF  PENDBRH IN (270,157,200)
                      THEN PENDBRH=825; ELSE
      IF  PENDBRH IN (042,068)                 ESMR:2009-1451
                      THEN PENDBRH=826; ELSE   ESMR:2009-2086
      IF  PENDBRH IN (088)
                      THEN PENDBRH=826; ELSE
      IF  PENDBRH IN (277,013)
                      THEN PENDBRH=827;        ESMR:2016-2588 */

   /* IF  NTBRCH=024 THEN NTBRCH=800; ELSE
      IF  NTBRCH=045 THEN NTBRCH=800; ELSE
      IF  NTBRCH=016 THEN NTBRCH=800; ELSE
      IF  NTBRCH=060 THEN NTBRCH=801; ELSE
      IF  NTBRCH=121 THEN NTBRCH=801; ELSE
      IF  NTBRCH=204 THEN NTBRCH=801; ELSE
      IF  NTBRCH=154 THEN NTBRCH=801; ELSE
      IF  NTBRCH=053 THEN NTBRCH=802; ELSE
      IF  NTBRCH=120 THEN NTBRCH=802; ELSE
      IF  NTBRCH=170 THEN NTBRCH=802; ELSE
      IF  NTBRCH=252 THEN NTBRCH=802; ELSE
      IF  NTBRCH=033 THEN NTBRCH=803; ELSE
      IF  NTBRCH=140 THEN NTBRCH=803; ELSE
      IF  NTBRCH=228 THEN NTBRCH=803; ELSE
      IF  NTBRCH=007 THEN NTBRCH=804; ELSE
      IF  NTBRCH=089 THEN NTBRCH=804; ELSE
      IF  NTBRCH=216 THEN NTBRCH=804; ELSE
      IF  NTBRCH=217 THEN NTBRCH=804; ELSE
      IF  NTBRCH=037 THEN NTBRCH=805; ELSE
      IF  NTBRCH=079 THEN NTBRCH=805; ELSE
      IF  NTBRCH=110 THEN NTBRCH=805; ELSE
      IF  NTBRCH=010 THEN NTBRCH=806; ELSE
      IF  NTBRCH=238 THEN NTBRCH=806; ELSE
      IF  NTBRCH=004 THEN NTBRCH=807; ELSE
      IF  NTBRCH=172 THEN NTBRCH=807; ELSE
      IF  NTBRCH=231 THEN NTBRCH=807; ELSE
      IF  NTBRCH=171 THEN NTBRCH=808; ELSE
      IF  NTBRCH=253 THEN NTBRCH=808; ELSE
      IF  NTBRCH=265 THEN NTBRCH=808; ELSE
      IF  NTBRCH=266 THEN NTBRCH=808; ELSE
      IF  NTBRCH=005 THEN NTBRCH=809; ELSE
      IF  NTBRCH=049 THEN NTBRCH=809; ELSE
      IF  NTBRCH=080 THEN NTBRCH=809; ELSE
      IF  NTBRCH=046 THEN NTBRCH=811; ELSE
      IF  NTBRCH=168 THEN NTBRCH=811; ELSE
      IF  NTBRCH=196 THEN NTBRCH=811; ELSE
      IF  NTBRCH=002 THEN NTBRCH=812; ELSE
      IF  NTBRCH=248 THEN NTBRCH=812; ELSE
      IF  NTBRCH=129 THEN NTBRCH=812; ELSE
      IF  NTBRCH=038 THEN NTBRCH=812; ELSE
      IF  NTBRCH=066 THEN NTBRCH=812; ELSE
      IF  NTBRCH=226 THEN NTBRCH=812; ELSE
      IF  NTBRCH=032 THEN NTBRCH=813; ELSE
      IF  NTBRCH=185 THEN NTBRCH=813; ELSE
      IF  NTBRCH=125 THEN NTBRCH=815; ELSE
      IF  NTBRCH=019 THEN NTBRCH=815; ELSE
      IF  NTBRCH=036 THEN NTBRCH=815; ELSE
      IF  NTBRCH=124 THEN NTBRCH=816; ELSE
      IF  NTBRCH=148 THEN NTBRCH=816; ELSE
      IF  NTBRCH=018 THEN NTBRCH=816; ELSE
      IF  NTBRCH=035 THEN NTBRCH=816; ELSE
      IF  NTBRCH=267 THEN NTBRCH=816; ELSE
      IF  NTBRCH=006 THEN NTBRCH=817; ELSE
      IF  NTBRCH=054 THEN NTBRCH=817; ELSE
      IF  NTBRCH IN (040,169,225,230,232,262)
                     THEN NTBRCH=818; ELSE
      IF  NTBRCH  IN (268,199,133,020,127)
                     THEN NTBRCH=814; ELSE
      IF  NTBRCH  IN (008,264)
                     THEN NTBRCH=819; ELSE
      IF  NTBRCH  IN (009,123,244)
                      THEN NTBRCH=823;ELSE
      IF  NTBRCH  IN (135,078,153,025,081)
                      THEN NTBRCH=820;ELSE
      IF  NTBRCH  IN (151,015,103,096,145)
                      THEN NTBRCH=822;ELSE
      IF  NTBRCH  IN (094,041,128,141)
                      THEN NTBRCH=821;ELSE
      IF  NTBRCH  IN (057,164)
                      THEN NTBRCH=824;ELSE
      IF  NTBRCH  IN (270,157,200)
                      THEN NTBRCH=825;ELSE
      IF  NTBRCH  IN (042,068)               ESMR:2009-1451
                      THEN NTBRCH=826;ELSE   ESMR:2009-2086
      IF  NTBRCH  IN (088)
                      THEN NTBRCH=826;ELSE
      IF  NTBRCH  IN (277,013)
                      THEN NTBRCH=827;       ESMR:2016-2588 */

   /* IF  COSTCTR=024 THEN COSTCTR=800; ELSE
      IF  COSTCTR=045 THEN COSTCTR=800; ELSE
      IF  COSTCTR=016 THEN COSTCTR=800; ELSE
      IF  COSTCTR=060 THEN COSTCTR=801; ELSE
      IF  COSTCTR=121 THEN COSTCTR=801; ELSE
      IF  COSTCTR=204 THEN COSTCTR=801; ELSE
      IF  COSTCTR=154 THEN COSTCTR=801; ELSE
      IF  COSTCTR=053 THEN COSTCTR=802; ELSE
      IF  COSTCTR=120 THEN COSTCTR=802; ELSE
      IF  COSTCTR=170 THEN COSTCTR=802; ELSE
      IF  COSTCTR=252 THEN COSTCTR=802; ELSE
      IF  COSTCTR=033 THEN COSTCTR=803; ELSE
      IF  COSTCTR=140 THEN COSTCTR=803; ELSE
      IF  COSTCTR=228 THEN COSTCTR=803; ELSE
      IF  COSTCTR=007 THEN COSTCTR=804; ELSE
      IF  COSTCTR=089 THEN COSTCTR=804; ELSE
      IF  COSTCTR=216 THEN COSTCTR=804; ELSE
      IF  COSTCTR=217 THEN COSTCTR=804; ELSE
      IF  COSTCTR=037 THEN COSTCTR=805; ELSE
      IF  COSTCTR=079 THEN COSTCTR=805; ELSE
      IF  COSTCTR=110 THEN COSTCTR=805; ELSE
      IF  COSTCTR=010 THEN COSTCTR=806; ELSE
      IF  COSTCTR=238 THEN COSTCTR=806; ELSE
      IF  COSTCTR=004 THEN COSTCTR=807; ELSE
      IF  COSTCTR=172 THEN COSTCTR=807; ELSE
      IF  COSTCTR=231 THEN COSTCTR=807; ELSE
      IF  COSTCTR=171 THEN COSTCTR=808; ELSE
      IF  COSTCTR=253 THEN COSTCTR=808; ELSE
      IF  COSTCTR=265 THEN COSTCTR=808; ELSE
      IF  COSTCTR=266 THEN COSTCTR=808; ELSE
      IF  COSTCTR=005 THEN COSTCTR=809; ELSE
      IF  COSTCTR=049 THEN COSTCTR=809; ELSE
      IF  COSTCTR=080 THEN COSTCTR=809; ELSE
      IF  COSTCTR=046 THEN COSTCTR=811; ELSE
      IF  COSTCTR=168 THEN COSTCTR=811; ELSE
      IF  COSTCTR=196 THEN COSTCTR=811; ELSE
      IF  COSTCTR=002 THEN COSTCTR=812; ELSE
      IF  COSTCTR=248 THEN COSTCTR=812; ELSE
      IF  COSTCTR=129 THEN COSTCTR=812; ELSE
      IF  COSTCTR=038 THEN COSTCTR=812; ELSE
      IF  COSTCTR=066 THEN COSTCTR=812; ELSE
      IF  COSTCTR=226 THEN COSTCTR=812; ELSE
      IF  COSTCTR=032 THEN COSTCTR=813; ELSE
      IF  COSTCTR=185 THEN COSTCTR=813; ELSE
      IF  COSTCTR=125 THEN COSTCTR=815; ELSE
      IF  COSTCTR=019 THEN COSTCTR=815; ELSE
      IF  COSTCTR=036 THEN COSTCTR=815; ELSE
      IF  COSTCTR=124 THEN COSTCTR=816; ELSE
      IF  COSTCTR=148 THEN COSTCTR=816; ELSE
      IF  COSTCTR=018 THEN COSTCTR=816; ELSE
      IF  COSTCTR=035 THEN COSTCTR=816; ELSE
      IF  COSTCTR=267 THEN COSTCTR=816; ELSE
      IF  COSTCTR=006 THEN COSTCTR=817; ELSE
      IF  COSTCTR=054 THEN COSTCTR=817; ELSE
      IF  COSTCTR IN (040,169,225,230,232,262)
                      THEN COSTCTR=818; ELSE
      IF  COSTCTR IN (268,199,133,020,127)
                      THEN COSTCTR=814; ELSE
      IF  COSTCTR IN (008,264)
                      THEN COSTCTR=819; ELSE
      IF  COSTCTR IN (009,123,244)
                      THEN COSTCTR=823; ELSE
      IF  COSTCTR IN (135,078,153,025,081)
                      THEN COSTCTR=820; ELSE
      IF  COSTCTR IN (151,015,103,096,145)
                      THEN COSTCTR=822; ELSE
      IF  COSTCTR IN (094,041,128,141)
                      THEN COSTCTR=821; ELSE
      IF  COSTCTR IN (057,164)
                      THEN COSTCTR=824; ELSE
      IF  COSTCTR IN (270,157,200)
                      THEN COSTCTR=825; ELSE
      IF  COSTCTR IN (042,068)                 ESMR:2009-1451
                      THEN COSTCTR=826; ELSE   ESMR:2009-2086
      IF  COSTCTR IN (088)
                      THEN COSTCTR=826; ELSE
      IF  COSTCTR IN (277,013)
                      THEN COSTCTR=827;        ESMR:2016-2588 */

   /* IF  COSTCTR=3024 THEN COSTCTR=3800; ELSE
      IF  COSTCTR=3045 THEN COSTCTR=3800; ELSE
      IF  COSTCTR=3016 THEN COSTCTR=3800; ELSE
      IF  COSTCTR=3060 THEN COSTCTR=3801; ELSE
      IF  COSTCTR=3121 THEN COSTCTR=3801; ELSE
      IF  COSTCTR=3204 THEN COSTCTR=3801; ELSE
      IF  COSTCTR=3154 THEN COSTCTR=3801; ELSE
      IF  COSTCTR=3053 THEN COSTCTR=3802; ELSE
      IF  COSTCTR=3120 THEN COSTCTR=3802; ELSE
      IF  COSTCTR=3170 THEN COSTCTR=3802; ELSE
      IF  COSTCTR=3252 THEN COSTCTR=3802; ELSE
      IF  COSTCTR=3033 THEN COSTCTR=3803; ELSE
      IF  COSTCTR=3140 THEN COSTCTR=3803; ELSE
      IF  COSTCTR=3228 THEN COSTCTR=3803; ELSE
      IF  COSTCTR=3007 THEN COSTCTR=3804; ELSE
      IF  COSTCTR=3089 THEN COSTCTR=3804; ELSE
      IF  COSTCTR=3216 THEN COSTCTR=3804; ELSE
      IF  COSTCTR=3217 THEN COSTCTR=3804; ELSE
      IF  COSTCTR=3037 THEN COSTCTR=3805; ELSE
      IF  COSTCTR=3079 THEN COSTCTR=3805; ELSE
      IF  COSTCTR=3110 THEN COSTCTR=3805; ELSE
      IF  COSTCTR=3010 THEN COSTCTR=3806; ELSE
      IF  COSTCTR=3238 THEN COSTCTR=3806; ELSE
      IF  COSTCTR=3004 THEN COSTCTR=3807; ELSE
      IF  COSTCTR=3172 THEN COSTCTR=3807; ELSE
      IF  COSTCTR=3231 THEN COSTCTR=3807; ELSE
      IF  COSTCTR=3171 THEN COSTCTR=3808; ELSE
      IF  COSTCTR=3253 THEN COSTCTR=3808; ELSE
      IF  COSTCTR=3265 THEN COSTCTR=3808; ELSE
      IF  COSTCTR=3266 THEN COSTCTR=3808; ELSE
      IF  COSTCTR=3005 THEN COSTCTR=3809; ELSE
      IF  COSTCTR=3049 THEN COSTCTR=3809; ELSE
      IF  COSTCTR=3080 THEN COSTCTR=3809; ELSE
      IF  COSTCTR=3046 THEN COSTCTR=3811; ELSE
      IF  COSTCTR=3168 THEN COSTCTR=3811; ELSE
      IF  COSTCTR=3196 THEN COSTCTR=3811; ELSE
      IF  COSTCTR=3002 THEN COSTCTR=3812; ELSE
      IF  COSTCTR=3248 THEN COSTCTR=3812; ELSE
      IF  COSTCTR=3129 THEN COSTCTR=3812; ELSE
      IF  COSTCTR=3038 THEN COSTCTR=3812; ELSE
      IF  COSTCTR=3066 THEN COSTCTR=3812; ELSE
      IF  COSTCTR=3226 THEN COSTCTR=3812; ELSE
      IF  COSTCTR=3032 THEN COSTCTR=3813; ELSE
      IF  COSTCTR=3185 THEN COSTCTR=3813; ELSE
      IF  COSTCTR=3125 THEN COSTCTR=3815; ELSE
      IF  COSTCTR=3019 THEN COSTCTR=3815; ELSE
      IF  COSTCTR=3036 THEN COSTCTR=3815; ELSE
      IF  COSTCTR=3124 THEN COSTCTR=3816; ELSE
      IF  COSTCTR=3148 THEN COSTCTR=3816; ELSE
      IF  COSTCTR=3018 THEN COSTCTR=3816; ELSE
      IF  COSTCTR=3035 THEN COSTCTR=3816; ELSE
      IF  COSTCTR=3267 THEN COSTCTR=3816; ELSE
      IF  COSTCTR=3006 THEN COSTCTR=3817; ELSE
      IF  COSTCTR=3054 THEN COSTCTR=3817; ELSE
      IF  COSTCTR IN (3040,3169,3225,3230,3232,3262)
                       THEN COSTCTR=3818; ELSE
      IF  COSTCTR IN (3268,3199,3133,3020,3127)
                      THEN COSTCTR=3814;  ELSE
      IF  COSTCTR IN (3008,3264)
                      THEN COSTCTR=3819;  ELSE
      IF  COSTCTR IN (3009,3123,3244)
                      THEN COSTCTR=3823;  ELSE
      IF  COSTCTR IN (3135,3078,3153,3025,3081)
                      THEN COSTCTR=3820; ELSE
      IF  COSTCTR IN (3151,3015,3103,3096,3145)
                      THEN COSTCTR=3822; ELSE
      IF  COSTCTR IN (3094,3041,3128,3141)
                      THEN COSTCTR=3821; ELSE
      IF  COSTCTR IN (3057,3164)
                      THEN COSTCTR=3824; ELSE
      IF  COSTCTR IN (3270,3157,3200)
                      THEN COSTCTR=3825; ELSE
      IF  COSTCTR IN (3042,3068)               ESMR:2009-1451
                      THEN COSTCTR=3826; ELSE  ESMR:2009-2086
      IF  COSTCTR IN (3088)
                      THEN COSTCTR=3826; ELSE
      IF  COSTCTR IN (3277,3013)
                      THEN COSTCTR=3827;       ESMR:2016-2588 */


