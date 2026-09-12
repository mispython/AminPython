"""PBMISFMT: reusable conversion of the original SAS include.

Usage from another job:
    import PBMISFMT
    names = PBMISFMT.available_formats()
    result = PBMISFMT.put(value, names[0])
    results = PBMISFMT.apply_format(values, names[0])

Original macro names are module constants and are also in MACROS.
Original format names are in FORMATS; named functions omit only the SAS $ prefix.
Keep imports qualified because different libraries can define the same names.
Run this file with --list, or FORMAT VALUE, for command-line lookups.

Parity limits: overlapping ranges use first-listed match, without SAS FUZZ;
character ranges use Unicode ordering. PICTURE padding/overflow and special
numeric missing codes are not fully reproduced. Validate against production SAS.
"""

import argparse
import math
from decimal import Decimal, ROUND_DOWN


def missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def resolve(value, macros):
    if isinstance(value, dict) and 'macro' in value:
        return macros[value['macro']]
    return value


def matches(value, lo, hi, exlo, exhi):
    if isinstance(lo, dict) and 'missing' in lo:
        return missing(value) if lo['missing'] == '.' else value == lo['missing']
    if missing(value):
        return False  # SAS LOW excludes numeric missing values.
    lower = isinstance(lo, dict) and lo.get('special') == 'LOW'
    upper = isinstance(hi, dict) and hi.get('special') == 'HIGH'
    return (lower or (value > lo if exlo else value >= lo)) and (upper or (value < hi if exhi else value <= hi))


def lookup(formats, name, value, macros=None):
    name = name.upper().rstrip('.')
    spec = formats[name]
    macros = macros or {}
    if isinstance(value, bytes):
        value = value.decode('utf-8')
    if name.startswith('$'):
        value = '' if missing(value) else str(value).rstrip()
    elif not missing(value):
        value = float(value)
    fallback = None
    for lo, hi, exlo, exhi, label, options in spec['rules']:
        lo, hi = resolve(lo, macros), resolve(hi, macros)
        if isinstance(lo, dict) and lo.get('special') == 'OTHER':
            fallback = label
            continue
        if matches(value, lo, hi, exlo, exhi):
            if spec['kind'] == 'PICTURE':
                # Source pictures use MULT explicitly and no ROUND option.
                n = (abs(Decimal(str(value))) * Decimal(str(options.get('MULT', 1)))).to_integral_value(rounding=ROUND_DOWN)
                decimals = len(label.split('.')[1]) if '.' in label else 0
                return options.get('PREFIX', '') + format(n / Decimal(10)**decimals, f',.{decimals}f')
            return label
    if fallback is not None:
        return fallback
    if spec['kind'] == 'INVALUE':
        return value
    if missing(value):
        return '.'
    return str(value) if name.startswith('$') else format(value, 'g')


def library_cli(formats, macros):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('format', nargs='?')
    parser.add_argument('value', nargs='?')
    args = parser.parse_args()
    if args.list:
        print('\n'.join(formats))
    elif args.format is not None and args.value is not None:
        print(lookup(formats, args.format, args.value, macros))
    else:
        parser.error('Use --list or FORMAT VALUE')

# Compact declarations expand to the original ordered SAS rules.
_LOW = {'special': 'LOW'}
_HIGH = {'special': 'HIGH'}
_OTHER = {'special': 'OTHER'}


def _span(start, end, *, exclude_start=False, exclude_end=False):
    return start, end, exclude_start, exclude_end


def _map(result, *selectors, options=None):
    rules = []
    for selector in selectors:
        bounds = selector if isinstance(selector, tuple) else (selector, selector, False, False)
        rules.append((*bounds, result, dict(options or {})))
    return rules

# SAS macro constants
AGELIMIT = 12

MAXAGE = 18

AGEBELOW = 11

MACROS = {
    'AGELIMIT': AGELIMIT,
    'MAXAGE': MAXAGE,
    'AGEBELOW': AGEBELOW,
}

