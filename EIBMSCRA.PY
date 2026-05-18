#!/usr/bin/env python3
"""
Python conversion of mainframe SAS job EIBMSCRA.

This job keeps SAS include files separate. Put converted include modules under
./includes, for example includes/pbmisfmt.py and includes/pbbdpfmt.py.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


DEFAULT_BASE = Path("Data_Warehouse/MIS/XMIS")
DEFAULT_OUTPUT_DIR = DEFAULT_BASE / "output"


# SAS: %INC PGM(PBMISFMT,PBBDPFMT);
try:
    from includes import pbbdpfmt, pbmisfmt  # noqa: F401
except ImportError:
    pbbdpfmt = pbmisfmt = None


@dataclass(frozen=True)
class Branch:
    branch: int
    brchcd: str


@dataclass(frozen=True)
class HrBranch:
    staff: int
    branch: int
    brchcd: str


@dataclass(frozen=True)
class HrHo:
    staff: int
    hoe: str


@dataclass
class SrsRecord:
    staff: int
    product: str
    ncore: str
    branch: int = 0
    brchcd: str = ""
    hoe: str = ""
    tag: str = ""
    acctno: int | None = None
    aanum: str = ""
    c1cnt: int = 0
    c2cnt: int = 0
    c3cnt: int = 0
    c1bal: float = 0.0
    c2bal: float = 0.0
    c3bal: float = 0.0


@dataclass
class Summary:
    values: dict[str, object]
    sums: dict[str, float] = field(default_factory=lambda: defaultdict(float))


def parse_sas_number(raw: str, implied_decimals: int = 0) -> float:
    value = raw.strip()
    if not value:
        return 0.0
    if "." in value:
        return float(value)
    return int(value) / (10**implied_decimals)


def parse_int(raw: str) -> int:
    return int(parse_sas_number(raw))


def resolve_input_path(path: Path) -> Path:
    path_variants = [path]
    if path.suffix.lower() != ".txt":
        path_variants.append(path.with_name(f"{path.name}.txt"))

    if path.is_absolute():
        for variant in path_variants:
            if variant.exists():
                return variant
        return path

    candidates = [
        base / variant
