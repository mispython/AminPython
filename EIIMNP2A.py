"""Python port of AminPython/1INPUT (JCL job EIIMNP2A)."""

import argparse
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from itertools import groupby
from pathlib import Path

import pandas as pd
import pyreadstat

EPOCH = date(1960, 1, 1)
HPD_AITAB = {128, 130, 131, 132}
HPD_CONVENTIONAL = {380, 381, 700, 705, 720, 725}
KEEP = """
LOANTYPE NTBRCH ACCTNO NOTENO NAME BORSTAT LOANSTAT NETPROC ORGBAL
CURBAL NOTETERM BLDATE LOANTYP ISSUEDT DAYS NETBAL BRANCH MAKE MODEL
DEALERNO COMPNAME PRIMOFHP CUSTFISS GUAREND OLDNOTEDAYARR CAP SCORE2
""".split()
TOTAL_COLUMNS = KEEP + [
    "TOTNET", "_FREQ_", "_TYPE_", "ISSDTE", "CACNAME", "REGION",
    "SUBTOT", "GRANDTOT", "REPTDATE",
]

# Numeric format rules from PBBLNFMT and PBBELF on AminPython/main.
FORMATS = {
    "LNCUSTCD": [
        ("1", "01"),
        ("2", "02"),
        ("3", "03"),
        ("4", "04"),
        ("5", "05"),
        ("6", "06"),
        ("10", "10"),
        ("11", "11"),
        ("12", "12"),
        ("13", "13"),
        ("15", "15"),
        ("17", "17"),
        ("20", "20"),
        ("30", "30"),
        ("32", "32"),
        ("33", "33"),
        ("34", "34"),
        ("35", "35"),
        ("36", "36"),
        ("37", "37"),
        ("38", "38"),
        ("39", "39"),
        ("40", "40"),
        ("41", "41"),
        ("42", "42"),
        ("43", "43"),
        ("44", "44"),
        ("46", "46"),
        ("47", "47"),
        ("48", "48"),
        ("49", "49"),
        ("51", "51"),
        ("52", "52"),
        ("53", "53"),
        ("54", "54"),
        ("50", "50"),
        ("57", "57"),
        ("59", "59"),
        ("60", "60"),
        ("61", "61"),
        ("62", "62"),
        ("63", "63"),
        ("64", "64"),
        ("65", "65"),
        ("66", "41"),
        ("67", "44"),
        ("68", "48"),
        ("69", "52"),
        ("70", "70"),
        ("71", "71"),
        ("72", "72"),
        ("73", "73"),
        ("74", "74"),
        ("75", "75"),
        ("76", "76"),
        ("77", "77"),
        ("78", "78"),
        ("79", "79"),
        ("80", "80"),
        ("81", "81"),
        ("85", "85"),
        ("86", "86"),
        ("87", "87"),
        ("88", "88"),
        ("89", "89"),
        ("90", "90"),
        ("91", "91"),
        ("92", "92"),
        ("95", "95"),
        ("96", "96"),
        ("98", "98"),
        ("99", "99"),
        ("OTHER", "79"),
    ],
    "BRCHCD": [
        ("1,7000-9000,9994-9996,9998-9999", "HOE"),
        ("3000-3001,3999", "IBU"),
        ("4000-4999", "IBU"),
        ("800,3800", "H01"),
        ("801,3801", "H02"),
        ("802,3802", "H03"),
        ("803,3803", "H04"),
        ("804,3804", "H05"),
        ("805,3805", "H06"),
        ("806,3806", "H07"),
        ("807,3807", "H08"),
        ("808,3808", "H09"),
        ("809,3809", "H10"),
        ("811,3811", "H11"),
        ("812,3812", "H12"),
        ("813,3813", "H13"),
        ("814,3814", "H14"),
        ("815,3815", "H15"),
        ("816,3816", "H16"),
        ("817,3817", "H17"),
        ("818,3818", "H18"),
        ("819,3819", "H19"),
        ("820,3820", "H20"),
        ("821,3821", "H21"),
        ("822,3822", "H22"),
        ("823,3823", "H23"),
        ("824,3824", "H24"),
        ("825,3825", "H25"),
        ("826,3826", "H26"),
        ("827,3827", "H27"),
        ("828,3828", "H28"),
        ("844,3844", "H44"),
        ("845,3845", "H45"),
        ("846,3846", "H46"),
        ("847,3847", "H47"),
        ("848,3848", "H48"),
        ("849,3849", "H49"),
        ("850,3850", "H50"),
        ("851,3851", "H51"),
        ("852,3852", "H52"),
        ("853,3853", "H53"),
        ("854,3854", "H54"),
        ("855,3855", "H55"),
        ("856,3856", "H56"),
        ("857,3857", "H57"),
        ("858,3858", "H58"),
        ("859,3859", "H59"),
        ("860,3860", "H60"),
        ("861,3861", "H61"),
        ("862,3862", "H62"),
        ("863,3863", "H63"),
        ("2,3002", "JSS"),
        ("3,3003", "JRC"),
        ("4,3004", "MLK"),
        ("5,3005", "IMO"),
        ("6,3006", "PPG"),
        ("7,3007", "JBU"),
        ("8,3008", "KTN"),
        ("9,3009", "JYK"),
        ("10,3010", "ASR"),
        ("11,3011", "GRN"),
        ("12,3012", "PPH"),
        ("13,3013", "KBU"),
        ("14,3014", "TMH"),
        ("15,3015", "KPG"),
        ("16,3016", "NLI"),
        ("17,3017", "TPN"),
        ("18,3018", "PJN"),
        ("19,3019", "DUA"),
        ("20,3020", "TCL"),
        ("21,3021", "BPT"),
        ("22,3022", "SMY"),
        ("23,3023", "KMT"),
        ("24,3024", "RSH"),
        ("25,3025", "SAM"),
        ("26,3026", "SPG"),
        ("27,3027", "NTL"),
        ("28,3028", "MUA"),
        ("29,3029", "JRL"),
        ("30,3030", "KTU"),
        ("31,3031", "SKC"),
        ("32,3032", "WSS"),
        ("33,3033", "KKU"),
        ("34,3034", "KGR"),
        ("35,3035", "SSA"),
        ("36,3036", "SS2"),
        ("37,3037", "TSA"),
        ("38,3038", "JKL"),
        ("39,3039", "KKG"),
        ("40,3040", "JSB"),
        ("41,3041", "JIH"),
        ("42,3042", "BMM"),
        ("43,3043", "BTG"),
        ("44,3044", "TWU"),
        ("45,3045", "SRB"),
        ("46,3046", "APG"),
        ("47,3047", "SGM"),
        ("48,3048", "MTK"),
        ("49,3049", "JLP"),
        ("50,3050", "MRI"),
        ("51,3051", "SMG"),
        ("52,3052", "UTM"),
        ("53,3053", "TMI"),
        ("54,3054", "BBB"),
        ("55,3055", "LBN"),
        ("56,3056", "KJG"),
        ("57,3057", "SPI"),
        ("58,3058", "SBU"),
        ("59,3059", "PKL"),
        ("60,3060", "BAM"),
        ("61,3061", "KLI"),
        ("62,3062", "SDK"),
        ("63,3063", "GMS"),
        ("64,3064", "PDN"),
        ("65,3065", "BHU"),
        ("66,3066", "BDA"),
        ("67,3067", "CMR"),
        ("68,3068", "SAT"),
        ("69,3069", "BKI"),
        ("70,3070", "PSA"),
        ("71,3071", "BCG"),
        ("72,3072", "PPR"),
        ("73,3073", "SPK"),
        ("74,3074", "SIK"),
        ("75,3075", "CAH"),
        ("76,3076", "PRS"),
        ("77,3077", "PLI"),
        ("78,3078", "SJA"),
        ("79,3079", "MSI"),
        ("80,3080", "MLB"),
        ("81,3081", "SBH"),
        ("82,3082", "MCG"),
        ("83,3083", "JBB"),
        ("84,3084", "PMS"),
        ("85,3085", "SST"),
        ("86,3086", "CLN"),
        ("87,3087", "MSG"),
        ("88,3088", "KUM"),
        ("89,3089", "TPI"),
        ("90,3090", "BTL"),
        ("91,3091", "KUG"),
        ("92,3092", "KLG"),
        ("93,3093", "EDU"),
        ("94,3094", "STP"),
        ("95,3095", "TIN"),
        ("96,3096", "SGK"),
        ("97,3097", "HSL"),
        ("98,3098", "TCY"),
        ("102,3102", "PRJ"),
        ("103,3103", "JJG"),
        ("104,3104", "KKL"),
        ("105,3105", "KTI"),
        ("106,3106", "CKI"),
        ("107,3107", "JLT"),
        ("108,3108", "BSI"),
        ("109,3109", "KSR"),
        ("110,3110", "TJJ"),
        ("111,3111", "AKH"),
        ("112,3112", "LDO"),
        ("113,3113", "TML"),
        ("114,3114", "BBA"),
        ("115,3115", "KNG"),
        ("116,3116", "TRI"),
        ("117,3117", "KKI"),
        ("118,3118", "TMW"),
        ("120,3120", "PIH"),
        ("121,3121", "PRA"),
        ("122,3122", "SKN"),
        ("123,3123", "IGN"),
        ("124,3124", "S14"),
        ("125,3125", "KJA"),
        ("126,3126", "PTS"),
        ("127,3127", "TSM"),
        ("128,3128", "SGB"),
        ("129,3129", "BSR"),
        ("130,3130", "PDG"),
        ("131,3131", "TMG"),
        ("132,3132", "CKT"),
        ("133,3133", "PKG"),
        ("134,3134", "RPG"),
        ("135,3135", "BSY"),
        ("136,3136", "TCS"),
        ("137,3137", "JPP"),
        ("138,3138", "WMU"),
        ("139,3139", "JRT"),
        ("140,3140", "CPE"),
        ("141,3141", "STL"),
        ("142,3142", "KBD"),
        ("143,3143", "LDU"),
        ("144,3144", "KHG"),
        ("145,3145", "BSD"),
        ("146,3146", "PSG"),
        ("147,3147", "PNS"),
        ("148,3148", "PJO"),
        ("149,3149", "BFT"),
        ("150,3150", "LMM"),
        ("151,3151", "SLY"),
        ("152,3152", "ATR"),
        ("153,3153", "USJ"),
        ("154,3154", "BSJ"),
        ("155,3155", "TTJ"),
        ("156,3156", "TMR"),
        ("157,3157", "BPJ"),
        ("158,3158", "SPL"),
        ("159,3159", "RLU"),
        ("160,3160", "MTH"),
        ("161,3161", "DGG"),
        ("162,3162", "SEA"),
        ("163,3163", "JKA"),
        ("164,3164", "KBS"),
        ("165,3165", "TKA"),
        ("166,3166", "PGG"),
        ("167,3167", "BBG"),
        ("168,3168", "KLC"),
        ("169,3169", "CTD"),
        ("170,3170", "PJA"),
        ("171,3171", "JMR"),
        ("172,3172", "TMJ"),
        ("173,3173", "SCA"),
        ("174,3174", "BBP"),
        ("175,3175", "LBG"),
        ("176,3176", "TPG"),
        ("177,3177", "JRU"),
        ("178,3178", "MIN"),
        ("179,3179", "OUG"),
        ("180,3180", "KBG"),
        ("181,3181", "SRO"),
        ("182,3182", "JPU"),
        ("183,3183", "JCL"),
        ("184,3184", "JPN"),
        ("185,3185", "KCY"),
        ("186,3186", "JTZ"),
        ("188,3188", "PLT"),
        ("189,3189", "BNH"),
        ("190,3190", "BTR"),
        ("191,3191", "KPT"),
        ("192,3192", "MRD"),
        ("193,3193", "MKH"),
        ("194,3194", "SRK"),
        ("195,3195", "BWK"),
        ("196,3196", "JHL"),
        ("197,3197", "TNM"),
        ("198,3198", "TDA"),
        ("199,3199", "JTH"),
        ("201,3201", "PDA"),
        ("202,3202", "RWG"),
        ("203,3203", "SJM"),
        ("204,3204", "BTW"),
        ("205,3205", "SNG"),
        ("206,3206", "TBM"),
        ("207,3207", "BCM"),
        ("208,3208", "JSI"),
        ("209,3209", "STW"),
        ("210,3210", "TMM"),
        ("211,3211", "TPD"),
        ("212,3212", "JMA"),
        ("213,3213", "JKB"),
        ("214,3214", "JGA"),
        ("215,3215", "JKP"),
        ("216,3216", "SKI"),
        ("217,3217", "TMB"),
        ("220,3220", "GHS"),
        ("221,3221", "TSK"),
        ("222,3222", "TDC"),
        ("223,3223", "TRJ"),
        ("224,3224", "JAH"),
        ("225,3225", "TIH"),
        ("226,3226", "JPR"),
        ("227,3227", "KSB"),
        ("228,3228", "INN"),
        ("229,3229", "TSJ"),
        ("230,3230", "SSH"),
        ("231,3231", "BBM"),
        ("232,3232", "TMD"),
        ("233,3233", "BEN"),
        ("234,3234", "SRM"),
        ("235,3235", "SBM"),
        ("236,3236", "UYB"),
        ("237,3237", "KLS"),
        ("238,3238", "JKT"),
        ("239,3239", "KMY"),
        ("240,3240", "KAP"),
        ("241,3241", "DJA"),
        ("242,3242", "TKK"),
        ("243,3243", "KKR"),
        ("244,3244", "GRT"),
        ("245,3245", "BDR"),
        ("246,3246", "BGH"),
        ("247,3247", "BPR"),
        ("249,3249", "TAI"),
        ("248,3248", "JTS"),
        ("250,3250", "TEA"),
        ("251,3251", "KPR"),
        ("252,3252", "TMA"),
        ("253,3253", "JTT"),
        ("254,3254", "KPH"),
        ("255,3255", "SBP"),
        ("256,3256", "PBR"),
        ("257,3257", "RAU"),
        ("258,3258", "JTA"),
        ("259,3259", "SAN"),
        ("260,3260", "KDN"),
        ("261,3261", "GMG"),
        ("262,3262", "TCT"),
        ("263,3263", "BTA"),
        ("264,3264", "JBH"),
        ("265,3265", "JAI"),
        ("266,3266", "JDK"),
        ("267,3267", "TDI"),
        ("268,3268", "BBT"),
        ("269,3269", "MKA"),
        ("270,3270", "BPI"),
        ("273,3273", "LHA"),
        ("277,3277", "WSU"),
        ("278,3278", "JPI"),
        ("274,3274", "STG"),
        ("275,3275", "MSL"),
        ("276,3276", "JAS"),
        ("279,3279", "PTJ"),
        ("280,3280", "KDA"),
        ("281,3281", "PLT"),
        ("282,3282", "PTT"),
        ("283,3283", "PSE"),
        ("284,3284", "BSP"),
        ("285,3285", "BMC"),
        ("286,3286", "BIH"),
        ("287,3287", "SUA"),
        ("288,3288", "SPT"),
        ("289,3289", "TEE"),
        ("290,3290", "TDY"),
        ("291,3291", "BSL"),
        ("292,3292", "BMJ"),
        ("293,3293", "BSA"),
        ("294,3294", "KKM"),
        ("295,3295", "BKR"),
        ("296,3296", "BJL"),
        ("701,3701", "IKB"),
        ("702,3702", "IPJ"),
        ("703,3703", "IWS"),
        ("704,3704", "IJK"),
    ],
    "CACNAME": [
        ("2,18,35,38,40,41,53,66,120,124,128,129,141,148,169,170,225,226,230,232,236,248,262,267,802,812,816,818", "CAC-K. LUMPUR "),
        ("3,15,19,22,26,29,36,46,56,69,83,94,96,97,701,118,122,125,131,132,136,138,145,151,155,157,162,163,270,167,168,173,178,179,195,198,180,196,197,202,220,229,241,252,280,811,815,822,103,821,825,269,284,285,288,289,702", "CAC-CITY CENTRE"),
        ("27,42,60,68,88,121,154,177,204,206,255,801,826", "CAC-BUTTERWOTH"),
        ("6,54,107,114,126,150,159,171,205,253,265,266,808,817", "CAC-PENANG"),
        ("7,37,52,59,61,79,89,105,110,147,174,176,216,217,222,286,804,805,287,290", "CAC-JOHOR BAHRU"),
        ("20,25,43,78,81,92,109,127,133,135,153,199,201,203,221,240,250,268,814,820", "CAC-KELANG"),
        ("OTHER", "NON CAC"),
    ],
    "REGIOFF": [
        ("3,22,40,46,53,56,120,122,129,136,155,168,169,170,173,220,225,226,232,252,262,802,818,284,285", "SELWP1"),
        ("2,15,29,41,66,83,94,96,97,701,103,118,128,138,141,151,178,195,196,197,248,821,822", "SELWP2"),
        ("18,19,26,35,36,38,81,124,125,131,145,148,157,162,163,167,179,198,230,241,267,269,270,280,825", "SELWP3"),
        ("20,25,31,43,69,73,78,92,109,127,133,135,153,180,199,201,202,203,221,235,240,250,268,814,820,279,288,289,702", "SELWP4"),
        ("7,21,28,37,47,52,59,61,75,79,87,89,91,93,102,105,110,144,147,174,176,216,217,222,224,234,242,247,286,804,805,287,290", "JOHOR"),
        ("6,10,11,27,34,42,54,57,60,68,70,74,77,86,88,104,107,114,121,126,150,154,159,164,171,177,204,205,206,213,238,253,255,258,265,266,801,806,808,817,826,704", "PNGKDHPLS"),
        ("5,9,23,49,51,67,71,76,80,85,95,108,123,137,146,152,158,207,208,209,210,211,243,244,245,246,249,251,256,809", "PERAK"),
        ("4,16,17,24,39,45,63,64,65,111,156,160,165,172,212,223,231,254,800,807", "MLKNSEM"),
        ("8,13,14,30,48,106,113,116,117,139,233,237,239,257,260,261,263,264,277,827,819,703", "PAHKELTER"),
        ("32,50,58,90,130,175,182,183,184,185,273,274,275,186,189,190,191,192,193,194,259,813,281", "SARAWAK"),
        ("33,44,55,62,72,112,115,140,142,143,149,161,228,803,278,276,282,283", "SABAHLBN"),
        ("OTHER", "NON REGION"),
    ],
}