# Formats: group only adjacent rules with the same result.
# _span(a, b) includes both endpoints; exclusions are stated explicitly.
# _map(result, selectors...) preserves source order and exceptions.
FORMATS = {
    'BRCHCD': {
        "kind": 'VALUE',
        "rules": [
            *_map('HOE', 1, _span(3000, 3001), 7000, _span(7500, 8000), _span(8050, 8750)),
            *_map('JSS', 2, 3002),
            *_map('JRC', 3, 3003),
            *_map('MLK', 4, 3004),
            *_map('IMO', 5, 3005),
            *_map('PPG', 6, 3006),
            *_map('JBU', 7, 3007),
            *_map('KTN', 8, 3008),
            *_map('JYK', 9, 3009),
            *_map('ASR', 10, 3010),
            *_map('GRN', 11, 3011),
            *_map('PPH', 12, 3012),
            *_map('KBU', 13, 3013),
            *_map('TMH', 14, 3014),
            *_map('KPG', 15, 3015),
            *_map('NLI', 16, 3016),
            *_map('TPN', 17, 3017),
            *_map('PJN', 18, 3018),
            *_map('DUA', 19, 3019),
            *_map('TCL', 20, 3020),
            *_map('BPT', 21, 3021),
            *_map('SMY', 22, 3022),
            *_map('KMT', 23, 3023),
            *_map('RSH', 24, 3024),
            *_map('SAM', 25, 3025),
            *_map('SPG', 26, 3026),
            *_map('NTL', 27, 3027),
            *_map('MUA', 28, 3028),
            *_map('JRL', 29, 3029),
            *_map('KTU', 30, 3030),
            *_map('SKC', 31, 3031),
            *_map('WSS', 32, 3032),
            *_map('KKU', 33, 3033),
            *_map('KGR', 34, 3034),
            *_map('SSA', 35, 3035),
            *_map('SS2', 36, 3036),
            *_map('TSA', 37, 3037),
            *_map('JKL', 38, 3038),
            *_map('KKG', 39, 3039),
            *_map('JSB', 40, 3040),
            *_map('JIH', 41, 3041),
            *_map('BMM', 42, 3042),
            *_map('BTG', 43, 3043),
            *_map('TWU', 44, 3044),
            *_map('SRB', 45, 3045),
            *_map('APG', 46, 3046),
            *_map('SGM', 47, 3047),
            *_map('MTK', 48, 3048),
            *_map('JLP', 49, 3049),
            *_map('MRI', 50, 3050),
            *_map('SMG', 51, 3051),
            *_map('UTM', 52, 3052),
            *_map('TMI', 53, 3053),
            *_map('BBB', 54, 3054),
            *_map('LBN', 55, 3055),
            *_map('KJG', 56, 3056),
            *_map('SPI', 57, 3057),
            *_map('SBU', 58, 3058),
            *_map('PKL', 59, 3059),
            *_map('BAM', 60, 3060),
            *_map('KLI', 61, 3061),
            *_map('SDK', 62, 3062),
            *_map('GMS', 63, 3063),
            *_map('PDN', 64, 3064),
            *_map('BHU', 65, 3065),
            *_map('BDA', 66, 3066),
            *_map('CMR', 67, 3067),
            *_map('SAT', 68, 3068),
            *_map('BKI', 69, 3069),
            *_map('PSA', 70, 3070),
            *_map('BCG', 71, 3071),
            *_map('PPR', 72, 3072),
            *_map('SPK', 73, 3073),
            *_map('SIK', 74, 3074),
            *_map('CAH', 75, 3075),
            *_map('PRS', 76, 3076),
            *_map('PLI', 77, 3077),
            *_map('SJA', 78, 3078),
            *_map('MSI', 79, 3079),
            *_map('MLB', 80, 3080),
            *_map('SBH', 81, 3081),
            *_map('MCG', 82, 3082),
            *_map('JBB', 83, 3083),
            *_map('PMS', 84, 3084),
            *_map('SST', 85, 3085),
            *_map('CLN', 86, 3086),
            *_map('MSG', 87, 3087),
            *_map('KUM', 88, 3088),
            *_map('TPI', 89, 3089),
            *_map('BTL', 90, 3090),
            *_map('KUG', 91, 3091),
            *_map('KLG', 92, 3092),
            *_map('EDU', 93, 3093),
            *_map('STP', 94, 3094),
            *_map('TIN', 95, 3095),
            *_map('SGK', 96, 3096),
            *_map('HSL', 97, 3097),
            *_map('TCY', 98, 3098),
            *_map('PRJ', 102, 3102),
            *_map('JJG', 103, 3103),
            *_map('KKL', 104, 3104),
            *_map('KTI', 105, 3105),
            *_map('CKI', 106, 3106),
            *_map('JLT', 107, 3107),
            *_map('BSI', 108, 3108),
            *_map('KSR', 109, 3109),
            *_map('TJJ', 110, 3110),
            *_map('AKH', 111, 3111),
            *_map('LDO', 112, 3112),
            *_map('TML', 113, 3113),
            *_map('BBA', 114, 3114),
            *_map('KNG', 115, 3115),
            *_map('TRI', 116, 3116),
            *_map('KKI', 117, 3117),
            *_map('TMW', 118, 3118),
            *_map('BNV', 119, 3119),
            *_map('PIH', 120, 3120),
            *_map('PRA', 121, 3121),
            *_map('SKN', 122, 3122),
            *_map('IGN', 123, 3123),
            *_map('S14', 124, 3124),
            *_map('KJA', 125, 3125),
            *_map('PTS', 126, 3126),
            *_map('TSM', 127, 3127),
            *_map('SGB', 128, 3128),
            *_map('BSR', 129, 3129),
            *_map('PDG', 130, 3130),
            *_map('TMG', 131, 3131),
            *_map('CKT', 132, 3132),
            *_map('PKG', 133, 3133),
            *_map('RPG', 134, 3134),
            *_map('BSY', 135, 3135),
            *_map('TCS', 136, 3136),
            *_map('JPP', 137, 3137),
            *_map('WMU', 138, 3138),
            *_map('JRT', 139, 3139),
            *_map('CPE', 140, 3140),
            *_map('STL', 141, 3141),
            *_map('KBD', 142, 3142),
            *_map('LDU', 143, 3143),
            *_map('KHG', 144, 3144),
            *_map('BSD', 145, 3145),
            *_map('PSG', 146, 3146),
            *_map('PNS', 147, 3147),
            *_map('PJO', 148, 3148),
            *_map('BFT', 149, 3149),
            *_map('LMM', 150, 3150),
            *_map('SLY', 151, 3151),
            *_map('ATR', 152, 3152),
            *_map('USJ', 153, 3153),
            *_map('BSJ', 154, 3154),
            *_map('TTJ', 155, 3155),
            *_map('TMR', 156, 3156),
            *_map('BPJ', 157, 3157),
            *_map('SPL', 158, 3158),
            *_map('RLU', 159, 3159),
            *_map('MTH', 160, 3160),
            *_map('DGG', 161, 3161),
            *_map('SEA', 162, 3162),
            *_map('JKA', 163, 3163),
            *_map('KBS', 164, 3164),
            *_map('TKA', 165, 3165),
            *_map('PGG', 166, 3166),
            *_map('BBG', 167, 3167),
            *_map('KLC', 168, 3168),
            *_map('CTD', 169, 3169),
            *_map('PJA', 170, 3170),
            *_map('JMR', 171, 3171),
            *_map('TMJ', 172, 3172),
            *_map('SCA', 173, 3173),
            *_map('BBP', 174, 3174),
            *_map('LBG', 175, 3175),
            *_map('TPG', 176, 3176),
            *_map('JRU', 177, 3177),
            *_map('MIN', 178, 3178),
            *_map('OUG', 179, 3179),
            *_map('KBG', 180, 3180),
            *_map('JPU', 182, 3182),
            *_map('JCL', 183, 3183),
            *_map('JPN', 184, 3184),
            *_map('KCY', 185, 3185),
            *_map('JTZ', 186, 3186),
            *_map('PLT', 188, 3188),
            *_map('BNH', 189, 3189),
            *_map('BTR', 190, 3190),
            *_map('KPT', 191, 3191),
            *_map('MRD', 192, 3192),
            *_map('MKH', 193, 3193),
            *_map('SRK', 194, 3194),
            *_map('BWK', 195, 3195),
            *_map('JHL', 196, 3196),
            *_map('TNM', 197, 3197),
            *_map('TDA', 198, 3198),
            *_map('JTH', 199, 3199),
            *_map('PDA', 201, 3201),
            *_map('RWG', 202, 3202),
            *_map('SJM', 203, 3203),
            *_map('BTW', 204, 3204),
            *_map('SNG', 205, 3205),
            *_map('TBM', 206, 3206),
            *_map('BCM', 207, 3207),
            *_map('JSI', 208, 3208),
            *_map('STW', 209, 3209),
            *_map('TMM', 210, 3210),
            *_map('TPD', 211, 3211),
            *_map('JMA', 212, 3212),
            *_map('JKB', 213, 3213),
            *_map('JGA', 214, 3214),
            *_map('JKP', 215, 3215),
            *_map('SKI', 216, 3216),
            *_map('TMB', 217, 3217),
            *_map('GHS', 220, 3220),
            *_map('TSK', 221, 3221),
            *_map('TDC', 222, 3222),
            *_map('TRJ', 223, 3223),
            *_map('JAH', 224, 3224),
            *_map('TIH', 225, 3225),
            *_map('JPR', 226, 3226),
            *_map('KSB', 227, 3227),
            *_map('INN', 228, 3228),
            *_map('TSJ', 229, 3229),
            *_map('SSH', 230, 3230),
            *_map('BBM', 231, 3231),
            *_map('TMD', 232, 3232),
            *_map('BEN', 233, 3233),
            *_map('SRM', 234, 3234),
            *_map('SBM', 235, 3235),
            *_map('UYB', 236, 3236),
            *_map('KLS', 237, 3237),
            *_map('JKT', 238, 3238),
            *_map('KMY', 239, 3239),
            *_map('KAP', 240, 3240),
            *_map('DJA', 241, 3241),
            *_map('TKK', 242, 3242),
            *_map('KKR', 243, 3243),
            *_map('GRT', 244, 3244),
            *_map('BDR', 245, 3245),
            *_map('BGH', 246, 3246),
            *_map('BPR', 247, 3247),
            *_map('JTS', 248, 3248),
            *_map('TAI', 249, 3249),
            *_map('TEA', 250, 3250),
            *_map('KPR', 251, 3251),
            *_map('TMA', 252, 3252),
            *_map('JTT', 253, 3253),
            *_map('KPH', 254, 3254),
            *_map('SBP', 255, 3255),
            *_map('PBR', 256, 3256),
            *_map('RAU', 257, 3257),
            *_map('JTA', 258, 3258),
            *_map('SAN', 259, 3259),
            *_map('KDN', 260, 3260),
            *_map('GMG', 261, 3261),
            *_map('TCT', 262, 3262),
            *_map('BTA', 263, 3263),
            *_map('JBH', 264, 3264),
            *_map('JAI', 265, 3265),
            *_map('JDK', 266, 3266),
            *_map('TDI', 267, 3267),
            *_map('BBT', 268, 3268),
            *_map('MKA', 269, 3269),
            *_map('BPI', 270, 3270),
            *_map('LHA', 273, 3273),
            *_map('WSU', 277, 3277),
            *_map('JPI', 278, 3278),
            *_map('STG', 274, 3274),
            *_map('MSL', 275, 3275),
            *_map('JAS', 276, 3276),
            *_map('PTJ', 279, 3279),
            *_map('KDA', 280, 3280),
            *_map('PLT', 281, 3281),
            *_map('PTT', 282, 3282),
            *_map('PSE', 283, 3283),
            *_map('BSP', 284, 3284),
            *_map('BMC', 285, 3285),
            *_map('BIH', 286, 3286),
            *_map('SUA', 287, 3287),
            *_map('SPT', 288, 3288),
            *_map('TEE', 289, 3289),
            *_map('TDY', 290, 3290),
            *_map('BSL', 291, 3291),
            *_map('BMJ', 292, 3292),
            *_map('BSA', 293, 3293),
            *_map('KKM', 294, 3294),
            *_map('BKR', 295, 3295),
            *_map('BJL', 296, 3296),
            *_map('IKB', 701, 3701),
            *_map('IPJ', 702, 3702),
            *_map('IWS', 703, 3703),
            *_map('IJK', 704, 3704),
        ],
    },

    '$GROUPF': {
        "kind": 'VALUE',
        "rules": [
            *_map('GROUP 1',
                'BBB', 'BDA', 'BMM', 'DUA', 'IMO', 'JKL', 'JRC', 'JRL', 'JSS', 'JSB', 'JYK', 'JBU', 'KPG',
                'KLC', 'MLK', 'PPG', 'SS2', 'SPG', 'SSA', 'SAM', 'SJA', 'TCL', 'TSA',
            ),
            *_map('GROUP 2',
                'BAM', 'ASR', 'BSY', 'BSR', 'BTG', 'BPT', 'CMR', 'GRN', 'IGN', 'JIH', 'JJG', 'JBB', 'KJG',
                'KLG', 'KBU', 'KKU', 'KTN', 'WSS', 'KLI', 'MSI', 'MLB', 'MRI', 'MUA', 'NTL', 'PDG', 'PJN',
                'SMY', 'SRB', 'SGK', 'SKN', 'SAT', 'SBH', 'TCS', 'TMI', 'TMG', 'TMW', 'TPN',
            ),
            *_map('GROUP 3',
                'BBA', 'APG', 'BHU', 'BSD', 'BKI', 'BNV', 'BTL', 'BCG', 'CAH', 'CKT', 'JPP', 'JLP', 'JLT',
                'KBR', 'KMT', 'KJA', 'KUG', 'KKG', 'KUM', 'LBN', 'LMM', 'LDO', 'MTK', 'NLI', 'PIH', 'PRS',
                'PJO', 'PKL', 'PKG', 'PTS', 'PSG', 'RSH', 'STL', 'S14', 'SGM', 'SKC', 'STP', 'SBU', 'SPK',
                'SPI', 'TCY', 'TJJ', 'TSM', 'TTJ', 'TPI', 'TMH', 'TWU', 'USJ', 'UTM', 'WMU',
            ),
            *_map('GROUP 4',
                'AKH', 'ATR', 'BBG', 'BBP', 'BSI', 'BPJ', 'BSJ', 'BFT', 'CLN', 'CKI', 'CTD', 'CPE', 'DGG',
                'EDU', 'GMS', 'JKA', 'JMR', 'JRT', 'HSL', 'KHG', 'KGR', 'KNG', 'KBS', 'KBD', 'KTI', 'KKL',
                'KKI', 'KSR', 'KTU', 'LDU', 'MCG', 'MTH', 'MSG', 'PJA', 'PPR', 'PRJ', 'PMS', 'PPH', 'PNS',
                'PSA', 'PGG', 'PDN', 'PRA', 'PLI', 'RPJ', 'RLU', 'SDK', 'SEA', 'SGB', 'SLY', 'SMG', 'SIK',
                'SPL', 'SCA', 'SST', 'TMJ', 'TMR', 'TPG', 'TIN', 'TML', 'TKA', 'TRI', 'GHS', 'BPI',
            ),
            *_map('HOE', 'HOE'),
            *_map('GROUP 4', _OTHER),
        ],
    },

    '$ACKNOF': {
        "kind": 'VALUE',
        "rules": [
            *_map('NEF', '21930'),
            *_map('NIF', '21940'),
            *_map('SFT', '21960'),
            *_map('3F', '21950'),
            *_map('SHP', '21910', '21920'),
            *_map('SPECIAL DEPOSIT WITHOLDING TAX', _span('32300', '32699')),
            *_map('OTHER', _OTHER),
        ],
    },

    'SAPROD': {
        "kind": 'VALUE',
        "rules": [
            *_map('SPTFSD', 204),
            *_map('SD    ', _OTHER),
        ],
    },

    'CAPROD': {
        "kind": 'VALUE',
        "rules": [
            *_map('OTHER',
                104, 105, 107, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 140, 141, 142, 143,
                144, 145, 146, 147, 148, 149, 171, 172, 173,
            ),
            *_map('DD   ', _OTHER),
        ],
    },

    'ODPROD': {
        "kind": 'VALUE',
        "rules": [
            *_map('OTHER',
                104, 105, 107, 126, 127, 128, 130, 131, 132, 133, 134, 135, 136, 140, 141, 142, 143, 144,
                145, 146, 147, 148, 149, 171, 172, 173,
            ),
            *_map('OD   ', _OTHER),
        ],
    },

    'LNPROD': {
        "kind": 'VALUE',
        "rules": [
            *_map('HL   ', 4, 5, 100, 101, 200, 201, 204, 205, 209, 210, 211, 212, 214, 215, 219, 220),
            *_map('HLCAG', 225, 226),
            *_map('FL   ', _OTHER),
        ],
    },

    'SADPRG': {
        "kind": 'VALUE',
        "rules": [
            *_map('01)RM        1.00 - RM         5.00', _span(_LOW, 5)),
            *_map('02)RM        5.01 - RM        10.00', _span(5, 10)),
            *_map('03)RM       10.01 - RM        50.00', _span(10, 50)),
            *_map('04)RM       50.01 - RM       100.00', _span(50, 100)),
            *_map('05)RM      100.01 - RM       500.00', _span(100, 500)),
            *_map('06)RM      500.01 - RM     1,000.00', _span(500, 1000)),
            *_map('07)RM    1,000.01 - RM     1,500.00', _span(1000, 1500)),
            *_map('08)RM    1,500.01 - RM     2,000.00', _span(1500, 2000)),
            *_map('09)RM    2,000.01 - RM     2,500.00', _span(2000, 2500)),
            *_map('10)RM    2,500.01 - RM     3,000.00', _span(2500, 3000)),
            *_map('11)RM    3,000.01 - RM     3,500.00', _span(3000, 3500)),
            *_map('12)RM    3,500.01 - RM     4,000.00', _span(3500, 4000)),
            *_map('13)RM    4,000.01 - RM     4,500.00', _span(4000, 4500)),
            *_map('14)RM    4,500.01 - RM     5,000.00', _span(4500, 5000)),
            *_map('15)RM    5,000.01 - RM     6,000.00', _span(5000, 6000)),
            *_map('16)RM    6,000.01 - RM     7,000.00', _span(6000, 7000)),
            *_map('17)RM    7,000.01 - RM     8,000.00', _span(7000, 8000)),
            *_map('18)RM    8,000.01 - RM     9,000.00', _span(8000, 9000)),
            *_map('19)RM    9,000.01 - RM    10,000.00', _span(9000, 10000)),
            *_map('20)RM   10,000.01 - RM    15,000.00', _span(10000, 15000)),
            *_map('21)RM   15,000.01 - RM    20,000.00', _span(15000, 20000)),
            *_map('22)RM   20,000.01 - RM    25,000.00', _span(20000, 25000)),
            *_map('23)RM   25,000.01 - RM    30,000.00', _span(25000, 30000)),
            *_map('24)RM   30,000.01 - RM    35,000.00', _span(30000, 35000)),
            *_map('25)RM   35,000.01 - RM    40,000.00', _span(35000, 40000)),
            *_map('26)RM   40,000.01 - RM    45,000.00', _span(40000, 45000)),
            *_map('27)RM   45,000.01 - RM    50,000.00', _span(45000, 50000)),
            *_map('28)RM   50,000.01 - RM    55,000.00', _span(50000, 55000)),
            *_map('29)RM   55,000.01 - RM    60,000.00', _span(55000, 60000)),
            *_map('30)RM   60,000.01 - RM    65,000.00', _span(60000, 65000)),
            *_map('31)RM   65,000.01 - RM    70,000.00', _span(65000, 70000)),
            *_map('32)RM   70,000.01 - RM    75,000.00', _span(70000, 75000)),
            *_map('33)RM   75,000.01 - RM    80,000.00', _span(75000, 80000)),
            *_map('34)RM   80,000.01 - RM    85,000.00', _span(80000, 85000)),
            *_map('35)RM   85,000.01 - RM    90,000.00', _span(85000, 90000)),
            *_map('36)RM   90,000.01 - RM    95,000.00', _span(90000, 95000)),
            *_map('37)RM   95,000.01 - RM   100,000.00', _span(95000, 100000)),
            *_map('38)RM  100,000.01 - RM   150,000.00', _span(100000, 150000)),
            *_map('39)RM  150,000.01 - RM   200,000.00', _span(150000, 200000)),
            *_map('40)RM  200,000.01 - RM   300,000.00', _span(200000, 300000)),
            *_map('41)RM  300,000.01 - RM   500,000.00', _span(300000, 500000)),
            *_map('42)RM  500,000.01 - RM 1,000,000.00', _span(500000, 1000000)),
            *_map('43)RM1,000,000.01 - RM 2,000,000.00', _span(1000000, 2000000)),
            *_map('44)RM2,000,000.01 - RM 3,000,000.00', _span(2000000, 3000000)),
            *_map('45)RM3,000,000.01 - RM 4,000,000.00', _span(3000000, 4000000)),
            *_map('46)RM4,000,000.01 - RM 5,000,000.00', _span(4000000, 5000000)),
            *_map('47)RM5,000,000.01 - RM10,000,000.00', _span(5000000, 10000000)),
            *_map('48)          ABOVE RM 10,000,000.00', _span(10000000, _HIGH)),
        ],
    },

    'SA1PRG': {
        "kind": 'VALUE',
        "rules": [
            *_map('01)RM        1.00 - RM         5.00', _span(_LOW, 5)),
            *_map('02)RM        5.01 - RM        10.00', _span(5, 10)),
            *_map('03)RM       10.01 - RM        50.00', _span(10, 50)),
            *_map('04)RM       50.01 - RM       100.00', _span(50, 100)),
            *_map('05)RM      100.01 - RM       500.00', _span(100, 500)),
            *_map('06)RM      500.01 - RM     1,000.00', _span(500, 1000)),
            *_map('07)RM    1,000.01 - RM     1,500.00', _span(1000, 1500)),
            *_map('08)RM    1,500.01 - RM     2,000.00', _span(1500, 2000)),
            *_map('09)RM    2,000.01 - RM     2,500.00', _span(2000, 2500)),
            *_map('10)RM    2,500.01 - RM     3,000.00', _span(2500, 3000)),
            *_map('11)RM    3,000.01 - RM     3,500.00', _span(3000, 3500)),
            *_map('12)RM    3,500.01 - RM     4,000.00', _span(3500, 4000)),
            *_map('13)RM    4,000.01 - RM     4,500.00', _span(4000, 4500)),
            *_map('14)RM    4,500.01 - RM     5,000.00', _span(4500, 5000)),
            *_map('15)RM    5,000.01 - RM     6,000.00', _span(5000, 6000)),
            *_map('16)RM    6,000.01 - RM     7,000.00', _span(6000, 7000)),
            *_map('17)RM    7,000.01 - RM     8,000.00', _span(7000, 8000)),
            *_map('18)RM    8,000.01 - RM     9,000.00', _span(8000, 9000)),
            *_map('19)RM    9,000.01 - RM    10,000.00', _span(9000, 10000)),
            *_map('20)RM   10,000.01 - RM    15,000.00', _span(10000, 15000)),
            *_map('21)RM   15,000.01 - RM    20,000.00', _span(15000, 20000)),
            *_map('22)RM   20,000.01 - RM    25,000.00', _span(20000, 25000)),
            *_map('23)RM   25,000.01 - RM    30,000.00', _span(25000, 30000)),
            *_map('24)RM   30,000.01 - RM    35,000.00', _span(30000, 35000)),
            *_map('25)RM   35,000.01 - RM    40,000.00', _span(35000, 40000)),
            *_map('26)RM   40,000.01 - RM    45,000.00', _span(40000, 45000)),
            *_map('27)RM   45,000.01 - RM    50,000.00', _span(45000, 50000)),
            *_map('28)RM   50,000.01 - RM    55,000.00', _span(50000, 55000)),
            *_map('29)RM   55,000.01 - RM    60,000.00', _span(55000, 60000)),
            *_map('30)RM   60,000.01 - RM    65,000.00', _span(60000, 65000)),
            *_map('31)RM   65,000.01 - RM    70,000.00', _span(65000, 70000)),
            *_map('32)RM   70,000.01 - RM    75,000.00', _span(70000, 75000)),
            *_map('33)RM   75,000.01 - RM    80,000.00', _span(75000, 80000)),
            *_map('34)RM   80,000.01 - RM    85,000.00', _span(80000, 85000)),
            *_map('35)RM   85,000.01 - RM    90,000.00', _span(85000, 90000)),
            *_map('36)RM   90,000.01 - RM    95,000.00', _span(90000, 95000)),
            *_map('37)RM   95,000.01 - RM   100,000.00', _span(95000, 100000)),
            *_map('38)RM  100,000.01 - RM   150,000.00', _span(100000, 150000)),
            *_map('39)RM  150,000.01 - RM   200,000.00', _span(150000, 200000)),
            *_map('40)RM  200,000.01 - RM   300,000.00', _span(200000, 300000)),
            *_map('41)RM  300,000.01 - RM   350,000.00', _span(300000, 350000)),
            *_map('42)RM  350,000.01 - RM   360,000.00', _span(350000, 360000)),
            *_map('43)RM  360,000.01 - RM   500,000.00', _span(360000, 500000)),
            *_map('44)RM  500,000.01 - RM   510,000.00', _span(500000, 510000)),
            *_map('45)RM  510,000.01 - RM   550,000.00', _span(510000, 550000)),
            *_map('46)RM  550,000.01 - RM   850,000.00', _span(550000, 850000)),
            *_map('47)RM  850,000.01 - RM   860,000.00', _span(850000, 860000)),
            *_map('48)RM  860,000.01 - RM 1,000,000.00', _span(860000, 1000000)),
            *_map('49)RM1,000,000.01 - RM 2,000,000.00', _span(1000000, 2000000)),
            *_map('50)RM2,000,000.01 - RM 3,000,000.00', _span(2000000, 3000000)),
            *_map('51)RM3,000,000.01 - RM 4,000,000.00', _span(3000000, 4000000)),
            *_map('52)RM4,000,000.01 - RM 5,000,000.00', _span(4000000, 5000000)),
            *_map('53)RM5,000,000.01 - RM10,000,000.00', _span(5000000, 10000000)),
            *_map('54)          ABOVE RM 10,000,000.00', _span(10000000, _HIGH)),
        ],
    },

    'SA2PRG': {
        "kind": 'VALUE',
        "rules": [
            *_map('ZERO BALANCE                             ', _span(_LOW, 0)),
            *_map('01)RM              1.00 - RM         5.00', _span(0, 5)),
            *_map('02)ABOVE RM        5.00 - RM        10.00', _span(5, 10)),
            *_map('03)ABOVE RM       10.00 - RM        50.00', _span(10, 50)),
            *_map('04)ABOVE RM       50.00 - RM       100.00', _span(50, 100)),
            *_map('05)ABOVE RM      100.00 - RM       500.00', _span(100, 500)),
            *_map('06)ABOVE RM      500.00 - RM     1,000.00', _span(500, 1000)),
            *_map('07)ABOVE RM    1,000.00 - RM     1,500.00', _span(1000, 1500)),
            *_map('08)ABOVE RM    1,500.00 - RM     2,000.00', _span(1500, 2000)),
            *_map('09)ABOVE RM    2,000.00 - RM     2,500.00', _span(2000, 2500)),
            *_map('10)ABOVE RM    2,500.00 - RM     3,000.00', _span(2500, 3000)),
            *_map('11)ABOVE RM    3,000.00 - RM     3,500.00', _span(3000, 3500)),
            *_map('12)ABOVE RM    3,500.00 - RM     4,000.00', _span(3500, 4000)),
            *_map('13)ABOVE RM    4,000.00 - RM     4,500.00', _span(4000, 4500)),
            *_map('14)ABOVE RM    4,500.00 - RM     5,000.00', _span(4500, 5000)),
            *_map('15)ABOVE RM    5,000.00 - RM     6,000.00', _span(5000, 6000)),
            *_map('16)ABOVE RM    6,000.00 - RM     7,000.00', _span(6000, 7000)),
            *_map('17)ABOVE RM    7,000.00 - RM     8,000.00', _span(7000, 8000)),
            *_map('18)ABOVE RM    8,000.00 - RM     9,000.00', _span(8000, 9000)),
            *_map('19)ABOVE RM    9,000.00 - RM    10,000.00', _span(9000, 10000)),
            *_map('20)ABOVE RM   10,000.00 - RM    15,000.00', _span(10000, 15000)),
            *_map('21)ABOVE RM   15,000.00 - RM    20,000.00', _span(15000, 20000)),
            *_map('22)ABOVE RM   20,000.00 - RM    25,000.00', _span(20000, 25000)),
            *_map('23)ABOVE RM   25,000.00 - RM    30,000.00', _span(25000, 30000)),
            *_map('24)ABOVE RM   30,000.00 - RM    35,000.00', _span(30000, 35000)),
            *_map('25)ABOVE RM   35,000.00 - RM    40,000.00', _span(35000, 40000)),
            *_map('26)ABOVE RM   40,000.00 - RM    45,000.00', _span(40000, 45000)),
            *_map('27)ABOVE RM   45,000.00 - RM    50,000.00', _span(45000, 50000)),
            *_map('28)ABOVE RM   50,000.00 - RM    55,000.00', _span(50000, 55000)),
            *_map('29)ABOVE RM   55,000.00 - RM    60,000.00', _span(55000, 60000)),
            *_map('30)ABOVE RM   60,000.00 - RM    65,000.00', _span(60000, 65000)),
            *_map('31)ABOVE RM   65,000.00 - RM    70,000.00', _span(65000, 70000)),
            *_map('32)ABOVE RM   70,000.00 - RM    75,000.00', _span(70000, 75000)),
            *_map('33)ABOVE RM   75,000.00 - RM    80,000.00', _span(75000, 80000)),
            *_map('34)ABOVE RM   80,000.00 - RM    85,000.00', _span(80000, 85000)),
            *_map('35)ABOVE RM   85,000.00 - RM    90,000.00', _span(85000, 90000)),
            *_map('36)ABOVE RM   90,000.00 - RM    95,000.00', _span(90000, 95000)),
            *_map('37)ABOVE RM   95,000.00 - RM   100,000.00', _span(95000, 100000)),
            *_map('38)ABOVE RM  100,000.00 - RM   150,000.00', _span(100000, 150000)),
            *_map('39)ABOVE RM  150,000.00 - RM   200,000.00', _span(150000, 200000)),
            *_map('40)ABOVE RM  200,000.00 - RM   300,000.00', _span(200000, 300000)),
            *_map('41)ABOVE RM  300,000.00 - RM   350,000.00', _span(300000, 350000)),
            *_map('42)ABOVE RM  350,000.00 - RM   360,000.00', _span(350000, 360000)),
            *_map('43)ABOVE RM  360,000.00 - RM   500,000.00', _span(360000, 500000)),
            *_map('44)ABOVE RM  500,000.00 - RM   510,000.00', _span(500000, 510000)),
            *_map('45)ABOVE RM  510,000.00 - RM   550,000.00', _span(510000, 550000)),
            *_map('46)ABOVE RM  550,000.00 - RM   600,000.00', _span(550000, 600000)),
            *_map('47)ABOVE RM  600,000.00 - RM   700,000.00', _span(600000, 700000)),
            *_map('48)ABOVE RM  700,000.00 - RM   800,000.00', _span(700000, 800000)),
            *_map('49)ABOVE RM  800,000.00 - RM   850,000.00', _span(800000, 850000)),
            *_map('50)ABOVE RM  850,000.00 - RM   860,000.00', _span(850000, 860000)),
            *_map('51)ABOVE RM  860,000.00 - RM   900,000.00', _span(860000, 900000)),
            *_map('52)ABOVE RM  900,000.00 - RM 1,000,000.00', _span(900000, 1000000)),
            *_map('53)ABOVE RM1,000,000.00 - RM 1,100,000.00', _span(1000000, 1100000)),
            *_map('54)ABOVE RM1,100,000.00 - RM 1,200,000.00', _span(1100000, 1200000)),
            *_map('55)ABOVE RM1,200,000.00 - RM 1,300,000.00', _span(1200000, 1300000)),
            *_map('56)ABOVE RM1,300,000.00 - RM 1,400,000.00', _span(1300000, 1400000)),
            *_map('57)ABOVE RM1,400,000.00 - RM 1,500,000.00', _span(1400000, 1500000)),
            *_map('58)ABOVE RM1,500,000.00 - RM 1,600,000.00', _span(1500000, 1600000)),
            *_map('59)ABOVE RM1,600,000.00 - RM 1,700,000.00', _span(1600000, 1700000)),
            *_map('60)ABOVE RM1,700,000.00 - RM 1,800,000.00', _span(1700000, 1800000)),
            *_map('61)ABOVE RM1,800,000.00 - RM 1,900,000.00', _span(1800000, 1900000)),
            *_map('62)ABOVE RM1,900,000.00 - RM 2,000,000.00', _span(1900000, 2000000)),
            *_map('63)ABOVE RM2,000,000.00 - RM 3,000,000.00', _span(2000000, 3000000)),
            *_map('64)ABOVE RM3,000,000.00 - RM 4,000,000.00', _span(3000000, 4000000)),
            *_map('65)ABOVE RM4,000,000.00 - RM 5,000,000.00', _span(4000000, 5000000)),
            *_map('66)ABOVE RM5,000,000.00 - RM10,000,000.00', _span(5000000, 10000000)),
            *_map('67)                ABOVE RM 10,000,000.00', _span(10000000, _HIGH)),
        ],
    },

    'SA3PRG': {
        "kind": 'VALUE',
        "rules": [
            *_map('01)NEGATIVE BALANCE                      ', _span(_LOW, 0, exclude_end=True)),
            *_map('02)ZERO BALANCE                          ', 0),
            *_map('03)ABOVE RM        0.00 - RM         5.00', _span(0, 5, exclude_start=True)),
            *_map('04)ABOVE RM        5.00 - RM        10.00', _span(5, 10, exclude_start=True)),
            *_map('05)ABOVE RM       10.00 - RM        50.00', _span(10, 50, exclude_start=True)),
            *_map('06)ABOVE RM       50.00 - RM       100.00', _span(50, 100, exclude_start=True)),
            *_map('07)ABOVE RM      100.00 - RM       500.00', _span(100, 500, exclude_start=True)),
            *_map('08)ABOVE RM      500.00 - RM     1,000.00', _span(500, 1000, exclude_start=True)),
            *_map('09)ABOVE RM    1,000.00 - RM     1,500.00', _span(1000, 1500, exclude_start=True)),
            *_map('10)ABOVE RM    1,500.00 - RM     2,000.00', _span(1500, 2000, exclude_start=True)),
            *_map('11)ABOVE RM    2,000.00 - RM     2,500.00', _span(2000, 2500, exclude_start=True)),
            *_map('12)ABOVE RM    2,500.00 - RM     3,000.00', _span(2500, 3000, exclude_start=True)),
            *_map('13)ABOVE RM    3,000.00 - RM     3,500.00', _span(3000, 3500, exclude_start=True)),
            *_map('14)ABOVE RM    3,500.00 - RM     4,000.00', _span(3500, 4000, exclude_start=True)),
            *_map('15)ABOVE RM    4,000.00 - RM     4,500.00', _span(4000, 4500, exclude_start=True)),
            *_map('16)ABOVE RM    4,500.00 - RM     5,000.00', _span(4500, 5000, exclude_start=True)),
            *_map('17)ABOVE RM    5,000.00 - RM     6,000.00', _span(5000, 6000, exclude_start=True)),
            *_map('18)ABOVE RM    6,000.00 - RM     7,000.00', _span(6000, 7000, exclude_start=True)),
            *_map('19)ABOVE RM    7,000.00 - RM     8,000.00', _span(7000, 8000, exclude_start=True)),
            *_map('20)ABOVE RM    8,000.00 - RM     9,000.00', _span(8000, 9000, exclude_start=True)),
            *_map('21)ABOVE RM    9,000.00 - RM    10,000.00', _span(9000, 10000, exclude_start=True)),
            *_map('22)ABOVE RM   10,000.00 - RM    15,000.00', _span(10000, 15000, exclude_start=True)),
            *_map('23)ABOVE RM   15,000.00 - RM    20,000.00', _span(15000, 20000, exclude_start=True)),
            *_map('24)ABOVE RM   20,000.00 - RM    25,000.00', _span(20000, 25000, exclude_start=True)),
            *_map('25)ABOVE RM   25,000.00 - RM    30,000.00', _span(25000, 30000, exclude_start=True)),
            *_map('26)ABOVE RM   30,000.00 - RM    35,000.00', _span(30000, 35000, exclude_start=True)),
            *_map('27)ABOVE RM   35,000.00 - RM    40,000.00', _span(35000, 40000, exclude_start=True)),
            *_map('28)ABOVE RM   40,000.00 - RM    45,000.00', _span(40000, 45000, exclude_start=True)),
            *_map('29)ABOVE RM   45,000.00 - RM    50,000.00', _span(45000, 50000, exclude_start=True)),
            *_map('30)ABOVE RM   50,000.00 - RM    55,000.00', _span(50000, 55000, exclude_start=True)),
            *_map('31)ABOVE RM   55,000.00 - RM    60,000.00', _span(55000, 60000, exclude_start=True)),
            *_map('32)ABOVE RM   60,000.00 - RM    65,000.00', _span(60000, 65000, exclude_start=True)),
            *_map('33)ABOVE RM   65,000.00 - RM    70,000.00', _span(65000, 70000, exclude_start=True)),
            *_map('34)ABOVE RM   70,000.00 - RM    75,000.00', _span(70000, 75000, exclude_start=True)),
            *_map('35)ABOVE RM   75,000.00 - RM    80,000.00', _span(75000, 80000, exclude_start=True)),
            *_map('36)ABOVE RM   80,000.00 - RM    85,000.00', _span(80000, 85000, exclude_start=True)),
            *_map('37)ABOVE RM   85,000.00 - RM    90,000.00', _span(85000, 90000, exclude_start=True)),
            *_map('38)ABOVE RM   90,000.00 - RM    95,000.00', _span(90000, 95000, exclude_start=True)),
            *_map('39)ABOVE RM   95,000.00 - RM   100,000.00', _span(95000, 100000, exclude_start=True)),
            *_map('40)ABOVE RM  100,000.00 - RM   150,000.00', _span(100000, 150000, exclude_start=True)),
            *_map('41)ABOVE RM  150,000.00 - RM   200,000.00', _span(150000, 200000, exclude_start=True)),
            *_map('42)ABOVE RM  200,000.00 - RM   300,000.00', _span(200000, 300000, exclude_start=True)),
            *_map('43)ABOVE RM  300,000.00 - RM   350,000.00', _span(300000, 350000, exclude_start=True)),
            *_map('44)ABOVE RM  350,000.00 - RM   360,000.00', _span(350000, 360000, exclude_start=True)),
            *_map('45)ABOVE RM  360,000.00 - RM   500,000.00', _span(360000, 500000, exclude_start=True)),
            *_map('46)ABOVE RM  500,000.00 - RM   510,000.00', _span(500000, 510000, exclude_start=True)),
            *_map('47)ABOVE RM  510,000.00 - RM   550,000.00', _span(510000, 550000, exclude_start=True)),
            *_map('48)ABOVE RM  550,000.00 - RM   850,000.00', _span(550000, 850000, exclude_start=True)),
            *_map('49)ABOVE RM  850,000.00 - RM   860,000.00', _span(850000, 860000, exclude_start=True)),
            *_map('50)ABOVE RM  860,000.00 - RM  1000,000.00', _span(860000, 1000000, exclude_start=True)),
            *_map('51)ABOVE RM 1000,000.00 - RM  2000,000.00', _span(1000000, 2000000, exclude_start=True)),
            *_map('52)ABOVE RM 2000,000.00 - RM  3000,000.00', _span(2000000, 3000000, exclude_start=True)),
            *_map('53)ABOVE RM 3000,000.00 - RM  4000,000.00', _span(3000000, 4000000, exclude_start=True)),
            *_map('54)ABOVE RM 4000,000.00 - RM  5000,000.00', _span(4000000, 5000000, exclude_start=True)),
            *_map('55)ABOVE RM 5000,000.00 - RM10,000,000.00', _span(5000000, 10000000, exclude_start=True)),
            *_map('56)ABOVE RM 10,000,000.00                ', _span(10000000, _HIGH, exclude_start=True)),
        ],
    },

    'PROFNORM': {
        "kind": 'VALUE',
        "rules": [
            *_map('1)UP TO RM 5,000.00', _span(_LOW, 5000)),
            *_map('2)UP TO RM10,000.00', _span(5000, 10000)),
            *_map('3)UP TO RM30,000.00', _span(10000, 30000)),
            *_map('4)UP TO RM50,000.00', _span(30000, 50000)),
            *_map('5)UP TO RM75,000.00', _span(50000, 75000)),
            *_map('6)ABOVE RM75,000.00', _span(75000, _HIGH)),
        ],
    },

    'SEXNORM': {
        "kind": 'VALUE',
        "rules": [
            *_map('1)BELOW 12 YRS', _span(_LOW, 12)),
            *_map('2)12 - 18 YRS', _span(12, 18)),
            *_map('3)18 - 50 YRS', _span(18, 50)),
            *_map('4)50 YRS AND ABOVE', _span(50, _HIGH)),
        ],
    },

    'PROFYAA': {
        "kind": 'VALUE',
        "rules": [
            *_map('1)BELOW RM   500.00', _span(_LOW, 500)),
            *_map('2)UP TO RM 2,000.00', _span(500, 2000)),
            *_map('3)UP TO RM 5,000.00', _span(2000, 5000)),
            *_map('4)UP TO RM10,000.00', _span(5000, 10000)),
            *_map('5)UP TO RM30,000.00', _span(10000, 30000)),
            *_map('6)UP TO RM50,000.00', _span(30000, 50000)),
            *_map('7)UP TO RM75,000.00', _span(50000, 75000)),
            *_map('8)ABOVE RM75,000.00', _span(75000, _HIGH)),
        ],
    },

    'SEXYW': {
        "kind": 'VALUE',
        "rules": [
            *_map('1)BELOW 12 YRS', _span(_LOW, 12)),
            *_map('2)12 - 18 YRS', _span(12, 18)),
        ],
    },

    'PROFPLUS': {
        "kind": 'VALUE',
        "rules": [
            *_map('1)UP TO RM 2,000.00', _span(_LOW, 2000)),
            *_map('1)UP TO RM 5,000.00', _span(2000, 5000)),
            *_map('2)UP TO RM10,000.00', _span(5000, 10000)),
            *_map('3)UP TO RM30,000.00', _span(10000, 30000)),
            *_map('4)UP TO RM50,000.00', _span(30000, 50000)),
            *_map('5)UP TO RM75,000.00', _span(50000, 75000)),
            *_map('6)ABOVE RM75,000.00', _span(75000, _HIGH)),
        ],
    },

    'PROFWISE': {
        "kind": 'VALUE',
        "rules": [
            *_map('1)UP TO RM 5,000.00', _span(_LOW, 5000)),
            *_map('2)UP TO RM10,000.00', _span(5000, 10000)),
            *_map('3)UP TO RM20,000.00', _span(10000, 20000)),
            *_map('4)UP TO RM30,000.00', _span(20000, 30000)),
            *_map('5)UP TO RM50,000.00', _span(30000, 50000)),
            *_map('6)ABOVE RM50,000.00', _span(50000, _HIGH)),
        ],
    },

    'SDNAME': {
        "kind": 'VALUE',
        "rules": [
            *_map('PLUS SAVING', 200),
            *_map('STAFF', 201),
            *_map('YOUNG ACHIEVER', 202),
            *_map('50 PLUS', 203),
            *_map('AL-WADIAH', 204),
            *_map('BASIC SAVING', 205),
            *_map('BASIC 55 SAVING', 206),
            *_map('PB BRIGHT STAR SA', 208),
            *_map('PB MYSALARY SA', 210),
            *_map('WISE', 212),
            *_map('PB SAVELINK', 213),
            *_map('BESTARI SAVING', 214),
            *_map('STAFF WADIAH', 215),
            *_map('PB UNIONPAY SA', 216),
            *_map('STAFF MONEYPLUS SA', 227),
            *_map('MONEYPLUS SA', 228),
            *_map('GIA', 480),
            *_map('STAFF GIA', 481),
        ],
    },

    '$RACE': {
        "kind": 'VALUE',
        "rules": [
            *_map('OTHERS', '0'),
            *_map('MALAY', '1'),
            *_map('CHINESE', '2'),
            *_map('INDIAN', '3'),
            *_map('OTHERS', _OTHER),
        ],
    },

    'CADPRG': {
        "kind": 'VALUE',
        "rules": [
            *_map(' 1)         RM0 -     RM1,000', 1000),
            *_map(' 2)     RM1,001 -     RM2,000', 2000),
            *_map(' 3)     RM2,001 -     RM2,500', 2500),
            *_map(' 4)     RM2,501 -     RM5,000', 3000, 5000),
            *_map(' 5)     RM5,001 -    RM10,000', 10000),
            *_map(' 6)    RM10,001 -    RM20,000', 20000),
            *_map(' 7)    RM20,001 -    RM30,000', 30000),
            *_map(' 8)    RM30,001 -    RM40,000', 40000),
            *_map(' 9)    RM40,001 -    RM50,000', 50000),
            *_map('10)   RM50,001 -   RM100,000', 75000, 100000),
            *_map('11)  RM100,001 -   RM150,000', 150000),
            *_map('12)  RM150,001 -   RM200,000', 200000),
            *_map('13)  RM200,001 -   RM250,000', 250000),
            *_map('14)  RM250,001 -   RM500,000', 500000),
            *_map('15)  RM500,001 - RM1,000,000', 1000000),
            *_map('16)RM1,000,001 - RM2,000,000', 2000000),
            *_map('17)RM2,000,001 - RM3,000,000', 3000000),
            *_map('18)RM3,000,001 - RM4,000,000', 4000000),
            *_map('19)RM4,000,001 - RM5,000,000', 5000000),
            *_map('20)RM5,000,001 AND ABOVE', _OTHER),
        ],
    },

    'ICADPRG': {
        "kind": 'VALUE',
        "rules": [
            *_map(' 1)     BELOW  RM2,000', 1000, 2000),
            *_map(' 2) RM2,000 -  RM3,000', 2500, 3000),
            *_map(' 3) RM3,000 -  RM5,000', 5000),
            *_map(' 4) RM5,000 -  RM10,000', 10000),
            *_map(' 5) RM10,000 - RM30,000', 20000, 30000),
            *_map(' 6) RM30,000 - RM50,000', 40000, 50000),
            *_map(' 7) RM50,000 - RM75,000', 75000),
            *_map(' 8) RM75,000 - RM100,000', 100000),
            *_map(' 9) RM100,000 -  RM150,000', 150000),
            *_map('10) RM150,000 -  RM200,000', 200000),
            *_map('11) RM200,000 AND ABOVE', _OTHER),
        ],
    },

    '$CPARTYF': {
        "kind": 'VALUE',
        "rules": [
            *_map('01', '01'),
            *_map('10', '02', '03'),
            *_map('20', '04', '05', '06'),
            *_map('10', '10', '11', '12'),
            *_map('20', '13', '15', '17', '20', '30', '32', '33', '34', '35', '36', '37', '38', '39', '40'),
            *_map('60', '50', '57', '59', '60', '61', '62', '63', '64', '65', '66', '67', '68', '69'),
            *_map('70', '70', '71', '72', '73', '74'),
            *_map('60', '75'),
            *_map('76', '76', '77', '78'),
            *_map('79', '79'),
            *_map('80', '80', '81', '85', '86', '90', '91', '92', '95', '96', '98', '99'),
            *_map('76', _OTHER),
        ],
    },

    '$CPARTY': {
        "kind": 'VALUE',
        "rules": [
            *_map('BANK NEGARA MALAYSIA', '01'),
            *_map('DOMESTIC BANKING INSTITUTION', '10'),
            *_map('DOMESTIC NON-BANK FI', '20'),
            *_map('DOMESTIC BUSINESS ENTERPRISES', '60'),
            *_map('GOVERNMENT', '70'),
            *_map('INDIVIDUALS', '76'),
            *_map('DOMESTIC OTHER ENTITIES NIE', '79'),
            *_map('NON RESIDENTS/FOREIGN ENTITIES', '80'),
        ],
    },

    '$PURPOSE': {
        "kind": 'VALUE',
        "rules": [
            *_map('PERSONAL', '1'),
            *_map('JOINT', '2'),
            *_map('PERSONAL', '4'),
            *_map('OTHERS  ', _OTHER),
        ],
    },

    'CARANGED': {
        "kind": 'VALUE',
        "rules": [
            *_map(' 1)         BELOW RM2,000', 2000),
            *_map(' 2)     RM2,000 - RM3,000', 3000),
            *_map(' 3)     RM3,000 - RM5,000', 5000),
            *_map(' 4)    RM5,000 - RM10,000', 10000),
            *_map(' 5)   RM10,000 - RM30,000', 30000),
            *_map(' 6)   RM30,000 - RM50,000', 50000),
            *_map(' 7)   RM50,000 - RM75,000', 75000),
            *_map(' 8)  RM75,000 - RM100,000', 100000),
            *_map(' 9) RM100,000 - RM150,000', 150000),
            *_map('10) RM150,000 - RM200,000', 200000),
            *_map('11) RM200,000 AND ABOVE  ', 200001),
        ],
    },

    'PROD': {
        "kind": 'VALUE',
        "rules": [
            *_map('ACE ACCOUNT', 150),
            *_map('AL-WADIAH CURRENT A/C', 160),
        ],
    },

    'AGEDESC': {
        "kind": 'VALUE',
        "rules": [
            *_map('WITHOUT BIRTHDATE', 0),
            *_map('BELOW 12 YEARS', {'macro': 'AGEBELOW'}),
            *_map('12 TO BELOW 18 YEARS', {'macro': 'AGELIMIT'}),
            *_map('18 AND ABOVE', {'macro': 'MAXAGE'}),
        ],
    },

    '$STATE': {
        "kind": 'VALUE',
        "rules": [
            *_map('PERAK', 'A'),
            *_map('SELANGOR', 'B'),
            *_map('PAHANG', 'C'),
            *_map('KELANTAN', 'D'),
            *_map('JOHOR', 'J'),
            *_map('KEDAH', 'K'),
            *_map('LABUAN', 'L'),
            *_map('MELAKA', 'M'),
            *_map('NEGERI SEMBILAN', 'N'),
            *_map('PULAU PINANG', 'P'),
            *_map('SARAWAK', 'Q'),
            *_map('PERLIS', 'R'),
            *_map('SABAH', 'S'),
            *_map('TERENGGANU', 'T'),
            *_map('WILAYAH PERSEKUTUAN', 'W'),
        ],
    },

    'FDPROD': {
        "kind": 'VALUE',
        "rules": [
            *_map('1 MONTH', 340),
            *_map('3 MONTHS', 341),
            *_map('6 MONTHS', 342),
            *_map('9 MONTHS', 343),
            *_map('12 MONTHS', 344),
            *_map('15 MONTHS', 345),
            *_map('18 MONTHS', 346),
            *_map('21 MONTHS', 347),
            *_map('24 MONTHS', 348),
            *_map('36 MONTHS', 349),
            *_map('48 MONTHS', 350),
            *_map('60 MONTHS', 351),
            *_map(' ', _OTHER),
        ],
    },

    'IBWRNGE': {
        "kind": 'INVALUE',
        "rules": [
            *_map(10000, _span(_LOW, 10000)),
            *_map(30000, _span(10000, 30000)),
            *_map(50000, _span(30000, 50000)),
            *_map(75000, _span(50000, 75000)),
            *_map(100000, _span(75000, 100000)),
            *_map(100001, _span(100000, _HIGH)),
        ],
    },

    'CARANGE': {
        "kind": 'INVALUE',
        "rules": [
            *_map(2000, _span(_LOW, 2000)),
            *_map(3000, _span(2000, 3000)),
            *_map(5000, _span(3000, 5000)),
            *_map(10000, _span(5000, 10000)),
            *_map(30000, _span(10000, 30000)),
            *_map(50000, _span(30000, 50000)),
            *_map(75000, _span(50000, 75000)),
            *_map(100000, _span(75000, 100000)),
            *_map(150000, _span(100000, 150000)),
            *_map(200000, _span(150000, 200000)),
            *_map(200001, _span(200000, _HIGH)),
        ],
    },

    'ISARANGE': {
        "kind": 'INVALUE',
        "rules": [
            *_map(1000, _span(_LOW, 1000)),
            *_map(5000, _span(1000, 5000)),
            *_map(25000, _span(5000, 25000)),
            *_map(50000, _span(25000, 50000)),
            *_map(50001, _span(50000, _HIGH)),
        ],
    },

    'ISARANGD': {
        "kind": 'VALUE',
        "rules": [
            *_map(' 1)       BELOW RM1,000', 1000),
            *_map(' 2)   RM1,000 - RM5,000', 5000),
            *_map(' 3)  RM5,000 - RM25,000', 25000),
            *_map(' 4) RM25,000 - RM50,000', 50000),
            *_map(' 5) RM50,000 AND ABOVE ', 50001),
        ],
    },

    'IWSRNGE': {
        "kind": 'VALUE',
        "rules": [
            *_map(' 1) UP TO   RM  3,000', _span(_LOW, 3001, exclude_end=True)),
            *_map(' 2) UP TO   RM 10,000', _span(3001, 10001, exclude_end=True)),
            *_map(' 3) UP TO   RM 30,000', _span(10001, 30001, exclude_end=True)),
            *_map(' 4) UP TO   RM 50,000', _span(30001, 50001, exclude_end=True)),
            *_map(' 5) UP TO   RM 75,000', _span(50001, 75001, exclude_end=True)),
            *_map(' 6) UP TO   RM100,000', _span(75001, 100001, exclude_end=True)),
            *_map(' 7) ABOVE RM100,000  ', _span(100001, _HIGH)),
        ],
    },

    'IWSRNGX': {
        "kind": 'VALUE',
        "rules": [
            *_map(' 1) FIRST RM  5,000', _span(_LOW, 5000)),
            *_map(' 2) NEXT  RM  5,000', _span(5000, 10000)),
            *_map(' 3) NEXT  RM 40,000', _span(10000, 50000)),
            *_map(' 4) NEXT  RM100,000', _span(50000, 150000)),
            *_map(' 5) NEXT  RM200,000', _span(150000, 350000)),
            *_map(' 6) NEXT  RM300,000', _span(350000, 650000)),
            *_map(' 6) NEXT  RM550,000', _span(650000, 1200000)),
            *_map(' 7) THEREAFTER     ', _span(1200000, _HIGH)),
        ],
    },

    'IBWSRNGD': {
        "kind": 'VALUE',
        "rules": [
            *_map(' 1) UP TO   RM 10,000', _span(_LOW, 10001, exclude_end=True)),
            *_map(' 2) UP TO   RM 30,000', _span(10001, 30001, exclude_end=True)),
            *_map(' 3) UP TO   RM 50,000', _span(30001, 50001, exclude_end=True)),
            *_map(' 4) UP TO   RM 75,000', _span(50001, 75001, exclude_end=True)),
            *_map(' 5) UP TO   RM100,000', _span(75001, 100001, exclude_end=True)),
            *_map(' 6) ABOVE RM100,000  ', _span(100001, _HIGH)),
        ],
    },

    'HUNDRED': {
        "kind": 'PICTURE',
        "rules": [
            *_map('0,000,009.99', _span(_LOW, 0, exclude_end=True), options={'PREFIX': '-', 'MULT': 1}),
            *_map('0,000,009.99', _span(0, _HIGH), options={'MULT': 1}),
        ],
    },

    'THOUSAND': {
        "kind": 'PICTURE',
        "rules": [
            *_map('0,000,000,009', _span(_LOW, 0, exclude_end=True), options={'PREFIX': '-', 'MULT': 0.001}),
            *_map('0,000,000,009', _span(0, _HIGH), options={'MULT': 0.001}),
        ],
    },

    'MILLION': {
        "kind": 'PICTURE',
        "rules": [
            *_map('0,000,000,009', _span(_LOW, 0, exclude_end=True), options={'PREFIX': '-', 'MULT': 1e-06}),
            *_map('0,000,000,009', _span(0, _HIGH), options={'MULT': 1e-06}),
        ],
    },

    'LNPOGRP': {
        "kind": 'VALUE',
        "rules": [
            *_map('01-SELANGOR/WILAYAH REG.   I',
                2, 3, 22, 46, 53, 56, 120, 129, 136, 169, 170, 173, 196, 226, 232, 252, 262, 802, 811, 818,
                284, 285, 291,
            ),
            *_map('02-SELANGOR/WILAYAH REG.  II',
                15, 29, 40, 41, 66, 83, 96, 97, 101, 103, 118, 128, 141, 151, 195, 197, 248, 269, 701, 812,
                821, 822,
            ),
            *_map('03-SELANGOR/WILAYAH REG. III',
                18, 19, 35, 36, 81, 124, 125, 131, 135, 145, 148, 162, 167, 180, 220, 241, 267, 280, 292,
                295, 815, 816,
            ),
            *_map('04-SOUTHERN REGION I       ',
                7, 37, 52, 59, 61, 79, 87, 89, 91, 93, 102, 105, 110, 144, 147, 174, 176, 216, 217, 222, 234,
                286, 287, 290, 804, 805,
            ),
            *_map('05-CENTRAL REGION           ',
                5, 9, 49, 51, 67, 71, 76, 80, 85, 95, 123, 137, 146, 152, 158, 207, 208, 209, 210, 244, 245,
                251, 809, 823,
            ),
            *_map('06-SARAWAK REGION           ',
                32, 50, 58, 90, 130, 175, 183, 184, 185, 186, 189, 190, 191, 192, 193, 194, 259, 813, 273,
                274, 275, 281,
            ),
            *_map('07-SABAH REGION             ',
                33, 44, 55, 62, 72, 112, 115, 140, 142, 143, 149, 161, 228, 803, 278, 276, 282, 283,
            ),
            *_map('08-SOUTHERN REGION II       ',
                4, 16, 17, 21, 24, 28, 39, 45, 47, 63, 64, 65, 75, 111, 156, 160, 165, 172, 224, 231, 242,
                247, 254, 800, 807,
            ),
            *_map('09-NORTHERN REGION I        ',
                6, 10, 34, 54, 70, 74, 77, 86, 104, 107, 114, 126, 150, 159, 171, 205, 238, 258, 265, 266,
                806, 808, 817, 704,
            ),
            *_map('10-EAST COAST REGION        ',
                8, 13, 14, 30, 48, 106, 113, 116, 117, 139, 233, 237, 239, 257, 260, 261, 263, 264, 819, 277,
                703,
            ),
            *_map('11-SELANGOR/WILAYAH REG.  IV',
                26, 38, 94, 122, 138, 153, 155, 157, 163, 168, 178, 179, 198, 225, 230, 270, 296, 814, 820,
                279, 288, 289, 702,
            ),
            *_map('12-NORTHERN REGION II       ',
                23, 27, 42, 57, 60, 68, 88, 108, 121, 154, 164, 177, 204, 206, 211, 249, 256, 801, 824, 11,
                243,
            ),
            *_map('13-SELANGOR/WILAYAH REG.   V',
                20, 25, 31, 43, 69, 73, 78, 92, 109, 127, 133, 199, 201, 202, 203, 221, 235, 240, 268, 293,
                294,
            ),
            *_map('99-OTHER', _OTHER),
        ],
    },

}


