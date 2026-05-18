"""Converted SAS include: PBMISFMT.

MIS lookup formats used by the converted jobs. Keep this module separate from
main job scripts so it can be shared by multiple conversions.
"""

from __future__ import annotations

from typing import Any


def lookup(code: int | str, mapping: dict[Any, Any], default: Any = None) -> Any:
    return mapping.get(code, default)


STATECD = {
    1: "W", 2: "W", 3: "W", 4: "M", 5: "A", 6: "P", 7: "J", 8: "C",
    9: "A", 10: "K", 11: "K", 12: "D", 13: "D", 14: "D", 15: "W",
    16: "N", 17: "N", 18: "B", 19: "B", 20: "B", 21: "J", 22: "B",
    23: "A", 24: "N", 25: "B", 26: "W", 27: "P", 28: "J", 29: "W",
    30: "T", 31: "B", 32: "Q", 33: "S", 34: "R", 35: "B", 36: "B",
    37: "J", 38: "W", 39: "N", 40: "W", 41: "W", 42: "P", 43: "B",
    44: "S", 45: "N", 46: "B", 47: "J", 48: "C", 49: "A", 50: "Q",
    51: "A", 52: "J", 53: "W", 54: "P", 55: "L", 56: "B", 57: "K",
    58: "Q", 59: "J", 60: "P", 61: "J", 62: "S", 63: "N", 64: "N",
    65: "N", 66: "W", 67: "A", 68: "P", 69: "B", 70: "K", 71: "C",
    72: "S", 73: "B", 74: "K", 75: "J", 76: "A", 77: "K", 78: "B",
    79: "J", 80: "A", 81: "B", 82: "D", 83: "W", 84: "D", 85: "A",
    86: "K", 87: "J", 88: "K", 89: "J", 90: "Q", 91: "J", 92: "B",
    93: "J", 94: "W", 95: "A", 96: "B", 97: "W", 98: "J",
    102: "J", 103: "W", 104: "K", 105: "J", 106: "T", 107: "P",
    108: "A", 109: "B", 110: "J", 111: "M", 112: "S", 113: "C",
    114: "P", 115: "S", 116: "C", 117: "D", 118: "B", 119: "A",
    120: "B", 121: "P", 122: "B", 123: "A", 124: "B", 125: "B",
    126: "P", 127: "B", 128: "W", 129: "W", 130: "Q", 131: "B",
    133: "B", 134: "D", 135: "B", 136: "W", 137: "A", 138: "W",
    139: "C", 140: "S", 141: "W", 142: "S", 143: "S", 144: "J",
    145: "B", 146: "A", 147: "J", 148: "B", 149: "S", 150: "P",
    151: "W", 152: "A", 153: "B", 154: "P", 155: "B", 156: "M",
    157: "B", 158: "A", 159: "P", 160: "M", 161: "S", 162: "B",
    163: "W", 164: "P", 165: "M", 166: "J", 167: "B", 168: "W",
    169: "W", 170: "B", 171: "P", 172: "M", 173: "B", 174: "J",
    175: "Q", 176: "J", 177: "P", 178: "W", 179: "W", 180: "B",
    183: "Q", 184: "Q", 185: "Q", 186: "Q", 188: "Q", 189: "Q",
    190: "Q", 191: "Q", 192: "Q", 193: "Q", 194: "Q", 195: "W",
    196: "W", 197: "W", 198: "W", 199: "B", 201: "B", 202: "B",
    203: "B", 204: "P", 205: "P", 206: "P", 207: "A", 208: "A",
    209: "A", 210: "A", 211: "A", 214: "J", 215: "J", 216: "J",
    217: "J", 220: "C", 221: "B", 222: "J", 224: "J", 225: "B",
    226: "W", 227: "B", 228: "S", 230: "W", 231: "M", 232: "W",
    233: "C", 234: "J", 235: "B", 237: "C", 238: "K", 239: "C",
    240: "B", 241: "B", 242: "J", 243: "A", 244: "A", 245: "A",
    246: "A", 247: "J", 248: "W", 249: "A", 250: "B", 251: "A",
    252: "B", 253: "P", 254: "N", 256: "A", 257: "C", 258: "K",
    259: "Q", 260: "T", 261: "D", 262: "W", 263: "C", 264: "C",
    265: "P", 266: "P", 267: "W", 268: "B", 269: "W", 270: "B",
    273: "Q", 274: "Q", 275: "Q", 276: "S", 277: "D", 278: "S",
    279: "W", 280: "B", 281: "Q", 282: "S", 283: "S", 284: "W",
    285: "B", 286: "J", 287: "J", 288: "W", 289: "B", 290: "J",
    291: "B", 292: "W", 293: "B", 294: "B", 295: "B", 296: "W",
    701: "W", 702: "W", 703: "D", 704: "K", 800: "N", 801: "P",
    802: "W", 803: "S", 804: "J", 805: "J", 806: "K", 807: "M",
    808: "P", 809: "A", 811: "W", 812: "W", 813: "Q", 814: "B",
    815: "B", 816: "B", 817: "P", 818: "W", 819: "C", 820: "B",
    821: "W", 822: "W", 823: "A", 824: "K", 825: "B", 826: "P",
    827: "D",
}