def missing(value):
    return pd.isna(value) or isinstance(value, str) and not value.strip()


def read_member(folder, member, columns=None):
    path = folder / (member.lower() + ".sas7bdat")
    if not path.is_file():
        path = folder / (member.upper() + ".sas7bdat")
    frame, _ = pyreadstat.read_sas7bdat(str(path), disable_datetime_conversion=True)
    frame.columns = frame.columns.str.upper()
    if columns is not None:
        frame = frame[columns]
    return frame.to_dict("records")


def by_value(value):
    return (0, "") if missing(value) else (1, value.rstrip() if isinstance(value, str) else value)


def by_key(row, columns):
    return tuple(by_value(row.get(column)) for column in columns)


def match_merge(left, right, columns, require_left=False, require_right=False):
    """SAS BY merge: advance each input once per iteration, retain its values within the group."""
    def groups(rows):
        key = lambda row: by_key(row, columns)
        return {k: list(group) for k, group in groupby(sorted(rows, key=key), key)}

    left_groups, right_groups = groups(left), groups(right)
    for key in sorted(left_groups.keys() | right_groups.keys()):
        a, b = left_groups.get(key, []), right_groups.get(key, [])
        if (require_left and not a) or (require_right and not b):
            continue
        row = {}
        for index in range(max(len(a), len(b))):
            if index < len(a):
                row.update(a[index])
            if index < len(b):
                row.update(b[index])
            yield row.copy()