def format_value(name, value):
    """Apply an original SAS format name; accepts trailing dots and $ names."""
    return lookup(FORMATS, name.strip(), value, MACROS)


def put(value, format_name):
    """SAS-style argument order: put(value, 'BRCHCD.')."""
    return format_value(format_name, value)


def informat(value, informat_name):
    """Apply an INVALUE definition; reject VALUE/PICTURE names."""
    name = informat_name.strip().upper().rstrip('.')
    if FORMATS[name]['kind'] != 'INVALUE':
        raise ValueError(f'{name} is not an INVALUE definition')
    return format_value(name, value)


def apply_format(values, format_name):
    """Map an iterable to a list, or a pandas Series to a Series retaining its index.

    A Series uses its native map method; scalar lookups need no pandas import.
    """
    if isinstance(values, (str, bytes)):
        raise TypeError('Pass a list or Series; use put() for a scalar value')
    if hasattr(values, 'map') and hasattr(values, 'index'):
        return values.map(lambda value: format_value(format_name, value))
    return [format_value(format_name, value) for value in values]


def available_formats():
    """List exact SAS format names, including character-format $ prefixes."""
    return sorted(FORMATS)


def get_rules(format_name):
    """Return an independent copy of a format's kind and ordered mapping rules."""
    from copy import deepcopy
    return deepcopy(FORMATS[format_name.strip().upper().rstrip('.')])