def statecd(branch: int) -> str:
    return lookup(branch, STATECD, "B")


BRANCHCD = {
    1: "HEAD OFFICE", 2: "JLN SULTAN SULAIMAN", 3: "JLN RAJA CHULAN",
    4: "MELAKA", 5: "IPOH MAIN OFFICE", 6: "PENANG", 7: "JOHOR BAHRU",
    8: "KUANTAN", 9: "JLN YANG KALSOM", 10: "ALOR SETAR", 11: "GURUN",
    12: "PASIR PUTEH", 13: "KOTA BHARU", 14: "TANAH MERAH", 15: "KEPUNG",
    16: "NILAI", 17: "TAMPIN", 18: "PJ NEW TOWN", 19: "DAMANSARA UTAMA",
    20: "TMN CHI LIUNG", 21: "BATU PAHAT", 22: "SEMENYIH", 23: "KAMUNTING",
    24: "RASAH", 25: "SHAH ALAM", 26: "SERI PETALING", 27: "NIBONG TEBAL",
    28: "MUAR", 29: "JLN RAJA LAUT", 30: "KUALA TRENGGANU",
    31: "SEKINCHAN", 32: "WISMA SABERKAS (WSS)", 33: "KOTA KINABALU",
    34: "KANGAR", 35: "SERI SETIA", 36: "S S 2", 37: "TMN SENTOSA",
    38: "JLN KELANG LAMA", 39: "KUALA KELAWANG", 40: "JLN SUNGEI BESI",
    41: "JLN IPOH", 42: "BKT MERTAJAM", 43: "BANTING", 44: "TAWAU",
    45: "SEREMBAN", 46: "AMPANG", 47: "SEGAMAT", 48: "MENTAKAB",
    49: "JELAPANG", 50: "MIRI", 51: "SERI MANJUNG", 52: "ULU TIRAM",
    53: "TMN MALURI", 54: "BDR BAYAN BARU", 55: "LABUAN", 56: "KAJANG",
    57: "SG PETANI", 58: "SIBU", 59: "PONTIAN KECIL", 60: "BAGAN AJAM",
    61: "KULAI", 62: "SANDAKAN", 63: "GEMAS", 64: "PORT DICKSON",
    65: "BAHAU", 66: "BKT DAMANSARA", 67: "CHEMOR", 68: "SIMPANG AMPAT",
    69: "BATANG KALI", 70: "POKOK SENA", 71: "BRINCHANG", 72: "PAPAR",
    73: "SG PELEK", 74: "SIK", 75: "CHAAH", 76: "PANTAI REMIS",
    77: "PULAU LANGKAWI", 78: "SUBANG JAYA", 79: "MASAI", 80: "MENGLEMBU",
    81: "SG BULOH", 82: "MACHANG", 83: "JLN BUKIT BINTANG", 84: "PASIR MAS",
    85: "SG SIPUT", 86: "CHANGLUN", 87: "MERSING", 88: "KULIM",
    89: "TAMPOI", 90: "BINTULU", 91: "KLUANG", 92: "KLANG", 93: "ENDAU",
    94: "SETAPAK", 95: "TELUK INTAN", 96: "SERI GOMBAK",
    97: "JLN TUN H S LEE", 98: "TMN CENTURY", 101: "KAMPONG BAHRU",
