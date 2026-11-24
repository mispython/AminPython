"""Fixed record layouts shared by the CCD report programs."""

LAYOUTS = {'pbb': {'summary': [{'branch': ['@1   BRANCH Z3.           @5   NOACC1 COMMA7.0  @13  BRHAMT1 '
                                 'COMMA16.2           @30  NOACC2 COMMA7.0  @38  BRHAMT2 COMMA15.2           @54  '
                                 'NOACC3 COMMA7.0  @62  BRHAMT3 COMMA15.2           @78  NOACC4 COMMA8.0  @87  '
                                 'BRHAMT4 COMMA17.2           @105 NOACC5 COMMA8.0  @114 BRHAMT5 COMMA17.2',
                                 '@1   BRHCODE           @5   NOACC6 COMMA7.0  @13  BRHAMT6 COMMA16.2           '
                                 '@30  NOACC7 COMMA7.0  @38  BRHAMT7 COMMA15.2           @54  NOACC8 COMMA7.0  '
                                 '@62  BRHAMT8 COMMA15.2           @78  NOACC9 COMMA8.0  @87  BRHAMT9 '
                                 'COMMA17.2           @105 NOACC10 COMMA8.0 @114 BRHAMT10 COMMA17.2',
                                 '@5   NOACC11 COMMA7.0 @13  BRHAMT11 COMMA16.2           @30  NOACC12 COMMA7.0 '
                                 '@38  BRHAMT12 COMMA15.2           @54  NOACC13 COMMA7.0 @62  BRHAMT13 '
                                 'COMMA15.2           @78  NOACC14 COMMA8.0 @87  BRHAMT14 COMMA17.2           '
                                 '@105 NOACC15 COMMA8.0 @114 BRHAMT15 COMMA17.2',
                                 '@5   NOACC16 COMMA7.0 @13  BRHAMT16 COMMA16.2           @30  NOACC17 COMMA7.0 '
                                 '@38  BRHAMT17 COMMA15.2           @54  SUBACC COMMA7.0  @62  SUBBRH  '
                                 'COMMA15.2           @78  SUBAC2 COMMA8.0  @87  SUBBR2  COMMA17.2           @105 '
                                 'SOTACC COMMA8.0  @114 TOTBRH  COMMA17.2'],
                      'total': ["@1   '----------------------------------------'           @41  "
                                "'----------------------------------------'           @81  "
                                "'----------------------------------------'           @121 '----------'",
                                "@1  'TOT'           @5   TOTACC1 COMMA7.0  @13  TOTAMT1 COMMA16.2           @30  "
                                'TOTACC2 COMMA7.0  @38  TOTAMT2 COMMA15.2           @54  TOTACC3 COMMA7.0  @62  '
                                'TOTAMT3 COMMA15.2           @78  TOTACC4 COMMA8.0  @87  TOTAMT4 '
                                'COMMA17.2           @105 TOTACC5 COMMA8.0  @114 TOTAMT5 COMMA17.2',
                                '@5   TOTACC6 COMMA7.0  @13  TOTAMT6 COMMA16.2           @30  TOTACC7 COMMA7.0  '
                                '@38  TOTAMT7 COMMA15.2           @54  TOTACC8 COMMA7.0  @62  TOTAMT8 '
                                'COMMA15.2           @78  TOTACC9 COMMA8.0  @87  TOTAMT9 COMMA17.2           @105 '
                                'TOTACC10 COMMA8.0 @114 TOTAMT10 COMMA17.2',
                                '@5   TOTACC11 COMMA7.0 @13  TOTAMT11 COMMA16.2           @30  TOTACC12 COMMA7.0 '
                                '@38  TOTAMT12 COMMA15.2           @54  TOTACC13 COMMA7.0 @62  TOTAMT13 '
                                'COMMA15.2           @78  TOTACC14 COMMA8.0 @87  TOTAMT14 COMMA17.2           '
                                '@105 TOTACC15 COMMA8.0 @114 TOTAMT15 COMMA17.2',
                                '@5   TOTACC16 COMMA7.0 @13  TOTAMT16 COMMA16.2           @30  TOTACC17 COMMA7.0 '
                                '@38  TOTAMT17 COMMA15.2           @54  SGTOTACC COMMA7.0 @62  SGTOTBRH '
                                'COMMA15.2           @78  SGTOTAC2 COMMA8.0 @87  SGTOTBR2 COMMA17.2           '
                                '@105 GTOTACC COMMA8.0  @114 GTOTBRH  COMMA17.2',
                                "@1   '----------------------------------------'           @41  "
                                "'----------------------------------------'           @81  "
                                "'----------------------------------------'           @121 '----------'",
                                ''],
                      'header': ["@1   'PROGRAM-ID : LNCCD002'         @43  'P U B L I C   B A N K   B E R H A "
                                 "D'         @118 'PAGE NO.: ' PAGECNT",
                                 "@40  'OUTSTANDING LOANS IN ARREARS '         @69  TYPE  $14.         @85  "
                                 '"&RDATE"',
                                 "@1   ' '",
                                 "@1   'BRH    NO          < 1 MTH'         @33         'NO     1 TO < 2 "
                                 "MTH'         @58         'NO     2 TO < 3 MTH'         @84        'NO      3 TO "
                                 "< 4 MTH'         @111       'NO      4 TO < 5 MTH'",
                                 "@1   '       NO     5 TO < 6 MTH'         @33         'NO     6 TO < 7 "
                                 "MTH'         @58         'NO     7 TO < 8 MTH'         @84        'NO      8 TO "
                                 "< 9 MTH'         @111       'NO     9 TO < 10 MTH'",
                                 "@1   '       NO   10 TO < 11 MTH'         @33         'NO   11 TO < 12 "
                                 "MTH'         @58         'NO   12 TO < 18 MTH'         @84        'NO    18 TO "
                                 "< 24 MTH'         @111       'NO    24 TO < 36 MTH'",
                                 "@1   '       NO         > 36 MTH'         @33         'NO          "
                                 "DEFICIT'         @58        'NO   SUBTOTAL >=3MTH'         @84        'NO   "
                                 "SUBTOTAL >=6MTH'         @111       'NO             TOTAL'",
                                 "@1   '----------------------------------------'         @41  "
                                 "'----------------------------------------'         @81  "
                                 "'----------------------------------------'         @121 '----------'"]},
                     {'branch': ['@1   BRANCH Z3.               @5   NOACC1 COMMA7.0  @13  BRHAMT1 '
                                 'COMMA16.2               @30  NOACC2 COMMA7.0  @38  BRHAMT2 '
                                 'COMMA15.2               @54  NOACC3 COMMA7.0  @62  BRHAMT3 '
                                 'COMMA15.2               @78  NOACC4 COMMA8.0  @87  BRHAMT4 '
                                 'COMMA17.2               @105 NOACC5 COMMA8.0  @114 BRHAMT5 COMMA17.2',
                                 '@1   BRHCODE               @5   NOACC6  COMMA7.0  @13  BRHAMT6 '
                                 'COMMA16.2               @30  NOACC7  COMMA7.0  @38  BRHAMT7 '
                                 'COMMA15.2               @54  NOACC8  COMMA7.0  @62  BRHAMT8 '
                                 'COMMA15.2               @78  NOACC9  COMMA8.0  @87  BRHAMT9 '
                                 'COMMA17.2               @105 NOACC10 COMMA8.0  @114 BRHAMT10 COMMA17.2',
                                 '@5   NOACC11 COMMA7.0  @13  BRHAMT11 COMMA16.2               @30  NOACC12 '
                                 'COMMA7.0  @38  BRHAMT12 COMMA15.2               @54  NOACC13 COMMA7.0  @62  '
                                 'BRHAMT13 COMMA15.2               @78  NOACC14 COMMA8.0  @87  BRHAMT14 '
                                 'COMMA17.2               @105 NOACC15 COMMA8.0  @114 BRHAMT15 COMMA17.2',
                                 '@54  SUBACC  COMMA7.0  @62  SUBBRH  COMMA15.2               @78  SUBAC2  '
                                 'COMMA8.0  @87  SUBBR2  COMMA17.2               @105 SOTACC  COMMA8.0  @114 '
                                 'TOTBRH  COMMA17.2'],
                      'total': ["@1   '----------------------------------------'               @41  "
                                "'----------------------------------------'               @81  "
                                "'----------------------------------------'               @121 '----------'",
                                "@1  'TOT'               @5   TOTACC1 COMMA7.0  @13  TOTAMT1 "
                                'COMMA16.2               @30  TOTACC2 COMMA7.0  @38  TOTAMT2 '
                                'COMMA15.2               @54  TOTACC3 COMMA7.0  @62  TOTAMT3 '
                                'COMMA15.2               @78  TOTACC4 COMMA8.0  @87  TOTAMT4 '
                                'COMMA17.2               @105 TOTACC5 COMMA8.0  @114 TOTAMT5 COMMA17.2',
                                '@5   TOTACC6 COMMA7.0  @13  TOTAMT6 COMMA16.2               @30  TOTACC7 '
                                'COMMA7.0  @38  TOTAMT7 COMMA15.2               @54  TOTACC8 COMMA7.0  @62  '
                                'TOTAMT8 COMMA15.2               @78  TOTACC9 COMMA8.0  @87  TOTAMT9 '
                                'COMMA17.2               @105 TOTACC10 COMMA8.0 @114 TOTAMT10 COMMA17.2',
                                '@5   TOTACC11 COMMA7.0 @13  TOTAMT11 COMMA16.2               @30  TOTACC12 '
                                'COMMA7.0 @38  TOTAMT12 COMMA15.2               @54  TOTACC13 COMMA7.0 @62  '
                                'TOTAMT13 COMMA15.2               @78  TOTACC14 COMMA8.0 @87  TOTAMT14 '
                                'COMMA17.2               @105 TOTACC15 COMMA8.0 @114 TOTAMT15 COMMA17.2',
                                '@54  SGTOTACC COMMA7.0 @62  SGTOTBRH COMMA15.2               @78  SGTOTAC2 '
                                'COMMA8.0 @87  SGTOTBR2 COMMA17.2               @105 GTOTACC COMMA8.0  @114 '
                                'GTOTBRH  COMMA17.2',
                                "@1   '----------------------------------------'               @41  "
                                "'----------------------------------------'               @81  "
                                "'----------------------------------------'               @121 '----------'",
                                ''],
                      'header': ["@1   'PROGRAM-ID : LNCCD02A'             @43  'P U B L I C   B A N K   B E R H "
                                 "A D'             @118 'PAGE NO.: ' PAGECNT",
                                 "@45  'OUTSTANDING LOANS IN ARREARS '             @74  TYPE  $14.             "
                                 '@90  "&RDATE"',
                                 "@1   ' '",
                                 "@1   'BRH    NO          < 1 MTH'             @33         'NO     1 TO < 2 "
                                 "MTH'             @58         'NO     2 TO < 3 MTH'             @84        "
                                 "'NO      3 TO < 4 MTH'             @111       'NO      4 TO < 5 MTH'",
                                 "@1   '       NO     5 TO < 6 MTH'             @33         'NO     6 TO < 7 "
                                 "MTH'             @58         'NO     7 TO < 8 MTH'             @84        "
                                 "'NO      8 TO < 9 MTH'             @111       'NO     9 TO < 12 MTH'",
                                 "@1   '       NO   12 TO < 18 MTH'             @33         'NO   18 TO < 24 "
                                 "MTH'             @58         'NO   24 TO < 36 MTH'             @84        "
                                 "'NO          > 36 MTH'             @111       'NO           DEFICIT'",
                                 "@58        'NO   SUBTOTAL >=3MTH'             @84        'NO   SUBTOTAL "
                                 ">=6MTH'             @111       'NO             TOTAL'",
                                 "@1   '----------------------------------------'             @41  "
                                 "'----------------------------------------'             @81  "
                                 "'----------------------------------------'             @121 '----------'"]},
                     {'branch': ['@1   BRANCH Z3.           @5   NOACC1 COMMA7.0  @13  BRHAMT1 '
                                 'COMMA16.2           @30  NOACC2 COMMA7.0  @38  BRHAMT2 COMMA15.2           @54  '
                                 'NOACC3 COMMA7.0  @62  BRHAMT3 COMMA15.2           @78  NOACC4 COMMA8.0  @87  '
                                 'BRHAMT4 COMMA17.2           @105 NOACC5 COMMA8.0  @114 BRHAMT5 COMMA17.2',
                                 '@1   BRHCODE           @5   NOACC6 COMMA7.0  @13  BRHAMT6 COMMA16.2           '
                                 '@30  NOACC7 COMMA7.0  @38  BRHAMT7 COMMA15.2           @54  NOACC8 COMMA7.0  '
                                 '@62  BRHAMT8 COMMA15.2           @78  NOACC9 COMMA8.0  @87  BRHAMT9 '
                                 'COMMA17.2           @105 NOACC10 COMMA8.0 @114 BRHAMT10 COMMA17.2',
                                 '@5   NOACC11 COMMA7.0 @13  BRHAMT11 COMMA16.2           @30  NOACC12 COMMA7.0 '
                                 '@38  BRHAMT12 COMMA15.2           @54  NOACC13 COMMA7.0 @62  BRHAMT13 '
                                 'COMMA15.2           @78  NOACC14 COMMA8.0 @87  BRHAMT14 COMMA17.2           '
                                 '@105 NOACC15 COMMA8.0 @114 BRHAMT15 COMMA17.2',
                                 '@5   NOACC16 COMMA7.0 @13  BRHAMT16 COMMA16.2           @30  NOACC17 COMMA7.0 '
                                 '@38  BRHAMT17 COMMA15.2           @54  SUBACC  COMMA7.0 @62  SUBBRH   '
                                 'COMMA15.2           @78  SUBAC2  COMMA8.0 @87  SUBBR2   COMMA17.2           '
                                 '@105 SOTACC  COMMA8.0 @114 TOTBRH   COMMA17.2'],
                      'total': ["@1   '----------------------------------------'           @41  "
                                "'----------------------------------------'           @81  "
                                "'----------------------------------------'           @121 '----------'",
                                "@1  'TOT'           @5   TOTACC1 COMMA7.0  @13  TOTAMT1 COMMA16.2           @30  "
                                'TOTACC2 COMMA7.0  @38  TOTAMT2 COMMA15.2           @54  TOTACC3 COMMA7.0  @62  '
                                'TOTAMT3 COMMA15.2           @78  TOTACC4 COMMA8.0  @87  TOTAMT4 '
                                'COMMA17.2           @105 TOTACC5 COMMA8.0  @114 TOTAMT5 COMMA17.2',
                                '@5   TOTACC6 COMMA7.0  @13  TOTAMT6 COMMA16.2           @30  TOTACC7 COMMA7.0  '
                                '@38  TOTAMT7 COMMA15.2           @54  TOTACC8 COMMA7.0  @62  TOTAMT8 '
                                'COMMA15.2           @78  TOTACC9 COMMA8.0  @87  TOTAMT9 COMMA17.2           @105 '
                                'TOTACC10 COMMA8.0 @114 TOTAMT10 COMMA17.2',
                                '@5   TOTACC11 COMMA7.0 @13  TOTAMT11 COMMA16.2           @30  TOTACC12 COMMA7.0 '
                                '@38  TOTAMT12 COMMA15.2           @54  TOTACC13 COMMA7.0 @62  TOTAMT13 '
                                'COMMA15.2           @78  TOTACC14 COMMA8.0 @87  TOTAMT14 COMMA17.2           '
                                '@105 TOTACC15 COMMA8.0 @114 TOTAMT15 COMMA17.2',
                                '@5   TOTACC16 COMMA7.0 @13  TOTAMT16 COMMA16.2           @30  TOTACC17 COMMA7.0 '
                                '@38  TOTAMT17 COMMA15.2           @54  SGTOTACC COMMA7.0 @62  SGTOTBRH '
                                'COMMA15.2           @78  SGTOTAC2 COMMA8.0 @87  SGTOTBR2 COMMA17.2           '
                                '@105 GTOTACC COMMA8.0  @114 GTOTBRH  COMMA17.2',
                                "@1   '----------------------------------------'           @41  "
                                "'----------------------------------------'           @81  "
                                "'----------------------------------------'           @121 '----------'",
                                ''],
                      'header': ["@1   'PROGRAM-ID : LNCCD004'         @43  'P U B L I C   B A N K   B E R H A "
                                 "D'         @118 'PAGE NO.: ' PAGECNT",
                                 "@41  'OUTSTANDING LOANS CLASSIFIED AS NPL '         @77  TYPE  $14.         "
                                 '@91  "&RDATE"',
                                 "@1   ' '",
                                 "@1   'BRH     NO         < 1 MTH'         @34         'NO     1 TO < 2 "
                                 "MTH'         @59         'NO     2 TO < 3 MTH'         @84        'NO      3 TO "
                                 "< 4 MTH'         @111       'NO      4 TO < 5 MTH'",
                                 "@1   '        NO    5 TO < 6 MTH'         @34         'NO     6 TO < 7 "
                                 "MTH'         @59         'NO     7 TO < 8 MTH'         @84        'NO      8 TO "
                                 "< 9 MTH'         @111       'NO     9 TO < 10 MTH'",
                                 "@1   '        NO  10 TO < 11 MTH'         @34         'NO   11 TO < 12 "
                                 "MTH'         @59         'NO   12 TO < 18 MTH'         @84        'NO    18 TO "
                                 "< 24 MTH'         @111       'NO    24 TO < 36 MTH'",
                                 "@1   '        NO        > 36 MTH'         @34         'NO          "
                                 "DEFICIT'         @59        'NO   SUBTOTAL >=3MTH'         @84        'NO   "
                                 "SUBTOTAL >=6MTH'         @111       'NO             TOTAL'",
                                 "@1   '----------------------------------------'         @41  "
                                 "'----------------------------------------'         @81  "
                                 "'----------------------------------------'         @121 '----------'"]}],
         'detail': {'body': ['@1   BRHCODE        @5   ACCTNO              @16  NAME        @41  '
                             'NOTENO              @54  PRODUCT        @59  BORSTAT             @68  ISSDTE   '
                             'DDMMYY8.        @79  DAYDIFF             @84  ARREARS        @98  BALANCE  '
                             'COMMA17.2  @116 NOISTLPD COMMA7.        @127 DELQCD   $5.',
                             '@5   LASTRAN  DDMMYY8.   @16  MATURDT  DDMMYY8.        @29  LSTTRNAM COMMA17.2  '
                             '@46  PAYAMT   COMMA11.2        @59  COLLDESC',
                             '@35   CAP COMMA16.2',
                             "@1   ' '",
                             "@41  '----------------------------------------'           @81  "
                             "'----------------------------------------'           @121 '----------'",
                             "@5   'SUBTOTAL'         @35 BRHCAP COMMA16.2                                  @100 "
                             'BRHARR COMMA17.2',
                             "@41  '----------------------------------------'           @81  "
                             "'----------------------------------------'           @121 '----------'",
                             '',
                             "@41  '----------------------------------------'           @81  "
                             "'----------------------------------------'           @121 '----------'",
                             "@5   'BRANCH TOTAL'    @35 BRHCAPB COMMA16.2                                  @100 "
                             'BRHAMT COMMA17.2',
                             "@41  '----------------------------------------'           @81  "
                             "'----------------------------------------'           @121 '----------'",
                             '',
                             "@41  '----------------------------------------'           @81  "
                             "'----------------------------------------'           @121 '----------'",
                             "@5   'GRAND TOTAL'     @35 TOTALCAP COMMA16.2                                    "
                             '@100 TOTAL COMMA17.2',
                             "@41  '----------------------------------------'           @81  "
                             "'----------------------------------------'           @121 '----------'",
                             ''],
                    'header': ['_PAGE_',
                               "@1   'PROGRAM-ID : LNCCDQ10 - BRANCH : ' BRANCH  3.         @43  'P U B L I C   B "
                               "A N K   B E R H A D'         @118 'PAGE NO.: ' PAGECNT",
                               "@39  TYPE '2 MTHS & ABOVE AND NEW A/C WITH ARREAR '              'AS AT ' "
                               '"&RDATE"',
                               "@1   ' '",
                               "@1   'BRH'         @5   'ACCTNO'           @16 'NAME'         @40  "
                               "'NOTENO'           @50 'PRODUCT'         @59  'BORSTAT'          @68 'ISSUE "
                               "DT'         @78  'DAYS'             @84 'ARREARS'         @108 'BALANCE'          "
                               "@116 'NO ISTL'         @127 'DELQ'",
                               "@1   ' '         @5   'LST TR DT'        @16  'MAT. DATE'         @36  'LST TR "
                               "AMT'       @49  'ISTL AMT'         @69  'COLLATERAL DESCRIPTION'         @116 '   "
                               "PAID'          @127 'CODE'",
                               "@35   'CAPCLOSE'",
                               "@1   '----------------------------------------'         @41  "
                               "'----------------------------------------'         @81  "
                               "'----------------------------------------'         @121 '----------'"]}},
 'pibb': {'summary': [{'branch': ['@1   BRANCH Z3.           @5   NOACC1 COMMA7.0  @13  BRHAMT1 '
                                  'COMMA16.2           @30  NOACC2 COMMA7.0  @38  BRHAMT2 COMMA15.2           '
                                  '@54  NOACC3 COMMA7.0  @62  BRHAMT3 COMMA15.2           @78  NOACC4 COMMA8.0  '
                                  '@87  BRHAMT4 COMMA17.2           @105 NOACC5 COMMA8.0  @114 BRHAMT5 COMMA17.2',
                                  '@1   BRHCODE           @5   NOACC6 COMMA7.0  @13  BRHAMT6 COMMA16.2           '
                                  '@30  NOACC7 COMMA7.0  @38  BRHAMT7 COMMA15.2           @54  NOACC8 COMMA7.0  '
                                  '@62  BRHAMT8 COMMA15.2           @78  NOACC9 COMMA8.0  @87  BRHAMT9 '
                                  'COMMA17.2           @105 NOACC10 COMMA8.0 @114 BRHAMT10 COMMA17.2',
                                  '@5   NOACC11 COMMA7.0 @13  BRHAMT11 COMMA16.2           @30  NOACC12 COMMA7.0 '
                                  '@38  BRHAMT12 COMMA15.2           @54  NOACC13 COMMA7.0 @62  BRHAMT13 '
                                  'COMMA15.2           @78  NOACC14 COMMA8.0 @87  BRHAMT14 COMMA17.2           '
                                  '@105 NOACC15 COMMA8.0 @114 BRHAMT15 COMMA17.2',
                                  '@5   NOACC16 COMMA7.0 @13  BRHAMT16 COMMA16.2           @30  NOACC17 COMMA7.0 '
                                  '@38  BRHAMT17 COMMA15.2           @54  SUBACC COMMA7.0  @62  SUBBRH  '
                                  'COMMA15.2           @78  SUBAC2 COMMA8.0  @87  SUBBR2  COMMA17.2           '
                                  '@105 SOTACC COMMA8.0  @114 TOTBRH  COMMA17.2'],
                       'total': ["@1   '----------------------------------------'           @41  "
                                 "'----------------------------------------'           @81  "
                                 "'----------------------------------------'           @121 '----------'",
                                 "@1  'TOT'           @5   TOTACC1 COMMA7.0  @13  TOTAMT1 COMMA16.2           "
                                 '@30  TOTACC2 COMMA7.0  @38  TOTAMT2 COMMA15.2           @54  TOTACC3 COMMA7.0  '
                                 '@62  TOTAMT3 COMMA15.2           @78  TOTACC4 COMMA8.0  @87  TOTAMT4 '
                                 'COMMA17.2           @105 TOTACC5 COMMA8.0  @114 TOTAMT5 COMMA17.2',
                                 '@5   TOTACC6 COMMA7.0  @13  TOTAMT6 COMMA16.2           @30  TOTACC7 COMMA7.0  '
                                 '@38  TOTAMT7 COMMA15.2           @54  TOTACC8 COMMA7.0  @62  TOTAMT8 '
                                 'COMMA15.2           @78  TOTACC9 COMMA8.0  @87  TOTAMT9 COMMA17.2           '
                                 '@105 TOTACC10 COMMA8.0 @114 TOTAMT10 COMMA17.2',
                                 '@5   TOTACC11 COMMA7.0 @13  TOTAMT11 COMMA16.2           @30  TOTACC12 COMMA7.0 '
                                 '@38  TOTAMT12 COMMA15.2           @54  TOTACC13 COMMA7.0 @62  TOTAMT13 '
                                 'COMMA15.2           @78  TOTACC14 COMMA8.0 @87  TOTAMT14 COMMA17.2           '
                                 '@105 TOTACC15 COMMA8.0 @114 TOTAMT15 COMMA17.2',
                                 '@5   TOTACC16 COMMA7.0 @13  TOTAMT16 COMMA16.2           @30  TOTACC17 COMMA7.0 '
                                 '@38  TOTAMT17 COMMA15.2           @54  SGTOTACC COMMA7.0 @62  SGTOTBRH '
                                 'COMMA15.2           @78  SGTOTAC2 COMMA8.0 @87  SGTOTBR2 COMMA17.2           '
                                 '@105 GTOTACC COMMA8.0  @114 GTOTBRH  COMMA17.2',
                                 "@1   '----------------------------------------'           @41  "
                                 "'----------------------------------------'           @81  "
                                 "'----------------------------------------'           @121 '----------'",
                                 ''],
                       'header': ["@1   'PROGRAM-ID : LNCCDI02'         @43  'P U B L I C   I S L A M I C   B A N "
                                  "K   B E R H A D'         @118 'PAGE NO.: ' PAGECNT",
                                  "@40  'OUTSTANDING LOANS IN ARREARS '         @69  TYPE  $14.         @85  "
                                  '"&RDATE"',
                                  "@1   ' '",
                                  "@1   'BRH    NO          < 1 MTH'         @33         'NO     1 TO < 2 "
                                  "MTH'         @58         'NO     2 TO < 3 MTH'         @84        'NO      3 "
                                  "TO < 4 MTH'         @111       'NO      4 TO < 5 MTH'",
                                  "@1   '       NO     5 TO < 6 MTH'         @33         'NO     6 TO < 7 "
                                  "MTH'         @58         'NO     7 TO < 8 MTH'         @84        'NO      8 "
                                  "TO < 9 MTH'         @111       'NO     9 TO < 10 MTH'",
                                  "@1   '       NO   10 TO < 11 MTH'         @33         'NO   11 TO < 12 "
                                  "MTH'         @58         'NO   12 TO < 18 MTH'         @84        'NO    18 TO "
                                  "< 24 MTH'         @111       'NO    24 TO < 36 MTH'",
                                  "@1   '       NO         > 36 MTH'         @33         'NO          "
                                  "DEFICIT'         @58        'NO   SUBTOTAL >=3MTH'         @84        'NO   "
                                  "SUBTOTAL >=6MTH'         @111       'NO             TOTAL'",
                                  "@1   '----------------------------------------'         @41  "
                                  "'----------------------------------------'         @81  "
                                  "'----------------------------------------'         @121 '----------'"]},
                      {'branch': ['@1   BRANCH Z3.               @5   NOACC1 COMMA7.0  @13  BRHAMT1 '
                                  'COMMA16.2               @30  NOACC2 COMMA7.0  @38  BRHAMT2 '
                                  'COMMA15.2               @54  NOACC3 COMMA7.0  @62  BRHAMT3 '
                                  'COMMA15.2               @78  NOACC4 COMMA8.0  @87  BRHAMT4 '
                                  'COMMA17.2               @105 NOACC5 COMMA8.0  @114 BRHAMT5 COMMA17.2',
                                  '@1   BRHCODE               @5   NOACC6  COMMA7.0  @13  BRHAMT6 '
                                  'COMMA16.2               @30  NOACC7  COMMA7.0  @38  BRHAMT7 '
                                  'COMMA15.2               @54  NOACC8  COMMA7.0  @62  BRHAMT8 '
                                  'COMMA15.2               @78  NOACC9  COMMA8.0  @87  BRHAMT9 '
                                  'COMMA17.2               @105 NOACC10 COMMA8.0  @114 BRHAMT10 COMMA17.2',
                                  '@5   NOACC11 COMMA7.0  @13  BRHAMT11 COMMA16.2               @30  NOACC12 '
                                  'COMMA7.0  @38  BRHAMT12 COMMA15.2               @54  NOACC13 COMMA7.0  @62  '
                                  'BRHAMT13 COMMA15.2               @78  NOACC14 COMMA8.0  @87  BRHAMT14 '
                                  'COMMA17.2               @105 NOACC15 COMMA8.0  @114 BRHAMT15 COMMA17.2',
                                  '@54  SUBACC  COMMA7.0  @62  SUBBRH  COMMA15.2               @78  SUBAC2  '
                                  'COMMA8.0  @87  SUBBR2  COMMA17.2               @105 SOTACC  COMMA8.0  @114 '
                                  'TOTBRH  COMMA17.2'],
                       'total': ["@1   '----------------------------------------'               @41  "
                                 "'----------------------------------------'               @81  "
                                 "'----------------------------------------'               @121 '----------'",
                                 "@1  'TOT'               @5   TOTACC1 COMMA7.0  @13  TOTAMT1 "
                                 'COMMA16.2               @30  TOTACC2 COMMA7.0  @38  TOTAMT2 '
                                 'COMMA15.2               @54  TOTACC3 COMMA7.0  @62  TOTAMT3 '
                                 'COMMA15.2               @78  TOTACC4 COMMA8.0  @87  TOTAMT4 '
                                 'COMMA17.2               @105 TOTACC5 COMMA8.0  @114 TOTAMT5 COMMA17.2',
                                 '@5   TOTACC6 COMMA7.0  @13  TOTAMT6 COMMA16.2               @30  TOTACC7 '
                                 'COMMA7.0  @38  TOTAMT7 COMMA15.2               @54  TOTACC8 COMMA7.0  @62  '
                                 'TOTAMT8 COMMA15.2               @78  TOTACC9 COMMA8.0  @87  TOTAMT9 '
                                 'COMMA17.2               @105 TOTACC10 COMMA8.0 @114 TOTAMT10 COMMA17.2',
                                 '@5   TOTACC11 COMMA7.0 @13  TOTAMT11 COMMA16.2               @30  TOTACC12 '
                                 'COMMA7.0 @38  TOTAMT12 COMMA15.2               @54  TOTACC13 COMMA7.0 @62  '
                                 'TOTAMT13 COMMA15.2               @78  TOTACC14 COMMA8.0 @87  TOTAMT14 '
                                 'COMMA17.2               @105 TOTACC15 COMMA8.0 @114 TOTAMT15 COMMA17.2',
                                 '@54  SGTOTACC COMMA7.0 @62  SGTOTBRH COMMA15.2               @78  SGTOTAC2 '
                                 'COMMA8.0 @87  SGTOTBR2 COMMA17.2               @105 GTOTACC COMMA8.0  @114 '
                                 'GTOTBRH  COMMA17.2',
                                 "@1   '----------------------------------------'               @41  "
                                 "'----------------------------------------'               @81  "
                                 "'----------------------------------------'               @121 '----------'",
                                 ''],
                       'header': ["@1   'PROGRAM-ID : LNCCDI02'             @43  'P U B L I C   I S L A M I C   B "
                                  "A N K   B E R H A D'             @118 'PAGE NO.: ' PAGECNT",
                                  "@45  'OUTSTANDING LOANS IN ARREARS '             @74  TYPE  $14.             "
                                  '@90  "&RDATE"',
                                  "@1   ' '",
                                  "@1   'BRH    NO          < 1 MTH'             @33         'NO     1 TO < 2 "
                                  "MTH'             @58         'NO     2 TO < 3 MTH'             @84        "
                                  "'NO      3 TO < 4 MTH'             @111       'NO      4 TO < 5 MTH'",
                                  "@1   '       NO     5 TO < 6 MTH'             @33         'NO     6 TO < 7 "
                                  "MTH'             @58         'NO     7 TO < 8 MTH'             @84        "
                                  "'NO      8 TO < 9 MTH'             @111       'NO     9 TO < 12 MTH'",
                                  "@1   '       NO   12 TO < 18 MTH'             @33         'NO   18 TO < 24 "
                                  "MTH'             @58         'NO   24 TO < 36 MTH'             @84        "
                                  "'NO          > 36 MTH'             @111       'NO           DEFICIT'",
                                  "@58        'NO   SUBTOTAL >=3MTH'             @84        'NO   SUBTOTAL "
                                  ">=6MTH'             @111       'NO             TOTAL'",
                                  "@1   '----------------------------------------'             @41  "
                                  "'----------------------------------------'             @81  "
                                  "'----------------------------------------'             @121 '----------'"]},
                      {'branch': ['@1   BRANCH Z3.           @5   NOACC1 COMMA7.0  @13  BRHAMT1 '
                                  'COMMA16.2           @30  NOACC2 COMMA7.0  @38  BRHAMT2 COMMA15.2           '
                                  '@54  NOACC3 COMMA7.0  @62  BRHAMT3 COMMA15.2           @78  NOACC4 COMMA8.0  '
                                  '@87  BRHAMT4 COMMA17.2           @105 NOACC5 COMMA8.0  @114 BRHAMT5 COMMA17.2',
                                  '@1   BRHCODE           @5   NOACC6 COMMA7.0  @13  BRHAMT6 COMMA16.2           '
                                  '@30  NOACC7 COMMA7.0  @38  BRHAMT7 COMMA15.2           @54  NOACC8 COMMA7.0  '
                                  '@62  BRHAMT8 COMMA15.2           @78  NOACC9 COMMA8.0  @87  BRHAMT9 '
                                  'COMMA17.2           @105 NOACC10 COMMA8.0 @114 BRHAMT10 COMMA17.2',
                                  '@5   NOACC11 COMMA7.0 @13  BRHAMT11 COMMA16.2           @30  NOACC12 COMMA7.0 '
                                  '@38  BRHAMT12 COMMA15.2           @54  NOACC13 COMMA7.0 @62  BRHAMT13 '
                                  'COMMA15.2           @78  NOACC14 COMMA8.0 @87  BRHAMT14 COMMA17.2           '
                                  '@105 NOACC15 COMMA8.0 @114 BRHAMT15 COMMA17.2',
                                  '@5   NOACC16 COMMA7.0 @13  BRHAMT16 COMMA16.2           @30  NOACC17 COMMA7.0 '
                                  '@38  BRHAMT17 COMMA15.2           @54  SUBACC  COMMA7.0 @62  SUBBRH   '
                                  'COMMA15.2           @78  SUBAC2  COMMA8.0 @87  SUBBR2   COMMA17.2           '
                                  '@105 SOTACC  COMMA8.0 @114 TOTBRH   COMMA17.2'],
                       'total': ["@1   '----------------------------------------'           @41  "
                                 "'----------------------------------------'           @81  "
                                 "'----------------------------------------'           @121 '----------'",
                                 "@1  'TOT'           @5   TOTACC1 COMMA7.0  @13  TOTAMT1 COMMA16.2           "
                                 '@30  TOTACC2 COMMA7.0  @38  TOTAMT2 COMMA15.2           @54  TOTACC3 COMMA7.0  '
                                 '@62  TOTAMT3 COMMA15.2           @78  TOTACC4 COMMA8.0  @87  TOTAMT4 '
                                 'COMMA17.2           @105 TOTACC5 COMMA8.0  @114 TOTAMT5 COMMA17.2',
                                 '@5   TOTACC6 COMMA7.0  @13  TOTAMT6 COMMA16.2           @30  TOTACC7 COMMA7.0  '
                                 '@38  TOTAMT7 COMMA15.2           @54  TOTACC8 COMMA7.0  @62  TOTAMT8 '
                                 'COMMA15.2           @78  TOTACC9 COMMA8.0  @87  TOTAMT9 COMMA17.2           '
                                 '@105 TOTACC10 COMMA8.0 @114 TOTAMT10 COMMA17.2',
                                 '@5   TOTACC11 COMMA7.0 @13  TOTAMT11 COMMA16.2           @30  TOTACC12 COMMA7.0 '
                                 '@38  TOTAMT12 COMMA15.2           @54  TOTACC13 COMMA7.0 @62  TOTAMT13 '
                                 'COMMA15.2           @78  TOTACC14 COMMA8.0 @87  TOTAMT14 COMMA17.2           '
                                 '@105 TOTACC15 COMMA8.0 @114 TOTAMT15 COMMA17.2',
                                 '@5   TOTACC16 COMMA7.0 @13  TOTAMT16 COMMA16.2           @30  TOTACC17 COMMA7.0 '
                                 '@38  TOTAMT17 COMMA15.2           @54  SGTOTACC COMMA7.0 @62  SGTOTBRH '
                                 'COMMA15.2           @78  SGTOTAC2 COMMA8.0 @87  SGTOTBR2 COMMA17.2           '
                                 '@105 GTOTACC COMMA8.0  @114 GTOTBRH  COMMA17.2',
                                 "@1   '----------------------------------------'           @41  "
                                 "'----------------------------------------'           @81  "
                                 "'----------------------------------------'           @121 '----------'",
                                 ''],
                       'header': ["@1   'PROGRAM-ID : LNCCDI04'         @43  'P U B L I C   I S L A M I C   B A N "
                                  "K   B E R H A D'         @118 'PAGE NO.: ' PAGECNT",
                                  "@41  'OUTSTANDING LOANS CLASSIFIED AS NPL '         @77  TYPE  $14.         "
                                  '@91  "&RDATE"',
                                  "@1   ' '",
                                  "@1   'BRH     NO         < 1 MTH'         @34         'NO     1 TO < 2 "
                                  "MTH'         @59         'NO     2 TO < 3 MTH'         @84        'NO      3 "
                                  "TO < 4 MTH'         @111       'NO      4 TO < 5 MTH'",
                                  "@1   '        NO    5 TO < 6 MTH'         @34         'NO     6 TO < 7 "
                                  "MTH'         @59         'NO     7 TO < 8 MTH'         @84        'NO      8 "
                                  "TO < 9 MTH'         @111       'NO     9 TO < 10 MTH'",
                                  "@1   '        NO  10 TO < 11 MTH'         @34         'NO   11 TO < 12 "
                                  "MTH'         @59         'NO   12 TO < 18 MTH'         @84        'NO    18 TO "
                                  "< 24 MTH'         @111       'NO    24 TO < 36 MTH'",
                                  "@1   '        NO        > 36 MTH'         @34         'NO          "
                                  "DEFICIT'         @59        'NO   SUBTOTAL >=3MTH'         @84        'NO   "
                                  "SUBTOTAL >=6MTH'         @111       'NO             TOTAL'",
                                  "@1   '----------------------------------------'         @41  "
                                  "'----------------------------------------'         @81  "
                                  "'----------------------------------------'         @121 '----------'"]}],
          'detail': {'body': ['@1   BRHCODE        @5   ACCTNO              @16  NAME        @41  '
                              'NOTENO              @54  PRODUCT        @59  BORSTAT             @68  ISSDTE   '
                              'DDMMYY8.        @79  DAYDIFF             @84  ARREARS        @98  BALANCE  '
                              'COMMA17.2  @116 NOISTLPD COMMA7.        @127 DELQCD   $5.',
                              '@5   LASTRAN  DDMMYY8.   @16  MATURDT  DDMMYY8.        @29  LSTTRNAM COMMA17.2  '
                              '@46  PAYAMT   COMMA11.2        @59  COLLDESC',
                              '@35   CAP COMMA16.2',
                              "@1   ' '",
                              "@41  '----------------------------------------'           @81  "
                              "'----------------------------------------'           @121 '----------'",
                              "@5   'SUBTOTAL'          @35 BRHCAP  COMMA16.2                                   "
                              '@100 BRHARR  COMMA17.2',
                              "@41  '----------------------------------------'           @81  "
                              "'----------------------------------------'           @121 '----------'",
                              '',
                              "@41  '----------------------------------------'           @81  "
                              "'----------------------------------------'           @121 '----------'",
                              "@5   'BRANCH TOTAL'      @35 BRHCAPB COMMA16.2                                    "
                              '@100 BRHAMT COMMA17.2',
                              "@41  '----------------------------------------'           @81  "
                              "'----------------------------------------'           @121 '----------'",
                              '',
                              "@41  '----------------------------------------'           @81  "
                              "'----------------------------------------'           @121 '----------'",
                              "@5   'GRAND TOTAL'      @35 TOTALCAP COMMA16.2                                     "
                              '@100 TOTAL COMMA17.2',
                              "@41  '----------------------------------------'           @81  "
                              "'----------------------------------------'           @121 '----------'",
                              ''],
                     'header': ['_PAGE_',
                                "@1   'PROGRAM-ID : LNCCDI10 - BRANCH : ' BRANCH  3.         @43  'P U B L I C   "
                                "I S L A M I C   B A N K   B E R H A D'         @118 'PAGE NO.: ' PAGECNT",
                                "@39  TYPE '2 MTHS & ABOVE AND NEW A/C WITH ARREAR '              'AS AT ' "
                                '"&RDATE"',
                                "@1   ' '",
                                "@1   'BRH'         @5   'ACCTNO'           @16 'NAME'         @40  "
                                "'NOTENO'           @50 'PRODUCT'         @59  'BORSTAT'          @68 'ISSUE "
                                "DT'         @78  'DAYS'             @84 'ARREARS'         @108 "
                                "'BALANCE'          @116 'NO ISTL'         @127 'DELQ'",
                                "@1   ' '         @5   'LST TR DT'        @16  'MAT. DATE'         @36  'LST TR "
                                "AMT'       @49  'ISTL AMT'         @69  'COLLATERAL DESCRIPTION'         @116 "
                                "'   PAID'          @127 'CODE'",
                                "@35   'CAPCLOSE'",
                                "@1   '----------------------------------------'         @41  "
                                "'----------------------------------------'         @81  "
                                "'----------------------------------------'         @121 '----------'"]}}}