def BRCHCD(value):
    """Apply the original SAS BRCHCD format."""
    return format_value('BRCHCD', value)


def GROUPF(value):
    """Apply the original SAS $GROUPF format."""
    return format_value('$GROUPF', value)


def ACKNOF(value):
    """Apply the original SAS $ACKNOF format."""
    return format_value('$ACKNOF', value)


def SAPROD(value):
    """Apply the original SAS SAPROD format."""
    return format_value('SAPROD', value)


def CAPROD(value):
    """Apply the original SAS CAPROD format."""
    return format_value('CAPROD', value)


def ODPROD(value):
    """Apply the original SAS ODPROD format."""
    return format_value('ODPROD', value)


def LNPROD(value):
    """Apply the original SAS LNPROD format."""
    return format_value('LNPROD', value)


def SADPRG(value):
    """Apply the original SAS SADPRG format."""
    return format_value('SADPRG', value)


def SA1PRG(value):
    """Apply the original SAS SA1PRG format."""
    return format_value('SA1PRG', value)


def SA2PRG(value):
    """Apply the original SAS SA2PRG format."""
    return format_value('SA2PRG', value)


def SA3PRG(value):
    """Apply the original SAS SA3PRG format."""
    return format_value('SA3PRG', value)


def PROFNORM(value):
    """Apply the original SAS PROFNORM format."""
    return format_value('PROFNORM', value)