def number(value, width, decimals=0, comma=False, zero=False):
    if missing(value):
        return " " * width
    rounded = Decimal(str(value)).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)
    spec = f",.{decimals}f" if comma else f".{decimals}f"
    result = format(rounded, spec)
    if len(result) > width:
        return "*" * width
    return result.zfill(width) if zero else result.rjust(width)


def lookup(name, value):
    default = "." if missing(value) else number(value, 32).strip()
    for codes, label in FORMATS[name]:
        if codes == "OTHER":
            default = label
            continue
        for code in codes.split(","):
            if code == ".":
                if missing(value):
                    return label
            elif not missing(value):
                low, _, high = code.partition("-")
                if int(low) <= value <= int(high or low):
                    return label
    return default


def issue_date(value):
    if missing(value):
        return None
    digits = number(value, 11, zero=True)[:8]
    try:
        return date(int(digits[4:]), int(digits[:2]), int(digits[2:4]))
    except ValueError:
        return None


def adjusted_bill_date(bill, issued):
    if issued is None:
        return None
    year = bill.year + (bill.month == 12)
    month = bill.month % 12 + 1
    limits = (31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    try:
        return date(year, month, min(issued.day, limits[month - 1]))
    except ValueError:
        return None


def select_loans(notes, dealers, caps, commissions, report_date):
    notes = match_merge(dealers, notes, ["DEALERNO"], require_right=True)
    notes = match_merge(caps, notes, ["ACCTNO", "NOTENO"], require_right=True)
    eligible = (
        row for row in notes
        if str(row["REVERSED"]).rstrip() != "Y"
        and not missing(row["NOTENO"])
        and not missing(row["NTBRCH"])
        and str(row["PAIDIND"]).rstrip() != "P"
        and str(row["BORSTAT"]).rstrip() not in {"F", "R", "I", "Z"}
        and row["LOANTYPE"] in HPD_AITAB | HPD_CONVENTIONAL
    )
    key = lambda row: by_key(row, ["ACCTNO", "COMMNO"])
    unique = (next(group) for _, group in groupby(sorted(eligible, key=key), key))
    result = []
    for row in match_merge(unique, commissions, ["ACCTNO", "COMMNO"], require_left=True):
        if missing(row["BLDATE"]):
            continue
        bill = EPOCH + timedelta(days=int(row["BLDATE"]))
        total = 0 if missing(row["BILTOT"]) else row["BILTOT"]
        if not missing(row["BILPAY"]) and row["BILPAY"] > 0 and total / row["BILPAY"] <= 0.01:
            bill = adjusted_bill_date(bill, issue_date(row["ISSUEDT"]))
        days = (report_date - bill).days if bill else None
        old_days = row["OLDNOTEDAYARR"]
        if not missing(old_days) and old_days > 0 and 98000 <= row["NOTENO"] <= 98999:
            days = max(days or 0, 0) + old_days
        if days is None or not 60 <= days <= 89:
            continue
        collateral = "" if missing(row["COLLDESC"]) else row["COLLDESC"]
        branch = row["NTBRCH"]
        row.update(
            BLDATE=(bill - EPOCH).days if bill else None,
            DAYS=days, NETBAL=row["BALANCE"],
            LOANTYP="HPD AITAB" if row["LOANTYPE"] in HPD_AITAB else "HPD CONVENTIONAL",
            BRANCH=lookup("BRCHCD", branch).ljust(3) + " " + number(branch, 3, zero=True),
            MAKE=collateral[:14], MODEL=collateral[13:34],
            CUSTFISS=lookup("LNCUSTCD", row["CUSTCODE"]),
            PRIMOFHP=number(row["PRMOFFHP"], 5)[2:5],
        )
        result.append({column: row.get(column) for column in KEEP})
    return sorted(result, key=lambda row: (by_value(row["GUAREND"]), descending(row["NETBAL"])))


def descending(value):
    return (1, 0) if missing(value) else (0, -value)


def report_rows(loans, report_date):
    rows = []
    totals = []
    for _, group in groupby(loans, lambda row: by_value(row["GUAREND"])):
        group = list(group)
        guarantor = group[0]["GUAREND"]
        total = None if missing(guarantor) else sum(
            row["NETBAL"] for row in group if not missing(row["NETBAL"])
        )
        if total is not None:
            totals.append(total)
        for row in group:
            issued = issue_date(row["ISSUEDT"])
            rows.append(dict(row, TOTNET=total, _FREQ_=len(group) if total is not None else None,
                             _TYPE_=1 if total is not None else None,
                             ISSDTE=issued.strftime("%d/%m/%Y") if issued else "",
                             CACNAME=lookup("CACNAME", row["NTBRCH"]),
                             REGION=lookup("REGIOFF", row["NTBRCH"])))
        if total is not None and len(group) > 1:
            rows.append(dict(GUAREND=guarantor, TOTNET=total, NETBAL=total,
                             _TYPE_=1, _FREQ_=len(group), SUBTOT="SUB-TOTAL"))
    rows.sort(key=lambda row: (descending(row["TOTNET"]), by_value(row["GUAREND"]), row.get("SUBTOT", "")))
    grand = sum(totals)
    rows.append(dict(SUBTOT="GRAND TOTAL", GRANDTOT=grand, NETBAL=grand, _TYPE_=0, _FREQ_=len(totals)))
    for row in rows:
        row["REPTDATE"] = report_date.strftime("%d/%m/%y")
    return rows


TXT_HEAD = {
    1: "A/C NO.", 19: "NOTE NO.", 29: "NAME", 65: " - ", 75: "BRANCH",
    84: "DAYS", 90: "BORSTAT", 101: "ISSUE DATE", 115: "NETPROC", 135: "NETBAL",
    155: "CAC NAME", 180: "REGION OFF", 200: "MAKE", 215: "MODEL", 255: "DEALER NO",
    265: "DEALER NAME", 305: "ORI BRANCH", 316: "CUSTFISS", 326: "CAPCLOSE", 343: "SCORE2",
}


def fixed_record(width, fields, encoding):
    record = bytearray(b" " * width)
    for column, value in fields.items():
        if missing(value) or column > width:
            continue
        offset = column - 1
        data = str(value).encode(encoding)
        if len(data) > width - offset:
            data = data[:width - offset].decode(encoding, errors="ignore").encode(encoding)
        record[offset:offset + len(data)] = data
    return bytes(record) + b"\n"


def text_fields(row):
    return {
        1: number(row.get("ACCTNO"), 12), 19: number(row.get("NOTENO"), 8),
        29: row.get("NAME"), 65: row.get("SUBTOT"), 75: row.get("BRANCH"),
        84: number(row.get("DAYS"), 4), 90: row.get("BORSTAT"), 101: row.get("ISSDTE"),
        115: number(row.get("NETPROC"), 13, 2, comma=True),
        135: number(row.get("NETBAL"), 13, 2, comma=True),
        155: row.get("CACNAME"), 180: row.get("REGION"), 200: row.get("MAKE"),
        215: row.get("MODEL"), 255: number(row.get("DEALERNO"), 8).lstrip(), 265: row.get("COMPNAME"),
        305: row.get("PRIMOFHP"), 316: row.get("CUSTFISS"),
        326: number(row.get("CAP"), 16, 2, comma=True), 343: row.get("SCORE2"),
    }


def rps_headers(branch, page, report_date):
    return [
        {1: "BRANCH    :  ", 14: branch, 44: "P U B L I C   I S L A M I C  B A N K   B E R H A D",
         122: f"PAGE NO : {page}"},
        {1: "REPORT NO :  2MTHNPL", 42: "CLOSE ATTENTION IN 2 MONTHS", 72: report_date.strftime("%d/%m/%y")},
        {}, {},
        {10: "A/C NO.", 19: "NOTE NO.", 29: "NAME", 65: "BRANCH", 74: "DAYS",
         80: "BORSTAT", 91: "ISSUE DATE", 115: "NETBAL"},
        {5: "-" * 130}, {}, {},
    ]


def write_reports(folder, loans, totals, report_date, encoding):
    with (folder / "NPLHP2M.TXT").open("wb") as stream:
        stream.write(fixed_record(350, {1: "PIBB - (CA IN 2 MONTHS) AS AT ", 38: totals[0]["REPTDATE"]}, encoding))
        stream.write(fixed_record(350, TXT_HEAD, encoding))
        for row in totals:
            stream.write(fixed_record(350, text_fields(row), encoding))
    with (folder / "NPLHP2M.RPS").open("wb") as stream:
        ordered = sorted(loans, key=lambda row: (row["BRANCH"], descending(row["NETBAL"])))
        for branch, group in groupby(ordered, lambda row: row["BRANCH"]):
            page = 1
            line = 7
            for header in rps_headers(branch, page, report_date):
                stream.write(fixed_record(138, header, encoding))
            for row in group:
                issued = issue_date(row["ISSUEDT"])
                fields = {
                    5: number(row["ACCTNO"], 12), 19: number(row["NOTENO"], 8), 29: row["NAME"],
                    65: branch, 74: number(row["DAYS"], 4), 83: row["BORSTAT"],
                    91: issued.strftime("%d/%m/%Y") if issued else "",
                    110: number(row["NETBAL"], 13, 2, comma=True),
                }
                stream.write(fixed_record(138, fields, encoding))
                line += 1
                if line > 55:
                    page += 1
                    for header in rps_headers(branch, page, report_date):
                        stream.write(fixed_record(138, header, encoding))
                    line = 7


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--loan-dir", required=True, type=Path)
    parser.add_argument("--icap-dir", required=True, type=Path)
    parser.add_argument("--icap-member", help="Override the default ICAP<MMYY> member name")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--report-encoding", default="utf-8")
    args = parser.parse_args()
    dates = read_member(args.loan_dir, "REPTDATE", ["REPTDATE"])
    if len(dates) != 1 or missing(dates[0]["REPTDATE"]):
        raise ValueError("REPTDATE must contain one nonmissing SAS date")
    report_date = EPOCH + timedelta(days=int(dates[0]["REPTDATE"]))
    previous = report_date.replace(day=1) - timedelta(days=1)
    loans = select_loans(
        read_member(args.loan_dir, "LNNOTE"),
        read_member(args.loan_dir, "HPCOMP", ["DEALERNO", "COMPNAME"]),
        read_member(args.icap_dir, args.icap_member or f"ICAP{previous:%m%y}", ["ACCTNO", "NOTENO", "CAP"]),
        read_member(args.loan_dir, "LNCOMM", ["ACCTNO", "COMMNO", "CORGAMT"]),
        report_date,
    )
    totals = report_rows(loans, report_date)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(loans, columns=KEEP).to_parquet(args.output_dir / f"loan2m{report_date:%m}.parquet", index=False)
    pd.DataFrame(totals, columns=TOTAL_COLUMNS).to_parquet(args.output_dir / "totname.parquet", index=False)
    write_reports(args.output_dir, loans, totals, report_date, args.report_encoding)


if __name__ == "__main__":
    main()