# PBBLNFMT product and arrears definitions.
HPD = frozenset({128, 130, 131, 132, 380, 381, 700, 705, 720, 725})


ARRCLASS = {'1': '0 - < 1 MTH   ',
 '10': '9 - < 12 MTH  ',
 '11': '12 - < 18 MTH ',
 '12': '18 - < 24 MTH ',
 '13': '24 - < 36 MTH ',
 '14': '36 MTH & ABOVE',
 '15': 'DEFICIT       ',
 '2': '1 - < 2 MTH   ',
 '3': '2 - < 3 MTH   ',
 '4': '3 - < 4 MTH   ',
 '5': '4 - < 5 MTH   ',
 '6': '5 - < 6 MTH   ',
 '7': '6 - < 7 MTH   ',
 '8': '7 - < 8 MTH   ',
 '9': '8 - < 9 MTH   '}

# PBBELF branch-to-CAC format.
CACBRCH = {'103': '912',
 '105': '914',
 '107': '915',
 '109': '913',
 '110': '914',
 '114': '915',
 '118': '912',
 '120': '911',
 '121': '916',
 '122': '912',
 '124': '911',
 '125': '912',
 '126': '915',
 '127': '913',
 '128': '911',
 '129': '911',
 '131': '912',
 '132': '912',
 '133': '913',
 '135': '913',
 '136': '912',
 '138': '912',
 '141': '911',
 '145': '912',
 '147': '914',
 '148': '911',
 '15': '912',
 '150': '915',
 '151': '912',
 '153': '913',
 '154': '916',
 '155': '912',
 '157': '912',
 '159': '915',
 '162': '912',
 '163': '912',
 '167': '912',
 '168': '912',
 '169': '911',
 '170': '911',
 '171': '915',
 '173': '912',
 '174': '914',
 '176': '914',
 '177': '916',
 '178': '912',
 '179': '912',
 '18': '911',
 '180': '912',
 '19': '912',
 '195': '912',
 '196': '912',
 '197': '912',
 '198': '912',
 '199': '913',
 '2': '911',
 '20': '913',
 '201': '913',
 '202': '912',
 '203': '913',
 '204': '916',
 '205': '915',
 '206': '916',
 '216': '914',
 '217': '914',
 '22': '912',
 '220': '912',
 '221': '913',
 '222': '914',
 '225': '911',
 '226': '911',
 '229': '912',
 '230': '911',
 '232': '911',
 '236': '911',
 '240': '913',
 '241': '912',
 '248': '911',
 '25': '913',
 '250': '913',
 '252': '912',
 '253': '915',
 '255': '916',
 '26': '912',
 '262': '911',
 '265': '915',
 '266': '915',
 '267': '911',
 '268': '913',
 '269': '912',
 '27': '916',
 '270': '912',
 '280': '912',
 '284': '912',
 '285': '912',
 '286': '914',
 '287': '914',
 '288': '912',
 '289': '912',
 '29': '912',
 '290': '914',
 '3': '912',
 '35': '911',
 '36': '912',
 '37': '914',
 '38': '911',
 '40': '911',
 '41': '911',
 '42': '916',
 '43': '913',
 '46': '912',
 '52': '914',
 '53': '911',
 '54': '915',
 '56': '912',
 '59': '914',
 '6': '915',
 '60': '916',
 '61': '914',
 '66': '911',
 '68': '916',
 '69': '912',
 '7': '914',
 '701': '912',
 '702': '912',
 '78': '913',
 '79': '914',
 '801': '916',
 '802': '911',
 '804': '914',
 '805': '914',
 '808': '915',
 '81': '913',
 '811': '912',
 '812': '911',
 '814': '913',
 '815': '912',
 '816': '911',
 '817': '915',
 '818': '911',
 '820': '913',
 '821': '912',
 '822': '912',
 '825': '912',
 '826': '916',
 '83': '912',
 '88': '916',
 '89': '914',
 '92': '913',
 '94': '912',
 '96': '912',
 '97': '912'}