def SEXNORM(value):
    """Apply the original SAS SEXNORM format."""
    return format_value('SEXNORM', value)


def PROFYAA(value):
    """Apply the original SAS PROFYAA format."""
    return format_value('PROFYAA', value)


def SEXYW(value):
    """Apply the original SAS SEXYW format."""
    return format_value('SEXYW', value)


def PROFPLUS(value):
    """Apply the original SAS PROFPLUS format."""
    return format_value('PROFPLUS', value)


def PROFWISE(value):
    """Apply the original SAS PROFWISE format."""
    return format_value('PROFWISE', value)


def SDNAME(value):
    """Apply the original SAS SDNAME format."""
    return format_value('SDNAME', value)


def RACE(value):
    """Apply the original SAS $RACE format."""
    return format_value('$RACE', value)


def CADPRG(value):
    """Apply the original SAS CADPRG format."""
    return format_value('CADPRG', value)


def ICADPRG(value):
    """Apply the original SAS ICADPRG format."""
    return format_value('ICADPRG', value)


def CPARTYF(value):
    """Apply the original SAS $CPARTYF format."""
    return format_value('$CPARTYF', value)


def CPARTY(value):
    """Apply the original SAS $CPARTY format."""
    return format_value('$CPARTY', value)


def PURPOSE(value):
    """Apply the original SAS $PURPOSE format."""
    return format_value('$PURPOSE', value)


def CARANGED(value):
    """Apply the original SAS CARANGED format."""
    return format_value('CARANGED', value)


def PROD(value):
    """Apply the original SAS PROD format."""
    return format_value('PROD', value)


def AGEDESC(value):
    """Apply the original SAS AGEDESC format."""
    return format_value('AGEDESC', value)


def STATE(value):
    """Apply the original SAS $STATE format."""
    return format_value('$STATE', value)


def FDPROD(value):
    """Apply the original SAS FDPROD format."""
    return format_value('FDPROD', value)


def IBWRNGE(value):
    """Apply the original SAS IBWRNGE format."""
    return format_value('IBWRNGE', value)


def CARANGE(value):
    """Apply the original SAS CARANGE format."""
    return format_value('CARANGE', value)


def ISARANGE(value):
    """Apply the original SAS ISARANGE format."""
    return format_value('ISARANGE', value)


def ISARANGD(value):
    """Apply the original SAS ISARANGD format."""
    return format_value('ISARANGD', value)


def IWSRNGE(value):
    """Apply the original SAS IWSRNGE format."""
    return format_value('IWSRNGE', value)


def IWSRNGX(value):
    """Apply the original SAS IWSRNGX format."""
    return format_value('IWSRNGX', value)


def IBWSRNGD(value):
    """Apply the original SAS IBWSRNGD format."""
    return format_value('IBWSRNGD', value)


def HUNDRED(value):
    """Apply the original SAS HUNDRED format."""
    return format_value('HUNDRED', value)


def THOUSAND(value):
    """Apply the original SAS THOUSAND format."""
    return format_value('THOUSAND', value)


def MILLION(value):
    """Apply the original SAS MILLION format."""
    return format_value('MILLION', value)


def LNPOGRP(value):
    """Apply the original SAS LNPOGRP format."""
    return format_value('LNPOGRP', value)


if __name__ == "__main__":
    library_cli(FORMATS, MACROS)
